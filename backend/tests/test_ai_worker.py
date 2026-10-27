"""Split deployment: cloud collector with AI_PROVIDER=none + separate AI worker (Ollama)."""
from __future__ import annotations

import dataclasses
import json
from datetime import timedelta

import httpx
import pytest

from app import main as main_module
from app import pipeline
from app.ai import provider as provider_module
from app.ai.provider import AIError, FakeProvider, OllamaProvider
from app.models import CollectionRun
from tests.conftest import hours_ago, item
from tests.fixtures.events import GROUPS


@pytest.fixture
def ai_disabled(monkeypatch):
    disabled = dataclasses.replace(pipeline.settings, ai_provider="none")
    monkeypatch.setattr(pipeline, "settings", disabled)
    monkeypatch.setattr(main_module, "settings", disabled)


def _load(web, now, key):
    for pub, title, excerpt, h in GROUPS[key]:
        web.add(item(pub, title, excerpt, hours_ago(now, h)))


def test_collector_with_ai_disabled_never_calls_model(client, web, collect, now, ai_disabled):
    ai = FakeProvider()
    _load(web, now, "comey_charged")
    collect(now, provider=ai)
    assert ai.calls == []
    story = client.get("/stories").json()["stories"][0]
    assert story["summary_status"] == "pending"
    detail = client.get(f"/stories/{story['id']}").json()
    assert "AI worker" in detail["summary"]["status_message"]


def test_ai_worker_fills_summaries_and_reuses_them(client, db, web, collect, now, ai_disabled):
    _load(web, now, "comey_charged")
    collect(now)
    ai = FakeProvider()
    run_id = pipeline.run_ai(session_factory=db, provider_factory=lambda: ai, now=now + timedelta(minutes=5))
    assert len(ai.calls) == 1
    with db() as s:
        run = s.get(CollectionRun, run_id)
        assert run.trigger == "ai" and run.status == "success" and run.summaries_generated == 1
    sid = client.get("/stories").json()["stories"][0]["id"]
    assert client.get(f"/stories/{sid}").json()["summary"]["status"] == "ready"
    pipeline.run_ai(session_factory=db, provider_factory=lambda: ai, now=now + timedelta(minutes=65))
    assert len(ai.calls) == 1  # unchanged story: no new generation
    status_ai = client.get("/status").json()["ai"]
    assert status_ai["provider_on_this_server"] == "none" and status_ai["configured_model"] is None
    assert status_ai["latest_summary_model"] == "fake-model" and status_ai["latest_summary_provider"] == "fake"
    assert status_ai["last_ai_worker_run"]["trigger"] == "ai"


def test_last_successful_collection_ignores_ai_runs(client, db, web, collect, now, ai_disabled):
    _load(web, now, "brewers_rays")
    collect(now)
    before = client.get("/stories").json()["last_successful_collection_at"]
    pipeline.run_ai(session_factory=db, provider_factory=FakeProvider, now=now + timedelta(minutes=30))
    assert client.get("/stories").json()["last_successful_collection_at"] == before


def test_ai_worker_without_model_leaves_summaries_untouched(db, web, collect, now, ai_disabled):
    _load(web, now, "brewers_rays")
    collect(now)

    def unavailable():
        raise AIError("Ollama is not reachable at http://localhost:11434")

    run_id = pipeline.run_ai(session_factory=db, provider_factory=unavailable, now=now)
    with db() as s:
        run = s.get(CollectionRun, run_id)
        assert run.status == "failed" and run.summaries_failed == 0
        assert "not reachable" in run.errors[0]["error"]


# ------------------------------------------------------------- OllamaProvider


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)


def _ollama(monkeypatch, status=200, payload=None, post_exc=None):
    sent = {}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"version": "test"}))

    def post(url, json=None, timeout=None):
        if post_exc:
            raise post_exc
        sent["url"], sent["body"] = url, json
        return _Resp(status, payload)

    monkeypatch.setattr(httpx, "post", post)
    return sent


def test_ollama_sends_schema_and_parses_json(monkeypatch):
    out = {"overview": "x"}
    sent = _ollama(monkeypatch, payload={"model": "granite4.2:3b", "done_reason": "stop",
                                         "message": {"content": json.dumps(out)}})
    p = OllamaProvider(model="granite4.2:3b", base_url="http://localhost:11434")
    raw, model = p.generate("sys", "user", {"type": "object"})
    assert raw == out and model == "granite4.2:3b"
    assert sent["url"].endswith("/api/chat")
    assert sent["body"]["format"] == {"type": "object"} and sent["body"]["stream"] is False
    assert sent["body"]["think"] is False and sent["body"]["options"]["num_predict"] == 2000
    assert sent["body"]["messages"][0] == {"role": "system", "content": "sys"}


@pytest.mark.parametrize(
    "status, payload, exc, message",
    [
        (404, {}, None, "not installed"),
        (500, {}, None, "HTTP 500"),
        (200, {"done_reason": "length", "message": {"content": "{"}}, None, "cut off"),
        (200, {"message": {"content": "not json"}}, None, "not valid JSON"),
        (200, {}, httpx.ReadTimeout("slow"), "timed out"),
    ],
)
def test_ollama_failures_raise_ai_error(monkeypatch, status, payload, exc, message):
    _ollama(monkeypatch, status=status, payload=payload, post_exc=exc)
    p = OllamaProvider(model="m", base_url="http://localhost:11434")
    with pytest.raises(AIError, match=message):
        p.generate("s", "u", {})


def test_ollama_unreachable_at_startup(monkeypatch):
    def down(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", down)
    with pytest.raises(AIError, match="not reachable"):
        OllamaProvider(model="m", base_url="http://localhost:11434")


def test_provider_none_is_refused(monkeypatch):
    monkeypatch.setattr(provider_module, "settings", dataclasses.replace(provider_module.settings, ai_provider="none"))
    with pytest.raises(AIError, match="disabled"):
        provider_module.get_provider()
