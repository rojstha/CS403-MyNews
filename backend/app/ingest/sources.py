"""News publishers and their public RSS feeds.

One publisher may have several feeds (sections); articles are de-duplicated by
normalized URL, so a story listed in both "world" and "latest" is stored once.
The first three publishers are the ones used by the course starter app.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Feed:
    publisher: str
    url: str


FEEDS: List[Feed] = [
    Feed("Fox News", "https://moxie.foxnews.com/google-publisher/latest.xml"),
    Feed("Fox News", "https://moxie.foxnews.com/google-publisher/world.xml"),
    Feed("Fox News", "https://moxie.foxnews.com/google-publisher/politics.xml"),
    Feed("NPR", "https://feeds.npr.org/1001/rss.xml"),
    Feed("NPR", "https://feeds.npr.org/1004/rss.xml"),
    Feed("NPR", "https://feeds.npr.org/1014/rss.xml"),
    Feed("BBC News", "https://feeds.bbci.co.uk/news/rss.xml"),
    Feed("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    Feed("The Guardian", "https://www.theguardian.com/world/rss"),
    Feed("The Guardian", "https://www.theguardian.com/us-news/rss"),
    Feed("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    Feed("CBS News", "https://www.cbsnews.com/latest/rss/main"),
    Feed("PBS NewsHour", "https://www.pbs.org/newshour/feeds/rss/headlines"),
]


def publishers() -> List[str]:
    seen: List[str] = []
    for feed in FEEDS:
        if feed.publisher not in seen:
            seen.append(feed.publisher)
    return seen
