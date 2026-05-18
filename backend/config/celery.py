"""Celery application — CS-233."""

from __future__ import annotations

import os
import sys

import django
from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun, worker_ready

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


def _banner(title: str, lines: list[tuple[str, object]]) -> None:
    """Print a human-readable, easy-to-skim banner straight to stdout.

    Railway and `celery worker` both flush stdout immediately, so this is the
    most reliable way to see runtime config without depending on structlog
    JSON renderer or grep.
    """
    width = 72
    bar = "=" * width
    print(f"\n{bar}", file=sys.stdout, flush=True)
    print(f"  {title}", file=sys.stdout, flush=True)
    print(bar, file=sys.stdout, flush=True)
    key_w = max((len(k) for k, _ in lines), default=0) + 2
    for key, value in lines:
        print(f"  {key:<{key_w}} {value}", file=sys.stdout, flush=True)
    print(f"{bar}\n", file=sys.stdout, flush=True)


@worker_ready.connect
def _log_worker_boot(sender, **_kwargs) -> None:
    """Print runtime config + active catalog versions when the worker is ready.

    Every restart shows whether the worker can see an active rubric/corpus/
    benchmark and which Postgres it is connected to. Reads at a glance — no
    need to shell in or grep JSON.
    """
    from django.conf import settings as dj_settings
    from django.db import connection

    def _safe_active(model_path: str, attr: str = "version"):
        try:
            module_path, cls = model_path.rsplit(".", 1)
            mod = __import__(module_path, fromlist=[cls])
            model = getattr(mod, cls)
            row = model.objects.filter(is_active=True).only(attr).first()
            return getattr(row, attr) if row else "<NONE>"
        except Exception as exc:
            return f"<ERROR: {exc.__class__.__name__}>"

    rubric = _safe_active("rubric.infrastructure.django.models.RubricVersion")
    corpus = _safe_active("corpus.infrastructure.django.models.CorpusVersion")
    benchmark = _safe_active("economics.infrastructure.django.models.BenchmarkVersion")

    try:
        from ingestion.infrastructure.django.models import ContractSubmission

        submissions = ContractSubmission.objects.count()
    except Exception as exc:
        submissions = f"<ERROR: {exc.__class__.__name__}>"

    db = connection.settings_dict
    broker = getattr(dj_settings, "CELERY_BROKER_URL", "") or ""
    broker_short = broker.split("@")[-1] if "@" in broker else broker

    _banner(
        "CELERY WORKER READY",
        [
            ("hostname:", getattr(sender, "hostname", "?")),
            ("db_host:", db.get("HOST")),
            ("db_name:", db.get("NAME")),
            ("db_port:", db.get("PORT")),
            ("broker:", broker_short),
            ("rubric_version (active):", rubric),
            ("corpus_version (active):", corpus),
            ("benchmark_version (active):", benchmark),
            ("contract_submission rows:", submissions),
        ],
    )


@task_prerun.connect
def _log_task_prerun(sender=None, task_id=None, args=None, kwargs=None, **_kwargs) -> None:
    name = getattr(sender, "name", str(sender))
    sub_id = (kwargs or {}).get("submission_id") or (args[0] if args else "?")
    print(f"\n[TASK ▶ START]  {name}  submission_id={sub_id}  task_id={task_id}", flush=True)


@task_postrun.connect
def _log_task_postrun(sender=None, task_id=None, state=None, args=None, kwargs=None, **_kwargs) -> None:
    name = getattr(sender, "name", str(sender))
    sub_id = (kwargs or {}).get("submission_id") or (args[0] if args else "?")
    icon = "✔" if state == "SUCCESS" else "✖"
    print(f"[TASK {icon} END]    {name}  submission_id={sub_id}  state={state}\n", flush=True)


@task_failure.connect
def _log_task_failure(sender=None, task_id=None, exception=None, **_kwargs) -> None:
    name = getattr(sender, "name", str(sender))
    print(
        f"[TASK ✖ FAILURE] {name}  task_id={task_id}  "
        f"error_class={exception.__class__.__name__ if exception else None}  "
        f"msg={str(exception) if exception else ''}",
        flush=True,
    )
