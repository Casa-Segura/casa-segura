---
law_id: pendiente-asamblea-d491c5c6
title: Pendiente — Decreto Asamblea Legislativa (UUID D491C5C6)
short_title: Pendiente
estado: pendiente_de_descarga
source_url: https://www.asamblea.gob.sv/sites/default/files/documents/decretos/D491C5C6-3C26-4D3D-B9A7-CC394CEE2D69.pdf
last_verified: 2026-05-09
relevance_to_casa_segura: unknown_until_fetched
---

# Pendiente: Decreto en asamblea.gob.sv (UUID D491C5C6)

> ⚠️ This file is a **stub**. The source PDF could not be fetched at the time this corpus was assembled because the Anthropic web fetcher could not validate `asamblea.gob.sv`'s SSL certificate / robots.txt at the moment. The decree must be retrieved manually and the file expanded.

## Source URL

https://www.asamblea.gob.sv/sites/default/files/documents/decretos/D491C5C6-3C26-4D3D-B9A7-CC394CEE2D69.pdf

## How to retrieve

1. Visit the URL in a normal browser (the SSL cert is valid for browsers — only the automated fetcher had trouble).
2. Save the PDF to `/raw/D491C5C6.pdf`.
3. Run text extraction (`pdftotext` or `pypdf`).
4. Identify the decreto number, fecha, and title.
5. Restructure into the same template as the other law files (frontmatter, summary, key articles, application to Casa Segura, citation format).

## Likely candidates (best guesses based on the project context)

Given that the user's surrounding URLs are housing-related (Inquilinato, IVU, FSV, Public Procurement, Arrendamiento Financiero), this decreto is likely one of:

- **Ley Especial para la Regularización de Lotificaciones y Parcelaciones para Uso Habitacional** (D.L. 805 of 26 July 2023, D.O. 158, T.440, 28-08-2023, with reforms in D.L. 70 of 13-08-2024 and D.L. 808 of 28-08-2023)
- **Ley para la Creación de la Dirección Nacional de Compras Públicas (DINAC)** — companion decree to the Public Procurement Law
- **Ley de Compras Públicas** itself (D.L. 868 of 25-01-2023)
- **Reformas a la Ley del FSV** (D.L. 595 of 19-03-2020 or D.L. 46 of 03-06-2021)
- **Ley Especial de Lotificaciones y Parcelaciones para Uso Habitacional** (D.L. 993 of 25-01-2012)

## Why it matters for Casa Segura

If this decreto is the **Lotificaciones Law**, it is highly relevant — it governs the regularization of land subdivisions for housing, which is one of the most common contexts for fraud in El Salvador (selling lots that are not properly inscribed, that are still in regularization process, or whose developers haven't met technical requirements).

In that case, the corresponding Casa Segura findings would include:

- `lotificacion_no_inscrita` (the lot is not inscribed in favor of the lote-habiente)
- `desarrollador_parcelario_no_continúa_proceso` (the developer is not continuing the regularization process — violation of art. 5 of D.L. 808)
- `lotificacion_anterior_a_septiembre_2012` (the development is the type subject to regularization — it can be regularized but with constraints)

When the file is filled in, the `relevance_to_casa_segura` should be updated, the `covers` list completed, and a `coverage_map` entry added to `README.md`.

## Citation format for findings (placeholder)

```json
{
  "law_id": "TBD",
  "article": "TBD",
  "anchor": "TBD",
  "url": "/laws/06-pendiente-asamblea-d491c5c6.md",
  "official_source": "TBD"
}
```
