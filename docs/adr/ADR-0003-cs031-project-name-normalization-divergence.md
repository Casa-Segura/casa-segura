---
id: ADR-0003
title: Project name canonicalization follows F2 (strip generic words) over CS-031 sample
status: Accepted
date: 2026-05-15
deciders: Backend lane
supersedes: —
related: docs/analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md `ProjectNameNormalizer`, docs/Roadmap/tickets/CS-031.md
---

## Context

`CS-031` ("Project name canonicalization") lists an acceptance example:

> `"  Residencial   LOS ÉBANOS!! "` → `"residencial los ebanos"`

`docs/analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md` defines the same
function (`ProjectNameNormalizer.normalize`) but with a concrete
`GENERIC_WORDS` set that the algorithm **strips from both ends** of the
token sequence:

```python
GENERIC_WORDS = {
    "proyecto", "residencial", "condominio", "urbanizacion",
    "lotificacion", "complejo", "parque",
}
```

Under the F2 rule, the same input produces `"los ebanos"` — the leading
`residencial` is dropped. The two specifications give different answers
for any project name that starts or ends with a generic word.

This isn't a small edge case: keeping the generic word means
`"Residencial El Roble"` and `"El Roble"` are treated as different
projects, defeating the dedupe key on `Project.normalized_name`. Casa
Segura's whole aggregation-by-project intelligence relies on that key
matching reliably.

## Decision

Adopt the **F2 algorithm** (strip generic words from both ends). The
implementation lives in
`platform_core/domain/project_name.py::normalize_project_name`.

Behaviour:

| Input | Result |
|---|---|
| `"Residencial Las Palmeras"` | `"las palmeras"` |
| `"PROYECTO URBANO CUMBRES DEL VOLCÁN"` | `"urbano cumbres del volcan"` |
| `"CONDOMINIO ARRECIFE 2"` | `"arrecife 2"` |
| `"Lotificación El Roble"` | `"el roble"` |
| `"Residencial"` alone | `""` → caller assigns `unknown_<hash>` placeholder |
| `"El Roble"` and `"Residencial El Roble"` | both → `"el roble"` (intentional dedupe) |

The function never raises and never assigns the placeholder itself;
callers (`platform_core` Project upsert logic, F2 service) map an empty
return value to `unknown_<sha1[:8]>` and skip dedupe via
`is_placeholder_normalized_name`.

CS-031's worked example will be updated to `"los ebanos"` in the next
ticket grooming pass.

## Consequences

**Positive.**
- Dedupe key actually dedupes the realistic Spanish-language inputs that
  arrive in El Salvador real estate contracts.
- Matches the more concrete spec; F4/F5/F6 don't need to second-guess
  classification's normalization.

**Negative.**
- Two legitimately distinct projects whose names collide post-strip
  (e.g. two different "El Roble" projects in different municipalities)
  are merged into one. Risk acknowledged in `_shared/GLOBAL_ASSUMPTIONS.md`
  §4 (OQ-N2). Mitigation: `Project.metadata` may carry locality hints
  later if we ever need to split.
- CS-031 sample copy needs editing.

## Alternatives considered

1. **Follow CS-031 verbatim.** Rejected: defeats the project dedupe
   purpose for the most common Spanish naming pattern.
2. **Strip only from the start, not the end.** Rejected: doesn't help
   "El Roble Residencial", which is common in Spanish marketing.
3. **Configurable per deployment.** Rejected: premature; one rule is
   easier to audit than a runtime flag.
