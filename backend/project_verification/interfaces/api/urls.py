"""URL routing for optional project-verification stub API."""

from django.urls import path

from . import views

app_name = "project_verification"

urlpatterns = [
    path(
        "manual/",
        views.ProjectVerificationManualStubView.as_view(),
        name="manual",
    ),
    path(
        "billboard-upload/",
        views.ProjectVerificationBillboardUploadStubView.as_view(),
        name="billboard-upload",
    ),
    path(
        "demo-result/",
        views.ProjectVerificationDemoResultStubView.as_view(),
        name="demo-result",
    ),
]
