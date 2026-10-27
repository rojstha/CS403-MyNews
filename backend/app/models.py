"""Database tables.

article ──many-to-one──> story ──one-to-one──> summary
                          │
                          └──many-to-many (story_background)──> background_resource
collection_run: one row per hourly/manual job (operational log, no article text).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .timeutil import utcnow

UTCDateTime = DateTime(timezone=True)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    headline: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    # Changes whenever the set of articles in the story changes.
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    # Article-set signature used to decide when background must be refreshed.
    background_signature: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    background_checked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    articles: Mapped[List["Article"]] = relationship(back_populates="story")
    summary: Mapped[Optional["Summary"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", uselist=False
    )
    background_links: Mapped[List["StoryBackground"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )


class Article(Base):
    __tablename__ = "articles"

    # sha1(normalized_url)[:20] — stable across re-fetches.
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    normalized_url: Mapped[str] = mapped_column(Text, unique=True)
    url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(80), index=True)
    feed_url: Mapped[str] = mapped_column(Text)
    guid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text)
    # Publisher-provided feed description/summary, stored verbatim (HTML stripped).
    excerpt: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    is_fixture: Mapped[int] = mapped_column(Integer, default=0)

    story_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    story: Mapped[Optional[Story]] = relationship(back_populates="articles")


class Summary(Base):
    """The single current AI analysis for a story, reused by every client."""

    __tablename__ = "summaries"

    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    # ready | failed | pending | outdated
    status: Mapped[str] = mapped_column(String(20), default="pending")
    input_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Fingerprint of the inputs we last *attempted*, so a failing story is not retried every read.
    attempted_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_article_ids: Mapped[list] = mapped_column(JSON, default=list)
    input_scope: Mapped[str] = mapped_column(String(40), default="feed_excerpts")
    provider: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    generated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)  # +1 per successful generation
    content: Mapped[Optional[dict]] = mapped_column(JSON(none_as_null=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    story: Mapped[Story] = relationship(back_populates="summary")


class BackgroundResource(Base):
    __tablename__ = "background_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="Wikipedia")
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    story_links: Mapped[List["StoryBackground"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class StoryBackground(Base):
    __tablename__ = "story_background"
    __table_args__ = (UniqueConstraint("story_id", "resource_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("background_resources.id", ondelete="CASCADE"), index=True
    )
    # The story term that led to this resource (explains why it was chosen).
    matched_term: Mapped[str] = mapped_column(Text, default="")
    rank: Mapped[int] = mapped_column(Integer, default=0)

    story: Mapped[Story] = relationship(back_populates="background_links")
    resource: Mapped[BackgroundResource] = relationship(back_populates="story_links")


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(20))  # scheduled | manual | test
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    # running | success | partial | failed
    status: Mapped[str] = mapped_column(String(20), default="running")
    feeds_ok: Mapped[int] = mapped_column(Integer, default=0)
    feeds_failed: Mapped[int] = mapped_column(Integer, default=0)
    articles_seen: Mapped[int] = mapped_column(Integer, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, default=0)
    articles_updated: Mapped[int] = mapped_column(Integer, default=0)
    articles_skipped: Mapped[int] = mapped_column(Integer, default=0)
    articles_expired: Mapped[int] = mapped_column(Integer, default=0)
    stories_created: Mapped[int] = mapped_column(Integer, default=0)
    stories_removed: Mapped[int] = mapped_column(Integer, default=0)
    summaries_generated: Mapped[int] = mapped_column(Integer, default=0)
    summaries_failed: Mapped[int] = mapped_column(Integer, default=0)
    background_links: Mapped[int] = mapped_column(Integer, default=0)
    # [{"stage": "feed", "source": "BBC", "error": "..."}] — never article text.
    errors: Mapped[list] = mapped_column(JSON, default=list)
    feed_results: Mapped[list] = mapped_column(JSON, default=list)
