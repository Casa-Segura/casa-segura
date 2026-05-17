"""Smoke test CS-270 harness (`scripts/retention_scheduler_dry_validate.py`)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _BACKEND_ROOT / "scripts" / "retention_scheduler_dry_validate.py"


def test_retention_scheduler_dry_validate_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=_BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_retention_scheduler_dry_validate_stdout_includes_manifest() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=_BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert '"cleanup_transient"' in proc.stdout or "cleanup_transient" in proc.stdout
