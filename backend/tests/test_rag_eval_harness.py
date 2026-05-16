"""CS-087 + CS-088: structural checks on the eval harness.

Note: we don't run a live sweep against a populated corpus inside this
unit-test process (that requires the full ingestion + sentence-transformers
model download). Live tuning runs in CI as a separate job after corpus
ingestion. These tests just guarantee the fixture and harness shape
remain healthy enough for that job to run.
"""

from __future__ import annotations

from corpus.application.evaluation import EvalCase, load_cases


def test_fixture_has_at_least_thirty_cases():
    cases = load_cases()
    assert len(cases) >= 30


def test_fixture_covers_six_categories_with_at_least_four_each():
    cases = load_cases()
    per_cat: dict[str, int] = {}
    for case in cases:
        per_cat[case.category] = per_cat.get(case.category, 0) + 1
    assert len(per_cat) >= 6
    for cat, count in per_cat.items():
        assert count >= 4, f"{cat} has only {count} cases (≥4 required)"


def test_fixture_pairs_have_law_and_anchor():
    cases = load_cases()
    for case in cases:
        assert isinstance(case, EvalCase)
        assert case.expected_law
        assert case.expected_anchor.startswith("art-")
