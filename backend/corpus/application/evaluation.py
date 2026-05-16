"""Similarity-threshold tuning harness (CS-087 + CS-088 glue).

Reads `fixtures/rag_eval_cases.yaml`, runs each case through the
`LegalCitationService`, and computes Top-1 precision per threshold and
overall.

Designed to run from `pytest` (so CI gates on regressions) AND from an
ad-hoc `python -m corpus.application.evaluation` invocation when product
wants to retune.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

import yaml

from corpus.application.retrieval import LegalCitationService


DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "rag_eval_cases.yaml"


@dataclass(frozen=True)
class EvalCase:
    category: str
    finding: str
    expected_law: str
    expected_anchor: str


@dataclass(frozen=True)
class EvalReport:
    threshold: float
    top_1_precision: float
    per_category: dict[str, float]
    misses: list[tuple[EvalCase, str]]


def load_cases(path: Path | None = None) -> list[EvalCase]:
    path = path or DEFAULT_FIXTURE
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out: list[EvalCase] = []
    for category, payload in (data.get("categories") or {}).items():
        for case in payload.get("cases", []):
            out.append(
                EvalCase(
                    category=category,
                    finding=case["finding"],
                    expected_law=case["expected"]["law_id"],
                    expected_anchor=case["expected"]["anchor"],
                )
            )
    return out


def evaluate_threshold(
    cases: Iterable[EvalCase],
    *,
    threshold: float,
    top_k: int = 5,
    service: LegalCitationService | None = None,
) -> EvalReport:
    """Run all `cases` and return Top-1 precision metrics for `threshold`."""

    service = service or LegalCitationService()
    cases = list(cases)
    hits = 0
    per_cat_hits: dict[str, list[int]] = {}
    misses: list[tuple[EvalCase, str]] = []

    for case in cases:
        per_cat = per_cat_hits.setdefault(case.category, [0, 0])
        per_cat[1] += 1
        citations = service.retrieve_legal_basis(
            finding=case.finding,
            threshold=threshold,
            top_k=top_k,
        )
        if citations and citations[0].law_id == case.expected_law and citations[0].anchor == case.expected_anchor:
            hits += 1
            per_cat[0] += 1
        else:
            got = "(no result)" if not citations else f"{citations[0].law_id}#{citations[0].anchor}"
            misses.append((case, got))

    return EvalReport(
        threshold=threshold,
        top_1_precision=hits / max(len(cases), 1),
        per_category={
            cat: hits / total if total else 0.0
            for cat, (hits, total) in per_cat_hits.items()
        },
        misses=misses,
    )


def sweep(thresholds: Iterable[float], **kwargs) -> list[EvalReport]:
    cases = load_cases(kwargs.pop("fixture_path", None))
    return [evaluate_threshold(cases, threshold=t, **kwargs) for t in thresholds]
