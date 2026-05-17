"""Enable anonymize crontab (ADR-0005), enable project metrics beat, audit dedupe."""

from __future__ import annotations

from django.db import migrations, models
from django.db.models import Q


def forwards_beat(apps, schema_editor) -> None:
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="America/El_Salvador",
    )

    pt_anon = PeriodicTask.objects.filter(name="retention.anonymize_old_analyses").first()
    if pt_anon:
        pt_anon.crontab_id = cron.pk
        pt_anon.interval_id = None
        pt_anon.enabled = True
        pt_anon.save(update_fields=["crontab_id", "interval_id", "enabled"])

    pt_rec = PeriodicTask.objects.filter(name="retention.recompute_project_metrics").first()
    if pt_rec:
        pt_rec.enabled = True
        pt_rec.save(update_fields=["enabled"])


def backwards_beat(apps, schema_editor) -> None:
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _ = IntervalSchedule.objects.get_or_create(every=3600, period="seconds")
    pt_anon = PeriodicTask.objects.filter(name="retention.anonymize_old_analyses").first()
    if pt_anon:
        pt_anon.crontab_id = None
        pt_anon.interval_id = interval.pk
        pt_anon.enabled = False
        pt_anon.save(update_fields=["crontab_id", "interval_id", "enabled"])

    pt_rec = PeriodicTask.objects.filter(name="retention.recompute_project_metrics").first()
    if pt_rec:
        pt_rec.enabled = False
        pt_rec.save(update_fields=["enabled"])


class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("platform_core", "0007_contractanalysis_executive_summary"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="privacyauditlog",
            constraint=models.UniqueConstraint(
                fields=("event_type", "related_id"),
                condition=Q(event_type="analysis_anonymized"),
                name="uq_privacy_audit_analysis_anonymized_related",
            ),
        ),
        migrations.RunPython(forwards_beat, backwards_beat),
    ]
