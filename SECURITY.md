# Security policy — Casa Segura

**Last reviewed:** 2026-05-16  
**Scope version:** repo root + shipped Casa Segura services described in [`README`](README.md) and [`ARCHITECTURE`](docs/ARCHITECTURE.md).

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

## Safe harbor

Assume good faith. Do not access or modify user data beyond the minimum credible proof; coordinated disclosure is appreciated.

## False positives / product disputes

Casa Segura MVP does **not** maintain an operator‑curated **developer blacklist** ([`PRD_GENERAL`](docs/Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md) BR‑11 analogue). Accuracy or discrepancy reports for reputation‑like stubs belong in **user-facing reporting** (**[CS-336](docs/Roadmap/tickets/CS-336.md)**) once wired — not treated as unpublished CVEs unless they uncover a systemic security flaw (e.g., IDOR leaking other users’ data).
