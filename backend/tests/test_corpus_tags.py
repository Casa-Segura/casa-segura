"""CS-082: tag normalization."""

from __future__ import annotations

import pytest

from corpus.application.tags import normalize_tag, normalize_tags


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Arrendamiento", "arrendamiento"),
        ("  Ñoño  ", "nono"),
        ("Cláusula nula", "clausula_nula"),
        ("rental-contracts", "rental_contracts"),
        ("Multi   Spaces", "multi_spaces"),
        ("", ""),
        ("---", ""),
    ],
)
def test_normalize_tag_strips_accents_and_punctuation(raw, expected):
    assert normalize_tag(raw) == expected


def test_normalize_tags_dedupes_preserving_order():
    assert normalize_tags(["Arrendamiento", "ARRENDAMIENTO", "Cláusula nula", "arrendamiento"]) == [
        "arrendamiento",
        "clausula_nula",
    ]


def test_normalize_tags_ignores_falsy():
    assert normalize_tags(["", None, "---", "  ", "tag"]) == ["tag"]
