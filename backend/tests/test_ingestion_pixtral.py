"""CS-054: Pixtral payload shape (image vs PDF) + happy path via respx."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from ingestion.application.ocr.errors import NotAnalyzableError, NotAnalyzableReason
from ingestion.application.ocr.extractors.pixtral import extract_via_pixtral
from shared.llm.openrouter import OpenRouterClient

BASE_URL = "https://openrouter.ai/api/v1"


@pytest.fixture(autouse=True)
def fast_backoff(monkeypatch):
    monkeypatch.setattr("shared.llm.openrouter.time.sleep", lambda _: None)


@pytest.fixture
def mock_router():
    with respx.mock(assert_all_called=False) as router:
        yield router


def _client():
    return OpenRouterClient(
        api_key="sk-or-v1-test",
        base_url=BASE_URL,
        timeout_seconds=5,
        max_retries=1,
        http_referer="https://test.local",
        x_title="Test",
    )


def _spanish_ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": "Este contrato establece las cláusulas de arrendamiento del inmueble."}}
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34, "cost": 0.005},
        },
    )


def test_image_payload_uses_image_url_block_without_plugins(mock_router, settings):
    settings.OPENROUTER_OCR_MODEL = "mistralai/pixtral-large-2411"
    settings.OPENROUTER_PDF_PLUGIN_ENGINE = "mistral-ocr"

    route = mock_router.post(f"{BASE_URL}/chat/completions").mock(return_value=_spanish_ok_response())

    client = _client()
    result = extract_via_pixtral(
        file_bytes=b"\xff\xd8\xff\xe0fake-jpeg",
        content_type="image/jpeg",
        filename="contract.jpg",
        client=client,
    )

    sent = json.loads(route.calls.last.request.read())
    blocks = sent["messages"][0]["content"]
    types = [b["type"] for b in blocks]
    assert "image_url" in types
    assert "file" not in types
    assert "plugins" not in sent  # NO plugin for images

    assert result.text.startswith("Este contrato")
    assert result.language == "es"
    assert result.tokens_consumed == 12 + 34


def test_pdf_payload_uses_file_block_with_mistral_ocr_plugin(mock_router, settings):
    settings.OPENROUTER_OCR_MODEL = "mistralai/pixtral-large-2411"
    settings.OPENROUTER_PDF_PLUGIN_ENGINE = "mistral-ocr"

    route = mock_router.post(f"{BASE_URL}/chat/completions").mock(return_value=_spanish_ok_response())

    client = _client()
    extract_via_pixtral(
        file_bytes=b"%PDF-1.5 fake",
        content_type="application/pdf",
        filename="contract.pdf",
        client=client,
    )

    sent = json.loads(route.calls.last.request.read())
    blocks = sent["messages"][0]["content"]
    types = [b["type"] for b in blocks]
    assert "file" in types
    assert "image_url" not in types
    assert sent["plugins"] == [{"id": "file-parser", "pdf": {"engine": "mistral-ocr"}}]
    file_block = next(b for b in blocks if b["type"] == "file")
    assert file_block["file"]["filename"] == "contract.pdf"
    expected_data_url = "data:application/pdf;base64," + base64.b64encode(b"%PDF-1.5 fake").decode("ascii")
    assert file_block["file"]["file_data"] == expected_data_url


def test_empty_bytes_rejected(settings):
    settings.OPENROUTER_OCR_MODEL = "mistralai/pixtral-large-2411"
    with pytest.raises(NotAnalyzableError) as exc:
        extract_via_pixtral(
            file_bytes=b"",
            content_type="image/png",
            filename="x.png",
            client=_client(),
        )
    assert exc.value.reason == NotAnalyzableReason.EMPTY_FILE


def test_unsupported_mime_rejected(settings):
    settings.OPENROUTER_OCR_MODEL = "mistralai/pixtral-large-2411"
    with pytest.raises(NotAnalyzableError) as exc:
        extract_via_pixtral(
            file_bytes=b"data",
            content_type="text/plain",
            filename="x.txt",
            client=_client(),
        )
    assert exc.value.reason == NotAnalyzableReason.UNSUPPORTED_FORMAT


def test_openrouter_error_maps_to_upstream_llm_error(mock_router, settings):
    settings.OPENROUTER_OCR_MODEL = "mistralai/pixtral-large-2411"
    mock_router.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(503, json={"error": "down"}))

    with pytest.raises(NotAnalyzableError) as exc:
        extract_via_pixtral(
            file_bytes=b"\xff\xd8\xff",
            content_type="image/jpeg",
            filename="x.jpg",
            client=_client(),
        )
    assert exc.value.reason == NotAnalyzableReason.UPSTREAM_LLM_ERROR
