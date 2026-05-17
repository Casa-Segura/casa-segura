"""URL conf for the classification internal API (mounted under /api/v1/internal/)."""

from __future__ import annotations

from django.urls import path

from classification.interfaces.api.views import InternalClassifyView

app_name = "classification"

urlpatterns = [
    path("classify", InternalClassifyView.as_view(), name="internal-classify"),
]
