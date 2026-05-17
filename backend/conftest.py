"""Root pytest configuration for Casa Segura backend (CS-032).

Reset strategy: **transactional rollback per test** (pytest-django default
via `@pytest.mark.django_db`). Each test runs inside a transaction that is
rolled back on teardown, so the database returns to its post-migration
state without re-running migrations. This is ~10x faster than truncate.

Use `@pytest.mark.django_db(transaction=True)` for tests that need to
verify DB-level constraint triggers, multi-connection visibility, or
the `reject_catalog_mutation` trigger from CS-030 — those cannot run
inside a wrapping transaction.

Run with `--reuse-db` after the first run for further speedup; CI uses
a fresh container per run (see CS-035)."""

from __future__ import annotations

import httpx
import pytest
import respx


@pytest.fixture(autouse=True)
def _enable_db_for_marker(request, db):
    """Touch the `db` fixture for tests that don't explicitly mark django_db.

    NOTE: pytest-django requires `@pytest.mark.django_db` per test. This
    autouse shim is intentionally NOT defined so we keep the contract
    explicit — remove the comment below and uncomment if you want
    implicit DB access:

        return db
    """
    return None


# ---------------------------------------------------------------------------
# OpenRouter test plumbing (CS-110 PR-2). Consolidates the respx + sleep
# patches that previously lived inline in each LLM-touching test module
# (see `tests/test_openrouter_client.py`, `tests/test_ingestion_pixtral.py`).
# Callers opt in by depending on `mock_openrouter`; the fixture also patches
# `time.sleep` so retry backoffs do not actually sleep.
# ---------------------------------------------------------------------------


OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"


@pytest.fixture
def mock_openrouter(monkeypatch):
    """Yield a respx MockRouter with neutralized retry sleep.

    Usage:

        def test_x(mock_openrouter):
            mock_openrouter.post(f"{OPENROUTER_BASE_URL}/chat/completions").mock(
                return_value=httpx.Response(200, json={...})
            )

    The fixture is intentionally not autouse: tests that exercise real HTTP
    paths (or want to assert real backoff timing) opt out by not depending
    on it.
    """
    monkeypatch.setattr("shared.llm.openrouter.time.sleep", lambda _: None)
    with respx.mock(assert_all_called=False) as router:
        yield router


def openrouter_response(payload: dict, *, status: int = 200) -> httpx.Response:
    """Build the canonical OpenRouter chat-completion envelope around `payload`.

    `payload` is the JSON the LLM is supposed to have returned in
    ``choices[0].message.content``. The helper renders it as a JSON string
    inside the envelope so callers do not duplicate the wrapping boilerplate.
    """
    import json as _json

    return httpx.Response(
        status,
        json={
            "choices": [{"message": {"content": _json.dumps(payload)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001},
        },
    )
