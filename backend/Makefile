.PHONY: help install migrate makemigrations migrations-check rollback fresh-db check format lint type-check test test-smoke seed-rubric seed-corpus retention-scheduler-dry-validate runserver shell celery-worker celery-beat dev-up dev-down dev-logs

help:                ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:             ## poetry install
	poetry install

migrate:             ## Apply all pending migrations.
	poetry run python manage.py migrate

makemigrations:      ## Generate migrations from model changes.
	poetry run python manage.py makemigrations

migrations-check:    ## Fail if model changes aren't captured in a migration (CI-friendly).
	poetry run python manage.py makemigrations --check --dry-run

rollback:            ## Roll back app to a specific migration. Usage: `make rollback APP=ingestion TO=0001_initial`
	@if [ -z "$(APP)" ] || [ -z "$(TO)" ]; then \
		echo "Usage: make rollback APP=<app_label> TO=<migration_name>"; \
		echo "Example: make rollback APP=ingestion TO=0001_initial"; \
		exit 1; \
	fi
	poetry run python manage.py migrate $(APP) $(TO)

fresh-db:            ## DANGER: drops + recreates `casasegura` DB, runs migrate. Local dev only.
	PGPASSWORD=administrador dropdb -h localhost -U postgres --if-exists casasegura && \
		PGPASSWORD=administrador createdb -h localhost -U postgres casasegura && \
		PGPASSWORD=administrador psql -h localhost -U postgres -d casasegura -c 'CREATE EXTENSION vector; CREATE EXTENSION pgcrypto; CREATE EXTENSION "uuid-ossp";'
	$(MAKE) migrate

check:               ## manage.py check + check --deploy
	poetry run python manage.py check
	poetry run python manage.py check --deploy

format:              ## black + isort
	poetry run black .
	poetry run isort .

lint:                ## ruff check
	poetry run ruff check .

type-check:          ## mypy
	poetry run mypy .

test:                ## pytest (all tests, verbose)
	poetry run pytest -v

test-smoke:          ## pytest -k smoke (CI fast lane)
	poetry run pytest -k smoke

seed-rubric:         ## python manage.py seed_rubric_version
	poetry run python manage.py seed_rubric_version

seed-corpus:         ## python manage.py seed_corpus_version
	poetry run python manage.py seed_corpus_version

retention-scheduler-dry-validate: ## ADR-0005 harness (CS-270): SLA constants + TZ, no DB
	poetry run python scripts/retention_scheduler_dry_validate.py

runserver:           ## Django dev server on :8000
	poetry run python manage.py runserver 0.0.0.0:8000

shell:               ## Django shell_plus if available, else shell
	poetry run python manage.py shell_plus 2>/dev/null || poetry run python manage.py shell

celery-worker:       ## Celery worker
	poetry run celery -A config worker -l info

celery-beat:         ## Celery beat
	poetry run celery -A config beat -l info

dev-up:              ## docker compose -f ../docker-compose.dev.yml up -d
	docker compose -f ../docker-compose.dev.yml up -d

dev-down:            ## docker compose -f ../docker-compose.dev.yml down
	docker compose -f ../docker-compose.dev.yml down

dev-logs:            ## docker compose -f ../docker-compose.dev.yml logs -f
	docker compose -f ../docker-compose.dev.yml logs -f
