"""EPIC-04 PR-0: add F2 §5.1 classification + economic raw fields to ContractAnalysis.

Adds the columns the F2 orchestrator (CS-110 / CS-111 / CS-112 / CS-113 / CS-114)
needs to persist its envelope on `contract_analysis`. None of these existed before:

    - classification_confidence  DECIMAL(4,3) NULL  (CHECK 0..1 OR NULL)
    - classification_attempts    smallint NOT NULL default 0  (CHECK <= 3)
    - elements_detected          jsonb NOT NULL default '{}'  (US-05 booleans)
    - reclassification_indicators jsonb NULL  (§8.4 envelope)
    - project_name_canonical     varchar(255) NULL
    - economic_fields_raw        jsonb NULL  (§8.5 coerced payload)

Backwards keeps the column drops in the reverse order of declaration so the
operation is a clean round-trip; the migration smoke test in CI exercises both
directions per CS-035.
"""

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("platform_core", "0004_sms_delivery_channels"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractanalysis",
            name="classification_confidence",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="F2 §5.1: confidence of the accepted classification (NULL until classifier runs)",
                max_digits=4,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="contractanalysis",
            name="classification_attempts",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="F2 §5.1: 0 pre-run, 1 single call, 2 if §8.3 validator fired",
            ),
        ),
        migrations.AddField(
            model_name="contractanalysis",
            name="elements_detected",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="F2 §5.1 / US-05: structural boolean flags (public_deed, arbitration_clause, …)",
            ),
        ),
        migrations.AddField(
            model_name="contractanalysis",
            name="reclassification_indicators",
            field=models.JSONField(
                blank=True,
                help_text="F2 §8.4 envelope {indicators, count, severity}; NULL when leasing detector did not run",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="contractanalysis",
            name="project_name_canonical",
            field=models.CharField(
                blank=True,
                help_text="F2 §5.1 raw canonical project name as extracted (pre-normalization)",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="contractanalysis",
            name="economic_fields_raw",
            field=models.JSONField(
                blank=True,
                help_text="F2 §8.5 coerced extraction payload; NULL for non-economic contract types",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="contractanalysis",
            constraint=models.CheckConstraint(
                condition=(
                    Q(classification_confidence__isnull=True)
                    | (Q(classification_confidence__gte=0) & Q(classification_confidence__lte=1))
                ),
                name="ck_contract_analysis_classification_confidence_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="contractanalysis",
            constraint=models.CheckConstraint(
                condition=Q(classification_attempts__lte=3),
                name="ck_contract_analysis_classification_attempts_max",
            ),
        ),
    ]
