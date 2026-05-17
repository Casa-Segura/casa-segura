"""`IsInternal` DRF permission backed by a shared-secret header.

CS-110 / CS-115 need a QA-facing endpoint (``/api/v1/internal/classify``)
that runs the F2 orchestrator on raw text without going through the
public ingestion flow. The endpoint must not be reachable from the
public surface, but the production deployment does not yet have a full
auth tier, so we gate it behind a single shared secret carried in the
``X-Internal-Token`` header against the ``INTERNAL_API_TOKEN`` Django
setting.

Behaviour:

* If the setting is empty / unset, every request is denied (fail-closed
  — never reveal the endpoint without an explicit operator decision).
* Otherwise the request is allowed iff the header matches the setting
  via ``secrets.compare_digest`` (constant-time comparison so token
  validity cannot be inferred by response timing).

The header name is exposed as a module constant so the test suite and
the deployment runbook agree on the canonical spelling.
"""

from __future__ import annotations

import secrets
from typing import Final

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from django.conf import settings

INTERNAL_TOKEN_HEADER: Final[str] = "X-Internal-Token"  # noqa: S105 — header name, not a secret value
"""Header the internal endpoint consults for the shared secret.

Django normalises this into ``HTTP_X_INTERNAL_TOKEN`` on the WSGI side,
which DRF exposes via ``request.headers[INTERNAL_TOKEN_HEADER]``."""


class IsInternal(BasePermission):
    """Allow requests carrying a matching ``X-Internal-Token`` header.

    Fail-closed: if ``settings.INTERNAL_API_TOKEN`` is empty, no header
    value can satisfy the check. The presented token is compared against
    the configured token in constant time.
    """

    message = "missing or invalid X-Internal-Token"

    def has_permission(self, request: Request, view) -> bool:
        configured = getattr(settings, "INTERNAL_API_TOKEN", "") or ""
        if not configured:
            return False
        presented = request.headers.get(INTERNAL_TOKEN_HEADER, "")
        if not presented:
            return False
        return secrets.compare_digest(str(presented), str(configured))


__all__ = ["INTERNAL_TOKEN_HEADER", "IsInternal"]
