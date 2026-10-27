"""Download feeds. Each feed is isolated: one failure never stops the others."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

import httpx

from ..config import settings
from .parse import ParsedArticle, parse_feed
from .sources import FEEDS, Feed


@dataclass
class FeedResult:
    feed: Feed
    articles: List[ParsedArticle]
    skipped: int
    error: Optional[str] = None


# Signature: (url) -> feed text. Replaced in tests to simulate outages.
Fetcher = Callable[[str], str]


def http_fetcher(url: str) -> str:
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    with httpx.Client(timeout=settings.feed_timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def fetch_all(now: datetime, feeds: Optional[List[Feed]] = None, fetcher: Fetcher = http_fetcher) -> List[FeedResult]:
    results: List[FeedResult] = []
    for feed in feeds or FEEDS:
        try:
            text = fetcher(feed.url)
            articles, skipped = parse_feed(text, feed.publisher, feed.url, now, settings.future_tolerance_minutes)
            results.append(FeedResult(feed, articles, skipped))
        except Exception as exc:  # noqa: BLE001 — isolate every feed failure
            results.append(FeedResult(feed, [], 0, f"{type(exc).__name__}: {exc}"[:300]))
    return results
