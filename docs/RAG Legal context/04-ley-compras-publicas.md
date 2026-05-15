---
law_id: ley-compras-publicas
title: Ley de Compras Públicas (LCP)
short_title: LCP
decreto: D.L. 868 (and companion decree creating DINAC)
fecha_emision: 2023-01-25
diario_oficial: Publicado 02-03-2023, vigente desde 10-03-2023
reformas_count: 0
ultima_reforma: null
estado: vigente
materia: Compras públicas / contratación administrativa
sources:
  - https://www.trade.gov/market-intelligence/el-salvador-new-public-procurement-law
  - https://imprentanacional.gob.sv/servicios/archivo-digital-del-diario-oficial/
last_verified: 2026-05-09
relevance_to_casa_segura: medium
covers:
  - government procurement and contracting (national and municipal)
  - DINAC, the new autonomous procurement regulator
  - COMPRASAL electronic procurement system
  - RUPES (Unique Registry of State Providers)
  - bidding methods and thresholds
note: |
  This file is a structured summary based on the U.S. ITA market intelligence
  article and the Asamblea Legislativa announcement. The full text was not
  directly accessible at retrieval time (asamblea.gob.sv blocked the fetch).
  When the full decree is downloaded, expand each section with article-level
  citations.
---

# Ley de Compras Públicas (LCP)

## Plain-language summary

The new Public Procurement Law (LCP) approved by the Legislative Assembly on 25 January 2023 and in force since 10 March 2023 regulates **all government procurement** by central agencies, autonomous entities, and municipalities using public funds. It replaces the Procurement and Contracting of the Public Administration Law (LACAP).

The LCP creates the **Dirección Nacional de Compras Públicas (DINAC)**, an autonomous regulator that owns government procurement policy and runs **COMPRASAL** (the electronic procurement system). All companies — national and foreign — that want to sell to the Salvadoran government must register in **RUPES** (Registro Único de Proveedores del Estado), with exceptions during national emergencies.

**Strategic projects and procurements done by the Dirección de Obras Municipales (DOM) are excluded** from the LCP.

The four procurement methods are: (a) Competitive Bidding, (b) Price Comparison, (c) Direct Purchasing, and (d) Low Amount. Threshold for competitive bidding: **$87,600**.

## Application to Casa Segura

This law matters when:
- A "developer" claims their project is part of a government program (Ministry of Vivienda, FSV, IVU, municipality)
- A buyer is being offered "preferential government pricing" or "DOM-discounted" properties
- A seller claims registration in RUPES as a credibility marker

Key fraud-detection angles:

1. **Phantom government contracts.** A seller claims a building is part of a government project. RUPES + COMPRASAL records can verify whether the developer is a registered, contracted state provider.
2. **DOM-exclusion misuse.** Some sellers exploit the fact that DOM strategic projects are excluded from LCP transparency to claim opacity is normal. Casa Segura can flag this pattern.
3. **State-of-Exception cover.** Direct purchases under the State of Exception (March 2022) are exempt from competitive bidding. A "developer" may abuse this to fabricate a fake government contract.

Findings the verdict engine should ground here:

- **`gov_project_claim_unverified`** → cross-check with COMPRASAL and RUPES databases
- **`developer_not_in_rupes`** → indicates the seller cannot legally contract with the State for projects above thresholds
- **`dom_exclusion_misuse`** → flag when a project claims DOM affiliation without verifiable basis

## Key provisions (summary level)

### Scope and replacement of LACAP
- Applies to: government agencies, autonomous entities, municipalities — when public funds are used.
- Replaces: Ley de Adquisiciones y Contrataciones de la Administración Pública (LACAP).
- Excluded: strategic projects and DOM-managed procurements.

### DINAC — Dirección Nacional de Compras Públicas
A new autonomous regulator created by a companion decree (Ley de Creación de la Dirección Nacional de Compras Públicas). Responsibilities:
- Setting government procurement policy and regulation
- Administering COMPRASAL
- Maintaining RUPES

### COMPRASAL — Electronic Procurement System
The mandatory electronic platform through which all government procurement runs (with emergency exceptions). All registered providers must transact via COMPRASAL.

### RUPES — Registro Único de Proveedores del Estado
Single registry of state providers. **All companies wanting to sell to the government must register** (national or foreign), except during national emergency or urgency as defined by law.

> **Casa Segura signal:** if a developer claims they "build for the government" but cannot show RUPES registration, that's a flag. Public RUPES records (when accessible via COMPRASAL) make this verifiable.

### Procurement methods
- **(a) Competitive Bidding** — threshold above $87,600
- **(b) Price Comparison** — under $87,600, requires quotes from at least 3 suppliers
- **(c) Direct Purchasing** — allowed during national emergency or urgency (e.g. State of Exception)
- **(d) Low Amount** — for small purchases

The law mandates **high technology use** and consideration of **sustainability and innovation criteria**.

### State of Exception interaction
Purchases tied to the State of Exception declared in March 2022 operate under the emergency exemptions noted above. A developer claiming State-of-Exception cover for a private real estate project should be a red flag — that exemption is for emergency procurement, not residential development.

## Practical fraud patterns to watch

| Pattern | Verification |
|---|---|
| Developer claims to be a "proveedor del Estado" — verify RUPES registration | RUPES (via DINAC/COMPRASAL) |
| Project claims to be a government social-housing project | Verify with Ministerio de Vivienda + FSV portal |
| "DOM-built" claim with no public records | DOM publishes its strategic projects |
| State-of-Exception bidding cited for residential housing sale | LCP State-of-Exception is for emergency procurement |
| Sale price "subsidized by competitive bidding under $87,600" | Threshold check |

## Cross-references

- **FSV-financed worker housing**: see `03-ley-fsv.md` (FSV is itself a public-law institution with its own regime).
- **IVU contracts**: see `02-ley-ivu.md` (institutional housing under different special law).
- **Real estate transfer tax**: Ley del Impuesto sobre Transferencia de Bienes Raíces.

## Pending: full article-level breakdown

When the complete LCP and DINAC decrees are downloaded from the Diario Oficial archive, expand this file with:
- Article-by-article scope, definitions
- Detailed procurement method articles (Title II)
- DINAC governance articles
- Sanctions and disqualification articles
- RUPES inscription rules

Suggested retrieval: https://imprentanacional.gob.sv/servicios/archivo-digital-del-diario-oficial/, search for D.O. 2 March 2023.

## Citation format for findings

```json
{
  "law_id": "ley-compras-publicas",
  "section": "RUPES registration",
  "url": "/laws/04-ley-compras-publicas.md#rupes--registro-unico-de-proveedores-del-estado",
  "official_source": "Ley de Compras Públicas, D.O. 02-03-2023, vigente 10-03-2023"
}
```
