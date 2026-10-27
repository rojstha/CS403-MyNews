"""AI model providers. Only the backend worker ever calls these.

To add another provider, implement `generate()` and register it in get_provider().
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config import settings


class AIError(Exception):
    """Generation failed; the caller records an honest 'failed' status."""


class Provider:
    name = "base"

    def generate(self, system: str, user: str, schema: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Return (parsed JSON output, model id that actually served the request)."""
        raise NotImplementedError


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: Optional[str] = None):
        import anthropic

        self._anthropic = anthropic
        # Reads ANTHROPIC_API_KEY from the server environment.
        self.client = anthropic.Anthropic(timeout=180.0, max_retries=2)
        self.model = model or settings.ai_model

    def generate(self, system, user, schema):
        anthropic = self._anthropic
        kwargs = dict(
            model=self.model,
            max_tokens=settings.ai_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            thinking={"type": "adaptive"},
            output_config={"effort": settings.ai_effort, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if settings.ai_use_fallbacks:
                # Server-side fallback: if the model declines, the API retries on a fallback model.
                response = self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            else:
                response = self.client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise AIError("AI provider rate limit reached") from exc
        except anthropic.AuthenticationError as exc:
            raise AIError("AI provider rejected the API key") from exc
        except anthropic.BadRequestError as exc:
            raise AIError(f"AI request rejected: {exc.message}"[:300]) from exc
        except anthropic.APIStatusError as exc:
            raise AIError(f"AI provider error HTTP {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise AIError("Could not reach the AI provider") from exc

        if response.stop_reason == "refusal":
            raise AIError("The AI model declined to summarise this story")
        if response.stop_reason == "max_tokens":
            raise AIError("AI output was cut off (max_tokens)")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            raise AIError("AI response contained no text")
        try:
            return json.loads(text), response.model
        except json.JSONDecodeError as exc:
            raise AIError("AI response was not valid JSON") from exc


class OllamaProvider(Provider):
    """Free, local open-source model served by Ollama (https://ollama.com).

    Uses Ollama's structured outputs: the same JSON schema as the Anthropic
    provider is passed as `format`, so the model must answer in that shape.
    """

    name = "ollama"

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        import httpx

        self._httpx = httpx
        self.model = model or settings.ai_model
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        try:
            httpx.get(f"{self.base_url}/api/version", timeout=5.0).raise_for_status()
        except httpx.HTTPError as exc:
            raise AIError(f"Ollama is not reachable at {self.base_url}") from exc

    def generate(self, system, user, schema):
        httpx = self._httpx
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            # Low temperature: stick closely to the articles.
            "options": {
                "temperature": 0.2,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_num_predict,
            },
        }
        if settings.ollama_think in ("true", "false"):
            body["think"] = settings.ollama_think == "true"
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=settings.ollama_timeout_seconds)
        except httpx.TimeoutException as exc:
            raise AIError("Local AI model timed out") from exc
        except httpx.HTTPError as exc:
            raise AIError("Could not reach the local AI model") from exc
        if response.status_code == 404:
            raise AIError(f"Model '{self.model}' is not installed in Ollama")
        if response.status_code != 200:
            raise AIError(f"Ollama error HTTP {response.status_code}")
        data = response.json()
        if data.get("done_reason") == "length":
            raise AIError("AI output was cut off (context or length limit)")
        text = (data.get("message") or {}).get("content") or ""
        if not text.strip():
            raise AIError("AI response contained no text")
        try:
            return json.loads(text), data.get("model") or self.model
        except json.JSONDecodeError as exc:
            raise AIError("AI response was not valid JSON") from exc


class FakeProvider(Provider):
    """Deterministic stand-in used ONLY by automated tests. Counts calls."""

    name = "fake"

    def __init__(self, responder: Optional[Callable[[str], Dict[str, Any]]] = None, fail: bool = False):
        self.calls: List[str] = []
        self.responder = responder
        self.fail = fail

    def generate(self, system, user, schema):
        self.calls.append(user)
        if self.fail:
            raise AIError("Simulated AI outage")
        if self.responder:
            return self.responder(user), "fake-model"
        labels = sorted({part.split('"')[0] for part in user.split('label="')[1:]})
        return (
            {
                "overview": "Test overview.",
                "overview_citations": labels,
                "agreement": "Sources agree in test.",
                "disagreement": "No meaningful disagreement is visible in the available coverage.",
                "uncertainty": "Test uncertainty.",
                "perspectives_supported": False,
                "perspectives_note": "Insufficient evidence for distinct perspectives. Test.",
                "perspectives": [],
            },
            "fake-model",
        )


def get_provider() -> Provider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider()
    if settings.ai_provider == "ollama":
        return OllamaProvider()
    if settings.ai_provider == "none":
        raise AIError("AI is disabled in this process (AI_PROVIDER=none)")
    raise AIError(f"Unknown AI_PROVIDER '{settings.ai_provider}'")
