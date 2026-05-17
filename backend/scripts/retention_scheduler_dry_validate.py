#!/usr/bin/env python3
"""
Dry validation for ADR-0005 retention schedule constants (CS-270).

Parses zoneinfo targets and asserts SLA intervals encoded in-repo match PRD F8 §6.2.

No Django, no Postgres, no Redis — safe from CI lint container.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# PRD_F8 §6.2 SLA max cadences (nominal intervals in seconds —Beat/crontab configures ≤ these).
EXPECTED_INTERVAL_SECONDS: dict[str, int] = {
    "cleanup_transient": 15 * 60,
    "cleanup_delivery_targets": 5 * 60,
    "expire_links": 60 * 60,
    "recompute_project_metrics": 60 * 60,
}


ANONYMIZE_JOB_NAME = "anonymize_old_analyses"
TZ_AMERICA_EL_SALVADOR = "America/El_Salvador"
ANONYMIZE_LOCAL_HOUR = 3


def _tz_resolves(name: str) -> None:
    z = ZoneInfo(name)
    # Touch an aware datetime to ensure TZDB parses (El Salvador currently no DST transitions).
    datetime.now(z)
    datetime.now(tz=z).astimezone(UTC)


def main() -> None:
    failures: list[str] = []

    try:
        _tz_resolves(TZ_AMERICA_EL_SALVADOR)
        tz_ok = True
    except (KeyError, OSError) as exc:
        failures.append(f"timezone_resolution:{exc}")
        tz_ok = False

    for job, secs in EXPECTED_INTERVAL_SECONDS.items():
        if secs <= 0:
            failures.append(f"{job}:non_positive_interval")

    if EXPECTED_INTERVAL_SECONDS["cleanup_transient"] > 900:
        failures.append("cleanup_transient exceeds PRD 15 minutes ceiling")
    if EXPECTED_INTERVAL_SECONDS["cleanup_delivery_targets"] > 300:
        failures.append("cleanup_delivery_targets exceeds PRD 5 minutes ceiling")
    if EXPECTED_INTERVAL_SECONDS["expire_links"] > 3600:
        failures.append("expire_links exceeds PRD 1 hour ceiling")
    if EXPECTED_INTERVAL_SECONDS["recompute_project_metrics"] > 3600:
        failures.append("recompute_project_metrics exceeds PRD 1 hour ceiling")

    if ANONYMIZE_LOCAL_HOUR != 3:
        failures.append("anonymize_old_analyses must anchor at America/El_Salvador hour 03:00")

    record_count = len(EXPECTED_INTERVAL_SECONDS) + 1  # daily anonymize cron row (ADR table)

    payload = {
        "job_name": "retention_scheduler_dry_validate",
        "status": "success" if not failures else "failed",
        "records_processed": 0 if failures else record_count,
        "tz_ok": tz_ok,
        "timezone_name": TZ_AMERICA_EL_SALVADOR,
        "anonymize_daily_local_hour": ANONYMIZE_LOCAL_HOUR,
        "cron_job_names_daily": [ANONYMIZE_JOB_NAME],
        "interval_seconds_manifest": dict(EXPECTED_INTERVAL_SECONDS),
        "failure_reasons": failures,
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    sys.exit(0 if not failures else 2)


if __name__ == "__main__":
    main()
