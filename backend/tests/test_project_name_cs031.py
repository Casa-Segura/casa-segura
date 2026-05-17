"""CS-031 — project name normalization + collision policy (ProjectLinker / ADR-0003)."""

from __future__ import annotations

import pytest

from classification.application.project_linker import ProjectLinker
from classification.domain.project_name_extraction import ProjectNameExtraction
from platform_core.domain.project_name import is_placeholder_normalized_name, normalize_project_name


def test_normalize_residencial_los_ebanos_adr0003() -> None:
    """Ticket AC1 + ADR-0003: generic token stripped; snapshot ``los ebanos``."""
    assert normalize_project_name("  Residencial   LOS ÉBANOS!! ") == "los ebanos"


def test_normalize_accent_equivalence() -> None:
    assert normalize_project_name("café") == normalize_project_name("cafe")


def test_placeholder_pattern() -> None:
    assert is_placeholder_normalized_name("unknown_deadbeef")
    assert not is_placeholder_normalized_name("los ebanos")


def test_punctuation_stripped_consistently() -> None:
    assert normalize_project_name("/foo.bar|baz") == "foo bar baz"


@pytest.mark.django_db(transaction=True)
def test_linker_collision_same_normalized_name() -> None:
    """AC4: two raw strings colliding on ``normalized_name`` hit upsert path."""
    key = normalize_project_name("LOS ÉBANOS")
    assert key == normalize_project_name("  Residencial   LOS ÉBANOS!! ")
    ext_first = ProjectNameExtraction(
        raw="LOS ÉBANOS",
        normalized=key,
        confidence=0.95,
    )
    ext_second = ProjectNameExtraction(
        raw="  Residencial   LOS ÉBANOS!! ",
        normalized=key,
        confidence=0.9,
    )
    linker = ProjectLinker()
    r1 = linker.link_or_create_project(ext_first)
    r2 = linker.link_or_create_project(ext_second)
    assert r1.was_created is True
    assert r2.was_created is False
    assert r2.was_collision is True
    assert r1.project_id == r2.project_id
