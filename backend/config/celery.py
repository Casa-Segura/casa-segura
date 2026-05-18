"""Celery application — CS-233."""

from __future__ import annotations

import os

import django
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("casasegura")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Worker CLI imports this module directly (not via manage.py); models must be
# registered before task modules that touch ORM / Django apps.
django.setup()

app.autodiscover_tasks()

# Retention tasks live outside INSTALLED_APPS autodiscovery path (ADR-0005).
import ingestion.infrastructure.celery.pipeline_tasks  # noqa: E402, F401
import platform_core.worker.retention.tasks  # noqa: E402, F401
