"""CS-052: routing decisions for `ocr.detect_kind`.

Covers MIME-based dispatch, the PRD §US-04 100-char native-text threshold
(BVA at 99 / 100 / 101) and the `force_strategy` QA override.
"""

from __future__ import annotations

from unittest.mock import patch

from ingestion.application.ocr.router import detect_kind
from ingestion.domain.enums import ExtractionStrategy, FileFormat


# ─── MIME-based dispatch ────────────────────────────────────────────────


def test_image_jpeg_routes_to_pixtral():
    decision = detect_kind(content_type="image/jpeg", file_bytes=b"\xff\xd8\xff\xe0", filename="x.jpg")
    assert decision.strategy == ExtractionStrategy.VISION_LLM
    assert decision.file_format == FileFormat.JPEG


def test_image_png_routes_to_pixtral():
    decision = detect_kind(content_type="image/png", file_bytes=b"\x89PNG", filename="x.png")
    assert decision.strategy == ExtractionStrategy.VISION_LLM


def test_pdf_without_native_text_routes_to_pixtral():
    # A minimal non-text PDF: pypdf won't extract anything.
    pdf = b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
    decision = detect_kind(content_type="application/pdf", file_bytes=pdf, filename="x.pdf")
    assert decision.strategy == ExtractionStrategy.VISION_LLM
    assert decision.file_format == FileFormat.PDF


def test_unknown_mime_falls_back_to_tesseract():
    decision = detect_kind(content_type="application/octet-stream", file_bytes=b"???", filename="weird")
    assert decision.strategy == ExtractionStrategy.TESSERACT


# ─── BVA: PRD §US-04 100-char native-text threshold ────────────────────


def _decision_with_probe(stripped_len: int):
    """Patch the pypdf probe so it returns text of `stripped_len` non-whitespace chars."""

    probe_text = "a" * stripped_len
    fake_page = type("FakePage", (), {"extract_text": staticmethod(lambda: probe_text)})
    fake_reader = type("FakeReader", (), {"pages": [fake_page]})

    with patch("pypdf.PdfReader", return_value=fake_reader):
        return detect_kind(
            content_type="application/pdf",
            file_bytes=b"%PDF-1.5 fake",
            filename="x.pdf",
        )


def test_pdf_first_page_99_chars_routes_to_vision():
    """≤ 100 chars on first page → scanned PDF → vision."""
    decision = _decision_with_probe(99)
    assert decision.strategy == ExtractionStrategy.VISION_LLM
    assert decision.reason == "scanned_pdf_routed_to_pixtral"


def test_pdf_first_page_100_chars_routes_to_vision():
    """PRD comparator `> 100`: exactly 100 chars is below the threshold → vision."""
    decision = _decision_with_probe(100)
    assert decision.strategy == ExtractionStrategy.VISION_LLM


def test_pdf_first_page_101_chars_routes_to_pypdf():
    """> 100 chars on first page → native-text PDF → pypdf."""
    decision = _decision_with_probe(101)
    assert decision.strategy == ExtractionStrategy.PYPDF
    assert decision.reason == "pdf_with_extractable_text"


# ─── force_strategy QA override ────────────────────────────────────────


def test_force_strategy_overrides_automatic_routing_for_pdf():
    """Even on a native-text PDF, force_strategy=VISION_LLM wins."""
    decision = _decision_with_probe(500)
    assert decision.strategy == ExtractionStrategy.PYPDF  # baseline

    fake_page = type("FakePage", (), {"extract_text": staticmethod(lambda: "a" * 500)})
    fake_reader = type("FakeReader", (), {"pages": [fake_page]})
    with patch("pypdf.PdfReader", return_value=fake_reader):
        forced = detect_kind(
            content_type="application/pdf",
            file_bytes=b"%PDF-1.5 fake",
            filename="x.pdf",
            force_strategy=ExtractionStrategy.VISION_LLM,
        )
    assert forced.strategy == ExtractionStrategy.VISION_LLM
    assert forced.reason == "forced_vision_llm"


def test_force_strategy_overrides_image_to_tesseract():
    """Images normally go to Pixtral; force_strategy=TESSERACT honours the override."""
    decision = detect_kind(
        content_type="image/jpeg",
        file_bytes=b"\xff\xd8\xff",
        filename="x.jpg",
        force_strategy=ExtractionStrategy.TESSERACT,
    )
    assert decision.strategy == ExtractionStrategy.TESSERACT
    assert decision.reason == "forced_tesseract"


def test_force_strategy_pypdf_on_image_is_honoured_but_extractor_decides_failure():
    """The router blindly honours the override; downstream extractors decide
    whether they can handle the input. Routing must not silently drop the flag."""
    decision = detect_kind(
        content_type="image/png",
        file_bytes=b"\x89PNG",
        filename="x.png",
        force_strategy=ExtractionStrategy.PYPDF,
    )
    assert decision.strategy == ExtractionStrategy.PYPDF
    assert decision.reason == "forced_pypdf"
