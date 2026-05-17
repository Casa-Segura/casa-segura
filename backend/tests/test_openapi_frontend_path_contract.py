"""OpenAPI drift guard — paths the Next.js server bridge hard-codes stay documented.

Keeps ingestion + project-verification contracts aligned with FE defaults in
frontend/src/server/contract-env.ts and frontend/src/server/project-verification-backend.ts.
"""

from __future__ import annotations

import pytest

from django.test import Client

# Paths must appear as keys in drf-spectacular output (mounted under Django URL prefix).
_EXPECTED_SCHEMA_PATH_KEYS: frozenset[str] = frozenset(
    {
        "/api/v1/project-verification/billboard-upload/",
        "/api/v1/project-verification/demo-result/",
        "/api/v1/project-verification/manual/",
        "/api/v1/submissions/",
        "/api/v1/submissions/{submission_id}/",
    }
)


@pytest.mark.django_db
def test_openapi_schema_includes_frontend_bridge_paths():
    """Schema generation succeeds and lists paths required by Casa Segura server actions."""

    client = Client()
    resp = client.get(
        "/api/v1/schema/schema/",
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )
    assert resp.status_code == 200, resp.content.decode()[:400]
    body = resp.json()
    documented = frozenset(body.get("paths", {}).keys())

    missing = sorted(_EXPECTED_SCHEMA_PATH_KEYS - documented)
    assert not missing, (
        "OpenAPI schema missing frontend bridge paths; update DRF URLs or regenerate "
        "FE defaults if intentional — missing paths: " + ", ".join(missing)
    )
