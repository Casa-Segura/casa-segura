"""Celery application — CS-233."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("casasegura")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Retention tasks live outside INSTALLED_APPS autodiscovery path (ADR-0005).
import platform_core.worker.retention.tasks  # noqa: E402, F401
