"""CS-081: chunker behaviour + BVA around the 1500-char boundary."""

from __future__ import annotations

import pytest

from corpus.application.chunker import CHUNK_CHAR_BOUNDARY, chunk_law
from corpus.application.loader import ParsedLaw


def _law(body: str, *, is_stub: bool = False) -> ParsedLaw:
    return ParsedLaw(
        law_id="test-law",
        title="Test Law",
        short_title="Test",
        decree="",
        issued_at=None,
        official_gazette="",
        last_verified=None,
        source_url="",
        subject="",
        status="in_force",
        body=body,
        content_hash="deadbeef",
        is_stub=is_stub,
        raw_frontmatter={"covers": ["arrendamiento", "Cláusula nula"]},
    )


def test_chunker_returns_empty_for_stub_law():
    law = _law("### Art. 1 — Pendiente\nContenido pendiente", is_stub=True)
    assert chunk_law(law) == []


def test_chunker_returns_one_chunk_per_article():
    body = "### Art. 1 — Primero\nTexto del primero.\n\n" "### Art. 2 — Segundo\nTexto del segundo."
    drafts = chunk_law(_law(body))
    assert [d.article_number for d in drafts] == ["Art. 1", "Art. 2"]
    assert all(d.anchor.startswith("art-") for d in drafts)


def test_chunker_carries_law_level_tags():
    body = "### Art. 1 — Único\nContenido."
    drafts = chunk_law(_law(body))
    assert drafts[0].tags == ["arrendamiento", "clausula_nula"]


# ─── BVA: 1500-char boundary ────────────────────────────────────────────


def _article_of(length: int) -> str:
    filler_paragraph = ("Lorem ipsum dolor sit amet. " * 5).strip() + "\n\n"
    body = "### Art. 1 — Bordes\n"
    # Build body up to the desired length.
    while len(body) < length + len("### Art. 1 — Bordes\n"):
        body += filler_paragraph
    return body[: length + len("### Art. 1 — Bordes\n")]


# Length is filler after the markdown heading (`### Art. 1 …` is counted by the
# chunker). With CHUNK_CHAR_BOUNDARY=1500 and a 20-char heading, one chunk iff
# 20 + length <= 1500 i.e. length <= 1480.


@pytest.mark.parametrize(
    "length,expected_chunks",
    [
        (1479, 1),
        (1480, 1),
        (1481, 2),  # crosses boundary → splits on paragraphs / hard slice
    ],
)
def test_chunker_bva_around_1500_chars(length, expected_chunks):
    drafts = chunk_law(_law(_article_of(length)))
    assert len(drafts) == expected_chunks


def test_chunker_handles_very_long_paragraph():
    long_paragraph = "a" * (CHUNK_CHAR_BOUNDARY * 3 + 5)
    body = f"### Art. 1 — Largo\n{long_paragraph}"
    drafts = chunk_law(_law(body))
    # Should hard-slice into ≥3 chunks (the hard-slice fallback).
    assert len(drafts) >= 3
