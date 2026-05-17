"""URL routing for optional project-verification API (EPIC-12)."""

from django.urls import path

from . import views

app_name = "project_verification"

urlpatterns = [
    path(
        "manual/",
        views.ProjectVerificationManualView.as_view(),
        name="manual",
    ),
    path(
        "billboard-upload/",
        views.ProjectVerificationBillboardUploadView.as_view(),
        name="billboard-upload",
    ),
    path(
        "demo-result/",
        views.ProjectVerificationDemoResultView.as_view(),
        name="demo-result",
    ),
]
