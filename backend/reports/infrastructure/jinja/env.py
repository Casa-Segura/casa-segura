"""Jinja2 environment factory for the report templates.

Templates live under ``backend/reports/templates/report/v<version>/`` so
the env loads from the package directory directly. Autoescape is **on**
for HTML — every variable interpolation is escaped by default; explicit
``{{ var | safe }}`` is required for trusted markup (we never use it
for user-supplied text).
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

_TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "templates"


def make_env(template_version: str = "v1") -> Environment:
    """Return a Jinja2 ``Environment`` rooted at the template version folder."""

    version_dir = _TEMPLATES_ROOT / "report" / template_version
    if not version_dir.exists():
        raise FileNotFoundError(f"Template version directory not found: {version_dir}")
    env = Environment(
        loader=FileSystemLoader(str(version_dir)),
        autoescape=select_autoescape(["html", "htm", "j2"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["round1"] = lambda v: f"{float(v):.1f}"
    env.filters["intpct"] = lambda v: f"{round(float(v))}%"
    return env


def templates_root() -> Path:
    return _TEMPLATES_ROOT


__all__ = ["make_env", "templates_root"]
