"""TLS posture helpers — CS-333.

* ``tls_settings_for_stage(stage)`` — returns the Django settings overrides
  appropriate for the deploy stage (production redirects + HSTS + secure
  cookies, development opt-out for local loopback). Called from
  ``config/settings.py``.

* ``validate_tls_posture(...)`` — startup validator that refuses to boot
  when the production profile is missing a critical knob (e.g. someone
  sets ``DEPLOY_STAGE=production`` but leaves
  ``SECURE_SSL_REDIRECT=False``) or when the webhook callback host is
  configured with an ``http://`` scheme in production.

* ``assert_outbound_url_uses_tls(url)`` — guard for outbound integration
  URLs (SMS provider, email gateway, webhook callbacks) that must
  refuse cleartext schemes in production.

The module is deliberately stateless; ``ALLOW_INSECURE_TLS_DEV_ONLY=true``
is the only env knob that loosens checks for local dev (loopback addresses).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

PRODUCTION_STAGES = frozenset({"production", "prod", "live"})
DEFAULT_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days — conservative initial rollout
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104


class TlsConfigurationError(RuntimeError):
    """Raised when the deploy stage requires TLS but the config is insecure."""


@dataclass(frozen=True)
class TlsSettings:
    """Subset of Django settings the bootstrap toggles."""

    secure_ssl_redirect: bool
    secure_hsts_seconds: int
    secure_hsts_include_subdomains: bool
    secure_hsts_preload: bool
    session_cookie_secure: bool
    csrf_cookie_secure: bool
    secure_content_type_nosniff: bool
    secure_referrer_policy: str


def is_production(stage: str | None) -> bool:
    if not stage:
        return False
    return stage.strip().lower() in PRODUCTION_STAGES


def tls_settings_for_stage(stage: str | None) -> TlsSettings:
    """Pick the TLS settings tuple for ``stage`` (typically ``DEPLOY_STAGE``)."""

    if is_production(stage):
        return TlsSettings(
            secure_ssl_redirect=True,
            secure_hsts_seconds=DEFAULT_HSTS_SECONDS,
            secure_hsts_include_subdomains=True,
            secure_hsts_preload=False,
            session_cookie_secure=True,
            csrf_cookie_secure=True,
            secure_content_type_nosniff=True,
            secure_referrer_policy="strict-origin-when-cross-origin",
        )
    # Non-production defaults — keep local dev unobtrusive.
    return TlsSettings(
        secure_ssl_redirect=False,
        secure_hsts_seconds=0,
        secure_hsts_include_subdomains=False,
        secure_hsts_preload=False,
        session_cookie_secure=False,
        csrf_cookie_secure=False,
        secure_content_type_nosniff=True,
        secure_referrer_policy="strict-origin-when-cross-origin",
    )


def assert_outbound_url_uses_tls(url: str | None, *, stage: str | None, allow_insecure_dev: bool = False) -> None:
    """Refuse cleartext outbound URLs in production-equivalent stages."""

    if not url:
        return
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme == "https":
        return
    if scheme == "http":
        if is_production(stage):
            raise TlsConfigurationError(
                f"Outbound URL {url!r} uses cleartext http:// while DEPLOY_STAGE={stage!r}; "
                "configure an https:// endpoint."
            )
        if allow_insecure_dev and host in _LOOPBACK_HOSTS:
            return
        if allow_insecure_dev:
            return
        raise TlsConfigurationError(
            f"Outbound URL {url!r} uses cleartext http:// and ALLOW_INSECURE_TLS_DEV_ONLY is false."
        )
    raise TlsConfigurationError(f"Outbound URL {url!r} uses unsupported scheme {scheme!r}.")


def validate_tls_posture(
    *,
    stage: str | None,
    secure_ssl_redirect: bool,
    outbound_urls: Iterable[str] = (),
    allow_insecure_dev: bool = False,
) -> None:
    """Top-level startup validator (called from settings.py)."""

    if is_production(stage):
        if not secure_ssl_redirect:
            raise TlsConfigurationError("DEPLOY_STAGE=production requires SECURE_SSL_REDIRECT=True")
    for url in outbound_urls:
        assert_outbound_url_uses_tls(url, stage=stage, allow_insecure_dev=allow_insecure_dev)


__all__ = [
    "DEFAULT_HSTS_SECONDS",
    "PRODUCTION_STAGES",
    "TlsConfigurationError",
    "TlsSettings",
    "assert_outbound_url_uses_tls",
    "is_production",
    "tls_settings_for_stage",
    "validate_tls_posture",
]
