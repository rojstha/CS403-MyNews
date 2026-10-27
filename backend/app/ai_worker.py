"""Entry point for the AI worker: `python -m app.ai_worker`.

Runs on a machine with Ollama (the developer's Mac, scheduled hourly by launchd).
It reads stories from the shared database, generates summaries for stories whose
inputs changed, and writes them back. It never fetches news; the cloud collector
does that.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import timedelta

from sqlalchemy import select

from .db import SessionLocal
from .models import CollectionRun
from .pipeline import run_ai
from .timeutil import as_utc, utcnow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SessionLocal() as session:
        busy = session.scalars(
            select(CollectionRun).where(
                CollectionRun.trigger == "ai",
                CollectionRun.status == "running",
                CollectionRun.started_at >= utcnow() - timedelta(minutes=50),
            )
        ).first()
    if busy:
        print(json.dumps({"skipped": True, "reason": f"AI run {busy.id} still running"}))
        return 0
    run_id = run_ai()
    with SessionLocal() as session:
        run = session.get(CollectionRun, run_id)
        print(json.dumps({
            "run_id": run.id, "status": run.status,
            "summaries_generated": run.summaries_generated, "summaries_failed": run.summaries_failed,
            "seconds": round((as_utc(run.finished_at) - as_utc(run.started_at)).total_seconds(), 1) if run.finished_at else None,
            "errors": [e.get("error") for e in (run.errors or [])][:5],
        }))
    return 1 if run.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
