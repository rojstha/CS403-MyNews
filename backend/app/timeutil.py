"""All backend timestamps are timezone-aware UTC."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso(value: Optional[datetime]) -> Optional[str]:
    value = as_utc(value)
    return value.isoformat().replace("+00:00", "Z") if value else None
