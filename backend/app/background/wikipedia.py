"""Pick background resources for a story from Wikipedia.

Method (docs/METHODS.md):
1. Candidate terms = capitalised phrases (people, places, organisations,
   events) found in the story's headlines and excerpts. A term must appear in
   a headline or in at least two articles; generic terms (countries the size of
   "US"/"UK", publisher names, "White House" ...) are excluded.
2. Candidates are ranked: multi-word phrases first, then by how many articles
   mention them.
3. The top candidates are looked up as exact Wikipedia titles (following
   redirects). Missing pages and disambiguation pages are rejected, and the
   resolved title must still share a word with the candidate. This avoids
   showing an unrelated link; if nothing survives, the app shows
   "No background resource available".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

import httpx

from ..config import settings
from ..text import entities

API_URL = "https://en.wikipedia.org/w/api.php"
MAX_RESOURCES = 3
MAX_CANDIDATES = 6

GENERIC_TERMS = {
    "us", "u.s", "u.s.", "usa", "uk", "u.k", "u.k.", "america", "american", "americans", "britain",
    "british", "europe", "european", "trump", "president", "president trump", "white house",
    "congress", "senate", "house", "government", "police", "republican", "republicans",
    "democrat", "democrats", "democratic", "gop", "state", "city", "court", "the latest",
    "bbc", "npr", "pbs", "cbs", "fox", "fox news", "cbs news", "bbc news", "guardian",
    "al jazeera", "newshour", "pbs news", "the guardian", "ap", "reuters", "watch", "game",
    "world", "national", "federal", "officials", "minister", "prime minister", "east", "west",
}


@dataclass
class Resource:
    url: str
    title: str
    description: str
    matched_term: str
    source: str = "Wikipedia"


# Signature: (list of candidate titles) -> {candidate: Resource}. Replaceable in tests.
Lookup = Callable[[List[str]], Dict[str, Resource]]


def _only_headline_start(word: str, article) -> bool:
    text = f"{article.title} {article.excerpt or ''}"
    occurrences = text.count(word)
    return occurrences <= 1 and article.title.startswith(word)


def candidate_terms(articles: Sequence) -> List[str]:
    score: Dict[str, List[float]] = {}
    display: Dict[str, str] = {}
    for a in articles:
        in_title = {e.lower() for e in entities(a.title)}
        mentioned = set()
        for phrase in entities(a.title) + entities(a.excerpt or ""):
            key = phrase.lower()
            if key in GENERIC_TERMS or len(key) < 3 or key in mentioned:
                continue
            mentioned.add(key)
            display.setdefault(key, phrase)
            # A single capitalised word that only opens a headline ("Opposition leader ...")
            # is usually just sentence case, not a name.
            if " " not in key and not key.isupper() and _only_headline_start(phrase, a):
                continue
            entry = score.setdefault(key, [0, 0])
            entry[0] += 1  # number of articles mentioning
            if key in in_title:
                entry[1] = 1
    ranked = []
    for key, (count, titled) in score.items():
        if not titled and count < 2:
            continue
        multi = 1 if " " in key else 0
        ranked.append((-multi, -count, -titled, key))
    ranked.sort()
    # Drop single words already covered by a chosen multi-word phrase ("Comey" vs "James Comey").
    chosen: List[str] = []
    for *_rest, key in ranked:
        if any(key in other.split() for other in chosen):
            continue
        chosen.append(key)
    return [display[k] for k in chosen[:MAX_CANDIDATES]]


def wikipedia_lookup(terms: List[str]) -> Dict[str, Resource]:
    if not terms:
        return {}
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "titles": "|".join(terms),
        "prop": "pageprops|extracts|info",
        "exintro": "1",
        "explaintext": "1",
        "exsentences": "2",
        "exlimit": "max",
        "inprop": "url",
    }
    with httpx.Client(timeout=15.0, headers={"User-Agent": settings.user_agent}) as client:
        response = client.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()["query"]

    # Map each requested term through normalization and redirects to a final title.
    resolved = {t: t for t in terms}
    for step in ("normalized", "redirects"):
        hops = {item["from"]: item["to"] for item in data.get(step, [])}
        resolved = {t: hops.get(cur, cur) for t, cur in resolved.items()}

    pages = {p["title"]: p for p in data.get("pages", [])}
    out: Dict[str, Resource] = {}
    for term, title in resolved.items():
        page = pages.get(title)
        if not page or page.get("missing") or page.get("invalid"):
            continue
        if "disambiguation" in (page.get("pageprops") or {}):
            continue
        term_words = {w.lower() for w in term.split()}
        if not term_words & {w.lower().strip("(),") for w in title.split()}:
            continue
        extract = (page.get("extract") or "").strip()
        if not extract or "may refer to" in extract:
            continue
        out[term] = Resource(
            url=page.get("fullurl") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            title=title,
            description=extract[:400],
            matched_term=term,
        )
    return out


def find_background(articles: Sequence, lookup: Lookup = wikipedia_lookup) -> List[Resource]:
    terms = candidate_terms(articles)
    found = lookup(terms)
    results: List[Resource] = []
    seen_urls = set()
    for term in terms:
        res = found.get(term)
        if res and res.url not in seen_urls:
            seen_urls.add(res.url)
            results.append(res)
        if len(results) >= MAX_RESOURCES:
            break
    return results
