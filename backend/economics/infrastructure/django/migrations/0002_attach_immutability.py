"""CS-030 follow-up: attach catalog-immutability trigger to benchmark_version."""

from __future__ import annotations

from django.db import migrations


TRIGGER_ADD = """
CREATE TRIGGER benchmark_version_immutable
  BEFORE UPDATE OR DELETE ON benchmark_version
  FOR EACH ROW EXECUTE FUNCTION reject_catalog_mutation();
"""
TRIGGER_DROP = "DROP TRIGGER IF EXISTS benchmark_version_immutable ON benchmark_version;"


class Migration(migrations.Migration):
    dependencies = [
        ("economics", "0001_initial"),
        ("platform_core", "0002_immutability_function_and_views"),
    ]

    operations = [
        migrations.RunSQL(sql=TRIGGER_ADD, reverse_sql=TRIGGER_DROP),
    ]
