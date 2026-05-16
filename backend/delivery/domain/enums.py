"""Delivery-local enums."""

from __future__ import annotations

from django.db import models


class DeliveryRequestStatus(models.TextChoices):
    """DeliveryRequest lifecycle (transient table). See DOMAIN_MODEL §4.3."""

    QUEUED = "queued", "Encolada"
    SENDING = "sending", "Enviando"
    DELIVERED = "delivered", "Entregada"
    FAILED = "failed", "Fallida"
    EXPIRED = "expired", "Expirada"


class ErrorClassification(models.TextChoices):
    """How a delivery failure should be retried (CS-029)."""

    TRANSIENT = "transient", "Transitorio (retry)"
    PERMANENT = "permanent", "Permanente (no retry)"
