"""CS-058 — strict disclaimer acceptance before ingestion (BR-07, PRD F1 §US-01)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from shared.domain.exceptions import DomainException


def merge_submission_upload_aliases(data: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten multipart-like payloads and map frontend field aliases."""

    merged: dict[str, Any] = {}
    try:
        key_iter = data.keys()
    except AttributeError:
        return dict(data)
    for key in key_iter:
        merged[key] = data.get(key)

    if (merged.get("disclaimer_method") in (None, "")) and merged.get(
        "disclaimer_acceptance_method"
    ) not in (None, ""):
        merged["disclaimer_method"] = merged["disclaimer_acceptance_method"]

    if (merged.get("source") in (None, "")) and merged.get("submission_source") not in (
        None,
        "",
    ):
        merged["source"] = merged["submission_source"]

    return merged


def require_disclaimer_accepted_or_raise(data: Mapping[str, Any]) -> None:
    """Reject uploads unless disclaimer acceptance is explicitly true (anti-tamper).

    Multipart booleans arrive as strings; only canonical true forms are accepted.
    """

    if "disclaimer_accepted" not in data:
        raise DomainException(
            "Disclaimer must be explicitly accepted before ingestion.",
            code="DISCLAIMER_REQUIRED",
            status=400,
        )

    raw = data.get("disclaimer_accepted")

    if raw is True:
        return

    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"true", "1"}:
            return

    raise DomainException(
        "Disclaimer must be explicitly accepted before ingestion.",
        code="DISCLAIMER_REQUIRED",
        status=400,
    )
