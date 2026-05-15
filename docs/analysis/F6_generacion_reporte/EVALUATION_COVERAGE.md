# Evaluation Coverage — F6: Report Generation

> Generated: 2026-05-15

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01 compose HTML | IMPLEMENTATION_PLAN Story US-01 + templates | COVERED |
| US-02 header + disclaimer | `_header.html.j2` partial | COVERED |
| US-03 verdict (score, band, override box) | `_verdict.html.j2` | COVERED |
| US-04 economic analysis with SVG bars + Art. 1686 | `_economic.html.j2` | COVERED |
| US-05 categories breakdown collapsible | `_categories.html.j2` | COVERED |
| US-06 findings ordered + cap at 25 | `_findings.html.j2` + `ReportFinder` | COVERED |
| US-07 three action blocks (LLM + deterministic) | `_actions.html.j2` + `TakeToLawyerLlm` | COVERED |
| US-08 anonymized template | `anonymized.html.j2` + branch in service | COVERED |
| US-09 PDF rendering | `ReportPdfRenderer` + WeasyPrint | COVERED |
| US-10 versioning | template_version + footer disclosure + hash | COVERED |
| BR-01 no persistence of HTML/PDF | Privacy contract by design | COVERED |
| BR-02 disclaimer locations | `_header`, `_findings`, `_footer` | COVERED |
| BR-03 stored versions used | Service reads stored fields | COVERED |
| BR-04 Spanish "tú" | Templates copy | COVERED |
| BR-05 no full contract text | Only `evidence_clause_snippet` rendered | COVERED |
| BR-06 no external logos | Style rule | COVERED |
| BR-07 anonymized degraded | Branch | COVERED |
| BR-08 Art. 1686 mode config | `REPORT_INCLUDE_ART_1686_WARNING` | COVERED |
| BR-09 project note | Footer disclaimer | COVERED |
| BR-10 project context line | Footer summary line | COVERED |
| BR-11 error reporting link | Footer `errores@casasegura.sv` | COVERED |
| BR-12 versions declared | Footer | COVERED |
| BR-13 no external JS | Inline only | COVERED |
| BR-14 no external resources | Inline CSS, no fonts/images URLs | COVERED |
| Data: optional `report_generation_log` | Migration | COVERED |
| Integration: F4 → F6 (chain) | Celery placeholder | COVERED |
| Integration: F6 → F7 (sync invocation) | F7's tasks call F6 | COVERED |
| LLM prompt §8.1 lawyer | `lawyer_prompt.py` verbatim | COVERED |
| NFR HTML P50 ≤ 500 ms | Stage 12 metrics | COVERED |
| NFR PDF P50 ≤ 3 s | Stage 12 metrics | COVERED |
| NFR PDF < 1 MB | Stage 12 metrics | COVERED |
| NFR browser compat | Inline CSS only | COVERED |
| NFR mobile 360 px | CSS media queries | COVERED (planned) |
| NFR offline rendering | No external assets | COVERED |
| NFR accessibility WCAG AA | High-contrast colors + alt text on icons | COVERED (planned) |

---

## Open Questions

| ID | Question | Default applied |
|---|---|---|
| Q-F6-01 | PDF fails but HTML works → deliver HTML via link, notify user | Assumed |
| Q-F6-02 | Show classification confidence to user | **No** (less confusion) |
| Q-F6-03 | White-labeling | **No at MVP** |
| Q-F6-04 | Lawyer block LLM vs deterministic | **LLM with fallback** |
| Q-F6-05 | "What comes next" section | **No at MVP** |
| Q-F6-06 | Sign PDF cryptographically | **No at MVP** |
| Q-F6-07 | Interactive charts | **No, plain SVG** |
| Q-F6-08 | JSON export | **No** |

---

## Edge Cases

- Override active but band already red → render the override box prominently; user sees both.
- All categories have only unverifiable criteria → score 4ish; band red; the report shows the unverifiable count prominently.
- Very long executive_summary (4+ sentences from a permissive LLM) → truncate to 3 sentences at render.
- LLM returns a lawyer block with 7 items → trim to 5.
- Project has only 1 analysis (this one) → omit the "N analyses, avg X.X" line.

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-F6-01 | WeasyPrint OS dep missing | Dockerfile asserts; smoke test in CI |
| R-F6-02 | Template drift breaks old analyses | Versioned templates; CI golden tests per version |
| R-F6-03 | LLM lawyer block returns harmful advice | Fallback + LLM prompt explicitly forbids legal counsel |
| R-F6-04 | Hash mismatch (different floats render differently) | Hash from canonical JSON of context, not from HTML bytes |

---

## Cross-Validation Log

| Iteration | Discrepancies | Files |
|---|---|---|
| 1 | 0 | — |
| 2 | 0 | — |
| 3 | 0 | — |
| 4 | 0 | Acceptance |

## PRD Alignment Log

| Iteration | Items Checked | Misalignments | Coverage % |
|---|---|---|---|
| 1 | 34 | 0 | 100% |

**End of document.**
