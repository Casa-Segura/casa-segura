"""Structured logging setup (CS-007).

Configures structlog so every log record is a single JSON line (production /
when DEBUG is False) or a colorized human-readable line (local dev). The
`correlation_id` and `schema_version` keys are always present, sourced from
contextvars populated by `CorrelationIdMiddleware`.

Synthetic handlers may inject `rubric_version`, `corpus_version`, and
`benchmark_version` into the context — those keys propagate verbatim and
default to `None`."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

SCHEMA_VERSION = "1.0.0"
SERVICE_NAME = "casa-segura-api"


def _add_service_context(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Always-on keys: service name + schema version."""
    event_dict.setdefault("service", SERVICE_NAME)
    event_dict.setdefault("schema_version", SCHEMA_VERSION)
    return event_dict


def _add_default_versions(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Ensure rubric/corpus/benchmark versions are present (default None) for log shape stability."""
    event_dict.setdefault("rubric_version", None)
    event_dict.setdefault("corpus_version", None)
    event_dict.setdefault("benchmark_version", None)
    return event_dict


def configure_logging(*, debug: bool, log_level: str = "INFO") -> None:
    """Initialize stdlib logging + structlog. Idempotent: safe to call multiple times."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_service_context,
        _add_default_versions,
        timestamper,
    ]

    if debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.processors.StackInfoRenderer(), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
