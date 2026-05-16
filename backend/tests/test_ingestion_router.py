"""CS-052: routing decisions for `ocr.detect_kind`."""

from __future__ import annotations

from ingestion.application.ocr.router import detect_kind
from ingestion.domain.enums import ExtractionStrategy, FileFormat


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
