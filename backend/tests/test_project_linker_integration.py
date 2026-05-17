"""CS-112 + CS-031 AC4 — integration tests for `ProjectLinker` against real DB.

These tests exercise the collision / placeholder policy declared by
PRD_F8 §US-02 + BR-07 (single source of truth for the upsert+placeholder
policy now lives in `classification.application.project_linker`).

Coverage matrix:

    BR-05 (case + diacritics collide on `normalized_name`)        — test_case_and_diacritics_collide
    BR-06 (placeholders never dedupe across submissions)          — test_placeholders_always_distinct
    BR-06 (same placeholder seed → idempotent return)             — test_placeholder_idempotent_within_submission
    BR-07 (placeholder rows tagged `metadata.placeholder = True`) — test_placeholder_marks_metadata_flag
    CS-031 AC4 (DB UNIQUE race → recover via IntegrityError)      — test_unique_constraint_race_recovers
    Normalization delegation (no drift from canonical helper)     — test_linker_delegates_normalization

Rule 9 (CS-031): the canonical normalizer in `platform_core.domain.project_name`
MUST be the single source of truth — `test_linker_delegates_normalization`
asserts the linker does not re-implement the rules.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from django.db import IntegrityError
from django.utils import timezone

from classification.application.project_linker import ProjectLinker
from classification.application.project_name_extractor import build_placeholder
from classification.domain.project_link import ProjectLinkResult
from classification.domain.project_name_extraction import ProjectNameExtraction
from platform_core.domain.project_name import (
    is_placeholder_normalized_name,
    normalize_project_name,
)
from platform_core.infrastructure.django.models import Project


PLACEHOLDER_REGEX = re.compile(r"^unknown_[0-9a-f]{8}$")


def _real_name_extraction(raw: str) -> ProjectNameExtraction:
    """Build a non-placeholder extraction via the canonical normalizer.

    Centralized so every test uses the same canonical path — adding a
    bespoke `normalized=` value would defeat the dedupe-by-normalization
    invariant we are trying to test.
    """
    normalized = normalize_project_name(raw)
    return ProjectNameExtraction(
        raw=raw,
        normalized=normalized,
        is_placeholder=False,
        confidence=0.9,
    )


def _placeholder_extraction(seed: str) -> ProjectNameExtraction:
    """Build a placeholder extraction whose `unknown_<hash>` is derived from `seed`."""
    placeholder = build_placeholder(seed)
    return ProjectNameExtraction(
        raw=None,
        normalized=placeholder,
        is_placeholder=False,  # validator overwrites based on shape
        confidence=0.0,
    )


# ---------------------------------------------------------------------------
# BR-05 — case + diacritics collide on `normalized_name`
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_case_and_diacritics_collide():
    """Two submissions with case/diacritic variants resolve to the same Project."""
    linker = ProjectLinker()

    first = linker.link_or_create_project(
        _real_name_extraction("Residencial Las Palmeras"),
    )
    second = linker.link_or_create_project(
        _real_name_extraction("RESIDENCIAL LAS PÁLMERAS"),
    )

    assert first.project_id == second.project_id
    assert first.was_created is True
    assert second.was_created is False
    assert second.was_collision is True
    assert Project.objects.filter(normalized_name="las palmeras").count() == 1


@pytest.mark.django_db
def test_collision_path_refreshes_last_analyzed():
    """PRD_F8 US-02: dedupe hit refreshes `last_analyzed` on the existing row."""
    linker = ProjectLinker()

    first_result = linker.link_or_create_project(
        _real_name_extraction("Residencial Solaris"),
    )
    first_ts = Project.objects.get(id=first_result.project_id).last_analyzed

    second_result = linker.link_or_create_project(
        _real_name_extraction("residencial SOLARIS"),
    )
    second_ts = Project.objects.get(id=second_result.project_id).last_analyzed

    assert second_ts > first_ts
    assert first_result.project_id == second_result.project_id


# ---------------------------------------------------------------------------
# BR-06 — placeholders never dedupe across submissions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_placeholders_always_distinct():
    """Two different submissions with unextractable names get distinct Project rows."""
    linker = ProjectLinker()

    first = linker.link_or_create_project(_placeholder_extraction("contract bytes one"))
    second = linker.link_or_create_project(_placeholder_extraction("contract bytes two"))

    assert first.project_id != second.project_id
    assert first.was_created is True
    assert second.was_created is True
    assert PLACEHOLDER_REGEX.match(first.normalized_name)
    assert PLACEHOLDER_REGEX.match(second.normalized_name)


@pytest.mark.django_db
def test_placeholder_idempotent_within_submission():
    """Same submission → same placeholder hash → second call returns the winning row.

    Models the retry-within-a-single-submission case: the placeholder's
    `IntegrityError` path re-fetches the row that won the race and returns
    it with `was_created=False`.
    """
    linker = ProjectLinker()

    seed = "deterministic submission payload"
    first = linker.link_or_create_project(_placeholder_extraction(seed))
    second = linker.link_or_create_project(_placeholder_extraction(seed))

    assert first.project_id == second.project_id
    assert first.was_created is True
    assert second.was_created is False
    assert Project.objects.filter(normalized_name=first.normalized_name).count() == 1


@pytest.mark.django_db
def test_placeholder_marks_metadata_flag():
    """PRD_F8 BR-07: placeholder rows are tagged so the recompute job can exclude them."""
    linker = ProjectLinker()

    result = linker.link_or_create_project(_placeholder_extraction("any submission"))

    row = Project.objects.get(id=result.project_id)
    assert row.metadata == {"placeholder": True}
    assert is_placeholder_normalized_name(row.normalized_name)


# ---------------------------------------------------------------------------
# CS-031 AC4 — DB UNIQUE race recovers via IntegrityError handler
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unique_constraint_race_recovers():
    """Simulate the race the `SELECT-then-INSERT` window cannot prevent.

    Real DB scenario: two transactions read `normalized_name` as missing,
    both try to INSERT, the unique constraint surfaces `IntegrityError` on
    the loser. The linker catches it and returns the winning row with
    `was_collision=True`.

    We reproduce it deterministically by stubbing the SELECT to return None
    while letting the INSERT collide with a row that was created out-of-band.
    """
    linker = ProjectLinker()
    extraction = _real_name_extraction("Residencial Lumen")

    pre_existing = Project.objects.create(
        canonical_name="Residencial Lumen",
        normalized_name=extraction.normalized,
        last_analyzed=timezone.now(),
    )

    # Force the `SELECT ... FOR UPDATE` lookup to miss so we hit the
    # IntegrityError handler, not the upsert branch.
    with patch(
        "classification.application.project_linker.Project.objects.select_for_update",
    ) as mock_sfu:
        mock_sfu.return_value.filter.return_value.first.return_value = None

        result = linker.link_or_create_project(extraction)

    assert result.project_id == pre_existing.id
    assert result.was_created is False
    assert result.was_collision is True
    assert Project.objects.filter(normalized_name=extraction.normalized).count() == 1


@pytest.mark.django_db
def test_placeholder_race_recovers_to_winner():
    """Same recovery contract, placeholder path: `was_collision=False` because
    placeholders are NEVER treated as a dedupe hit (PRD_F8 BR-07).
    """
    linker = ProjectLinker()
    extraction = _placeholder_extraction("placeholder race seed")

    pre_existing = Project.objects.create(
        canonical_name="raced placeholder",
        normalized_name=extraction.normalized,
        last_analyzed=timezone.now(),
        metadata={"placeholder": True},
    )

    # Force the placeholder INSERT to collide with the pre-existing row.
    with patch(
        "classification.application.project_linker.Project.objects.create",
        side_effect=IntegrityError("duplicate normalized_name"),
    ):
        result = linker.link_or_create_project(extraction)

    assert result.project_id == pre_existing.id
    assert result.was_created is False
    assert result.was_collision is False


# ---------------------------------------------------------------------------
# Rule 9 — normalization stays under the canonical function
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_linker_delegates_normalization():
    """ProjectLinker MUST persist whatever `normalized` the extraction carries.

    The linker never re-normalizes — that would let drift sneak in if the
    canonical function (`normalize_project_name`) changes. If a future
    refactor adds a re-normalization step, this test will catch it because
    the persisted slug will diverge from the input.
    """
    linker = ProjectLinker()
    extraction = ProjectNameExtraction(
        raw="Residencial Manzana Verde",
        normalized="manzana verde",  # canonical normalizer output
        is_placeholder=False,
        confidence=0.95,
    )

    result = linker.link_or_create_project(extraction)

    row = Project.objects.get(id=result.project_id)
    assert row.normalized_name == "manzana verde"
    # And the canonical normalizer agrees on what `Residencial Manzana Verde` yields.
    assert normalize_project_name("Residencial Manzana Verde") == "manzana verde"


@pytest.mark.django_db
def test_link_result_shape():
    """Smoke: result is a frozen `ProjectLinkResult`."""
    linker = ProjectLinker()
    result = linker.link_or_create_project(_real_name_extraction("Proyecto Norte"))

    assert isinstance(result, ProjectLinkResult)
    assert result.project_id is not None
    assert result.normalized_name
    assert result.was_created is True
    assert result.was_collision is False
