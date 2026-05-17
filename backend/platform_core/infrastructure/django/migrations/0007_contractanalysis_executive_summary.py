"""Add ContractAnalysis.executive_summary per PRD F8 DDL / US-07."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform_core", "0006_retention_beat_schedules"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractanalysis",
            name="executive_summary",
            field=models.TextField(
                blank=True,
                default="",
                help_text="F4 synthesized verdict narrative; preserved after anonymization (PRD F8 US-07)",
            ),
        ),
    ]
