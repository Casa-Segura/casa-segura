"""CS-030 follow-up: catalog-immutability trigger function + ops views.

- `reject_catalog_mutation()` is a generic plpgsql trigger function that
  refuses DELETE and refuses UPDATE of any column other than `is_active`
  (and the `updated_at` timestamp that flips with it). Attached to each
  versioned catalog table by per-module migrations.
- `v_system_health` and `v_retention_status` provide ops snapshots of
  in-flight work and overdue retention candidates (PRD_F8 §5.2).
"""

from __future__ import annotations

from django.db import migrations


CREATE_TRIGGER_FN = r"""
CREATE OR REPLACE FUNCTION reject_catalog_mutation() RETURNS trigger AS $$
DECLARE
    diff jsonb;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'catalog row deletion forbidden on table %', TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;

    -- Compare all columns except is_active and updated_at; reject any drift.
    diff := (to_jsonb(NEW) - 'is_active' - 'updated_at')
            - (to_jsonb(OLD) - 'is_active' - 'updated_at')::text[];
    -- Symmetric difference: detect a change in either direction.
    IF (to_jsonb(NEW) - 'is_active' - 'updated_at')
       IS DISTINCT FROM (to_jsonb(OLD) - 'is_active' - 'updated_at') THEN
        RAISE EXCEPTION 'catalog row mutation forbidden on table % (only is_active may change)',
            TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

DROP_TRIGGER_FN = "DROP FUNCTION IF EXISTS reject_catalog_mutation();"


CREATE_V_SYSTEM_HEALTH = r"""
CREATE OR REPLACE VIEW v_system_health AS
SELECT
    (
        SELECT COUNT(*) FROM contract_submission
         WHERE processing_status NOT IN (
            'completed', 'failed_extraction', 'failed_classification',
            'failed_analysis', 'rejected_language', 'rejected_type',
            'rejected_size', 'expired'
         )
    ) AS submissions_in_flight,
    (SELECT COUNT(*) FROM ocr_job WHERE status = 'running') AS ocr_jobs_running,
    (SELECT COUNT(*) FROM delivery_request WHERE status IN ('queued', 'sending')) AS deliveries_pending,
    (SELECT COUNT(*) FROM delivery_request WHERE status = 'failed') AS deliveries_failed,
    (SELECT COUNT(*) FROM contract_analysis WHERE anonymized_at IS NULL) AS analyses_active,
    (SELECT MAX(occurred_at) FROM privacy_audit_log) AS last_audit_event_at;
"""

DROP_V_SYSTEM_HEALTH = "DROP VIEW IF EXISTS v_system_health;"


CREATE_V_RETENTION_STATUS = r"""
CREATE OR REPLACE VIEW v_retention_status AS
SELECT
    (
        SELECT COUNT(*) FROM contract_analysis
         WHERE anonymized_at IS NULL AND created_at < NOW() - INTERVAL '90 days'
    ) AS analyses_overdue_anonymization,
    (SELECT COUNT(*) FROM contract_submission WHERE expires_at < NOW()) AS submissions_overdue_cleanup,
    (SELECT COUNT(*) FROM ocr_job WHERE expires_at < NOW()) AS ocr_jobs_overdue_cleanup,
    (SELECT COUNT(*) FROM delivery_request WHERE expires_at < NOW()) AS delivery_requests_overdue_cleanup,
    (SELECT COUNT(*) FROM privacy_audit_log WHERE expires_at < NOW()) AS audit_log_overdue_cleanup,
    (SELECT COUNT(*) FROM job_execution_log WHERE expires_at < NOW()) AS job_log_overdue_cleanup,
    (
        SELECT COUNT(*) FROM contract_analysis
         WHERE link_expires_at IS NOT NULL
           AND link_expires_at < NOW()
           AND delivery_status NOT IN ('expired')
    ) AS links_overdue_expiration;
"""

DROP_V_RETENTION_STATUS = "DROP VIEW IF EXISTS v_retention_status;"


class Migration(migrations.Migration):
    """Function + views depend on every entity table existing."""

    dependencies = [
        ("platform_core", "0001_initial"),
        ("ingestion", "0001_initial"),
        ("delivery", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_TRIGGER_FN, reverse_sql=DROP_TRIGGER_FN),
        migrations.RunSQL(sql=CREATE_V_SYSTEM_HEALTH, reverse_sql=DROP_V_SYSTEM_HEALTH),
        migrations.RunSQL(sql=CREATE_V_RETENTION_STATUS, reverse_sql=DROP_V_RETENTION_STATUS),
    ]
