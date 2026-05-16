# Classification evaluation harness (CS-115)

Synthetic, version-controlled corpus that pins F2 classification quality
against the targets in [`PRD_F2_CLASIFICACION`](../../docs/Casa%20Segura%20Formal%20PRDs/PRD_F2_CLASIFICACION.md)
§9. The fixture lives in `classification_eval_cases.yaml`; the harness
ships as the Django management command `eval_classification`.

## Threshold targets (PRD F2 §9)

The fixture declares the live numbers under `thresholds:` so they stay
in one place:

| Metric                                       | Target  | Source         |
|----------------------------------------------|---------|----------------|
| `macro_accuracy_min`                         | `0.95`  | PRD F2 §9 — ≥95% on in-scope docs |
| `not_classifiable_precision_min`             | `0.90`  | PRD F2 §9 + US-06 (low FP into in-scope) |
| `reclassification_false_positive_max`        | `0.02`  | PRD F2 §9 — <2% legit purchase → LEA |
| `reclassification_false_negative_max`        | `0.10`  | PRD F2 §9 — <10% disguised leases missed |

Override `macro_accuracy_min` at runtime with `--threshold`. The other
three are informational today; CI-side enforcement lands with the gate
work (see CS-115 AC4 status note).

## How to add a case

Each case is a top-level entry under `cases:` in
`classification_eval_cases.yaml`. Schema (validated strictly by the
harness via pydantic v2 — extra keys are rejected):

```yaml
- id: cls-cvc-001                # unique, lowercase, dash-separated
  contract_type: CVC             # ContractType enum (8 covered + NOT_CLASSIFIABLE)
  description: "Short Spanish description of the scenario."
  contract_text: |
    <synthetic excerpt, ~300-500 chars, Spanish, BR-07 safe>
  expected:
    contract_type: CVC           # gold post-classification label
    min_confidence: 0.85         # advisory floor
    leasing_indicators:          # OPTIONAL — only for CVC/CVP/APV
      expected_count: 0
      expected_recommendation: CVC   # CVC|CVP|APV|LEA
  tags: [happy_path, no_leasing_indicators]
```

**BR-07 / PRD_GENERAL §10:** `contract_text` MUST be synthetic. No real
names, addresses, DUI, IBAN, phone numbers, or emails. Use the obvious
placeholders the existing corpus uses (`JUAN PÉREZ`, `MARÍA GARCÍA`,
`Calle Falsa 123, San Salvador`, `$185,000.00`).

## How to run the harness

All commands run from `backend/`. None of them touch the DB.

```bash
# 1. CI-safe: validate the YAML schema and print the coverage matrix
#    (no LLM call, no cost).
python manage.py eval_classification --dry-run

# 2. Full run with default threshold from the fixture; live OpenRouter.
python manage.py eval_classification

# 3. Full run, override accuracy threshold, dump JSON report for
#    artifact storage.
python manage.py eval_classification --threshold 0.95 --out artifacts/cls_eval.json
```

The command exits with status `1` when macro accuracy drops below
`--threshold` (or the fixture default). This is the hook for the future
CI gate; today the gate is documented but not yet wired.

## Reclassification BVA (PRD §8.4 / BR-03)

Two intentionally crafted fixtures sit on the 4-of-6 indicator boundary:

* `cls-cvp-bva-003-of-6` — exactly **3** Art. 2 LAF indicators present.
  Expected: `contract_type` stays `CVP`, reclassification declines.
* `cls-cvp-bva-004-of-6` — exactly **4** Art. 2 LAF indicators present.
  Expected: `contract_type` is initially `CVP`, then
  `LeasingReclassificationDetector` flips the recommendation to `LEA`.

These two cases pin the `DEFAULT_RECLASSIFICATION_THRESHOLD = 4`
constant in `classification.domain.leasing_indicators`. Changing the
threshold means updating the BVA fixtures **and** filing a PRD revision
per BR-03 — both sides of the boundary need to move together.

A separate fixture (`cls-borderline-001`) exercises the validation band
(~0.65 confidence) called out in PRD US-01 / §8.3.
