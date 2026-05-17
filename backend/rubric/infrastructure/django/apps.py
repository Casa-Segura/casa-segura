from django.apps import AppConfig


class RubricConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rubric.infrastructure.django"
    label = "rubric"
    verbose_name = "Casa Segura — Rubric Engine"

    def ready(self) -> None:
        # Register Celery tasks so `app.autodiscover_tasks()` picks them up
        # even though the module lives outside the default ``tasks.py`` path.
        from rubric.infrastructure.celery import rubric_tasks  # noqa: F401  PLC0415
