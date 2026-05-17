"""CS-337 — fail CI on disclaimer copy drift.

Scans ``backend/`` for occurrences of the BR-07 canonical disclaimer
strings outside the allow-listed files. Run from the backend root:

    python -m scripts.lint_disclaimer_registry

Exit code 0 = clean, 1 = drift detected (file paths printed).

The allow-list is intentionally narrow:

* ``shared/legal/disclaimers.py`` and its ``__init__.py`` — the registry itself.
* ``scripts/lint_disclaimer_registry.py`` — this script's literal copy.
* ``tests/`` — fixtures may pin the registry string verbatim.
* ``reports/templates/`` — Jinja templates render the strings via the
  ``ctx.*`` interface, never embed the literal.

Any other file that contains a literal from
``CANONICAL_DISCLAIMER_LITERALS`` triggers a failure.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

from shared.legal.disclaimers import CANONICAL_DISCLAIMER_LITERALS

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Files whose presence of the literal is expected (registry, lint, fixtures).
ALLOWLIST_RELATIVE = (
    "shared/legal/disclaimers.py",
    "shared/legal/__init__.py",
    "scripts/lint_disclaimer_registry.py",
)
ALLOWLIST_PREFIXES = (
    "tests/",
    "reports/templates/",
)


def _is_allowlisted(rel_path: Path) -> bool:
    posix = rel_path.as_posix()
    if posix in ALLOWLIST_RELATIVE:
        return True
    return any(posix.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


def _iter_source_files() -> list[Path]:
    out: list[Path] = []
    for path in BACKEND_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".j2", ".html", ".txt", ".md"):
            continue
        try:
            rel = path.relative_to(BACKEND_ROOT)
        except ValueError:
            continue
        parts = rel.parts
        if any(skip in parts for skip in (".venv", "venv", "__pycache__", ".git", "node_modules")):
            continue
        out.append(rel)
    return out


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _violations() -> list[tuple[Path, int, str]]:
    """Return (path, line_number, matched_literal) tuples for drift."""

    canonical_norm = [(literal, _normalize(literal)) for literal in CANONICAL_DISCLAIMER_LITERALS]
    found: list[tuple[Path, int, str]] = []
    for rel in _iter_source_files():
        if _is_allowlisted(rel):
            continue
        try:
            content = (BACKEND_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        normalized = _normalize(content)
        for literal, literal_norm in canonical_norm:
            if literal_norm in normalized:
                # Find the offending line for ergonomics.
                lineno = 1
                for idx, line in enumerate(content.splitlines(), start=1):
                    if literal in line or literal_norm in _normalize(line):
                        lineno = idx
                        break
                found.append((rel, lineno, literal))
    return found


def main() -> int:
    violations = _violations()
    if not violations:
        print("OK: no canonical disclaimer drift detected.")
        return 0
    print("FAIL: canonical disclaimer literals embedded outside the registry.")
    print("Allow-listed files: " + ", ".join(ALLOWLIST_RELATIVE) + " + " + ", ".join(ALLOWLIST_PREFIXES))
    for path, line, literal in violations:
        print(f"  {path}:{line}  literal={literal!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
