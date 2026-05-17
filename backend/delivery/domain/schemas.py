"""Pydantic DTOs for delivery — CS-230 (framework-free; no Django imports)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, computed_field, field_validator, model_validator

# ─── Mirrors PostgreSQL CHECK constraints on delivery_request ───────────────

CHANNEL_VALUES = frozenset({"sms_summary", "email_pdf", "web_link"})
DELIVERY_REQUEST_STATUS_VALUES = frozenset({"queued", "sending", "delivered", "failed", "expired"})
ERROR_CLASSIFICATION_VALUES = frozenset({"transient", "permanent"})


class DeliveryChannelDTO(StrEnum):
    SMS_SUMMARY = "sms_summary"
    EMAIL_PDF = "email_pdf"
    WEB_LINK = "web_link"


class DeliveryRequestStatusDTO(StrEnum):
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


class ErrorClassificationDTO(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class DeliveryRequestDTO(BaseModel):
    """ORM-safe projection — excludes ciphertext by default."""

    model_config = ConfigDict(extra="forbid")

    id: str
    analysis_id: str
    channel: DeliveryChannelDTO
    target_hash: str
    status: DeliveryRequestStatusDTO
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    next_attempt_not_before: datetime | None = None
    delivered_at: datetime | None = None
    expires_at: datetime
    provider_message_id: str = ""
    last_error: str = ""
    last_error_classification: ErrorClassificationDTO | None = None
    target_value_encrypted: SecretStr | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_destination_cipher(self) -> bool:
        return self.target_value_encrypted is not None


class EnqueueDeliveryPayload(BaseModel):
    """Validated enqueue envelope from HTTP/workers."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    channel: DeliveryChannelDTO
    target_hash: str = ""
    target_value_encrypted: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)

    @model_validator(mode="after")
    def _channel_and_attempt_rules(self) -> EnqueueDeliveryPayload:
        if self.attempt_count >= self.max_attempts:
            raise ValueError("enqueue_attempts_exhausted")
        if self.channel != DeliveryChannelDTO.WEB_LINK and not (self.target_hash or "").strip():
            raise ValueError("target_hash_required")
        return self


class ZavuWebhookMessage(BaseModel):
    """Minimal shape for provider callbacks — extend per Zavu event docs."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None


class ZavuWebhookData(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: ZavuWebhookMessage | dict[str, Any] | None = None


class ZavuWebhookPayload(BaseModel):
    """Inbound webhook JSON — tolerant `data` nesting."""

    model_config = ConfigDict(extra="allow")

    type: str
    data: ZavuWebhookData | dict[str, Any] | None = None

    def resolve_message_id(self) -> str | None:
        if self.data is None:
            return None
        raw = self.data if isinstance(self.data, dict) else self.data.model_dump(mode="python")
        msg = raw.get("message")
        if isinstance(msg, dict):
            mid = msg.get("id")
            return str(mid) if mid else None
        if isinstance(msg, ZavuWebhookMessage) and msg.id:
            return msg.id
        return None


class RetryScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_count_after_failure: int = Field(ge=1)
    rng_seed: int | None = None


LiteralChannel = Literal["sms_summary", "email_pdf", "web_link"]
LiteralDeliveryStatus = Literal["queued", "sending", "delivered", "failed", "expired"]


def assert_whatsapp_summary_rejected(channel: str) -> str:
    """whatsapp_summary was removed — migrations rewrote rows."""
    if channel == "whatsapp_summary":
        raise ValueError("legacy channel whatsapp_summary is not allowed")
    return channel


class StrictDeliveryChannel(BaseModel):
    """Fails instantiation on typo — AC for CS-230."""

    model_config = ConfigDict(extra="forbid")

    channel: str

    @field_validator("channel")
    @classmethod
    def _must_be_allowed(cls, v: str) -> str:
        v = assert_whatsapp_summary_rejected(v)
        if v not in CHANNEL_VALUES:
            raise ValueError("delivery_channel_invalid")
        return v
