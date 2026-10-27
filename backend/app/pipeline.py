"""The scheduled collection job.

Stages (each isolated so one failure cannot erase valid data):
  1. fetch every feed               -> per-feed success/failure recorded
  2. upsert articles                -> duplicate URLs update the existing row
  3. expire articles > 168 h old    -> by publication time
  4. group new articles into stories
  5. clean up empty stories, their summaries and background links,
     and background resources no longer linked to any story
  6. refresh background resources for new/changed stories
  7. (re)generate AI summaries whose input fingerprint changed
  8. write the collection_runs record
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .ai import summarize
from .ai.provider import AIError, Provider, get_provider
from .background.wikipedia import Lookup, find_background, wikipedia_lookup
from .config import settings
from .db import SessionLocal
from .grouping.grouper import Doc, assign_stories, choose_headline
from .ingest.fetch import Fetcher, fetch_all, http_fetcher
from .ingest.sources import Feed
from .models import Article, BackgroundResource, CollectionRun, Story, StoryBackground, Summary
from .timeutil import as_utc, utcnow

log = logging.getLogger("mynews.pipeline")


def cutoff(now: datetime) -> datetime:
    return now - timedelta(hours=settings.retention_hours)


def membership_signature(article_ids: List[str]) -> str:
    return hashlib.sha256("|".join(sorted(article_ids)).encode()).hexdigest()


# ---------------------------------------------------------------- stages


def upsert_articles(session: Session, results, now: datetime, run: CollectionRun) -> None:
    oldest = cutoff(now)
    seen_ids = set()
    for result in results:
        run.articles_skipped += result.skipped
        for parsed in result.articles:
            run.articles_seen += 1
            if parsed.article_id in seen_ids:
                continue  # same URL listed in two sections of one publisher
            seen_ids.add(parsed.article_id)
            if parsed.published_at < oldest:
                run.articles_skipped += 1
                continue
            existing = session.get(Article, parsed.article_id)
            if existing is None:
                session.add(
                    Article(
                        id=parsed.article_id,
                        normalized_url=parsed.normalized_url,
                        url=parsed.url,
                        publisher=parsed.publisher,
                        feed_url=parsed.feed_url,
                        guid=parsed.guid,
                        title=parsed.title,
                        excerpt=parsed.excerpt,
                        published_at=parsed.published_at,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                run.articles_new += 1
            else:
                changed = (
                    existing.title != parsed.title
                    or (existing.excerpt or "") != parsed.excerpt
                    or as_utc(existing.published_at) != parsed.published_at
                )
                existing.last_seen_at = now
                if changed:
                    existing.title = parsed.title
                    existing.excerpt = parsed.excerpt
                    existing.published_at = parsed.published_at
                    run.articles_updated += 1
    session.flush()


def expire_articles(session: Session, now: datetime, run: CollectionRun) -> set:
    """Delete articles older than the window. Returns the story IDs that lost articles."""
    old = session.scalars(select(Article).where(Article.published_at < cutoff(now))).all()
    touched = {a.story_id for a in old if a.story_id}
    for article in old:
        session.delete(article)
    run.articles_expired += len(old)
    session.flush()
    return touched


def cleanup_orphans(session: Session, run: CollectionRun) -> None:
    has_articles = select(Article.story_id).where(Article.story_id.is_not(None)).distinct()
    empty = session.scalars(select(Story).where(Story.id.not_in(has_articles))).all()
    for story in empty:
        session.delete(story)  # cascades to summary and story_background rows
    run.stories_removed += len(empty)
    session.flush()
    linked = select(StoryBackground.resource_id).distinct()
    session.execute(delete(BackgroundResource).where(BackgroundResource.id.not_in(linked)))
    session.flush()


def group_articles(session: Session, now: datetime, run: CollectionRun, touched: set) -> None:
    articles = session.scalars(select(Article)).all()
    docs = [
        Doc(a.id, a.publisher, a.title, a.excerpt or "", as_utc(a.published_at), a.story_id) for a in articles
    ]
    assignments, _explanations = assign_stories(docs)
    by_id = {a.id: a for a in articles}
    existing_story_ids = set(session.scalars(select(Story.id)).all())
    for article_id, story_id in assignments.items():
        if story_id not in existing_story_ids:
            session.add(Story(id=story_id, headline="", created_at=now, updated_at=now))
            existing_story_ids.add(story_id)
            run.stories_created += 1
        by_id[article_id].story_id = story_id
        touched.add(story_id)
    session.flush()

    docs_by_story: Dict[str, List[Doc]] = {}
    for d in docs:
        docs_by_story.setdefault(d.story_id, []).append(d)
    for story_id in touched:
        story = session.get(Story, story_id)
        if story is None or story_id not in docs_by_story:
            continue
        story.headline = choose_headline(docs_by_story[story_id])
        story.updated_at = now
    session.flush()


def active_stories(session: Session) -> List[Story]:
    """Stories ordered by priority: more publishers first, then most recent."""
    rows = session.execute(
        select(
            Story,
            func.count(func.distinct(Article.publisher)).label("pubs"),
            func.max(Article.published_at).label("latest"),
        )
        .join(Article, Article.story_id == Story.id)
        .group_by(Story.id)
    ).all()
    rows.sort(key=lambda r: (-r.pubs, -(as_utc(r.latest).timestamp())))
    return [r.Story for r in rows]


def refresh_background(session: Session, now: datetime, run: CollectionRun, lookup: Lookup) -> None:
    done = 0
    for story in active_stories(session):
        if done >= settings.background_max_per_run:
            break
        articles = list(story.articles)
        signature = membership_signature([a.id for a in articles])
        if story.background_signature == signature:
            continue
        done += 1
        try:
            resources = find_background(articles, lookup)
        except Exception as exc:  # noqa: BLE001 — keep existing links on failure
            run.errors = run.errors + [{"stage": "background", "story": story.id, "error": str(exc)[:200]}]
            continue
        story.background_links.clear()
        session.flush()
        for rank, res in enumerate(resources):
            resource = session.scalar(select(BackgroundResource).where(BackgroundResource.url == res.url))
            if resource is None:
                resource = BackgroundResource(
                    url=res.url, title=res.title, description=res.description, source=res.source, fetched_at=now
                )
                session.add(resource)
                session.flush()
            session.add(StoryBackground(story_id=story.id, resource_id=resource.id, matched_term=res.matched_term, rank=rank))
            run.background_links += 1
        story.background_signature = signature
        story.background_checked_at = now
        session.flush()


def invalidate_dependent_summaries(session: Session) -> None:
    """Never keep summary text that cites an article that no longer exists."""
    active_ids = set(session.scalars(select(Article.id)).all())
    for summary in session.scalars(select(Summary).where(Summary.content.is_not(None))).all():
        if not set(summary.input_article_ids or []) <= active_ids:
            summary.content = None
            summary.status = "pending"
            summary.input_fingerprint = None
    session.flush()


def refresh_summaries(session: Session, now: datetime, run: CollectionRun, provider_factory: Callable[[], Provider]) -> None:
    provider: Optional[Provider] = None
    provider_error: Optional[str] = None
    generated = 0
    for story in active_stories(session):
        articles = list(story.articles)
        if len({a.publisher for a in articles}) < settings.ai_min_publishers:
            continue
        summary = story.summary
        if summary is None:
            summary = Summary(story_id=story.id, status="pending", input_article_ids=[], version=0)
            session.add(summary)
            session.flush()

        model = settings.ai_model
        fp = summarize.fingerprint(articles, model)
        if summary.input_fingerprint == fp and summary.status == "ready":
            continue  # unchanged inputs: reuse stored output, no AI call
        if generated >= settings.ai_max_summaries_per_run:
            if summary.status == "ready":
                summary.status = "outdated"  # new coverage arrived; old analysis is still valid for its inputs
            continue

        summary.last_attempt_at = now
        summary.attempted_fingerprint = fp
        generated += 1
        try:
            if provider is None and provider_error is None:
                try:
                    provider = provider_factory()
                except Exception as exc:  # noqa: BLE001
                    provider_error = str(exc)
            if provider is None:
                raise AIError(provider_error or "AI provider unavailable")
            raw, served_by = provider.generate(
                summarize.system_prompt(), summarize.build_user_message(articles), summarize.OUTPUT_SCHEMA
            )
            content = summarize.validate_output(raw, articles)
            summary.content = content
            summary.status = "ready"
            summary.input_fingerprint = fp
            summary.input_article_ids = [a.id for a in articles]
            summary.input_scope = "feed_excerpts"
            summary.provider = provider.name
            summary.model = served_by
            summary.prompt_version = summarize.PROMPT_VERSION
            summary.generated_at = now
            summary.version = (summary.version or 0) + 1
            summary.error = None
            run.summaries_generated += 1
        except Exception as exc:  # noqa: BLE001 — record honestly, never fabricate
            run.summaries_failed += 1
            summary.error = str(exc)[:300]
            active_ids = {a.id for a in articles}
            if summary.content and set(summary.input_article_ids or []) <= active_ids:
                summary.status = "outdated"  # older analysis, still only cites existing articles
            else:
                summary.content = None
                summary.status = "failed"
            if len(run.errors) < 50:
                run.errors = run.errors + [{"stage": "ai", "story": story.id, "error": str(exc)[:200]}]
        session.flush()


# ---------------------------------------------------------------- entry point


def run_collection(
    trigger: str = "scheduled",
    *,
    session_factory: sessionmaker = SessionLocal,
    fetcher: Fetcher = http_fetcher,
    feeds: Optional[List[Feed]] = None,
    provider_factory: Callable[[], Provider] = get_provider,
    background_lookup: Lookup = wikipedia_lookup,
    now: Optional[datetime] = None,
) -> int:
    """Run one collection. Returns the collection_runs.id."""
    now = now or utcnow()
    with session_factory() as session:
        run = CollectionRun(trigger=trigger, started_at=now, status="running", errors=[], feed_results=[])
        session.add(run)
        session.commit()
        run_id = run.id

    session = session_factory()
    try:
        run = session.get(CollectionRun, run_id)
        results = fetch_all(now, feeds, fetcher)
        run.feed_results = [
            {"publisher": r.feed.publisher, "url": r.feed.url, "ok": r.error is None, "articles": len(r.articles), "skipped": r.skipped, "error": r.error}
            for r in results
        ]
        run.feeds_ok = sum(1 for r in results if r.error is None)
        run.feeds_failed = sum(1 for r in results if r.error is not None)
        run.errors = [{"stage": "feed", "source": r.feed.url, "error": r.error} for r in results if r.error]

        upsert_articles(session, results, now, run)
        touched = expire_articles(session, now, run)
        group_articles(session, now, run, touched)
        cleanup_orphans(session, run)
        invalidate_dependent_summaries(session)
        session.commit()  # articles and stories are safe even if later stages fail

        if settings.background_enabled:
            try:
                refresh_background(session, now, run, background_lookup)
                cleanup_orphans(session, run)
                session.commit()
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                run = session.get(CollectionRun, run_id)
                run.errors = run.errors + [{"stage": "background", "error": str(exc)[:200]}]

        refresh_summaries(session, now, run, provider_factory)
        session.commit()

        if run.feeds_ok == 0:
            run.status = "failed"
        elif run.errors:
            run.status = "partial"
        else:
            run.status = "success"
        run.finished_at = utcnow()
        session.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("collection run failed")
        session.rollback()
        run = session.get(CollectionRun, run_id)
        run.status = "failed"
        run.finished_at = utcnow()
        run.errors = (run.errors or []) + [{"stage": "pipeline", "error": f"{type(exc).__name__}: {exc}"[:300]}]
        session.commit()
    finally:
        session.close()
    return run_id
