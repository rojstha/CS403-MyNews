"""Entry point for the scheduler: `python -m app.worker [--trigger scheduled|manual]`.

Run hourly by an external scheduler, independent of the web API and of any app user.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import timedelta

from sqlalchemy import select

from .db import SessionLocal
from .models import CollectionRun
from .pipeline import run_collection
from .timeutil import utcnow


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one My News collection job.")
    parser.add_argument("--trigger", default="scheduled", choices=["scheduled", "manual"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SessionLocal() as session:
        # Skip if another run (e.g. a manual demo run) is still in progress. A run
        # that crashed without finishing stops blocking after 50 minutes.
        busy = session.scalars(
            select(CollectionRun).where(
                CollectionRun.status == "running",
                CollectionRun.started_at >= utcnow() - timedelta(minutes=50),
            )
        ).first()
    if busy:
        print(json.dumps({"skipped": True, "reason": f"run {busy.id} still running"}))
        return 0
    run_id = run_collection(trigger=args.trigger)
    with SessionLocal() as session:
        run = session.get(CollectionRun, run_id)
        summary = {
            "run_id": run.id, "status": run.status, "feeds_ok": run.feeds_ok, "feeds_failed": run.feeds_failed,
            "articles_new": run.articles_new, "articles_expired": run.articles_expired,
            "stories_created": run.stories_created, "stories_removed": run.stories_removed,
            "summaries_generated": run.summaries_generated, "summaries_failed": run.summaries_failed,
            "errors": len(run.errors or []),
        }
    print(json.dumps(summary))
    return 1 if summary["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
