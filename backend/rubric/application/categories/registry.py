"""Bootstrap helper that registers every category's evaluators (CS-159..164)."""

from __future__ import annotations

from rubric.application.categories.category_a import register_category_a
from rubric.application.categories.category_b import register_category_b
from rubric.application.categories.category_c import register_category_c
from rubric.application.categories.category_d import register_category_d
from rubric.application.categories.category_e import register_category_e
from rubric.application.categories.category_f import register_category_f
from rubric.application.services.criterion_evaluator import CriterionRegistry

ALL_CRITERION_IDS = {
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A6",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "E8",
    "E9",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
}


def build_default_registry() -> CriterionRegistry:
    """Return a registry with every category's deterministic evaluators."""

    registry = CriterionRegistry()
    register_category_a(registry)
    register_category_b(registry)
    register_category_c(registry)
    register_category_d(registry)
    register_category_e(registry)
    register_category_f(registry)
    registry.health_check(ALL_CRITERION_IDS)
    return registry


__all__ = ["ALL_CRITERION_IDS", "build_default_registry"]
