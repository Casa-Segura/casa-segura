from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports.infrastructure.django"
    label = "reports"
    verbose_name = "Casa Segura — Report Generation"

    def ready(self) -> None:
        # Register Celery tasks (autodiscover only scans ``<app>/tasks.py`` by default).
        from reports.infrastructure.celery import report_tasks  # noqa: F401  PLC0415
