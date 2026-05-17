"""BR-16 / CS-358: stamped rubric version wins over globally active catalog."""

from __future__ import annotations

import pytest

from rubric.infrastructure.django.repositories import (
    RUBRIC_CATALOG_ACTIVE_BOOTSTRAP,
    RUBRIC_CATALOG_STAMPED,
    CriterionRepository,
)
from tests.factories import ContractAnalysisFactory, CriterionFactory, RubricVersionFactory


@pytest.mark.django_db
def test_load_specs_for_analysis_uses_stamped_version_not_active() -> None:
    """Only B is active; analysis is stamped with A — criteria must come from A."""
    v_a = RubricVersionFactory(version="br16-stamped-a", is_active=False)
    v_b = RubricVersionFactory(version="br16-active-b", is_active=True)
    CriterionFactory(rubric_version=v_a, code="ONLY_A")
    CriterionFactory(rubric_version=v_b, code="ONLY_B")
    analysis = ContractAnalysisFactory(rubric_version=v_a)

    specs, resolved, source = CriterionRepository().load_specs_for_analysis(analysis)

    assert source == RUBRIC_CATALOG_STAMPED
    assert resolved == "br16-stamped-a"
    ids = {s.criterion_id for s in specs}
    assert "ONLY_A" in ids
    assert "ONLY_B" not in ids


@pytest.mark.django_db
def test_load_specs_active_bootstrap_when_instance_has_no_stamp() -> None:
    """Defensive path: unset rubric_version_id on instance uses active catalog once."""
    RubricVersionFactory(version="br16-stamped-a", is_active=False)
    v_b = RubricVersionFactory(version="br16-active-b", is_active=True)
    CriterionFactory(rubric_version=v_b, code="ONLY_B")
    analysis = ContractAnalysisFactory(rubric_version=v_b)
    analysis.rubric_version_id = None

    specs, resolved, source = CriterionRepository().load_specs_for_analysis(analysis)

    assert source == RUBRIC_CATALOG_ACTIVE_BOOTSTRAP
    assert resolved == "br16-active-b"
    assert {s.criterion_id for s in specs} == {"ONLY_B"}


@pytest.mark.django_db
def test_stamped_catalog_stable_after_active_is_flipped() -> None:
    """Regression: after creating analysis stamped A, activate only B — resolver still reads A."""
    v_a = RubricVersionFactory(version="br16-stamped-a", is_active=True)
    CriterionFactory(rubric_version=v_a, code="ONLY_A")
    analysis = ContractAnalysisFactory(rubric_version=v_a)

    v_b = RubricVersionFactory(version="br16-active-b", is_active=False)
    CriterionFactory(rubric_version=v_b, code="ONLY_B")

    v_a.is_active = False
    v_a.save(update_fields=["is_active"])
    v_b.is_active = True
    v_b.save(update_fields=["is_active"])

    analysis.refresh_from_db()
    specs, resolved, source = CriterionRepository().load_specs_for_analysis(analysis)

    assert source == RUBRIC_CATALOG_STAMPED
    assert resolved == "br16-stamped-a"
    ids = {s.criterion_id for s in specs}
    assert "ONLY_A" in ids
    assert "ONLY_B" not in ids
