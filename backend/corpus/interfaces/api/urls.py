"""URL conf for the corpus API (mounted under /api/v1/corpus/)."""

from __future__ import annotations

from django.urls import path

from corpus.interfaces.api.views import RetrieveLegalBasisView

app_name = "corpus"

urlpatterns = [
    path("retrieve/", RetrieveLegalBasisView.as_view(), name="retrieve"),
]
