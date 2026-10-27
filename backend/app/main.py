"""HTTP API. Read-only for clients: nothing here fetches news or calls the AI.

GET  /health
GET  /stories            story list (newest first)
GET  /stories/{id}       full story detail
GET  /status             collection-run log (evidence of the hourly schedule)
POST /admin/collect      protected manual collection (X-Admin-Token header)
"""
from __future__ import annotations

import hmac
import logging
import threading
from datetime import timedelta
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .ingest.sources import publishers as publisher_names
from .models import Article, CollectionRun, Story, StoryBackground, Summary
from .pipeline import cutoff, run_collection
from .timeutil import as_utc, iso, utcnow

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="My News API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

SCOPE_NOTE = (
    "Input scope: headlines and short feed excerpts only, not full articles. "
    "Read the original coverage for full context."
)
STATUS_MESSAGES = {
    "ready": "",
    "outdated": "Newer coverage has arrived since this analysis was generated. It will be updated by the next hourly run.",
    "pending": "AI analysis has not been generated yet. It is created by the server's hourly AI worker, not by your device.",
    "failed": "AI analysis is currently unavailable because the AI service failed. Original coverage is still available below.",
    "not_generated": "AI analysis is not generated for this story.",
}


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _last_success(session: Session):
    return session.scalar(
        select(func.max(CollectionRun.finished_at)).where(
            CollectionRun.status.in_(["success", "partial"]), CollectionRun.trigger != "ai"
        )
    )


def _run_brief(run: Optional[CollectionRun]) -> Optional[dict]:
    if run is None:
        return None
    return {
        "id": run.id,
        "trigger": run.trigger,
        "started_at": iso(run.started_at),
        "finished_at": iso(run.finished_at),
        "status": run.status,
        "feeds_ok": run.feeds_ok,
        "feeds_failed": run.feeds_failed,
        "articles_seen": run.articles_seen,
        "articles_new": run.articles_new,
        "articles_updated": run.articles_updated,
        "articles_skipped": run.articles_skipped,
        "articles_expired": run.articles_expired,
        "stories_created": run.stories_created,
        "stories_removed": run.stories_removed,
        "summaries_generated": run.summaries_generated,
        "summaries_failed": run.summaries_failed,
        "background_links": run.background_links,
        "errors": run.errors or [],
    }


def _active_articles_by_story(session: Session, now) -> Dict[str, List[Article]]:
    # Exclude expired articles at read time, even if the hourly cleanup has not run yet.
    rows = session.scalars(
        select(Article).where(Article.published_at >= cutoff(now), Article.story_id.is_not(None))
    ).all()
    grouped: Dict[str, List[Article]] = {}
    for a in rows:
        grouped.setdefault(a.story_id, []).append(a)
    return grouped


def _summary_state(summary: Optional[Summary], articles: List[Article]):
    """Return (status, content) that is safe to show for the current article set."""
    if summary is None:
        publishers = {a.publisher for a in articles}
        return ("pending" if len(publishers) >= settings.ai_min_publishers else "not_generated"), None
    active_ids = {a.id for a in articles}
    status = summary.status
    content = summary.content
    if content is not None and not set(summary.input_article_ids or []) <= active_ids:
        # An input article expired since generation: never serve that text.
        return "pending", None
    if status == "ready" and set(summary.input_article_ids or []) != active_ids:
        status = "outdated"
    if status in ("failed", "pending"):
        content = None
    return status, content


@app.get("/health")
def health():
    return {"ok": True, "time": iso(utcnow())}


@app.get("/stories")
def list_stories(
    publisher: Optional[str] = Query(None, description="Only stories covered by this publisher"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Only stories updated within N hours"),
    multi_source: bool = Query(False, description="Only stories with 2+ publishers"),
    session: Session = Depends(get_session),
):
    now = utcnow()
    grouped = _active_articles_by_story(session, now)
    stories = session.scalars(select(Story).where(Story.id.in_(list(grouped)))).all() if grouped else []
    summaries = {s.story_id: s for s in session.scalars(select(Summary).where(Summary.story_id.in_(list(grouped)))).all()} if grouped else {}
    has_bg = set(session.scalars(select(StoryBackground.story_id).distinct()).all())
    items = []
    for story in stories:
        articles = grouped[story.id]
        pubs = sorted({a.publisher for a in articles})
        latest = max(as_utc(a.published_at) for a in articles)
        if publisher and publisher not in pubs:
            continue
        if multi_source and len(pubs) < 2:
            continue
        if hours and latest < now - timedelta(hours=hours):
            continue
        status, _ = _summary_state(summaries.get(story.id), articles)
        items.append(
            {
                "id": story.id,
                "headline": story.headline,
                "latest_published_at": iso(latest),
                "updated_at": iso(story.updated_at),
                "publisher_count": len(pubs),
                "publishers": pubs,
                "article_count": len(articles),
                # Lets an offline client drop expired articles and recount publishers.
                "article_dates": sorted(
                    ({"publisher": a.publisher, "published_at": iso(a.published_at)} for a in articles),
                    key=lambda d: d["published_at"],
                ),
                "summary_status": status,
                "has_background": story.id in has_bg,
            }
        )
    items.sort(key=lambda s: (s["latest_published_at"], s["id"]), reverse=True)
    last_run = session.scalars(select(CollectionRun).order_by(CollectionRun.id.desc()).limit(1)).first()
    return {
        "server_time": iso(now),
        "window_hours": settings.retention_hours,
        "ordering": "newest_first",
        "last_successful_collection_at": iso(_last_success(session)),
        "last_run": _run_brief(last_run),
        "publishers": publisher_names(),
        "count": len(items),
        "stories": items,
    }


@app.get("/stories/{story_id}")
def story_detail(story_id: str, session: Session = Depends(get_session)):
    now = utcnow()
    story = session.get(Story, story_id)
    articles = []
    if story is not None:
        articles = sorted(
            (a for a in story.articles if as_utc(a.published_at) >= cutoff(now)),
            key=lambda a: (as_utc(a.published_at), a.id),
        )
    if not articles:
        raise HTTPException(status_code=404, detail="Story not found or expired")

    article_json = [
        {
            "id": a.id,
            "publisher": a.publisher,
            "title": a.title,
            "url": a.url,
            "published_at": iso(a.published_at),
            "excerpt": a.excerpt or "",
            "excerpt_kind": "publisher_feed_excerpt",
        }
        for a in articles
    ]
    publishers: Dict[str, List[dict]] = {}
    for item in article_json:
        publishers.setdefault(item["publisher"], []).append(item)

    background = [
        {
            "title": link.resource.title,
            "url": link.resource.url,
            "description": link.resource.description,
            "source": link.resource.source,
            "matched_term": link.matched_term,
        }
        for link in sorted(story.background_links, key=lambda l: l.rank)
    ]

    status, content = _summary_state(story.summary, articles)
    s = story.summary
    summary = {
        "status": status,
        "status_message": STATUS_MESSAGES.get(status, ""),
        "label": "AI-generated",
        "generated_at": iso(s.generated_at) if s and content else None,
        "provider": s.provider if s and content else None,
        "model": s.model if s and content else None,
        "prompt_version": s.prompt_version if s and content else None,
        "version": s.version if s else 0,
        "input_scope": "feed_excerpts",
        "input_scope_note": SCOPE_NOTE,
        "input_article_ids": (s.input_article_ids if s and content else []),
        "content": content,
    }

    return {
        "server_time": iso(now),
        "id": story.id,
        "headline": story.headline,
        "created_at": iso(story.created_at),
        "updated_at": iso(story.updated_at),
        "latest_published_at": article_json[-1]["published_at"],
        "publisher_count": len(publishers),
        "publishers": [
            {"name": name, "articles": sorted(items, key=lambda i: i["published_at"], reverse=True)}
            for name, items in sorted(publishers.items())
        ],
        "articles": article_json,
        "background": background,
        "background_status": "available" if background else "none",
        "background_message": "" if background else "No background resource available",
        "summary": summary,
        "last_successful_collection_at": iso(_last_success(session)),
    }


def _ai_status(session: Session) -> dict:
    """What actually produces AI text, from stored data rather than unused defaults."""
    latest = session.scalars(
        select(Summary).where(Summary.generated_at.is_not(None)).order_by(Summary.generated_at.desc()).limit(1)
    ).first()
    last_ai_run = session.scalars(
        select(CollectionRun).where(CollectionRun.trigger == "ai").order_by(CollectionRun.id.desc()).limit(1)
    ).first()
    return {
        # "none" = this API server never calls a model; summaries come from the AI worker.
        "provider_on_this_server": settings.ai_provider,
        "configured_model": settings.ai_model if settings.ai_provider != "none" else None,
        "latest_summary_provider": latest.provider if latest else None,
        "latest_summary_model": latest.model if latest else None,
        "latest_summary_generated_at": iso(latest.generated_at) if latest else None,
        "last_ai_worker_run": _run_brief(last_ai_run),
    }


@app.get("/status")
def status(limit: int = Query(30, ge=1, le=200), session: Session = Depends(get_session)):
    runs = session.scalars(select(CollectionRun).order_by(CollectionRun.id.desc()).limit(limit)).all()
    now = utcnow()
    return {
        "server_time": iso(now),
        "schedule": "hourly at minute 0 UTC: cron-job.org calls POST /admin/collect?trigger=scheduled",
        "last_successful_collection_at": iso(_last_success(session)),
        "active_articles": session.scalar(select(func.count(Article.id)).where(Article.published_at >= cutoff(now))),
        "active_stories": session.scalar(select(func.count(func.distinct(Article.story_id))).where(Article.published_at >= cutoff(now))),
        "ready_summaries": session.scalar(select(func.count(Summary.story_id)).where(Summary.status == "ready")),
        "total_ai_generations_logged": session.scalar(select(func.coalesce(func.sum(CollectionRun.summaries_generated), 0))),
        "ai": _ai_status(session),
        "runs": [_run_brief(r) for r in runs],
    }


def _check_admin(token: Optional[str]) -> None:
    if not settings.admin_token or not token or not hmac.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Admin token required")


@app.post("/admin/collect", status_code=202)
def admin_collect(
    x_admin_token: Optional[str] = Header(None),
    trigger: str = Query("manual", pattern="^(manual|scheduled)$",
                         description="'scheduled' when called by the hourly external scheduler (cron-job.org)"),
    session: Session = Depends(get_session),
):
    _check_admin(x_admin_token)
    recent = session.scalars(
        select(CollectionRun).where(
            CollectionRun.status == "running",
            CollectionRun.trigger != "ai",
            CollectionRun.started_at >= utcnow() - timedelta(minutes=30),
        )
    ).first()
    if recent:
        raise HTTPException(status_code=409, detail=f"Collection run {recent.id} is already running")
    threading.Thread(target=run_collection, kwargs={"trigger": trigger}, daemon=True).start()
    return {"started": True, "trigger": trigger,
            "message": "Collection started; check GET /status for the result."}
