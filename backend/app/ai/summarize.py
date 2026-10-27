"""Build the AI input for a story, fingerprint it, and validate the output.

Fingerprint = hash(prompt version + model + every input article's id, title,
excerpt, publisher, time). If the fingerprint is unchanged, the stored summary
is reused and the model is NOT called again. If any input changes or an
article expires, the fingerprint changes and the summary is regenerated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..timeutil import iso

PROMPT_VERSION = "v2"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "summary_system.md"
INSUFFICIENT = "Insufficient evidence for distinct perspectives."

OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "overview_citations": {"type": "array", "items": {"type": "string"}},
        "agreement": {"type": "string"},
        "disagreement": {"type": "string"},
        "uncertainty": {"type": "string"},
        "perspectives_supported": {"type": "boolean"},
        "perspectives_note": {"type": "string"},
        "perspectives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "citations": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "citations"],
                            "additionalProperties": False,
                        },
                    },
                    "limits": {"type": "string"},
                },
                "required": ["name", "summary", "claims", "limits"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "overview", "overview_citations", "agreement", "disagreement", "uncertainty",
        "perspectives_supported", "perspectives_note", "perspectives",
    ],
    "additionalProperties": False,
}


def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def ordered(articles: Sequence) -> List:
    return sorted(articles, key=lambda a: (iso(a.published_at), a.id))


def fingerprint(articles: Sequence, model: str) -> str:
    payload = {
        "prompt": PROMPT_VERSION,
        "model": model,
        "articles": [
            [a.id, a.publisher, a.title, a.excerpt or "", iso(a.published_at)] for a in ordered(articles)
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _escape(text: str) -> str:
    return (text or "").replace("<", "‹").replace(">", "›")


def build_user_message(articles: Sequence) -> str:
    lines = ["<articles>"]
    for i, a in enumerate(ordered(articles), start=1):
        lines.append(
            f'<article label="A{i}" publisher="{_escape(a.publisher)}" published="{iso(a.published_at)}">\n'
            f"<headline>{_escape(a.title)}</headline>\n"
            f"<feed_excerpt>{_escape(a.excerpt) or '(no excerpt in feed)'}</feed_excerpt>\n"
            f"</article>"
        )
    lines.append("</articles>")
    lines.append(
        "Analyse this story following the system instructions. The input is limited to headlines and "
        "feed excerpts. Return only the JSON object."
    )
    return "\n".join(lines)


def labels_to_ids(articles: Sequence) -> Dict[str, str]:
    return {f"A{i}": a.id for i, a in enumerate(ordered(articles), start=1)}


def validate_output(raw: Dict[str, Any], articles: Sequence) -> Dict[str, Any]:
    """Map citation labels to article IDs and drop anything unsupported.

    Citations to labels that were not in the input are removed; claims left
    with no valid citation are removed; a perspective with no supported claim
    is removed; fewer than two remaining perspectives => insufficient evidence.
    """
    mapping = labels_to_ids(articles)

    def cite(labels) -> List[str]:
        out: List[str] = []
        for label in labels or []:
            article_id = mapping.get(str(label).strip().upper())
            if article_id and article_id not in out:
                out.append(article_id)
        return out

    perspectives = []
    for p in raw.get("perspectives") or []:
        claims = []
        for c in p.get("claims") or []:
            ids = cite(c.get("citations"))
            if ids and (c.get("text") or "").strip():
                claims.append({"text": c["text"].strip(), "article_ids": ids})
        if claims and (p.get("name") or "").strip():
            perspectives.append(
                {
                    "name": p["name"].strip(),
                    "summary": (p.get("summary") or "").strip(),
                    "claims": claims,
                    "limits": (p.get("limits") or "").strip(),
                    "article_ids": sorted({i for c in claims for i in c["article_ids"]}),
                }
            )

    supported = bool(raw.get("perspectives_supported")) and len(perspectives) >= 2
    note = (raw.get("perspectives_note") or "").strip()
    if not supported:
        perspectives = []
        if not note.startswith(INSUFFICIENT):
            note = INSUFFICIENT + (" " + note if note else "")
    else:
        note = ""

    overview_ids = cite(raw.get("overview_citations")) or [a.id for a in ordered(articles)]
    return {
        "overview": (raw.get("overview") or "").strip(),
        "overview_article_ids": overview_ids,
        "agreement": (raw.get("agreement") or "").strip(),
        "disagreement": (raw.get("disagreement") or "").strip(),
        "uncertainty": (raw.get("uncertainty") or "").strip(),
        "perspectives_supported": supported,
        "perspectives_note": note,
        "perspectives": perspectives,
    }
