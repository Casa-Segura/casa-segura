# Design Patterns — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15

---

## Patterns Applied

### Pure Deterministic Service

**Why it fits:** Every economic figure feeds the user's most concrete decision input. Determinism is non-negotiable. F5 has zero non-determinism: no LLM, no clock-based logic except `last_updated`, no network calls beyond Postgres reads.

**Implementation:** All methods on `EconomicAnalysisService` are pure functions of `(raw_fields, contract_type, benchmarks)`. Tests assert byte-for-byte reproducibility.

---

### Asymmetric Penalty Encoded as Assessment Enum

**Why it fits:** F5 never decides "this is a penalty"; it labels (`below_market_favorable`, `within_market`, `above_market`, `well_above_market`). F4 reads these labels and applies the rubric's asymmetric scale. F5 stays neutral.

**Implementation:** `BenchmarkComparison.assessment` enum; comparison logic in `_assess_rate`, `_assess_down_payment`, etc.

---

### Versioned Immutable Catalog (shared pattern)

Same as F3 corpus and F4 rubric. Benchmarks have a `BenchmarkVersion`; analyses pin theirs.

---

### Watermark Barrier (the source side)

**Why it fits:** F5 sets `contract_analysis.economic_summary`; F4 polls. The pattern is the same as F4↔F5; F5 is the *signal source*. F5 must therefore write atomically — either the full summary or nothing — so F4 never sees a half-built object.

**Implementation:** `ContractAnalysisRepository.persist_economic_summary` uses one UPDATE; the JSONB column is set in a single statement.

---

### Conservative-on-ambiguity

**Why it fits:** When the LLM extraction (F2) is unsure about a value, F5 chooses the interpretation least favorable to the buyer. Concretely: if `monthly_payment` is extracted with low confidence but a theoretical-amortization value is higher, F5 uses the theoretical (worst case) for the overcost computation.

**Implementation:** `_resolve_ambiguity` helper inside `EconomicAnalysisService`.

---

### Adapter (FrenchAmortization, CurrencyConverter)

**Why it fits:** Although the math is fixed (PRD §3 BR-06), isolating it in adapters keeps the service body readable and the math unit-testable.

---

## Patterns Considered and Rejected

### LLM-assisted reasoning ("Is this rate weird for this segment?")

Tempting: ask the LLM to opine on whether a rate is reasonable. Rejected because: introduces non-determinism, contradicts PRD BR-13 ("F5 does not call the LLM"), and the benchmark comparison is sufficient.

### Time-value-of-money / NPV computation

The PRD §10 Q-5 raises NPV ("would the savings be invested?"). Rejected for MVP. The current overcost is an honest aggregate.

### User-contributed benchmark

PRD §10 Q-8: allow a user to say "I have a preapproval at 8%". Rejected because: violates "no user data" posture; introduces UI complexity; small audience.

---

**End of document.**
