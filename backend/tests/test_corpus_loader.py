"""CS-080: loader parses real corpus markdown."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus.application.loader import laws_summary, load_corpus_markdown


CORPUS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "RAG Legal context"


@pytest.fixture(scope="module")
def parsed():
    if not CORPUS_ROOT.exists():
        pytest.skip("legal corpus markdown not present in this checkout")
    return load_corpus_markdown(CORPUS_ROOT)


def test_loader_finds_seven_canonical_files(parsed):
    assert len(parsed) == 7


def test_loader_marks_stub_file(parsed):
    by_law = {law.law_id: law for law in parsed}
    assert "pendiente-asamblea-d491c5c6" in by_law
    assert by_law["pendiente-asamblea-d491c5c6"].is_stub is True


def test_loader_extracts_inquilinato_metadata(parsed):
    by_law = {law.law_id: law for law in parsed}
    inquilinato = by_law["ley-inquilinato"]
    assert inquilinato.short_title.lower().startswith("inquilinato")
    assert inquilinato.source_url.startswith("https://")
    assert inquilinato.status in {"in_force", "in_force_with_amendments"}


def test_laws_summary_serialisable(parsed):
    summary = laws_summary(parsed)
    assert "laws" in summary
    assert any(item.get("is_stub") for item in summary["laws"])
