"""CS-006: OpenRouter client behaviour under happy and failure paths.

Uses `respx` to mock the outbound HTTP layer; no real network calls.
"""

from __future__ import annotations

import logging

import httpx
import pytest
import respx

from shared.llm.openrouter import OpenRouterClient, OpenRouterError

BASE_URL = "https://openrouter.ai/api/v1"


def _client(**overrides) -> OpenRouterClient:
    defaults = dict(
        api_key="sk-or-v1-test",
        base_url=BASE_URL,
        timeout_seconds=5,
        max_retries=3,
        http_referer="https://test.local",
        x_title="Test",
    )
    defaults.update(overrides)
    return OpenRouterClient(**defaults)


@pytest.fixture(autouse=True)
def fast_backoff(monkeypatch):
    """Don't actually sleep between retries in unit tests."""
    monkeypatch.setattr("shared.llm.openrouter.time.sleep", lambda _: None)


@pytest.fixture
def mock_router():
    with respx.mock(assert_all_called=False) as router:
        yield router


def test_chat_completion_returns_content_and_usage(mock_router):
    mock_router.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "extracted text"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0123},
            },
        )
    )

    with _client() as client:
        result = client.chat_completion(
            model="mistralai/pixtral-large-2411",
            messages=[{"role": "user", "content": "hello"}],
        )

    assert result.content == "extracted text"
    assert result.tokens_prompt == 10
    assert result.tokens_completion == 5
    assert result.cost_usd_cents == 1  # 0.0123 USD -> 1 cent (rounded)


def test_chat_completion_logs_completed_event(mock_router, caplog):
    mock_router.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "extracted text"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0123},
            },
        )
    )

    with caplog.at_level(logging.INFO, logger="shared.llm.openrouter"):
        with _client() as client:
            client.chat_completion(
                model="mistralai/pixtral-large-2411",
                messages=[{"role": "user", "content": "hello"}],
            )

    merged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "openrouter.chat_completion.completed" in merged


def test_chat_completion_injects_plugins_for_pdf(mock_router):
    route = mock_router.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )

    with _client() as client:
        client.chat_completion(
            model="mistralai/pixtral-large-2411",
            messages=[{"role": "user", "content": "x"}],
            plugins=[{"id": "file-parser", "pdf": {"engine": "mistral-ocr"}}],
        )

    sent = route.calls.last.request.read().decode()
    assert "file-parser" in sent
    assert "mistral-ocr" in sent
    # Required tracking headers
    headers = route.calls.last.request.headers
    assert headers["authorization"] == "Bearer sk-or-v1-test"
    assert headers["http-referer"] == "https://test.local"
    assert headers["x-title"] == "Test"


def test_retry_on_5xx_then_success(mock_router):
    mock_router.post(f"{BASE_URL}/chat/completions").mock(
        side_effect=[
            httpx.Response(503, json={"error": "busy"}),
            httpx.Response(503, json={"error": "busy"}),
            httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
        ]
    )

    with _client(max_retries=3) as client:
        result = client.chat_completion(
            model="m",
            messages=[{"role": "user", "content": "x"}],
        )

    assert result.content == "ok"


def test_4xx_does_not_retry(mock_router):
    route = mock_router.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(400, json={"error": "bad model"})
    )

    with _client(max_retries=3) as client:
        with pytest.raises(OpenRouterError) as exc:
            client.chat_completion(
                model="m",
                messages=[{"role": "user", "content": "x"}],
            )

    assert exc.value.status_code == 400
    assert route.call_count == 1


def test_missing_api_key_raises_at_call_time():
    client = _client(api_key="")
    with pytest.raises(OpenRouterError) as exc:
        client.chat_completion(model="m", messages=[{"role": "user", "content": "x"}])
    assert exc.value.status_code is None


def test_exhausted_retries_raise(mock_router, caplog):
    mock_router.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(500, json={"error": "boom"}))

    with caplog.at_level(logging.WARNING, logger="shared.llm.openrouter"):
        with _client(max_retries=2) as client:
            with pytest.raises(OpenRouterError):
                client.chat_completion(
                    model="m",
                    messages=[{"role": "user", "content": "x"}],
                )

    merged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "openrouter.chat_completion.exhausted_retries" in merged


def test_response_without_content_raises(mock_router):
    mock_router.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(200, json={"choices": []}))

    with _client() as client:
        with pytest.raises(OpenRouterError):
            client.chat_completion(
                model="m",
                messages=[{"role": "user", "content": "x"}],
            )
