"""Django system checks for EPIC-12 project verification (CS-356 / CS-353)."""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register


@register()
def reputation_http_adapter_requires_ready_flag(app_configs, **kwargs) -> list:
    """HTTP reputation adapter opts in only with explicit readiness review."""
    provider = getattr(settings, "PROJECT_REPUTATION_PROVIDER", "none")
    normalized = provider.strip().lower() if isinstance(provider, str) else "none"

    adapter_ready = bool(getattr(settings, "PROJECT_REPUTATION_ADAPTER_READY", False))

    if normalized == "http" and not adapter_ready:
        return [
            Error(
                (
                    "PROJECT_REPUTATION_PROVIDER=http requires PROJECT_REPUTATION_ADAPTER_READY=true "
                    "after SSRF/host allowlist configuration review."
                ),
                hint="Use PROJECT_REPUTATION_PROVIDER=none|stub until the adapter is deployed safely.",
                id="project_verification.E001",
            )
        ]

    unknown = normalized not in _ALLOWED_REPUTATION_PROVIDERS_FOR_STARTUP_CHECK
    if normalized and unknown:
        return [
            Error(
                "Unknown PROJECT_REPUTATION_PROVIDER; allowed values controlled by EPIC-12 registry.",
                hint=f"Got {normalized!r}. Use one of {sorted(_ALLOWED_REPUTATION_PROVIDERS_FOR_STARTUP_CHECK)}.",
                id="project_verification.E002",
            )
        ]

    return []


_ALLOWED_REPUTATION_PROVIDERS_FOR_STARTUP_CHECK = frozenset(
    ("", "none", "stub", "http"),
)
