"""End-to-end pipeline checks (PDF section 10) with fake feeds, fake AI, fake Wikipedia."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.ai.provider import FakeProvider
from app.ingest.parse import normalize_url, parse_feed
from app.models import Article, BackgroundResource, CollectionRun, Story, StoryBackground, Summary
from tests.conftest import hours_ago, item, rss
from tests.fixtures.events import GROUPS


def _load_group(web, now, key, url_suffix=""):
    out = []
    for pub, title, excerpt, h in GROUPS[key]:
        it = item(pub, title, excerpt, hours_ago(now, h))
        if url_suffix:
            it["url"] += url_suffix
        out.append(web.add(it))
    return out


def _count(db, model):
    with db() as s:
        return s.scalar(select(func.count()).select_from(model))


# ------------------------------------------------------------- repeated ingestion


def test_repeated_ingestion_does_not_duplicate(db, web, collect, now):
    for key in GROUPS:
        _load_group(web, now, key)
    collect(now)
    articles, stories = _count(db, Article), _count(db, Story)
    collect(now + timedelta(minutes=60))
    assert _count(db, Article) == articles
    assert _count(db, Story) == stories
    with db() as s:
        runs = s.scalars(select(CollectionRun).order_by(CollectionRun.id)).all()
        assert runs[1].articles_new == 0 and runs[1].stories_created == 0


def test_tracking_parameters_do_not_create_duplicates(db, web, collect, now):
    it = web.add(item("BBC News", "Two charged over RAF Fairford plot", "Two men charged.", hours_ago(now, 2),
                      url="https://www.bbc.co.uk/news/articles/abc?at_medium=RSS&at_campaign=rss"))
    collect(now)
    it["url"] = "https://bbc.co.uk/news/articles/abc/"
    collect(now + timedelta(hours=1))
    assert _count(db, Article) == 1
    assert normalize_url("https://www.bbc.co.uk/x?utm_source=a") == normalize_url("http://bbc.co.uk/x/")


# ------------------------------------------------------------- grouping in the pipeline


def test_same_event_from_publishers_is_one_story_with_correct_sources(client, web, collect, now):
    _load_group(web, now, "comey_charged")
    collect(now)
    stories = client.get("/stories").json()["stories"]
    assert len(stories) == 1
    assert stories[0]["publisher_count"] == 3
    detail = client.get(f"/stories/{stories[0]['id']}").json()
    names = [p["name"] for p in detail["publishers"]]
    assert names == ["BBC News", "NPR", "The Guardian"]
    for p in detail["publishers"]:
        for a in p["articles"]:
            assert a["publisher"] == p["name"] and a["url"].startswith("https://")


# ------------------------------------------------------------- seven-day window


def test_seven_day_boundary(client, db, web, collect, now):
    web.add(item("NPR", "Old flood story in Spain", "Floods hit Valencia.", hours_ago(now, 167)))
    web.add(item("BBC News", "Museum opens exhibit on river trade", "A small museum opened.", hours_ago(now, 1)))
    web.add(item("Fox News", "Way too old story", "Ancient.", hours_ago(now, 200)))
    collect(now)
    assert _count(db, Article) == 2  # 200 h article never stored

    # Two hours later the 167 h article is 169 h old: API hides it even before the next run.
    later = now + timedelta(hours=2)
    from app import main as main_module
    real = main_module.utcnow
    main_module.utcnow = lambda: later
    try:
        titles = [s["headline"] for s in client.get("/stories").json()["stories"]]
    finally:
        main_module.utcnow = real
    assert titles == ["Museum opens exhibit on river trade"]

    # The next run physically deletes it, and its story.
    web.items["NPR"].clear()
    collect(later)
    assert _count(db, Article) == 1
    assert _count(db, Story) == 1
    with db() as s:
        assert s.scalars(select(CollectionRun).order_by(CollectionRun.id.desc())).first().articles_expired == 1


def test_missing_and_future_dates_are_skipped(now):
    text = rss([
        item("NPR", "No date", "x", None),
        item("NPR", "From the future", "x", now + timedelta(days=2)),
        item("NPR", "Fine", "x", now - timedelta(hours=1)),
    ])
    articles, skipped = parse_feed(text, "NPR", "https://feeds.example/npr.xml", now)
    assert [a.title for a in articles] == ["Fine"]
    assert skipped == 2


# ------------------------------------------------------------- expiry inside a group


def test_source_expiration_inside_group_regenerates_summary(client, db, web, collect, now):
    ai = FakeProvider()
    pub, title, excerpt, _ = GROUPS["fairford_plot"][0]
    web.add(item(pub, title, excerpt, hours_ago(now, 166)))
    for pub, title, excerpt, h in GROUPS["fairford_plot"][1:]:
        web.add(item(pub, title, excerpt, hours_ago(now, 165)))
    collect(now, provider=ai)
    sid = client.get("/stories").json()["stories"][0]["id"]
    before = client.get(f"/stories/{sid}").json()
    assert before["publisher_count"] == 3 and before["summary"]["status"] == "ready"
    old_id = next(a["id"] for a in before["articles"] if a["publisher"] == "BBC News")

    later = now + timedelta(hours=3)  # BBC article is now 169 h old
    collect(later, provider=ai)
    from app import main as main_module
    real = main_module.utcnow
    main_module.utcnow = lambda: later
    try:
        after = client.get(f"/stories/{sid}").json()
    finally:
        main_module.utcnow = real
    assert [p["name"] for p in after["publishers"]] == ["Al Jazeera", "The Guardian"]
    assert after["summary"]["status"] == "ready"
    assert after["summary"]["version"] == 2
    assert old_id not in after["summary"]["input_article_ids"]
    assert len(ai.calls) == 2


def test_summary_citing_expired_article_is_never_served(client, db, web, collect, now):
    """Even if regeneration fails, text that depended on a removed article is withheld."""
    pub, title, excerpt, _ = GROUPS["fairford_plot"][0]
    web.add(item(pub, title, excerpt, hours_ago(now, 167)))
    for pub, title, excerpt, h in GROUPS["fairford_plot"][1:]:
        web.add(item(pub, title, excerpt, hours_ago(now, 160)))
    collect(now)
    stories = client.get("/stories").json()["stories"]
    assert len(stories) == 1
    sid = stories[0]["id"]
    later = now + timedelta(hours=2)
    collect(later, provider=FakeProvider(fail=True))
    with db() as s:
        summary = s.get(Summary, sid)
        assert summary.content is None and summary.status == "failed"


def test_empty_stories_and_unlinked_background_are_removed(db, web, collect, now):
    web.add(item("NPR", "Rare Valencia flood warning issued", "Valencia warning.", hours_ago(now, 167)))
    collect(now)
    assert _count(db, StoryBackground) >= 1 and _count(db, BackgroundResource) >= 1
    web.items["NPR"].clear()
    web.add(item("BBC News", "Short unrelated note", "nothing", hours_ago(now, 1)))
    collect(now + timedelta(hours=3), lookup=lambda terms: {})
    with db() as s:
        assert s.scalar(select(func.count()).select_from(Summary).where(Summary.story_id.not_in(select(Story.id)))) == 0
    assert _count(db, StoryBackground) == 0
    assert _count(db, BackgroundResource) == 0


# ------------------------------------------------------------- shared AI output


def test_shared_ai_output_is_reused(client, web, collect, now):
    ai = FakeProvider()
    _load_group(web, now, "jayz_superbowl")
    collect(now, provider=ai)
    assert len(ai.calls) == 1
    sid = client.get("/stories").json()["stories"][0]["id"]

    from fastapi.testclient import TestClient
    from app import main as main_module
    other_client = TestClient(main_module.app)
    reads = [c.get(f"/stories/{sid}").json()["summary"] for c in (client, other_client, client, other_client)]
    assert {(r["version"], r["generated_at"]) for r in reads} == {(1, reads[0]["generated_at"])}
    assert len(ai.calls) == 1  # reading never calls the model

    collect(now + timedelta(hours=1), provider=ai)  # unchanged inputs: no regeneration
    assert len(ai.calls) == 1


def test_new_coverage_triggers_regeneration(client, web, collect, now):
    ai = FakeProvider()
    items = GROUPS["machado_return"]
    web.add(item(*items[0][:3], hours_ago(now, items[0][3])))
    web.add(item(*items[1][:3], hours_ago(now, items[1][3])))
    collect(now, provider=ai)
    web.add(item(*items[2][:3], hours_ago(now, items[2][3])))
    collect(now + timedelta(hours=1), provider=ai)
    assert len(ai.calls) == 2
    story = client.get("/stories").json()["stories"][0]
    assert story["publisher_count"] == 3


# ------------------------------------------------------------- failures


def test_feed_outage_keeps_valid_stories(client, db, web, collect, now):
    _load_group(web, now, "comey_charged")
    collect(now)
    web.down.add("NPR")
    run_id = collect(now + timedelta(hours=1))
    with db() as s:
        run = s.get(CollectionRun, run_id)
        assert run.status == "partial" and run.feeds_failed == 1 and run.feeds_ok == 2
        assert any(e["stage"] == "feed" for e in run.errors)
    data = client.get("/stories").json()
    assert data["stories"][0]["publisher_count"] == 3  # NPR article still within window
    assert data["last_successful_collection_at"] is not None


def test_all_feeds_down_marks_run_failed_but_serves_data(client, db, web, collect, now):
    _load_group(web, now, "comey_charged")
    collect(now)
    web.down.update(web.items.keys())
    run_id = collect(now + timedelta(hours=1))
    with db() as s:
        assert s.get(CollectionRun, run_id).status == "failed"
    assert client.get("/stories").json()["count"] == 1


def test_ai_failure_gives_honest_status(client, web, collect, now):
    _load_group(web, now, "brewers_rays")
    collect(now, provider=FakeProvider(fail=True))
    sid = client.get("/stories").json()["stories"][0]["id"]
    summary = client.get(f"/stories/{sid}").json()["summary"]
    assert summary["status"] == "failed"
    assert summary["content"] is None
    assert "unavailable" in summary["status_message"]


def test_ai_provider_missing_does_not_crash_run(db, web, collect, now):
    _load_group(web, now, "brewers_rays")

    def broken():
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    from app import pipeline
    run_id = pipeline.run_collection("test", session_factory=db, fetcher=web.fetch, feeds=web.feeds(),
                                     provider_factory=broken, background_lookup=lambda t: {}, now=now)
    with db() as s:
        run = s.get(CollectionRun, run_id)
        assert run.status == "partial" and run.summaries_failed == 1
        assert _count(db, Article) == 2


def test_background_failure_keeps_stories(client, web, collect, now):
    _load_group(web, now, "fairford_plot")

    def down(terms):
        raise ConnectionError("Wikipedia unavailable")

    collect(now, lookup=down)
    sid = client.get("/stories").json()["stories"][0]["id"]
    detail = client.get(f"/stories/{sid}").json()
    assert detail["background_status"] == "none"
    assert detail["background_message"] == "No background resource available"
