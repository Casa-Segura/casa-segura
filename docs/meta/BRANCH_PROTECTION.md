# Branch protection (GitHub)

GitHub **branch protection** and **required status checks** are configured in the repository or organization settings; they cannot be enforced from git alone.

For merge to `main` / `development`, enable required checks to match the jobs in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) (names must match **exactly** as shown in the PR “Checks” tab):

| Required check name | Purpose |
| --- | --- |
| **Backend lint** | Ruff, Black, isort, retention dry-validate |
| **Backend tests** | Postgres + Redis, migrations, pytest |
| **Backend migration smoke (CS-035)** | Forward migrate → roll back to zero → re-apply |
| **Frontend build** | ESLint, Vitest, `tsc`, `next build` |

The root [`README.md`](../../README.md) “Integración continua” table lists the same names for operators wiring protection rules.

See also: [EPIC-01 — Persistence & Schema](../Roadmap/EPIC-01-persistence.md) for the migration-smoke ticket link.
