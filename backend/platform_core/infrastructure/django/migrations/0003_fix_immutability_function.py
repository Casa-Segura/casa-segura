"""Fix `reject_catalog_mutation()` — drop dead `diff` assignment with bad cast.

The 0002 version computed an unused `diff` variable with `jsonb - text[]`,
which Postgres rejects at runtime ("cannot cast type jsonb to text[]"). The
function works on INSERT (early return) but blows up on any UPDATE before
ever reaching the actual symmetric-difference check. This migration
re-creates the function with only the check that actually matters.
"""

from __future__ import annotations

from django.db import migrations


CREATE_TRIGGER_FN = r"""
CREATE OR REPLACE FUNCTION reject_catalog_mutation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'catalog row deletion forbidden on table %', TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;

    -- Allow flipping is_active (and the updated_at that auto-stamps with it);
    -- reject any other column drift.
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

# Reverse just re-installs the buggy 0002 version so a downward migrate
# keeps the function present; the bug only surfaces on UPDATE attempts.
REVERSE_TRIGGER_FN = r"""
CREATE OR REPLACE FUNCTION reject_catalog_mutation() RETURNS trigger AS $$
DECLARE
    diff jsonb;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'catalog row deletion forbidden on table %', TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;
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


class Migration(migrations.Migration):
    dependencies = [
        ("platform_core", "0002_immutability_function_and_views"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_TRIGGER_FN, reverse_sql=REVERSE_TRIGGER_FN),
    ]
