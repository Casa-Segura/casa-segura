"""Billboard vision extraction → structured JSON (EPIC-12 / CS-350)."""

from __future__ import annotations

import base64
import json
import time
from io import BytesIO
from typing import Any, Literal

import structlog
from PIL import Image
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from django.conf import settings

from project_verification.infrastructure.metrics import (
    PROJECT_VERIFICATION_OCR_OUTCOMES,
    PROJECT_VERIFICATION_VISION_SECONDS,
)
from shared.llm.openrouter import OpenRouterClient, OpenRouterError

logger = structlog.get_logger(__name__)

OcrOutcome = Literal["success", "low_confidence", "failure", "timeout", "parse_failure"]


class BillboardFields(BaseModel):
    model_config = {"extra": "forbid"}

    developer: str | None = Field(default=None, max_length=240)
    project: str | None = Field(default=None, max_length=240)
    permit: str | None = Field(default=None, max_length=240)
    address: str | None = Field(default=None, max_length=240)


class BillboardModelPayload(BaseModel):
    model_config = {"extra": "forbid"}

    developer: str | None = Field(default=None, max_length=240)
    project: str | None = Field(default=None, max_length=240)
    permit: str | None = Field(default=None, max_length=240)
    address: str | None = Field(default=None, max_length=240)
    confidence: Literal["high", "medium", "low", "unknown"] | None = "unknown"


BILLBOARD_VISION_PROMPT = (
    "Analiza la foto de una valla inmobiliaria en El Salvador y devolvé únicamente un "
    'objeto JSON con las claves: "developer","project","permit","address","confidence". '
    "Cada campo de texto debe ser corto (<=240 caracteres) o null si no es legible. "
    '"confidence" debe ser "high"|"medium"|"low"|"unknown" según nitidez. '
    "No incluyas comentarios, markdown ni texto antes o después del JSON."
)


_ALLOWED_IMAGE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)


def _build_image_messages(*, mime: str, raw: bytes) -> list[dict[str, Any]]:
    b64 = base64.b64encode(raw).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": BILLBOARD_VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]


def _coerce_json_object(content: str) -> dict[str, Any]:
    t = content.strip()

    fence_start = "```"
    if t.startswith(fence_start):
        t = t.removeprefix(fence_start)
        if t.lower().startswith("json"):
            t = t[4:].lstrip()
        fence_end_idx = t.rfind(fence_start)
        if fence_end_idx != -1:
            t = t[:fence_end_idx].strip()
    decoder = json.JSONDecoder()

    chunk = decoder.raw_decode(t.strip())[0]
    if isinstance(chunk, dict):
        return dict(chunk)
    return {}


def _map_confidence_band(*, structured: BillboardModelPayload | None) -> tuple[bool, bool, bool]:
    """Return (high, medium, low) OCR confidence flags."""

    if structured is None or structured.confidence is None:
        return False, False, True

    lv = structured.confidence
    if lv == "high":
        return True, False, False
    if lv == "medium":
        return False, True, False
    if lv == "low":
        return False, False, True
    return False, False, True


class BillboardExtractOutcome(BaseModel):
    model_config = {"extra": "forbid"}

    ocr_status: OcrOutcome
    fields: BillboardFields
    ocr_high_confidence: bool = False
    ocr_medium_confidence: bool = False
    ocr_low_confidence: bool = True


def extract_billboard_structured(  # noqa: PLR0911, PLR0915
    *, raw: bytes, content_type: str
) -> BillboardExtractOutcome:
    """Run gated vision OCR; discard bytes after parsing (no persistence)."""

    mime = (content_type or "").lower().split(";")[0].strip()
    started = time.perf_counter()

    if mime not in _ALLOWED_IMAGE_TYPES:
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="unsupported_media").inc()
        return BillboardExtractOutcome(
            ocr_status="failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    if not getattr(settings, "OPENROUTER_API_KEY", ""):
        duration = max(time.perf_counter() - started, 0)
        PROJECT_VERIFICATION_VISION_SECONDS.labels(flow="project_verification", stage="billboard_vision").observe(
            duration
        )
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="upstream_unconfigured").inc()
        logger.warning("project_verification.billboard.missing_api_key")

        return BillboardExtractOutcome(
            ocr_status="failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    max_bytes = int(getattr(settings, "OCR_MAX_BYTES", 15 * 1024 * 1024))
    if len(raw) > max_bytes:
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="payload_too_large").inc()

        return BillboardExtractOutcome(
            ocr_status="failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    mega_cap = float(getattr(settings, "PROJECT_VERIFICATION_MAX_MEGAPIXELS", 20.0))

    width = height = 0

    try:
        bio = BytesIO(raw)
        with Image.open(bio) as img:
            img.load()
            width, height = int(img.width), int(img.height)
    except Exception:
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="invalid_image_container").inc()

        return BillboardExtractOutcome(
            ocr_status="failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    if width * height <= 0 or width * height / 1_000_000.0 > mega_cap:
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="pixels_rejected").inc()

        return BillboardExtractOutcome(
            ocr_status="failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    model = getattr(settings, "PROJECT_VERIFICATION_VISION_MODEL", "") or getattr(settings, "OPENROUTER_OCR_MODEL", "")
    timeout = int(getattr(settings, "PROJECT_VERIFICATION_VISION_TIMEOUT_SECONDS", 45))

    client = OpenRouterClient(timeout_seconds=timeout, max_retries=1)

    try:
        try:

            result = client.chat_completion(
                model=model,
                messages=_build_image_messages(mime=mime, raw=raw),
            )

        except (OpenRouterError, OSError, TimeoutError) as exc:
            PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="timeout_upstream").inc()
            dur = max(time.perf_counter() - started, 0)
            PROJECT_VERIFICATION_VISION_SECONDS.labels(flow="project_verification", stage="billboard_vision").observe(
                dur
            )
            logger.warning(
                "project_verification.billboard.vision_upstream",
                outcome="timeout_upstream",
                error_type=type(exc).__name__,
            )

            return BillboardExtractOutcome(
                ocr_status="timeout",
                fields=BillboardFields(),
                ocr_low_confidence=True,
            )
    finally:
        client.close()

    duration = max(time.perf_counter() - started, 0)
    PROJECT_VERIFICATION_VISION_SECONDS.labels(flow="project_verification", stage="billboard_vision").observe(duration)

    text = result.content.strip()

    structured: BillboardModelPayload | None = None
    try:

        payload = _coerce_json_object(text)

        structured = BillboardModelPayload.model_validate(payload)

    except (
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        PydanticValidationError,
    ):
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="parse_failure").inc()

        return BillboardExtractOutcome(
            ocr_status="parse_failure",
            fields=BillboardFields(),
            ocr_low_confidence=True,
        )

    high, medium, low = _map_confidence_band(structured=structured)

    try:
        fields = BillboardFields(
            developer=structured.developer,
            project=structured.project,
            permit=structured.permit,
            address=structured.address,
        )

    except PydanticValidationError:
        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="parse_failure").inc()

        return BillboardExtractOutcome(
            ocr_status="parse_failure",
            fields=BillboardFields(),
            ocr_high_confidence=high,
            ocr_medium_confidence=medium,
            ocr_low_confidence=low,
        )

    sparse = not any([fields.developer, fields.project, fields.permit])

    if low or structured.confidence in ("unknown", None):
        status_l: OcrOutcome = "low_confidence"

        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="low_confidence").inc()

    elif sparse:
        status_l = "failure"

        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="sparse_fields").inc()
    else:
        status_l = "success"

        PROJECT_VERIFICATION_OCR_OUTCOMES.labels(outcome="success").inc()

    return BillboardExtractOutcome(
        ocr_status=status_l,
        fields=fields,
        ocr_high_confidence=high,
        ocr_medium_confidence=medium,
        ocr_low_confidence=low,
    )
