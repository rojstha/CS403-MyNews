"""Story grouping: same event across publishers vs. similar topic, different event.

Uses the clearly labelled FIXTURE dataset in tests/fixtures/events.py.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from app.grouping.grouper import Doc, assign_stories
from tests.fixtures.events import GROUPS, SEPARATE, SINGLE


def _docs(now, events):
    docs = []
    for key, items in events.items():
        for i, (pub, title, excerpt, hours) in enumerate(items):
            docs.append(Doc(f"{key}-{i}", pub, title, excerpt, now - timedelta(hours=hours)))
    return docs


def _stories(assignments):
    by_story = defaultdict(set)
    for doc_id, story_id in assignments.items():
        by_story[story_id].add(doc_id.rsplit("-", 1)[0])
    return by_story


def _all_fixture_docs(now):
    docs = _docs(now, GROUPS) + _docs(now, SEPARATE)
    for i, (pub, title, excerpt, hours) in enumerate(SINGLE):
        docs.append(Doc(f"single{i}-0", pub, title, excerpt, now - timedelta(hours=hours)))
    return docs


def test_five_multi_publisher_events_each_form_one_story(now):
    assignments, _ = assign_stories(_all_fixture_docs(now))
    story_of = {doc_id: sid for doc_id, sid in assignments.items()}
    for key, items in GROUPS.items():
        ids = {story_of[f"{key}-{i}"] for i in range(len(items))}
        assert len(ids) == 1, f"{key} was split into {len(ids)} stories"
        pubs = {p for p, *_ in items}
        assert len(pubs) >= 2


def test_related_topics_remain_separate_stories(now):
    assignments, _ = assign_stories(_all_fixture_docs(now))
    by_story = _stories(assignments)
    for keys in by_story.values():
        assert len(keys) == 1, f"different events merged: {sorted(keys)}"
    # Explicit checks for the two documented "same subject, different event" cases.
    assert assignments["comey_charged-0"] != assignments["comey_daughter-0"]
    assert assignments["israel_election-0"] != assignments["israel_westbank_mps-0"]


def test_single_source_story_is_kept(now):
    assignments, _ = assign_stories(_all_fixture_docs(now))
    sid = assignments["single0-0"]
    assert list(assignments.values()).count(sid) == 1


def test_new_coverage_joins_existing_story_and_ids_are_stable(now):
    items = GROUPS["machado_return"]
    first = [Doc("m0", items[0][0], items[0][1], items[0][2], now - timedelta(hours=10))]
    a1, _ = assign_stories(first)
    story_id = a1["m0"]
    # Later run: the first article keeps its story; new coverage arrives.
    docs = [Doc("m0", items[0][0], items[0][1], items[0][2], now - timedelta(hours=10), story_id)]
    docs += [Doc(f"m{i}", p, t, e, now - timedelta(hours=h)) for i, (p, t, e, h) in enumerate(items[1:], start=1)]
    a2, explanations = assign_stories(docs)
    assert a2 == {"m1": story_id, "m2": story_id}
    assert all(len(x.shared) >= 1 for x in explanations)


def test_one_shared_name_is_not_enough(now):
    docs = [
        Doc("a", "NPR", "Taylor Swift announces new stadium tour dates", "The singer adds shows in Europe.", now),
        Doc("b", "BBC News", "Taylor Swift testifies in ticket resale lawsuit", "A court heard evidence about resale fees.", now),
    ]
    assignments, _ = assign_stories(docs)
    assert assignments["a"] != assignments["b"]


def test_articles_far_apart_in_time_do_not_merge(now):
    pub, title, excerpt, _ = GROUPS["fairford_plot"][0]
    pub2, title2, excerpt2, _ = GROUPS["fairford_plot"][1]
    docs = [Doc("a", pub, title, excerpt, now - timedelta(hours=150)), Doc("b", pub2, title2, excerpt2, now)]
    assignments, _ = assign_stories(docs)
    assert assignments["a"] != assignments["b"]
