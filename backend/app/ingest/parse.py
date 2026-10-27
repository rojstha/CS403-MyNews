"""Turn raw RSS/Atom text into normalized article records.

Ported from the starter's articleFromFeedItem()/plainParagraphs(), but run on
the server. Publication-date policy (documented in README):
  * missing or unparseable date  -> article skipped (counted as "skipped")
  * date more than 60 min in the future -> skipped (clock error / bad feed)
We never substitute download time, because retention must use publication time.
"""
from __future__ import annotations

import calendar
import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

TRACKING_PARAMS = {
    "at_medium", "at_campaign", "at_ptr_name", "at_link_origin", "at_bbc_team",
    "at_link_id", "at_link_type", "at_format", "at_custom1", "at_custom2",
    "at_custom3", "at_custom4", "cmpid", "ftag", "ns_mchannel", "ns_source",
    "ns_campaign", "ns_linkname", "ns_fee", "intcmp", "partner", "ref", "taid",
    "fbclid", "gclid", "mc_cid", "mc_eid",
}


@dataclass
class ParsedArticle:
    article_id: str
    normalized_url: str
    url: str
    guid: Optional[str]
    title: str
    excerpt: str
    published_at: datetime
    publisher: str
    feed_url: str


def normalize_url(url: str) -> str:
    """Canonical form used for duplicate detection."""
    parts = urlsplit(url.strip())
    scheme = "https"
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", parts.path) or "/"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    return urlunsplit((scheme, host, path, urlencode(sorted(query)), ""))


def article_id_for(normalized_url: str) -> str:
    return hashlib.sha1(normalized_url.encode("utf-8")).hexdigest()[:20]


_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_RE = re.compile(r"<(script|style|figure|iframe|picture)[^>]*>.*?</\1>", re.S | re.I)


def strip_html(text: str) -> str:
    text = _BLOCK_RE.sub(" ", text or "")
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def _entry_date(entry) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
            except (OverflowError, ValueError, TypeError):
                continue
    return None


def _entry_link(entry) -> str:
    link = entry.get("link") or ""
    if not link:
        for candidate in entry.get("links", []) or []:
            if candidate.get("href"):
                link = candidate["href"]
                break
    if not link and str(entry.get("id", "")).startswith("http"):
        link = entry["id"]
    return link.strip()


def parse_feed(
    text: str, publisher: str, feed_url: str, now: datetime, future_tolerance_minutes: int = 60
) -> Tuple[List[ParsedArticle], int]:
    """Return (articles, skipped_count). Raises ValueError if the feed is unreadable."""
    parsed = feedparser.parse(text)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"feed could not be parsed: {parsed.get('bozo_exception')}")

    articles: List[ParsedArticle] = []
    skipped = 0
    latest_allowed = now + timedelta(minutes=future_tolerance_minutes)
    for entry in parsed.entries:
        title = strip_html(entry.get("title", ""))
        link = _entry_link(entry)
        published = _entry_date(entry)
        if not title or not link or published is None or published > latest_allowed:
            skipped += 1
            continue
        raw_excerpt = entry.get("summary") or entry.get("description") or ""
        excerpt = strip_html(raw_excerpt)[:1500]
        normalized = normalize_url(link)
        articles.append(
            ParsedArticle(
                article_id=article_id_for(normalized),
                normalized_url=normalized,
                url=link,
                guid=entry.get("id"),
                title=title,
                excerpt=excerpt,
                published_at=published,
                publisher=publisher,
                feed_url=feed_url,
            )
        )
    return articles, skipped
