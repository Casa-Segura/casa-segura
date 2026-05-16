---
id: EPIC-10
name: Frontend Web App
phase: cross
status: in_progress
depends_on:
  - EPIC-00
  - EPIC-08
prd_refs:
  - PRD_GENERAL US-01, US-04, US-05
  - UI-UX
feature: cross-cutting
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-10
---

# EPIC-10 — Frontend Web App

Next.js App Router surface in `frontend/` (canonical). Mobile-first at **360px**, Spanish **tú**. Disclosure copy for BR-07 is centralized via [[CS-297]] (`frontend/src/legal/disclaimer.ts`).

## Goal

Public-facing surface for contract submission and report viewing on web. Spanish, "tú" register.

## Definition of done

- [x] Landing page with one-sentence value proposition and clear CTA
- [x] Upload page with disclaimer gate, channel selector (email / WhatsApp / link), drag-drop + file picker
- [x] Loading state with rotating Spanish copy
- [x] Result page (when channel = link) embeds the HTML report
- [x] Expired-link friendly page ([[CS-295]] — PRD_US-05 copy + `noindex`; `/enlace-expirado` + documented 404/410 handling on `/r/...`)
- [ ] Deployed to Vercel
- [ ] QA passed on a real Android device

## Tickets

- [[CS-290]] — Landing page — **done**
- [[CS-291]] — Upload page with disclaimer gate — **done**
- [[CS-292]] — Channel selector component — **done**
- [[CS-293]] — Loading state with rotating copy — **done**
- [[CS-294]] — Result page (HTML report viewer) — **done**
- [[CS-295]] — Expired-link page — **done**
- [[CS-296]] — Server actions to call BE — **done**
- [[CS-297]] — Disclaimer module (single source for "Esto no es asesoría legal") — **done**
- [[CS-298]] — Vercel deploy — **ready** (repo wiring landed; operational AC pending first Vercel project)
- [[CS-299]] — Mobile QA pass at 360px — **ready** (checklist: `frontend/docs/CS-299-mobile-qa-checklist.md`)

## Notes

- [[UI-UX]] is the design reference
- HTML report URL/path and poll payloads may still be refined against OpenAPI from [[EPIC-08-multichannel-delivery]]; env templates document the current FE contract
