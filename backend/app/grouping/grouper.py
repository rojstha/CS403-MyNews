"""Assign articles to stories (events).

Method (explained in docs/METHODS.md):
1. Represent each article as a TF-IDF vector of its title (weight 2) and feed
   excerpt (weight 1). IDF is computed over every article in the 7-day window,
   so words that appear everywhere ("Trump", "war") count for little.
2. A new article may join an existing story only if, for at least one article
   already in that story:
     * the two were published within MAX_HOURS_APART of each other, and
     * their cosine similarity is >= SIM_THRESHOLD, and
     * they share at least MIN_SHARED_DISTINCTIVE distinctive terms (rare
       words or capitalised phrases). One shared name is never enough.
   and its average similarity to ALL articles in the story is >= STORY_AVG_THRESHOLD,
   so a story cannot "chain" into a different event through one loosely related member.
3. Otherwise the article starts a new single-source story.
Articles keep their story once assigned, so story IDs are stable and new
coverage joins the existing story instead of creating a duplicate entry.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..text import entity_keys, term_counts, tokens

SIM_THRESHOLD = 0.35
STORY_AVG_THRESHOLD = 0.25
STRONG_SIM_THRESHOLD = 0.55
MIN_SHARED_DISTINCTIVE = 2
MAX_HOURS_APART = 72.0
# A term is "distinctive" if it occurs in at most this fraction of window articles.
DISTINCTIVE_DF_FRACTION = 0.04
DISTINCTIVE_DF_FLOOR = 4
# IDF smoothing: behave as if the window held at least this many other articles,
# so scores are stable when only a handful of articles exist (tests, quiet hours).
IDF_PSEUDO_DOCS = 50


@dataclass
class Doc:
    id: str
    publisher: str
    title: str
    excerpt: str
    published_at: datetime
    story_id: Optional[str] = None
    # Filled in by the grouper:
    vector: Dict[str, float] = field(default_factory=dict)
    terms: Set[str] = field(default_factory=set)
    ents: Set[str] = field(default_factory=set)


@dataclass
class MatchExplanation:
    story_id: str
    other_id: str
    similarity: float
    shared: List[str]


class Corpus:
    def __init__(self, docs: List[Doc]):
        self.docs = docs
        n = max(len(docs), 1)
        df: Dict[str, int] = {}
        for d in docs:
            d.terms = set(tokens(d.title + " " + d.excerpt))
            d.ents = entity_keys(d.title, d.excerpt)
            for t in d.terms:
                df[t] = df.get(t, 0) + 1
        self.df = df
        self.n = n
        self.idf = {t: math.log((n + IDF_PSEUDO_DOCS) / (c + 1)) + 1.0 for t, c in df.items()}
        limit = max(DISTINCTIVE_DF_FLOOR, int(DISTINCTIVE_DF_FRACTION * n))
        self.distinctive = {t for t, c in df.items() if c <= limit}
        for d in docs:
            d.vector = self._vector(d)

    def _vector(self, d: Doc) -> Dict[str, float]:
        counts = term_counts(d.title, d.excerpt)
        vec = {t: (1 + math.log(c)) * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def shared_evidence(a: Doc, b: Doc, corpus: Corpus) -> List[str]:
    """Distinctive words plus multi-word capitalised phrases both articles mention."""
    words = sorted(t for t in (a.terms & b.terms) if t in corpus.distinctive)
    phrases = sorted(e for e in (a.ents & b.ents) if " " in e)
    return words + [p for p in phrases if p.split()[-1] not in words]


def pair_matches(a: Doc, b: Doc, corpus: Corpus) -> Tuple[bool, float, List[str]]:
    hours = abs((a.published_at - b.published_at).total_seconds()) / 3600.0
    if hours > MAX_HOURS_APART:
        return False, 0.0, []
    sim = cosine(a.vector, b.vector)
    if sim < SIM_THRESHOLD:
        return False, sim, []
    shared = shared_evidence(a, b, corpus)
    needed = MIN_SHARED_DISTINCTIVE if sim < STRONG_SIM_THRESHOLD else 1
    return len(shared) >= needed, sim, shared


def new_story_id() -> str:
    return uuid.uuid4().hex[:16]


def assign_stories(
    docs: List[Doc], id_factory: Callable[[], str] = new_story_id
) -> Tuple[Dict[str, str], List[MatchExplanation]]:
    """Assign every unassigned doc to a story. Returns ({doc_id: story_id}, explanations).

    Docs that already have a story_id keep it.
    """
    corpus = Corpus(docs)
    members: Dict[str, List[Doc]] = {}
    for d in docs:
        if d.story_id:
            members.setdefault(d.story_id, []).append(d)

    assignments: Dict[str, str] = {}
    explanations: List[MatchExplanation] = []
    pending = sorted((d for d in docs if not d.story_id), key=lambda d: (d.published_at, d.id))
    for doc in pending:
        best: Optional[MatchExplanation] = None
        for story_id, story_docs in members.items():
            story_best: Optional[MatchExplanation] = None
            for other in story_docs:
                ok, sim, shared = pair_matches(doc, other, corpus)
                if ok and (story_best is None or sim > story_best.similarity):
                    story_best = MatchExplanation(story_id, other.id, sim, shared)
            if story_best is None:
                continue
            average = sum(cosine(doc.vector, o.vector) for o in story_docs) / len(story_docs)
            if average < STORY_AVG_THRESHOLD:
                continue
            if best is None or story_best.similarity > best.similarity:
                best = story_best
        if best:
            doc.story_id = best.story_id
            explanations.append(best)
        else:
            doc.story_id = id_factory()
        members.setdefault(doc.story_id, []).append(doc)
        assignments[doc.id] = doc.story_id
    return assignments, explanations


def choose_headline(story_docs: List[Doc]) -> str:
    """The most representative title: highest total similarity to the other articles."""
    if len(story_docs) == 1:
        return story_docs[0].title
    if not story_docs[0].vector:
        Corpus(story_docs)
    scored = []
    for d in story_docs:
        total = sum(cosine(d.vector, o.vector) for o in story_docs if o is not d)
        scored.append((-total, d.published_at, d.title))
    scored.sort()
    return scored[0][2]
