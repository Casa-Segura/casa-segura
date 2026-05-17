# economic-summary fixtures

Normative examples for **[ECONOMIC_SUMMARY_CONTRACT.md](../../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md)**.

| File                         | Scenario                                      |
| ---------------------------- | --------------------------------------------- |
| `summary-full.json`          | PRD-aligned happy path (`CVP`, comparisons, overcost, warnings). |
| `summary-insufficient-data.json` | BR-09 / derivation_status `insufficient_data`. |
| `summary-warnings-heavy.json`| Multiple warnings plus two benchmark rows (delta null on one metric). |

**Glossary:** [`BENCHMARK_KEY_GLOSSARY.md`](./BENCHMARK_KEY_GLOSSARY.md).

**Note:** `benchmark_key` values are illustrative until **[CS-130](../../../Roadmap/tickets/CS-130.md)** lands `economic_benchmarks.yaml`; align keys with glossary when seeded.
