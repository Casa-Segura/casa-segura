"""Salvadoran permit format heuristic tests (EPIC-12 / CS-352)."""

from __future__ import annotations

import pytest

from project_verification.domain.permit_format import PermitFormatVerdict, evaluate_permit_format


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("P-2024-001", PermitFormatVerdict.OK),
        ("dgmp-442-01", PermitFormatVerdict.OK),
        ("MUN-SS-8844", PermitFormatVerdict.OK),
        ("EXP-00010294", PermitFormatVerdict.OK),
        ("RES-1200-2024", PermitFormatVerdict.OK),
    ],
)
def test_positive_templates(raw: str, expected: PermitFormatVerdict):
    assert evaluate_permit_format(raw).verdict == expected


def test_whitespace_normalized():
    assert evaluate_permit_format("\t DGMP-442-01 \r\n").verdict == PermitFormatVerdict.OK


def test_free_text_unknown():
    assert evaluate_permit_format("texto muy libre sobre el permiso").verdict == PermitFormatVerdict.UNKNOWN


def test_case_fold_matches_year_serial():
    assert evaluate_permit_format("p-2024-001").verdict == evaluate_permit_format("P-2024-001").verdict
