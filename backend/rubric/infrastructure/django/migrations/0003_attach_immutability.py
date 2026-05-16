"""CS-030 follow-up: attach catalog-immutability trigger to rubric_version."""

from __future__ import annotations

from django.db import migrations


TRIGGER_ADD = """
CREATE TRIGGER rubric_version_immutable
  BEFORE UPDATE OR DELETE ON rubric_version
  FOR EACH ROW EXECUTE FUNCTION reject_catalog_mutation();
"""
TRIGGER_DROP = "DROP TRIGGER IF EXISTS rubric_version_immutable ON rubric_version;"


class Migration(migrations.Migration):
    dependencies = [
        ("rubric", "0002_criterion_idx_criterion_types"),
        ("platform_core", "0002_immutability_function_and_views"),
    ]

    operations = [
        migrations.RunSQL(sql=TRIGGER_ADD, reverse_sql=TRIGGER_DROP),
    ]
