# Security policy — Casa Segura

**Version:** 1.0
**Last reviewed:** 2026-05-17
**Scope version:** repo root + shipped Casa Segura services described in [`README`](README.md) and [`ARCHITECTURE`](docs/ARCHITECTURE.md).
**Related runbooks:** [Secrets rotation](docs/RUNBOOK_SECRETS.md) · [TLS posture (CS-333)](docs/Roadmap/tickets/CS-333.md)

## Reporting vulnerabilities

Submit reports in **Spanish or English**. Initial triage acknowledgement is **best-effort within 72 business hours** unless volume or severity requires escalation.

### Preferred channel

Email **security@casa-segura.org** (must be monitored in production deployments). Provide:

- Brief description of impact and reproducibility steps  
- Affected component (web/API/worker/repo path)  
- Severity guess (critical / high / medium / low)  
- Credential-free repro where possible  

PGP encryption is welcome when published for that address.

## Scope

### In scope

- Casa Segura application code (`backend/`, `frontend/` in this repo)  
- Hosted infrastructure we operate for Casa Segura (misconfiguration leaking data, SSRF affecting our infra, unauthorized access paths)  

### Explicitly out of scope

- **Third‑party misuse** (e.g., abuse of frontier LLMs or telecom vendors outside our tenancy) — report upstream per their disclosure programs  
- **Social engineering**, spam, phishing, or physical attacks  
- **Dependency-only** issues without a reproducible Casa Segura integration path *(still welcomed as low‑priority FYI)*  

## Triage severity & response expectations

| Severity | Examples | Acknowledgement target | Resolution target |
|---|---|---|---|
| **Critical** | RCE, IDOR leaking other users' data, full database access | 24 business hours | 7 days (workaround) / 30 days (fix) |
| **High** | Auth bypass against `/api/v1/internal/*`, signed-link forgery | 48 business hours | 14 days |
| **Medium** | Stored XSS in HTML report, rate-limit bypass on public endpoints | 72 business hours | 30 days |
| **Low / informational** | Dependency CVE without exploitable path, hardening suggestion | 72 business hours | Triaged in next planning cycle |

Reports in Spanish receive an Spanish response; reports in English get an English response.

## Safe harbor

Assume good faith. Do not access or modify user data beyond the minimum credible proof; coordinated disclosure is appreciated.

## False positives / product disputes

Casa Segura MVP does **not** maintain an operator‑curated **developer blacklist** ([`PRD_GENERAL`](docs/Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md) BR‑11 analogue). Accuracy or discrepancy reports for reputation‑like stubs go through the user-facing report channel at **`POST /api/v1/feedback/error-reports/`** (CS-336) — not treated as unpublished CVEs unless they uncover a systemic security flaw (e.g., IDOR leaking other users' data).
