"""Deployment configuration checks ($0 plan: Render free web + Neon + cron-job.org + Mac AI worker)."""
from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from app import config, db

ROOT = Path(__file__).resolve().parents[2]
yaml = pytest.importorskip("yaml")
BLUEPRINT = yaml.safe_load((ROOT / "render.yaml").read_text())
SECRETS = {"ANTHROPIC_API_KEY", "CONTACT_INFO", "ADMIN_TOKEN", "DATABASE_URL"}


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        (
            "postgresql://u:p@ep-x.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+psycopg://u:p@ep-x.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        ),
        ("sqlite:///./x.db", "sqlite:///./x.db"),
    ],
)
def test_database_url_gets_psycopg_driver(monkeypatch, given, expected):
    monkeypatch.setenv("DATABASE_URL", given)
    assert config._database_url() == expected


def test_postgres_engine_disables_server_side_prepared_statements(monkeypatch):
    captured = {}
    monkeypatch.setattr(db, "create_engine", lambda url, **kw: captured.update(kw))
    db.make_engine("postgresql+psycopg://u:p@localhost/db")
    assert captured["connect_args"] == {"prepare_threshold": None}
    assert captured["pool_pre_ping"] is True  # Neon suspends idle compute; reconnect safely


def test_blueprint_is_only_free_resources():
    assert "databases" not in BLUEPRINT
    assert [s["type"] for s in BLUEPRINT["services"]] == ["web"]
    for svc in BLUEPRINT["services"]:
        assert svc["plan"] == "free"


def test_api_migrates_and_never_runs_ai():
    svc = BLUEPRINT["services"][0]
    assert svc["startCommand"].startswith("alembic upgrade head && ")
    env = {e["key"]: e for e in svc["envVars"]}
    assert env["AI_PROVIDER"]["value"] == "none"
    assert env["DATABASE_URL"] == {"key": "DATABASE_URL", "sync": False}
    assert env["ADMIN_TOKEN"]["generateValue"] is True


def test_no_secret_values_in_blueprint():
    for svc in BLUEPRINT["services"]:
        for env in svc["envVars"]:
            if env.get("key") in SECRETS:
                assert "value" not in env, f"{env['key']} must not be written in render.yaml"


def test_launchd_job_runs_ai_worker_hourly():
    plist = plistlib.loads((ROOT / "backend/deploy/mac/edu.cs403.mynews.aiworker.plist").read_bytes())
    assert plist["StartCalendarInterval"] == {"Minute": 5}
    assert plist["ProgramArguments"][-1].endswith("run_ai_worker.sh")


def test_secret_files_are_gitignored():
    ignore = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in ignore and "backend/logs/" in ignore
