"""URL conf for delivery provider webhooks (mounted under /api/v1/)."""

from __future__ import annotations

from django.urls import path

from delivery.interfaces.api.views import ZavuWebhookView

urlpatterns = [
    path("", ZavuWebhookView.as_view(), name="zavu-webhook"),
]
