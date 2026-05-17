"""Django application config for EPIC-12 stubs."""

from __future__ import annotations

from django.apps import AppConfig


class ProjectVerificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project_verification"
    label = "project_verification"
    verbose_name = "Project verification stubs"

    def ready(self) -> None:
        # Register system checks (reputation readiness, etc.).
        from project_verification import checks  # noqa: F401, PLC0415
