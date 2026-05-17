"""SMS transactional copy registry — CS-239 (segment budget enforced later in CS-240)."""

from __future__ import annotations

from shared.legal import DISCLAIMER_SMS_SHORTHAND_ES as DISCLAIMER_SHORTHAND_ES

SMS_TEMPLATE_REGISTRY_VERSION = "2026.05.17"

SMS_BODY_SUMMARY_TEMPLATE = (
    "Hola — tu informe Casa Segura ({public_short_id}) quedó en banda {band}. "
    "Abre el informe completo: {report_url}\n"
    f"{DISCLAIMER_SHORTHAND_ES}"
)


def validate_registry_strings_loaded() -> None:
    """Smoke hook for CI — ensures templates stay importable."""

    assert SMS_BODY_SUMMARY_TEMPLATE
    assert "{public_short_id}" in SMS_BODY_SUMMARY_TEMPLATE
