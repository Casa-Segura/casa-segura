"""Django settings for the Casa Segura backend (config project)."""

from datetime import timedelta
from pathlib import Path

import environ

from shared.observability.logging import configure_logging

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

# Railway exposes the public service domain via RAILWAY_PUBLIC_DOMAIN.
# Append it to ALLOWED_HOSTS so deploys don't 400 before someone remembers
# to set ALLOWED_HOSTS manually.
_RAILWAY_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default="")
if _RAILWAY_DOMAIN and _RAILWAY_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _RAILWAY_DOMAIN]

# Trust Railway's reverse proxy for HTTPS detection. Without this, request.is_secure()
# returns False on Railway and Django emits insecure cookies / refuses CSRF posts.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF needs the scheme + host for cross-origin POSTs (admin, DRF browsable API).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if _RAILWAY_DOMAIN:
    _railway_csrf = f"https://{_RAILWAY_DOMAIN}"
    if _railway_csrf not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, _railway_csrf]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "softdelete",
    "django_celery_beat",
    "django_prometheus",
    # Project — order matters for FK resolution at migration time:
    #   rubric/corpus/economics declare PKs referenced by platform_core.ContractAnalysis.
    "common.infrastructure.django.apps.CommonConfig",
    "rubric.infrastructure.django.apps.RubricConfig",
    "corpus.infrastructure.django.apps.CorpusConfig",
    "economics.infrastructure.django.apps.EconomicsConfig",
    "platform_core.infrastructure.django.apps.PlatformCoreConfig",
    "ingestion.infrastructure.django.apps.IngestionConfig",
    "classification.infrastructure.django.apps.ClassificationConfig",
    "reports.infrastructure.django.apps.ReportsConfig",
    "delivery.infrastructure.django.apps.DeliveryConfig",
    # EPIC-12 optional stubs (`/api/v1/project-verification/...`).
    "project_verification.apps.ProjectVerificationConfig",
]


MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "shared.observability.middleware.CorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves collected static files (admin, drf-spectacular UI)
    # without needing nginx/CDN in front. Must sit immediately after
    # SecurityMiddleware per WhiteNoise docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.infrastructure.django.middlewares.RequestLoggingMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "common.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = [
    "common.infrastructure.django.backends.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]


DB_ENGINE = env("DB_ENGINE", default="postgresql")
# Railway (and most PaaS) expose Postgres as a single DATABASE_URL.
# When present it wins over the discrete DB_* knobs.
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db_url("DATABASE_URL")}
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
elif DB_ENGINE == "sqlite":
    # NOTE: SQLite is only suitable for `manage.py check` / `makemigrations` validation.
    # Casa Segura models use Postgres-only field types (ArrayField, VectorField, GinIndex);
    # `migrate` requires Postgres 15+ with pgvector (CS-020).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="casasegura"),
            "USER": env("DB_USER", default="postgres"),
            # Aligns with docker-compose.dev.yml + CI service Postgres (local dev).
            "PASSWORD": env("DB_PASSWORD", default="administrador"),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
            "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
            "CONN_HEALTH_CHECKS": True,
            # CS-022 AC2: default off so per-view `transaction.atomic()` is the
            # explicit, intentional choice (cheaper + matches Django 5.2 guidance).
            # Flip via DB_ATOMIC_REQUESTS=True to wrap every request in an
            # implicit transaction.
            "ATOMIC_REQUESTS": env.bool("DB_ATOMIC_REQUESTS", default=False),
        }
    }


MIGRATION_MODULES = {
    "common": "common.infrastructure.django.migrations",
    "platform_core": "platform_core.infrastructure.django.migrations",
    "ingestion": "ingestion.infrastructure.django.migrations",
    "classification": "classification.infrastructure.django.migrations",
    "corpus": "corpus.infrastructure.django.migrations",
    "rubric": "rubric.infrastructure.django.migrations",
    "economics": "economics.infrastructure.django.migrations",
    "reports": "reports.infrastructure.django.migrations",
    "delivery": "delivery.infrastructure.django.migrations",
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "EXCEPTION_HANDLER": "config.exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Casa Segura API",
    "DESCRIPTION": "Casa Segura backend API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


# ─── OpenRouter (LLM gateway, CS-006) ───
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")
OPENROUTER_BASE_URL = env("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
OPENROUTER_OCR_MODEL = env("OPENROUTER_OCR_MODEL", default="mistralai/pixtral-large-2411")
OPENROUTER_PDF_PLUGIN_ENGINE = env("OPENROUTER_PDF_PLUGIN_ENGINE", default="mistral-ocr")
OPENROUTER_DEFAULT_TEXT_MODEL = env("OPENROUTER_DEFAULT_TEXT_MODEL", default="mistralai/pixtral-large-2411")
OPENROUTER_HTTP_REFERER = env("OPENROUTER_HTTP_REFERER", default="https://casa-segura.local")
OPENROUTER_X_TITLE = env("OPENROUTER_X_TITLE", default="Casa Segura OCR")
OPENROUTER_TIMEOUT_SECONDS = env.int("OPENROUTER_TIMEOUT_SECONDS", default=60)
OPENROUTER_MAX_RETRIES = env.int("OPENROUTER_MAX_RETRIES", default=3)


# ─── Internal API token (EPIC-04 PR-6) ───
# Shared secret for /api/v1/internal/* (currently: the F2 classify QA
# endpoint). Empty by default → endpoint is unreachable until the operator
# sets a value (fail-closed). Compared via secrets.compare_digest.
INTERNAL_API_TOKEN = env("INTERNAL_API_TOKEN", default="")


# ─── OCR pipeline (Phase 1, EPIC-02) ───
OCR_MAX_PAGES = env.int("OCR_MAX_PAGES", default=50)
OCR_MAX_BYTES = env.int("OCR_MAX_BYTES", default=15 * 1024 * 1024)  # CS-059: PRD §US-01 canonical
OCR_VISION_LLM_TIMEOUT = env.int("OCR_VISION_LLM_TIMEOUT", default=60)
OCR_TESSERACT_ENABLED = env.bool("OCR_TESSERACT_ENABLED", default=True)
OCR_TESSERACT_LANG = env("OCR_TESSERACT_LANG", default="spa")
OCR_TESSERACT_MIN_CONFIDENCE = env.int("OCR_TESSERACT_MIN_CONFIDENCE", default=60)


# ─── RAG retrieval (Phase 1, EPIC-03) ───
RAG_SIMILARITY_THRESHOLD = env.float("RAG_SIMILARITY_THRESHOLD", default=0.65)
RAG_TOP_K = env.int("RAG_TOP_K", default=5)
RAG_RERANKER_ENABLED = env.bool("RAG_RERANKER_ENABLED", default=False)
RAG_RERANKER_MODEL = env("RAG_RERANKER_MODEL", default="BAAI/bge-reranker-v2-m3")
RAG_RERANKER_POOL_SIZE = env.int("RAG_RERANKER_POOL_SIZE", default=10)
EMBEDDING_MODEL = env("EMBEDDING_MODEL", default="intfloat/multilingual-e5-large")
EMBEDDING_DEVICE = env("EMBEDDING_DEVICE", default="cpu")
EMBEDDING_BATCH_SIZE = env.int("EMBEDDING_BATCH_SIZE", default=32)


# ─── Active catalog versions ───
# Note: ACTIVE_CORPUSF_VERSION carries a legacy typo. Phase 1 honours
# both spellings (preferring the typo to match the live `.env`), and a
# follow-up will rename when the live secrets are updated.
ACTIVE_RUBRIC_VERSION = env("ACTIVE_RUBRIC_VERSION", default="")
ACTIVE_CORPUS_VERSION = env("ACTIVE_CORPUS_VERSION", default=env("ACTIVE_CORPUSF_VERSION", default=""))
ACTIVE_BENCHMARK_VERSION = env("ACTIVE_BENCHMARK_VERSION", default="")


# ─── Zavu webhooks (delivery / inbound notifications) ───
ZAVU_WEBHOOK_SECRET = env("ZAVU_WEBHOOK_SECRET", default="")

# ─── Zavu outbound (SMS / email via api.zavu.dev) ───
# Prefer ZAVUDEV_API_KEY (SDK name); fall back to ZAVU_API_KEY for compatibility.
ZAVUDEV_API_KEY = env("ZAVUDEV_API_KEY", default="") or env("ZAVU_API_KEY", default="")
ZAVU_SENDER_ID = env("ZAVU_SENDER_ID", default="")

# ─── Delivery targets & SMS ───
DELIVERY_TARGET_HASH_SALT = env("DELIVERY_TARGET_HASH_SALT", default="dev-local-salt-change-me")
PUBLIC_APP_BASE_URL = env("PUBLIC_APP_BASE_URL", default="http://localhost:8000")
SMS_PROVIDER = env("SMS_PROVIDER", default="stub")
SMS_API_BASE_URL = env("SMS_API_BASE_URL", default="")
SMS_API_KEY = env("SMS_API_KEY", default="")
SMS_FROM = env("SMS_FROM", default="")
SMS_TIMEOUT_SECONDS = env.float("SMS_TIMEOUT_SECONDS", default=15.0)
SMS_MAX_SENDS_PER_SECOND = env.int("SMS_MAX_SENDS_PER_SECOND", default=5)
SMS_SEGMENT_CHAR_BUDGET = env.int("SMS_SEGMENT_CHAR_BUDGET", default=480)
SMS_WEBHOOK_SECRET = env("SMS_WEBHOOK_SECRET", default="")

# ─── Public HTML report link TTL — worker ``web_link`` + GET `/r/<id>/` (maps ``REPORT_LINK_TTL_DAYS``) ───
PUBLIC_REPORT_LINK_TTL_DAYS = env.int("REPORT_LINK_TTL_DAYS", default=30)

# ─── Retention jobs (PRD F8 §6.3, ADR-0005, CS-271+) ───
JOB_BATCH_SIZE = env.int("JOB_BATCH_SIZE", default=100)
DELIVERY_TARGET_ERASE_GRACE_SECONDS = env.int("DELIVERY_TARGET_ERASE_GRACE_SECONDS", default=300)
ANONYMIZATION_AFTER_DAYS = env.int("ANONYMIZATION_AFTER_DAYS", default=90)


# ─── Optional project verification (EPIC-12 / CS-356) ───
# Mirrors `frontend` `PROJECT_VERIFICATION_ENABLED`; default-off for safe prod rollouts.
PROJECT_VERIFICATION_ENABLED = env.bool(
    "PROJECT_VERIFICATION_ENABLED",
    default=False,
)


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# `collectstatic` target. Required for the Railway preDeployCommand and any
# CDN/WhiteNoise serving path. Path is gitignored.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

configure_logging(debug=DEBUG, log_level=LOG_LEVEL)
