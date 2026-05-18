"""OpenRouter chat-completions client (CS-006).

Single entry point for any backend code that needs to call OpenRouter.
Wraps `httpx.Client` with:

  * Mandatory headers (`Authorization`, `HTTP-Referer`, `X-Title`).
  * Exponential backoff retry on 5xx and network errors.
  * Configurable timeout pulled from Django settings.
  * Stable error envelope (`OpenRouterError`) so callers can map failures
    to `ProcessingStatus.FAILED_EXTRACTION` without leaking provider quirks.

The client is intentionally synchronous: ingestion runs inside Celery
workers, and the retry loop is simpler than juggling asyncio inside a
Django request lifecycle. If a future caller needs async, wrap this in
`anyio.to_thread.run_sync`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from django.conf import settings

from shared.observability.pipeline_metrics import OPENROUTER_REQUEST_DURATION

logger = structlog.get_logger(__name__)


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter fails after all retries.

    Carries the HTTP status (if any) and the upstream payload so callers can
    record a stable `error_code` against `OcrJob` / `ProcessingStatus`.
    """

    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class ChatCompletionResult:
    """Subset of the OpenRouter response that callers actually consume."""

    content: str
    tokens_prompt: int | None
    tokens_completion: int | None
    cost_usd_cents: int | None
    raw: dict[str, Any]


class OpenRouterClient:
    """Synchronous client for `${OPENROUTER_BASE_URL}/chat/completions`.

    Use as a short-lived context manager (`with OpenRouterClient() as c:`)
    so the underlying HTTPX transport closes deterministically, or call
    `close()` manually.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        http_referer: str | None = None,
        x_title: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.OPENROUTER_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.OPENROUTER_MAX_RETRIES
        self.http_referer = http_referer or settings.OPENROUTER_HTTP_REFERER
        self.x_title = x_title or settings.OPENROUTER_X_TITLE

        if not self.api_key:
            # Defer to call-time: tests may construct the client without a key
            # and inject a `respx` transport that never hits the network.
            logger.warning("openrouter.client.missing_api_key")

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
            transport=transport,
        )

    def __enter__(self) -> OpenRouterClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        plugins: list[dict[str, Any]] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ChatCompletionResult:
        """POST `/chat/completions` and return the first choice.

        `plugins` is optional: pass it (e.g. `[{"id": "file-parser",
        "pdf": {"engine": "mistral-ocr"}}]`) for PDF documents so the
        Mistral OCR pre-parser runs before the model. Image (`image_url`)
        and pure-text payloads MUST NOT carry plugins.
        """

        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured", status_code=None)

        body: dict[str, Any] = {"model": model, "messages": messages}
        if plugins:
            body["plugins"] = plugins
        if extra_body:
            body.update(extra_body)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.x_title,
        }

        def _observe_error(seconds: float) -> None:
            OPENROUTER_REQUEST_DURATION.labels(model=model, outcome="error").observe(seconds)

        wall_start = time.perf_counter()
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            req_start = time.perf_counter()
            try:
                response = self._client.post("/chat/completions", json=body, headers=headers)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                _observe_error(time.perf_counter() - req_start)
                logger.warning(
                    "openrouter.transport_error",
                    attempt=attempt,
                    error=str(exc),
                    model=model,
                )
                self._sleep_backoff(attempt)
                continue

            if response.status_code >= 500:
                last_exc = OpenRouterError(
                    f"OpenRouter 5xx: {response.status_code}",
                    status_code=response.status_code,
                    payload=_safe_json(response),
                )
                _observe_error(time.perf_counter() - req_start)
                logger.warning(
                    "openrouter.upstream_5xx",
                    attempt=attempt,
                    status_code=response.status_code,
                    model=model,
                )
                self._sleep_backoff(attempt)
                continue

            if response.status_code >= 400:
                _observe_error(time.perf_counter() - req_start)
                raise OpenRouterError(
                    f"OpenRouter {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                    payload=_safe_json(response),
                )

            try:
                payload = response.json()
                parsed = _parse_response(payload)
            except OpenRouterError:
                _observe_error(time.perf_counter() - req_start)
                raise

            elapsed_ms = round((time.perf_counter() - req_start) * 1000)
            OPENROUTER_REQUEST_DURATION.labels(model=model, outcome="success").observe(elapsed_ms / 1000.0)
            logger.info(
                "openrouter.chat_completion.completed",
                model=model,
                elapsed_ms=elapsed_ms,
                attempt=attempt,
            )
            return parsed

        # Exhausted retries.
        elapsed_ms_total = round((time.perf_counter() - wall_start) * 1000)
        logger.warning(
            "openrouter.chat_completion.exhausted_retries",
            model=model,
            attempts=self.max_retries,
            elapsed_ms_total=elapsed_ms_total,
        )
        raise OpenRouterError(
            "OpenRouter exhausted retries",
            status_code=getattr(last_exc, "status_code", None),
            payload=getattr(last_exc, "payload", None),
        ) from last_exc

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        # 1, 2, 4 seconds (capped at 8s) for attempts 1..N.
        delay = min(2 ** (attempt - 1), 8)
        time.sleep(delay)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:1000]}


def _parse_response(payload: dict[str, Any]) -> ChatCompletionResult:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError(
            "OpenRouter response missing choices[0].message.content",
            status_code=200,
            payload=payload,
        ) from exc

    usage = payload.get("usage") or {}
    cost_usd = usage.get("cost")  # OpenRouter returns float USD when available
    cost_cents = round(cost_usd * 100) if isinstance(cost_usd, (int, float)) else None

    if isinstance(content, list):
        # When the response includes structured parts (e.g. tool calls), join
        # the text parts so downstream code keeps treating it as a string.
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        content = "".join(text_parts)

    return ChatCompletionResult(
        content=content or "",
        tokens_prompt=usage.get("prompt_tokens"),
        tokens_completion=usage.get("completion_tokens"),
        cost_usd_cents=cost_cents,
        raw=payload,
    )
