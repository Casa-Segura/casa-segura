"""CS-055: Tesseract Spanish fallback — mean-confidence gate + BVA."""

from __future__ import annotations

import io
import sys
import types
from unittest.mock import MagicMock

import pytest
from PIL import Image

from ingestion.application.ocr.errors import NotAnalyzableError, NotAnalyzableReason
from ingestion.application.ocr.extractors import tesseract as tesseract_extractor


@pytest.fixture
def fake_pytesseract(monkeypatch):
    """Inject a fake `pytesseract` module so the test never needs the
    real binary. Returns the mock so each test can program its
    ``image_to_data`` response."""

    fake = types.ModuleType("pytesseract")
    fake.Output = types.SimpleNamespace(DICT="dict")
    fake.TesseractNotFoundError = type("TesseractNotFoundError", (Exception,), {})
    fake.TesseractError = type("TesseractError", (Exception,), {})
    fake.image_to_data = MagicMock()
    monkeypatch.setitem(sys.modules, "pytesseract", fake)
    return fake


def _png_bytes() -> bytes:
    """Generate an in-memory 32x32 white PNG so PIL.Image.open succeeds."""

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def spanish_image(monkeypatch):
    """Bypass langdetect to a deterministic 'es' so tests focus on the gate."""

    monkeypatch.setattr(tesseract_extractor, "ensure_spanish", lambda _: "es")
    return _png_bytes()


def _set_min_confidence(settings, value):
    settings.OCR_TESSERACT_ENABLED = True
    settings.OCR_TESSERACT_LANG = "spa"
    settings.OCR_TESSERACT_MIN_CONFIDENCE = value


def test_mean_confidence_below_threshold_fails(settings, fake_pytesseract, spanish_image):
    """Mean = 59.9 < 60.0 → LOW_CONFIDENCE_OCR (PRD §US-07 AC3 lower bound)."""

    _set_min_confidence(settings, 60)
    fake_pytesseract.image_to_data.return_value = {
        "text": ["arrendamiento", "del", "inmueble"],
        # mean = (50 + 60 + 69.7) / 3 = 59.9
        "conf": [50, 60, 69.7],
    }

    with pytest.raises(NotAnalyzableError) as exc:
        tesseract_extractor.extract_via_tesseract(
            file_bytes=spanish_image,
            content_type="image/png",
        )
    assert exc.value.reason == NotAnalyzableReason.LOW_CONFIDENCE_OCR


def test_mean_confidence_at_threshold_passes(settings, fake_pytesseract, spanish_image):
    """Mean = 60.0 → PRD comparator `>= 60` → passes."""

    _set_min_confidence(settings, 60)
    fake_pytesseract.image_to_data.return_value = {
        "text": ["arrendamiento", "del", "inmueble"],
        # mean = (50 + 60 + 70) / 3 = 60.0 exactly
        "conf": [50, 60, 70],
    }

    result = tesseract_extractor.extract_via_tesseract(
        file_bytes=spanish_image,
        content_type="image/png",
    )
    assert "arrendamiento" in result.text


def test_mean_confidence_above_threshold_passes(settings, fake_pytesseract, spanish_image):
    """Mean = 60.1 → above threshold → passes."""

    _set_min_confidence(settings, 60)
    fake_pytesseract.image_to_data.return_value = {
        "text": ["arrendamiento", "del", "inmueble"],
        # mean = (60 + 60 + 60.3) / 3 = 60.1
        "conf": [60, 60, 60.3],
    }

    result = tesseract_extractor.extract_via_tesseract(
        file_bytes=spanish_image,
        content_type="image/png",
    )
    assert "del" in result.text


def test_negative_conf_placeholders_excluded_from_mean(settings, fake_pytesseract, spanish_image):
    """Tesseract returns `-1` for layout boxes; mean must ignore them."""

    _set_min_confidence(settings, 60)
    fake_pytesseract.image_to_data.return_value = {
        "text": ["arrendamiento", "del", "inmueble"],
        # mean ignoring -1 = (60 + 70) / 2 = 65 → passes
        "conf": [-1, 60, 70],
    }

    result = tesseract_extractor.extract_via_tesseract(
        file_bytes=spanish_image,
        content_type="image/png",
    )
    assert result.text  # not empty


def test_disabled_short_circuits_before_any_pytesseract_call(settings):
    """OCR_TESSERACT_ENABLED=false → OCR_UNAVAILABLE without invoking pytesseract."""

    settings.OCR_TESSERACT_ENABLED = False
    with pytest.raises(NotAnalyzableError) as exc:
        tesseract_extractor.extract_via_tesseract(
            file_bytes=_png_bytes(),
            content_type="image/png",
        )
    assert exc.value.reason == NotAnalyzableReason.OCR_UNAVAILABLE
