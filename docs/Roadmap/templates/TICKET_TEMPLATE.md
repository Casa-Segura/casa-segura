---
template: ticket
tags:
  - casa-segura
  - template
---

# CS-NNN — <verb> <noun>

```yaml
id: CS-NNN
epic: EPIC-NN
status: backlog | in_progress | done | blocked
owner: tbd
estimate: S | M | L           # S=1d, M=2-3d, L=>3d (split if L)
depends_on: [CS-NNN]
prd_refs: [PRD_GENERAL §X, RUBRICA §X]
```

## Context

2–3 sentences. Why this ticket exists. What product behavior it enables. Cite the PRD section that motivates it.

## Scope

**In:**
- ...
- ...

**Out (explicit):**
- ...
- ...

## Acceptance criteria

Each criterion must be **observable** and **testable**. Avoid vague verbs like "works", "supports", "handles". Prefer "given X, when Y, then Z".

- [ ] ...
- [ ] ...

### BVA — boundary value analysis

For any numeric threshold or enum boundary, list the boundary points and the expected behavior on either side. *Skip this section only if the ticket has no numeric/enum boundaries.*

| Input | Boundary | Expected |
|---|---|---|
| score = 4.9 | red/yellow | band = red |
| score = 5.0 | red/yellow | band = yellow |
| score = 7.9 | yellow/green | band = yellow |
| score = 8.0 | yellow/green | band = green |

## Test intent (Rule 9)

One sentence on **why** the behavior matters. A test that only checks `assert result == 5.0` is wrong; the test must encode that *5.0 is the lower bound of the yellow band per [[RUBRICA_CONTRATO]] §2.1*.

## Notes

- PRD reference: [[PRD_GENERAL]] §X
- Prior art / research: [[GENERATED-RESEARCH-...]]
- Open questions: ...
