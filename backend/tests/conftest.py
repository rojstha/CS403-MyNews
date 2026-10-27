from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Dict, List, Optional
from xml.sax.saxutils import escape

os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ["DATABASE_URL"] = "sqlite://"  # never touch a real database from tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app import pipeline
from app.ai.provider import FakeProvider
from app.background.wikipedia import Resource
from app.db import Base
from app.ingest.sources import Feed


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def item(publisher: str, title: str, excerpt: str, published: Optional[datetime], url: Optional[str] = None) -> dict:
    return {
        "publisher": publisher,
        "title": title,
        "excerpt": excerpt,
        "published": published,
        "url": url or f"https://{slug(publisher)}.example/{slug(title)}",
    }


def rss(items: List[dict]) -> str:
    parts = ['<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>']
    for it in items:
        date = f"<pubDate>{format_datetime(it['published'])}</pubDate>" if it["published"] else ""
        parts.append(
            f"<item><title>{escape(it['title'])}</title><link>{escape(it['url'])}</link>"
            f"<description>{escape(it['excerpt'])}</description>{date}</item>"
        )
    parts.append("</channel></rss>")
    return "".join(parts)


class FakeWeb:
    """Serves RSS per publisher; can simulate outages."""

    def __init__(self):
        self.items: Dict[str, List[dict]] = {}
        self.down: set = set()

    def add(self, it: dict) -> dict:
        self.items.setdefault(it["publisher"], []).append(it)
        return it

    def feeds(self) -> List[Feed]:
        return [Feed(p, f"https://feeds.example/{slug(p)}.xml") for p in self.items]

    def fetch(self, url: str) -> str:
        for p, its in self.items.items():
            if url == f"https://feeds.example/{slug(p)}.xml":
                if p in self.down:
                    raise ConnectionError(f"{p} feed unavailable (simulated)")
                return rss(its)
        raise ConnectionError("unknown feed")


def fake_lookup(terms):
    return {
        t: Resource(url=f"https://en.wikipedia.org/wiki/{t.replace(' ', '_')}", title=t, description=f"About {t}.", matched_term=t)
        for t in terms
    }


@pytest.fixture
def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def web():
    return FakeWeb()


@pytest.fixture
def ai():
    return FakeProvider()


@pytest.fixture
def collect(db, web, ai):
    """Run the real pipeline against fake feeds / fake AI / fake Wikipedia."""

    def _run(now: datetime, provider=None, lookup=fake_lookup, trigger="test"):
        prov = provider or ai
        return pipeline.run_collection(
            trigger,
            session_factory=db,
            fetcher=web.fetch,
            feeds=web.feeds(),
            provider_factory=lambda: prov,
            background_lookup=lookup,
            now=now,
        )

    return _run


@pytest.fixture
def client(db, monkeypatch):
    def _session():
        s = db()
        try:
            yield s
        finally:
            s.close()

    main_module.app.dependency_overrides[main_module.get_session] = _session
    yield TestClient(main_module.app)
    main_module.app.dependency_overrides.clear()


def hours_ago(now: datetime, h: float) -> datetime:
    return now - timedelta(hours=h)
