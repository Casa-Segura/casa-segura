# Benchmark keys — Spanish glossary (prep for CS-130 YAML)

Stable **`benchmark_key`** strings will come from **`economic_benchmarks.yaml`** ([CS-130](../../../Roadmap/tickets/CS-130.md)). Until that file lands, map **comparison rows + report copy** to **`RUBRICA_CONTRATO`** §14 illustrative ranges and keep **financial clarity** headings consistent with **`RUBRICA_CONTRATO`** §11 (same file: [link](../../../Casa%20Segura%20Formal%20PRDs/RUBRICA_CONTRATO.md)).

Cross-reference: **`ECONOMIC_SUMMARY_CONTRACT`** ([link](../../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md)) (`benchmark_key` column).

---

## Proposed mappings (rename when YAML seeds real keys)

| `benchmark_key` (provisional) | YAML path hint (§14 excerpt)                         | Etiqueta ES (usuario)                                           |
| ------------------------------ | ---------------------------------------------------- | ---------------------------------------------------------------- |
| `standard_down_payment_bank_purchase` | `standard_down_payment.bank_or_fsv_purchase.value` | Entrada inicial estándar (banca / FSV)                          |
| `standard_down_payment_direct_developer_mid` | `standard_down_payment.direct_developer_purchase.range` (mid) | Entrada inicial típica con desarrollador                         |
| `bank_mortgage_rate_min`       | `interest_rate.bank_mortgage.range` [0]            | Hipoteca bancaria — piso                                       |
| `bank_mortgage_rate_mid`       | midpoint of `bank_mortgage.range`                  | Hipoteca bancaria — punto medio                                   |
| `bank_mortgage_rate_max`       | `interest_rate.bank_mortgage.range` [1]             | Hipoteca bancaria — techo                                         |
| `fsv_rate_min`                 | `interest_rate.fsv.range` [0]                      | Crédito FSV — piso                                               |
| `fsv_rate_mid`                 | midpoint                                           | Crédito FSV — punto medio                                        |
| `fsv_rate_max`                 | `interest_rate.fsv.range` [1]                       | Crédito FSV — techo                                              |
| `developer_direct_rate_min`    | `interest_rate.developer_direct.range` [0]         | Financiamiento directo desarrollador — piso                       |
| `developer_direct_rate_max`    | `interest_rate.developer_direct.range` [1]         | Financiamiento directo desarrollador — techo                     |
| `credit_term_reasonable_min_months` | `credit_term.reasonable_range` [0] (years→months) | Plazo “razonable” (mín.)                                        |
| `credit_term_reasonable_max_months` | `credit_term.reasonable_range` [1]                | Plazo “razonable” (máx.)                                          |
| `credit_term_ivu_max_months`   | `credit_term.ivu_legal_max`                        | Tope IVU legal (meses, según modelo)                               |
| `total_cost_multiplier_healthy_max` | `total_cost_multiplier.healthy_max`             | Multiplicador costo total vs. efectivo — límite “saludable”      |
| `total_cost_multiplier_high_max`    | `total_cost_multiplier.high_max`                | Multiplicador costo total vs. efectivo — límite “alto”           |
| `total_cost_multiplier_excessive_min` | `total_cost_multiplier.excessive_min`          | Multiplicador costo total vs. efectivo — umbral “excesivo”        |
| `monthly_payment_ratio_healthy_max` | `monthly_payment.ratio_healthy_max`            | Ratio cuota / línea base — “saludable”                           |
| `monthly_payment_ratio_high_max`    | `monthly_payment.ratio_high_max`               | Ratio cuota / línea base — “alto”                                |
| `monthly_payment_ratio_excessive_min` | `monthly_payment.ratio_excessive_min`         | Ratio cuota / línea base — “excesivo”                             |

---

## Review checklist once CS-130 merges

- [ ] Every YAML **`benchmark_key`** has one row above (or rationale for omission).
- [ ] Spanish labels match **`metric_label`** style in **`benchmark_comparisons`** where applicable.
- [ ] BR-07 / disclaimers unaffected (registry remains single source).

