"""URL routes for the feedback API (CS-336)."""

from __future__ import annotations

from django.urls import path

from feedback.interfaces.api.views import ErrorReportView

app_name = "feedback"

urlpatterns = [
    path("error-reports/", ErrorReportView.as_view(), name="error-reports"),
]
