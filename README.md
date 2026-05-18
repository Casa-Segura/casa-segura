<p align="center">
  <img src="docs/assets/casa-segura-logo.png" alt="Casa Segura — marca de una casa estilizada sobre fondo verde azulado" width="140" height="140" />
</p>

<h1 align="center">Casa Segura</h1>

<p align="center">
  <strong>Automated analysis of Salvadoran real estate contracts</strong> — upload a PDF or clear photos and get a structured report (rubric score, findings, economic context, citations) so you can decide whether to negotiate or talk to a lawyer <strong>before</strong> signing. User-facing experiences use Spanish in the informal <strong>tú</strong> register.
</p>

<p align="center">
  <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-16.2-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js 16" /></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19" /></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript 5" /></a>
  <a href="https://tailwindcss.com/"><img src="https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 4" /></a>
  <img src="https://img.shields.io/badge/ESLint-9-4B32C3?style=flat-square&logo=eslint&logoColor=white" alt="ESLint 9" />
  <a href="https://vitest.dev/"><img src="https://img.shields.io/badge/Vitest-3-6E9F18?style=flat-square&logo=vitest&logoColor=white" alt="Vitest 3" /></a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white" alt="Django 5.2" /></a>
  <a href="https://www.django-rest-framework.org/"><img src="https://img.shields.io/badge/Django_REST_Framework-3.15+-ED462F?style=flat-square&logo=django&logoColor=white" alt="Django REST Framework" /></a>
  <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://docs.celeryq.dev/"><img src="https://img.shields.io/badge/Celery-5-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery 5" /></a>
  <a href="https://redis.io/"><img src="https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis 7" /></a>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 16" />
  <img src="https://img.shields.io/badge/pgvector-extension-111827?style=flat-square" alt="pgvector" />
  <a href="https://docs.docker.com/compose/"><img src="https://img.shields.io/badge/Docker_Compose-dev_stack-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Compose" /></a>
  <img src="https://img.shields.io/badge/OpenAPI-drf--spectacular-6BA539?style=flat-square&logo=openapiinitiative&logoColor=white" alt="OpenAPI via drf-spectacular" />
  <img src="https://img.shields.io/badge/observability-structlog_%2B_Prometheus-111827?style=flat-square" alt="structlog and Prometheus" />
</p>

<p align="center">
  Código en <a href="https://github.com/Casa-Segura/casa-segura"><strong>github.com/Casa-Segura/casa-segura</strong></a> (público, sin autenticación para lectura)
</p>

<p align="center">
  Documentación formal en <a href="docs/"><code>docs/</code></a> · <a href="docs/Roadmap/README.md">Roadmap</a> · <a href="AGENTS.md"><code>AGENTS.md</code></a> · <a href="AGENTS.md#commit-signing-policy">Política de firmado de commits</a>
</p>

---

> [!IMPORTANT]
> **Aviso legal (BR-07):** Todo lo que vea el usuario debe incluir la frase exacta **«Esto no es asesoría legal»**. Este repositorio es código y documentación de producto; **no** sustituye asesoría jurídica.

## Qué es este proyecto (y qué no es)

**Dentro del alcance:** ingestión + OCR, clasificación, evaluación con rúbrica, generación de informes y entrega multicanal (resumen por SMS, PDF por correo, enlace web), alineado con los PRDs formales — centrado en **entender el texto del contrato**, no en validar personas ni proyectos contra registros del Estado.

**Fuera de alcance para el MVP:** comprobaciones materiales en registros, verificación de vallas como requisito, listas negras, cuentas de usuario como modelo principal, asesoría legal personalizada, almacenamiento permanente de contratos en bruto y contratos fuera de El Salvador. Detalle: [PRD General](docs/Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md).

## Documentación y roadmap

Los requisitos se descomponen en **funciones F1–F8**, **épicas** y **tickets (`CS-*`)** con `depends_on`, criterios de aceptación y `status`. La capacidad se añade **de forma incremental**; el roadmap — no este README — es la lista de lo que está realmente hecho.

| Recurso                                                        | Para qué usarlo                                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [Índice del roadmap](docs/Roadmap/README.md)                   | Mapeo PRD → épica → ticket y bloques de numeración                                         |
| [Índice de fases](docs/Roadmap/phases/README.md)               | Elegir trabajo por fase de entrega                                                         |
| [Plan de trabajo paralelo](docs/Roadmap/PARALLEL_WORK_PLAN.md) | Carriles: `FE WORK`, `BE WORK`, `INFRA WORK`, `API / AI CONNECTIONS`                       |
| [Estado del proyecto (manual)](docs/meta/PROJECT_STATUS.md)    | Narrativa y highlights (los tickets siguen siendo la fuente de verdad del `status`)        |
| [`AGENTS.md`](AGENTS.md)                                       | Higiene de tickets/épicas, rutas canónicas (`backend/`, `frontend/`), normas de privacidad |

Referencias de arquitectura y dominio: [Mapa de funciones](docs/Casa%20Segura%20Formal%20PRDs/FEATURES_MAP.md), [Arquitectura](docs/ARCHITECTURE.md), [Modelo de dominio](docs/Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md).

### Identidad visual en el repo

| Artefacto                     | Ubicación                                                                                                                     |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Logo (README y documentación) | [`docs/assets/casa-segura-logo.png`](docs/assets/casa-segura-logo.png)                                                        |
| Favicon (app web Next.js)     | [`frontend/src/app/favicon.ico`](frontend/src/app/favicon.ico) — convención App Router; el navegador lo sirve automáticamente |

Diseño / tokens UX: [`docs/Design/casa-segura.pen`](docs/Design/casa-segura.pen) (Pencil); notas formales de UI en PRDs y `docs/`.

## Tecnología (resumen)

| Capa              | Stack                                                                                                                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Web**           | [Next.js](https://nextjs.org/) 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4, ESLint, Vitest                                                        |
| **API y dominio** | [Django](https://www.djangoproject.com/) 5.2 LTS, [Django REST Framework](https://www.django-rest-framework.org/), **Pydantic v2**, drf-spectacular (OpenAPI) |
| **Async / jobs**  | Celery, Redis                                                                                                                                                 |
| **Base de datos** | PostgreSQL 16 + **pgvector** (vectores + datos relacionales según PRDs)                                                                                       |
| **Entorno local** | [Docker Compose](docker-compose.dev.yml) — Postgres + Redis para desarrollo                                                                                   |

Decisiones de backend: [`docs/adr/`](docs/adr/) — [ADR-0001 — Django](docs/adr/ADR-0001-django-backend-stack.md) · [ADR-0002 — `platform_core`](docs/adr/ADR-0002-rename-platform-module-to-platform_core.md) · [ADR-0003 — CS-031](docs/adr/ADR-0003-cs031-project-name-normalization-divergence.md) · [ADR-0004 — Versionado](docs/adr/ADR-0004-versioning.md) · [ADR-0005 — Retención (Celery Beat)](docs/adr/ADR-0005-retention-job-scheduling.md).

Divulgación responsable: **[`SECURITY.md`](SECURITY.md)**.

Guías por servicio: [backend/README.md](backend/README.md) · [frontend/README.md](frontend/README.md) · [RAILWAY.md](RAILWAY.md).

### Base de datos (Postgres + pgvector)

- **Local:** [`docker-compose.dev.yml`](docker-compose.dev.yml) usa la imagen **PostgreSQL 16** con pgvector (`pgvector/pgvector:pg16`). Las extensiones `vector`, `pgcrypto` y `uuid-ossp` se crean al iniciar el volumen ([`infra/postgres/init/`](infra/postgres/init/)). Variables: copia [`backend/.env.example`](backend/.env.example) → `backend/.env` (CS-006).

- **Remoto (decisión explícita):** el backend Django, worker, beat y Postgres gestionado viven en **Railway**; la app web Next.js va en **Vercel** (no en Railway). Conexión: `DATABASE_URL` expuesta por Railway; cuando está presente, **anula** los `DB_*` discretos — detalle en [`backend/.env.example`](backend/.env.example) y guía operativa en [`RAILWAY.md`](RAILWAY.md).

- **Si el proveedor no ofrece pgvector** (riesgo R-01-1 en [EPIC-01](docs/Roadmap/EPIC-01-persistence.md)): usar Postgres externo con pgvector, por ejemplo **Neon** como fallback documentado en RAILWAY §3.B — no se compensa con parches en Django; el fallo es de imagen/proveedor.

- **Fallo al crear extensiones (`CREATE EXTENSION vector` erróneo o “extensión no disponible”):** corregir **imagen de Postgres / proveedor** (reprovisionar el plugin, usar Neon u otro host con la extensión). No es un bug de aplicación que se arregle con cambios de código del API.

## Estructura del repositorio

```text
backend/     # Django, ORM, DRF, Celery, ingestión y servicios de análisis
frontend/    # Next.js — landing, subida, selección de entrega, informe
docs/        # PRDs formales, roadmap (tickets/épicas), ADRs, activos de documentación
infra/       # Ayudas para desarrollo local (p. ej. init de Postgres)
```

## Inicio rápido (desarrollo)

> [!NOTE]
> Ajusta variables en `backend/.env`, `frontend/.env` y los `.env.example` de cada parte. No subas secretos al repositorio.

1. **Postgres y Redis**

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Backend** — desde `backend/`, instala dependencias (p. ej. con Poetry), migra y arranca el servidor de desarrollo Django (ajustes en `backend/config`). Detalle: [backend/README.md](backend/README.md).

3. **Frontend**

   ```bash
   cd frontend
   npm install
   cp .env.example .env   # CASASEGURA_API_BASE_URL y variables relacionadas
   npm run dev
   ```

   Abre [http://localhost:3000](http://localhost:3000). Más detalle: [frontend/README.md](frontend/README.md).

### Probar la experiencia web con datos de prueba

Los PDF y la imagen en la carpeta compartida están pensados para **El Salvador**; el mismo flujo sirve para demos en **LATAM** cuando amplies muestras regionales.

1. Abrí la carpeta **[datos de prueba](https://drive.google.com/drive/folders/1iTzumO-TPEulBXOxe4W6D0pTgGzWhtrl?usp=sharing)** en Google Drive (solo lectura).
2. Descargá uno de los PDF de ejemplo (los prefijos del nombre indican escenarios distintos).
3. En la app (local o desplegada), entrá a **`/subir`**, subí el archivo y seguí el informe hasta la entrega que configures.

Para ver el análisis de punta a punta necesitás el backend y las variables descritas arriba; si solo querés recorrer la UX sin API activa, seguí el modo sin backend en [frontend/README.md](frontend/README.md).

Guía para **protección de rama** / checks obligatorios: [`docs/meta/BRANCH_PROTECTION.md`](docs/meta/BRANCH_PROTECTION.md).

### Integración continua (CS-004)

El workflow [**`.github/workflows/ci.yml`**](.github/workflows/ci.yml) corre en **`push`** y **`pull_request`** contra `main` y `development`. Trabajo útil cuando configures protección de rama en GitHub (nombre de checks exactos):

| Check en GitHub        | Rol |
| -----------------------| --- |
| **Backend lint**        | Poetry + Ruff / Black (`--check`) / isort (`--check-only`) + script de validación de retención |
| **Backend tests**       | Postgres 16 (`pgvector`) + Redis → migraciones → `pytest` |
| **Backend migration smoke (CS-035)** | Migrar → `migrate app zero` en orden → volver a migrar |
| **Frontend build**      | Node 22 → `npm ci` → ESLint → **Vitest** → `tsc --noEmit` → `next build` |

Forks pueden reproducirlos con `act` opcionalmente; la vía habitual es abrir PR al repo público para que Actions reporte resultado.

Los fallos deliberados en **Python** muestran códigos de regla **`ruff`** en el log (p. ej. `F401` por import sin uso), que es cómo sabemos que el job de lint no está “silent green”.

### Pre-commit (CS-005)

Los hooks locales en [`.pre-commit-config.yaml`](.pre-commit-config.yaml) ejecutan **`ruff` (lint + autofix)** sobre `backend/**/*.py`, **`prettier --check`** (`prettier@3.8.3`) sobre `frontend/**/*.{ts,tsx,js,jsx,json,md}`, y comprobaciones genéricas (fin de archivo, espacios finales, YAML/TOML/conflictos). **`ruff format` no corre en pre-commit** (CI usa Black más Ruff lint). **`end-of-file-fixer`** omite **`docs/`**, **`frontend/public/`** y **`.cursor/rules/`** para evitar churn en roadmap o artefactos públicos cuando no tocás esos ficheros. Ruff está alineado con `backend/pyproject.toml`. ESLint y mypy siguen orientados a CI (notas en el propio config). Instalación única por clon:

```bash
pip install pre-commit          # o: pipx install pre-commit
pre-commit install
pre-commit run --all-files      # opcional, barrido inicial
```

> [!CAUTION]
> **Privacidad:** Trata como **sensibles** los contenidos OCR, destinos de entrega (SMS/correo/enlace), texto de informes, prompts, registros y cuerpos de error. No registres PII ni archivos en bruto más allá de lo que la API requiera.

## Contrato de la API backend

### Salud y disponibilidad

```
GET /api/health/   →  200 { "status": "ok", "service": "casa-segura-api", "schema_version": "1.0.0", "hostname": "..." }
GET /api/ready/    →  200 { "status": "ok", "schema_version": "1.0.0", "checks": { "database": "ok", "redis": "ok" }, "reasons": [] }
                   →  503 si la base de datos o Redis no están disponibles, con arreglo `reasons` de códigos de fallo.
```

### Sobre de errores (CS-009)

Toda respuesta — éxito o fallo — devuelve la cabecera entrante `X-Request-ID` (o un UUID4 generado). En errores, el mismo valor aparece en el cuerpo como `correlation_id`.

**Ejemplo de éxito:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: 5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f

{ ...carga útil... }
```

**Ejemplo de fallo** (sobre canónico desde `backend/config/exception_handler.py`):

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
X-Request-ID: 5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f

{
  "error_code": "validation_error",
  "message": "Request payload failed validation.",
  "details": { "submission_hash": ["This field is required."] },
  "correlation_id": "5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f",
  "schema_version": "1.0.0"
}
```

Códigos públicos registrados en `backend/shared/domain/exceptions.py::PUBLIC_ERROR_CODES`. Los módulos pueden ampliar el registro sin sombrear entradas existentes.

## Observabilidad (CS-007)

`backend/shared/observability/logging.py::configure_logging` emite logs JSON estructurados en producción (un registro por línea) con forma estable: `timestamp`, `level`, `service`, `correlation_id`, `schema_version`, `rubric_version`, `corpus_version`, más campos que el llamador añade.

`backend/shared/observability/middleware.py::CorrelationIdMiddleware` lee `X-Request-ID` (o genera UUID4), lo enlaza a contextvars de structlog durante la petición y lo repite en la respuesta. Límite: 128 caracteres; valores vacíos o demasiado largos caen a UUID4.

Ejemplo mínimo:

```python
import structlog

logger = structlog.get_logger(__name__)

def handle_submission(submission_id):
    logger.info("submission_received", submission_id=str(submission_id), strategy="pypdf")
```

Métricas en `/metrics/` vía `django-prometheus`.
