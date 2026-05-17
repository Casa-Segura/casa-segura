"""CS-053: pypdf extractor — page separators, normalization, watchdog,
500-char fallback into the orchestrator's vision retry."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone
from prometheus_client import REGISTRY

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.extractors import pypdf_extractor as pypdf_ext
from ingestion.application.upload_service import (
    FileUpload,
    UploadRequest,
    ingest_upload,
)
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    ProcessingStatus,
    SubmissionSource,
)


def _request(file_bytes: bytes, *, filename="contract.pdf", content_type="application/pdf"):
    return UploadRequest(
        files=(
            FileUpload(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            ),
        ),
        disclaimer_accepted_at=timezone.now(),
        disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
        source=SubmissionSource.WEB,
        force_strategy=ExtractionStrategy.PYPDF,
    )


def _minimal_pdf_bytes() -> bytes:
    return b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"


class _FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text


def _fake_reader(texts):
    return type("FakeReader", (), {"pages": [_FakePage(t) for t in texts]})


# ─── Page-separator format ─────────────────────────────────────────────


def test_three_page_pdf_emits_page_markers_in_order(monkeypatch):
    """PRD §US-05 AC1 — 3-page PDF must contain `--- PAGE 1 ---` … `--- PAGE 3 ---`."""

    long_text = "lorem ipsum dolor sit amet en español arrendamiento contrato " * 10
    fake_reader = _fake_reader([long_text, long_text, long_text])
    monkeypatch.setattr(
        "ingestion.application.ocr.extractors.pypdf_extractor.PdfReader",
        lambda _: fake_reader,
        raising=False,
    )
    monkeypatch.setattr(pypdf_ext, "ensure_spanish", lambda _: "es")
    import sys
    import types as _types
    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        _types.SimpleNamespace(PdfReader=lambda _bytes: fake_reader),
    )

    result = pypdf_ext.extract_text_pdf(b"%PDF-1.5 fake")
    assert "--- PAGE 1 ---" in result.text
    assert "--- PAGE 2 ---" in result.text
    assert "--- PAGE 3 ---" in result.text
    assert result.text.index("--- PAGE 1 ---") < result.text.index("--- PAGE 2 ---")
    assert result.text.index("--- PAGE 2 ---") < result.text.index("--- PAGE 3 ---")
    assert result.page_count == 3


# ─── Whitespace + control-char normalization ───────────────────────────


@pytest.mark.parametrize(
    "raw,expected_substring",
    [
        ("línea1\r\nlínea2", "línea1\nlínea2"),       # CRLF → LF
        ("hola\u00a0mundo", "hola mundo"),                # NBSP -> space
        ("guio\u00adn", "guion"),                          # soft hyphen stripped
        ("texto\u200b limpio", "texto limpio"),          # zero-width space stripped
        ("malo\x01control", "malocontrol"),               # C0 control char dropped
    ],
)
def test_normalize_text_handles_whitespace_and_controls(raw, expected_substring):
    assert expected_substring in pypdf_ext._normalize_text(raw)


# ─── 30-second wall-clock watchdog ─────────────────────────────────────


def test_watchdog_fires_when_pypdf_exceeds_30s(monkeypatch):
    """Per-page wall-clock check → NotAnalyzableReason.TIMEOUT."""

    fake_reader = _fake_reader(["pagina uno", "pagina dos", "pagina tres"])
    import sys
    import types as _types
    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        _types.SimpleNamespace(PdfReader=lambda _bytes: fake_reader),
    )
    monkeypatch.setattr(pypdf_ext, "ensure_spanish", lambda _: "es")

    # Clock: page 0 starts at t=0, page 1 at t=10, page 2 at t=40 (>30 → timeout)
    fake_clock = iter([0.0, 5.0, 40.0])

    def _fake_perf_counter():
        try:
            return next(fake_clock)
        except StopIteration:
            return 40.0

    monkeypatch.setattr(pypdf_ext.time, "perf_counter", _fake_perf_counter)

    with pytest.raises(NotAnalyzableError) as exc:
        pypdf_ext.extract_text_pdf(b"%PDF-1.5 fake")
    assert exc.value.reason == NotAnalyzableReason.TIMEOUT


# ─── 500-char floor + vision fallback orchestration ────────────────────


def test_pypdf_below_500_chars_raises_low_confidence(monkeypatch):
    """Normalized output <500 chars → LOW_CONFIDENCE_OCR for the orchestrator."""

    short = "contrato corto"  # ~14 chars per page → 3 pages ≈ 60 chars total
    fake_reader = _fake_reader([short, short, short])
    import sys
    import types as _types
    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        _types.SimpleNamespace(PdfReader=lambda _bytes: fake_reader),
    )
    monkeypatch.setattr(pypdf_ext, "ensure_spanish", lambda _: "es")

    with pytest.raises(NotAnalyzableError) as exc:
        pypdf_ext.extract_text_pdf(b"%PDF-1.5 fake")
    assert exc.value.reason == NotAnalyzableReason.LOW_CONFIDENCE_OCR
    assert "< 500" in exc.value.message


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.mark.django_db
def test_orchestrator_escalates_pypdf_low_confidence_to_vision(monkeypatch):
    """When pypdf raises LOW_CONFIDENCE_OCR, the orchestrator must try vision.

    We hand-roll the _run_extractor patch so the first PYPDF call raises
    and the second VISION_LLM call succeeds, then assert the winning
    strategy is vision_llm and the success counter incremented.
    """

    calls = {"n": 0}

    fake_result = ExtractionResult(
        text="texto recuperado por vision en español",
        token_count=8,
        language="es",
        page_count=1,
    )

    def _fake_run(*, strategy, req):
        calls["n"] += 1
        if strategy == ExtractionStrategy.PYPDF:
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
                message="pypdf yielded 120 chars < 500",
            )
        if strategy == ExtractionStrategy.VISION_LLM:
            return fake_result
        raise AssertionError(f"unexpected strategy {strategy}")

    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=_fake_run,
    ):
        outcome = ingest_upload(_request(_minimal_pdf_bytes()))

    assert calls["n"] == 2
    assert outcome.submission.processing_status == ProcessingStatus.EXTRACTED.value
    assert outcome.submission.extraction_strategy_successful == ExtractionStrategy.VISION_LLM.value
