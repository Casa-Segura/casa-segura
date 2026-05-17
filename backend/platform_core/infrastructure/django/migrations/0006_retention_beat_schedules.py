"""Seed django-celery-beat schedules for PRD F8 retention jobs (ADR-0005)."""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor) -> None:
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    def interval(seconds: int):
        obj, _ = IntervalSchedule.objects.get_or_create(every=seconds, period="seconds")
        return obj

    rows = (
        ("retention.cleanup_transient", interval(900), "platform.cleanup_transient", True),
        ("retention.cleanup_delivery_targets", interval(300), "platform.cleanup_delivery_targets", True),
        ("retention.expire_links", interval(3600), "platform.expire_links", True),
        (
            "retention.recompute_project_metrics",
            interval(3600),
            "platform.recompute_project_metrics",
            False,
        ),
        ("retention.anonymize_old_analyses", interval(3600), "platform.anonymize_old_analyses", False),
    )
    defaults_extra = {"kwargs": "{}", "headers": "{}"}
    for name, sched, task, enabled in rows:
        PeriodicTask.objects.update_or_create(
            name=name,
            defaults={
                "interval": sched,
                "crontab": None,
                "solar": None,
                "clocked": None,
                "task": task,
                "enabled": enabled,
                **defaults_extra,
            },
        )


def backwards(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name__startswith="retention.").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("platform_core", "0005_classification_f2_fields"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
