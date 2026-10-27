"""Lightweight text features shared by grouping and background lookup.

No ML libraries: tokens are lower-cased words minus stop words with a tiny
plural-stripping stemmer; "entities" are runs of capitalised words such as
"Keir Starmer" or "Gaza City" (a cheap stand-in for named-entity recognition).
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set

STOP_WORDS: Set[str] = set(
    """
    a about above after again against ago all also am amid among an and any are around as at
    back be because been before being below between both but by can cannot could day days did do
    does doing down during each early even ever every few first for from further get gets got had
    has have having he her here hers him his how however i if in into is it its just last late
    latest like live made make makes many may me more most much must my near new news next no nor
    not now of off on once one only or other our out over own people per said same say says see
    seen she should since so some still such take takes than that the their them then there these
    they this those three through to today told too two under until up upon us very via was we
    week weeks were what when where which while who whom why will with within without would year
    years yet you your according amid against report reports reported update updates video watch
    read listen analysis opinion here's what's it's could've new latest breaking exclusive
    npr pbs bbc cbs fox foxnews guardian jazeera newshour marist reuters associated press
    """.split()
)

# Capitalised words that start sentences/headlines but are not entities.
NON_ENTITY_WORDS: Set[str] = set(
    """
    The A An In On At For From With Without After Before As By Of To And But Or If When Where Why How
    What Who Which This That These Those It Its He She They We I You His Her Their Our Here There
    Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June
    July August September October November December Mr Mrs Ms Dr Breaking Live Watch Analysis
    Opinion Exclusive Update Video Photos Report Reports Says Said Could Would Should Will Can
    """.split()
)

_UPPER = "A-ZÀ-ÖØ-Þ"
_WORD_RE = re.compile(r"[^\W\d_][\w'’\-]*")
_ENTITY_RE = re.compile(
    rf"\b(?:[{_UPPER}][\w'’\-]+|[{_UPPER}]{{2,}})(?:\s+(?:of|de|al|bin|the|[{_UPPER}][\w'’\-]+|[{_UPPER}]{{2,}}))*"
)


def stem(word: str) -> str:
    word = word.lower().replace("’", "'")
    if word.endswith("'s"):
        word = word[:-2]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("es") and word[-3] in "sxz":
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss") and not word.endswith("us"):
        return word[:-1]
    return word


def tokens(text: str) -> List[str]:
    out = []
    for raw in _WORD_RE.findall(text or ""):
        word = raw.strip("-'’")
        lower = word.lower()
        if len(lower) < 3 or lower in STOP_WORDS:
            continue
        stemmed = stem(lower)
        if stemmed in STOP_WORDS or len(stemmed) < 3:
            continue
        out.append(stemmed)
    return out


def entities(text: str) -> List[str]:
    """Capitalised phrases, e.g. 'Supreme Court', 'Gaza', 'NATO'."""
    found: List[str] = []
    for match in _ENTITY_RE.finditer(text or ""):
        words = match.group(0).replace("’", "'").split()
        # Trim leading/trailing connector or non-entity words.
        while words and (words[0] in NON_ENTITY_WORDS or words[0].lower() in {"of", "de", "al", "bin", "the"}):
            words = words[1:]
        while words and (words[-1] in NON_ENTITY_WORDS or words[-1].lower() in {"of", "de", "al", "bin", "the"}):
            words = words[:-1]
        if not words:
            continue
        words = [w[:-2] if w.endswith("'s") else w for w in words]
        phrase = " ".join(words)
        if len(phrase) < 3 or phrase.lower() in STOP_WORDS:
            continue
        found.append(phrase)
    return found


def term_counts(title: str, excerpt: str) -> Dict[str, float]:
    """Bag of words with headline words weighted double."""
    counts: Dict[str, float] = {}
    for tok in tokens(title):
        counts[tok] = counts.get(tok, 0.0) + 2.0
    for tok in tokens(excerpt):
        counts[tok] = counts.get(tok, 0.0) + 1.0
    return counts


def entity_keys(title: str, excerpt: str) -> Set[str]:
    return {e.lower() for e in entities(title) + entities(excerpt)}


def keywords_from_title(title: str, limit: int = 4) -> List[str]:
    """Same idea as the starter's keywordsFromTitle(): readable title terms."""
    seen: List[str] = []
    for raw in _WORD_RE.findall(title or ""):
        word = raw.strip("-'’")
        if len(word) < 3 or word.lower() in STOP_WORDS:
            continue
        label = word if word.isupper() else word.capitalize()
        if label not in seen:
            seen.append(label)
    return seen[:limit] or ["News"]


def unique(seq: Iterable[str]) -> List[str]:
    out: List[str] = []
    for item in seq:
        if item not in out:
            out.append(item)
    return out
