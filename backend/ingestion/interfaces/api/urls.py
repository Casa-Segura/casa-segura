"""URL conf for the ingestion API (mounted under /api/v1/)."""

from __future__ import annotations

from django.urls import path

from ingestion.interfaces.api.views import SubmissionDetailView, SubmissionUploadView

app_name = "ingestion"

urlpatterns = [
    path("submissions/", SubmissionUploadView.as_view(), name="submission-upload"),
    path(
        "submissions/<uuid:submission_id>/",
        SubmissionDetailView.as_view(),
        name="submission-detail",
    ),
]
