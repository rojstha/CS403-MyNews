"""Runtime configuration, read once from environment variables.

Secrets (database password, AI key, admin token) live ONLY in the server
environment. Nothing here is ever sent to the Flutter app.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./mynews.db")
    # Render/Neon/Heroku style URLs use postgres:// — SQLAlchemy needs a driver name.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_database_url)
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", ""))

    # Retention: rolling window based on article publication time.
    retention_hours: int = field(default_factory=lambda: int(os.getenv("RETENTION_HOURS", "168")))
    # Articles dated further than this into the future are treated as invalid dates.
    future_tolerance_minutes: int = 60

    feed_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("FEED_TIMEOUT_SECONDS", "15")))

    # AI summarisation (server side only). AI_PROVIDER: anthropic | ollama | none.
    # "none" = this process never runs AI (e.g. the cloud collector); summaries
    # are written by `python -m app.ai_worker` on a machine that runs Ollama.
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "anthropic"))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "claude-opus-5-5"))
    ai_effort: str = field(default_factory=lambda: os.getenv("AI_EFFORT", "medium"))
    ai_max_tokens: int = field(default_factory=lambda: int(os.getenv("AI_MAX_TOKENS", "8000")))
    ai_use_fallbacks: bool = field(default_factory=lambda: _bool("AI_USE_FALLBACKS", True))
    # Cost guard: maximum number of summaries (re)generated in one hourly run.
    ai_max_summaries_per_run: int = field(default_factory=lambda: int(os.getenv("AI_MAX_SUMMARIES_PER_RUN", "25")))
    # Only summarise stories with at least this many distinct publishers (1 = all stories).
    ai_min_publishers: int = field(default_factory=lambda: int(os.getenv("AI_MIN_PUBLISHERS", "1")))

    # Local open-source model served by Ollama (free; runs on the developer's Mac).
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_num_ctx: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "8192")))
    ollama_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")))
    # Hidden "thinking" made the 3B model spend its whole output budget before
    # answering, so it is off by default. Blank = do not send the option at all
    # (for models without a thinking mode).
    ollama_think: str = field(default_factory=lambda: os.getenv("OLLAMA_THINK", "false").strip().lower())
    # Hard cap on generated tokens so a looping model cannot run for minutes.
    ollama_num_predict: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_PREDICT", "2000")))

    background_enabled: bool = field(default_factory=lambda: _bool("BACKGROUND_ENABLED", True))
    background_max_per_run: int = field(default_factory=lambda: int(os.getenv("BACKGROUND_MAX_PER_RUN", "60")))

    # Wikimedia and some publishers require a descriptive User-Agent with contact info.
    contact_info: str = field(default_factory=lambda: os.getenv("CONTACT_INFO", "CS 403 student project"))

    @property
    def user_agent(self) -> str:
        return f"MyNewsCS403/1.0 ({self.contact_info})"


settings = Settings()
