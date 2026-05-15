# Casa Segura — Legal Corpus

> Curated collection of Salvadoran laws relevant to housing, real estate fraud, and contract verification. Each file is structured for RAG ingestion: metadata header, plain-language summary, key articles with stable anchors, and explicit mapping to Casa Segura findings.

## Scope

This corpus is the legal grounding layer for the Casa Segura verdict engine. The product currently outputs `green | yellow | red` with short findings; the corpus turns each finding into a citation against a specific article of a specific law, so users see *why* something is risky in legal terms, not just *that* it is.

Salvadoran laws and decrees are public-domain government works and can be reproduced and redistributed. This collection is structured for two consumers:

1. **The Casa Segura LLM verdict engine** — retrieves articles by topic to ground findings.
2. **The user reading the result screen** — sees a one-line citation with a "leer la ley" expandable.

## Files

| # | File | Title | Decreto | Year | Status |
|---|---|---|---|---|---|
| 1 | `laws/01-ley-inquilinato.md` | Ley de Inquilinato | D.L. 2591 | 1958 (last reform 2008) | Vigente |
| 2 | `laws/02-ley-ivu.md` | Ley sobre Contratos del Instituto de Vivienda Urbana | D.L. 1486 | 1954 | Vigente con reformas |
| 3 | `laws/03-ley-fsv.md` | Ley del Fondo Social para la Vivienda | D.L. 328 | 1973 (last reform 2021) | Vigente |
| 4 | `laws/04-ley-compras-publicas.md` | Ley de Compras Públicas (LCP) | D.L. 868 | 2023 | Vigente — summary only |
| 5 | `laws/05-ley-arrendamiento-financiero.md` | Ley de Arrendamiento Financiero | D.L. 884 | 2002 | Vigente |
| 6 | `laws/06-pendiente-asamblea-d491c5c6.md` | (pendiente — fuente bloqueada) | — | — | Stub |
| 7 | `laws/07-ley-urbanismo-construccion.md` | Ley de Urbanismo y Construcción | D.L. 232 | 1951 (last reform 2021) | Vigente |

## Coverage map (which laws ground which Casa Segura finding categories)

### Flow 1 findings — project legitimacy (billboard photo)

| Finding category | Primary law | Secondary law |
|---|---|---|
| Project must have a visible, valid permit | Ley de Urbanismo y Construcción art. 1, 2, 5 | — |
| Permit must be from recognized authority (Ministerio de Vivienda or municipality) | Ley de Urbanismo y Construcción art. 1 | — |
| Permit format invalid for stated authority | Ley de Urbanismo y Construcción art. 1 | — |
| Permit > 1 year old, no work history | Ley de Urbanismo y Construcción art. 6 | — |
| Pre-1951 approval cited | Ley de Urbanismo y Construcción art. 7 | — |
| Developer / responsible architect not in Registro Nacional | Ley de Urbanismo y Construcción art. 4, 8 | — |
| Industrial project without Previsión Social clearance | Ley de Urbanismo y Construcción art. 8 final | — |
| Parcelación lot count incompatible with park reservation | Ley de Urbanismo y Construcción art. 2(e) | — |
| Government-project claim — verify RUPES/COMPRASAL | Ley de Compras Públicas | — |
| Property under Bien de Familia regime — transfer attempt is null | Ley IVU art. 3 | — |
| FSV anotación preventiva on the property | Ley FSV art. 55, 56 | — |

### Flow 2 findings — contract risk (PDF)

| Finding category | Primary law | Secondary law |
|---|---|---|
| Contract must be in writing | Ley de Inquilinato art. 4, 18 | Código Civil |
| Required clauses (parties, property ID, price) | Ley de Inquilinato art. 4, 18 | — |
| Receipt obligation by landlord/seller | Ley de Inquilinato art. 9, 20 | — |
| Tenant rights are non-waivable | Ley de Inquilinato art. 2 | — |
| Causes for terminating arrendamiento | Ley de Inquilinato art. 24, 25 | — |
| Government-financed housing contract rules | Ley IVU art. 2, 4, 5 | Ley FSV art. 7 |
| Bien de Familia regime restrictions in contract | Ley IVU art. 3, 6, 14 | — |
| FSV-financed purchase exemptions and rules | Ley FSV art. 7, 55, 68 | Ley IVU |
| Distinction: leasing vs sale (option to purchase) | Ley de Arrendamiento Financiero art. 2, 7 | — |
| Leasing contract must be written and registered in Registro de Comercio | Ley de Arrendamiento Financiero art. 7 | — |
| Civil rental disguised as financial leasing | Ley de Arrendamiento Financiero art. 1 | Ley de Inquilinato |
| Cross-flow: contract describes a property without a valid permit (Flow 1 → Flow 2) | Ley de Urbanismo y Construcción art. 1, 2 | — |

## How the verdict engine consumes this corpus

Each `.md` file follows the same anchor convention: `#art-<n>` for articles. The retrieval layer (see `ARCHITECTURE-LEGAL-LAYER.md`) embeds each `## Article N` chunk separately and matches incoming finding text to the top-k articles.

A finding referenced from this corpus has the shape:

```json
{
  "severity": "yellow",
  "title": "Sin mecanismo de fideicomiso",
  "explanation": "...",
  "evidence": "Cláusula 4 del contrato",
  "legal_basis": [
    {
      "law_id": "ley-inquilinato",
      "law_title": "Ley de Inquilinato",
      "article": "Art. 4",
      "article_url": "https://repo/laws/01-ley-inquilinato.md#art-4",
      "quote_es": "Todo contrato de arrendamiento... deberá constar por escrito..."
    }
  ]
}
```

## Disclaimer

This is a curated reference, not legal advice. Articles are paraphrased and summarized for an application context. For litigation or formal advice, consult the original Diario Oficial publications (linked in each file) and a licensed Salvadoran abogado.

## Contribution

Errors, missing reforms, or new laws relevant to housing fraud: open a PR. Each file's frontmatter has a `last_verified` field — update it if you check against the current Diario Oficial.
