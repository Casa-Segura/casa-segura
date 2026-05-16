# syntax=docker/dockerfile:1.6
#
# Casa Segura backend — multi-stage Docker build.
#
# Targets:
#   - web     : Gunicorn serving the Django WSGI app (no OCR/PDF deps).
#   - worker  : Celery worker (includes Tesseract, Poppler, libheif for OCR/PDF/HEIC).
#   - beat    : Celery beat scheduler (no OCR/PDF deps).
#
# Build with BuildKit, e.g.:
#   DOCKER_BUILDKIT=1 docker build --target web    -t casa-segura/web .
#   DOCKER_BUILDKIT=1 docker build --target worker -t casa-segura/worker .
#   DOCKER_BUILDKIT=1 docker build --target beat   -t casa-segura/beat .

# ---------------------------------------------------------------------------
# Stage 1: base — install Python deps with Poetry into an in-project venv.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.2.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true

# Build-time deps for compiling psycopg2 and other native extensions.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry into an isolated location.
RUN pip install "poetry==${POETRY_VERSION}"

# Copy dependency manifests first to maximize layer cache hits.
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies only (no dev) into ./.venv
RUN poetry install --no-root --no-ansi

# ---------------------------------------------------------------------------
# Stage 2: runtime-base — minimal image, copies the prebuilt venv.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

# Runtime-only deps: libpq5 for psycopg2, curl for healthchecks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy the prebuilt virtualenv from the base stage.
COPY --from=base --chown=appuser:appuser /app/.venv /app/.venv

# Copy application source.
COPY --chown=appuser:appuser . /app

USER appuser

# ---------------------------------------------------------------------------
# Stage 3a: web — Gunicorn serving Django.
# ---------------------------------------------------------------------------
FROM runtime-base AS web

EXPOSE 8000

# $PORT is set by Railway/most PaaS; default to 8000 for local `docker run`.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent --show-error "http://localhost:${PORT:-8000}/api/health/" || exit 1

# Shell form so $PORT expands. Railway overrides this via railway.toml startCommand
# (which also binds to $PORT). Local `docker run` falls back to 8000.
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --access-logfile -

# ---------------------------------------------------------------------------
# Stage 3b: worker — Celery worker with OCR/PDF/HEIC native deps.
# ---------------------------------------------------------------------------
FROM runtime-base AS worker

# Re-enter root briefly to install OS-level OCR/PDF deps.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-spa \
        poppler-utils \
        libheif1 \
    && rm -rf /var/lib/apt/lists/*
USER appuser

CMD ["celery", "-A", "shared.infrastructure.celery", "worker", "-l", "INFO"]

# ---------------------------------------------------------------------------
# Stage 3c: beat — Celery beat scheduler (DB-backed schedule).
# ---------------------------------------------------------------------------
FROM runtime-base AS beat

CMD ["celery", "-A", "shared.infrastructure.celery", "beat", "-l", "INFO", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
