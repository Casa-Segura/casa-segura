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

import pytest


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
