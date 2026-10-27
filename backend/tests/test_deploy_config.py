"""Deployment configuration checks (render.yaml and DATABASE_URL handling)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app import config

yaml = pytest.importorskip("yaml")
BLUEPRINT = yaml.safe_load((Path(__file__).resolve().parents[2] / "render.yaml").read_text())
SECRETS = {"ANTHROPIC_API_KEY", "CONTACT_INFO", "ADMIN_TOKEN", "DATABASE_URL"}


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./x.db", "sqlite:///./x.db"),
    ],
)
def test_database_url_gets_psycopg_driver(monkeypatch, given, expected):
    monkeypatch.setenv("DATABASE_URL", given)
    assert config._database_url() == expected


def _services():
    return {s["name"]: s for s in BLUEPRINT["services"]}


def test_blueprint_has_api_cron_and_database():
    services = _services()
    assert services["mynews-api"]["type"] == "web"
    cron = services["mynews-hourly-collect"]
    assert cron["type"] == "cron" and cron["schedule"] == "0 * * * *"
    assert "app.worker --trigger scheduled" in cron["startCommand"]
    assert BLUEPRINT["databases"][0]["name"] == "mynews-db"
    regions = {s["region"] for s in BLUEPRINT["services"]} | {BLUEPRINT["databases"][0]["region"]}
    assert len(regions) == 1


def test_both_services_migrate_and_use_the_same_database():
    for svc in _services().values():
        assert svc["startCommand"].startswith("alembic upgrade head && ")
        db = next(e for e in svc["envVars"] if e.get("key") == "DATABASE_URL")
        assert db["fromDatabase"] == {"name": "mynews-db", "property": "connectionString"}


def test_no_secret_values_in_blueprint():
    for svc in _services().values():
        for env in svc["envVars"]:
            if env.get("key") in SECRETS:
                assert "value" not in env, f"{env['key']} must not be written in render.yaml"
    for group in BLUEPRINT.get("envVarGroups", []):
        for env in group["envVars"]:
            assert "sync" not in env, "Render rejects sync: false inside environment groups"
            assert env["key"] not in SECRETS
