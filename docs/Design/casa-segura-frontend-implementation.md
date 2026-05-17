# Casa Segura Frontend Design Implementation

Source design: `docs/Design/casa-segura.pen`, inspected with Pencil MCP.

This document translates the current Pencil design into frontend implementation rules for the Next.js app. It is the handoff between the design canvas and the mobile-first contract analysis UI.

## Product Shape

Casa Segura should feel like a trustworthy legal analysis tool, not a generic upload form. The primary experience is still mobile-first, but desktop must graduate into a workbench: document on the left, live analysis and actions on the right.

## Core Tokens

| Token | Value | Use |
|---|---:|---|
| `bg` | `#FAF7F2` | App background |
| `surface` | `#FFFFFF` | Cards, panels, sheets |
| `surface-muted` | `#F4F1EC` | Desktop workbench background |
| `surface-subtle` | `#FAFAF9` | Toolbars and low-emphasis panels |
| `document-bg` | `#ECEAE6` | Document viewer canvas |
| `accent` | `#0F766E` | Primary CTA, active states, brand mark |
| `accent-light` | `#E6F2F1` | Selected states, positive neutral badges |
| `text-primary` | `#1F1A14` | Main copy |
| `text-secondary` | `#6B6258` | Supporting copy |
| `border` | `#E7E2D9` | Dividers, panel outlines |
| `border-strong` | `#D1CBC2` | Active toolbars, dashed upload borders |
| `verdict-green` | `#15803D` | Completed/pass states |
| `verdict-green-bg` | `#ECFDF5` | Pass backgrounds |
| `verdict-yellow` | `#CA8A04` | Review/in-progress/risk states |
| `verdict-yellow-bg` | `#FEFCE8` | Review backgrounds |
| `verdict-red` | `#B91C1C` | Failed/high-risk states |
| `verdict-red-bg` | `#FEF2F2` | Failed/high-risk backgrounds |

Keep a single accent color. Avoid purple/blue AI styling, neon glows, and pure black except inside media/document previews where the design uses dark chrome.

## Radius, Spacing, Type

- Primary radii: `8px` inputs/buttons, `12px` cards, `16px` prominent panels, `24px` hero cards, `999px` pills.
- Common spacing: `4`, `6`, `8`, `12`, `16`, `20`, `24`, `32`, `40`, `56`, `80`.
- Body font: `Inter`, already used in the frontend.
- Display option: `Newsreader` appears in the latest desktop landing treatment. Use it only for editorial landing moments, never dense dashboard/workbench UI.
- Body copy should remain at least `16px` on mobile. Small labels can use `12px` to `14px`.

## Reusable Components From Design

- `Button/Primary`: filled teal, `48px` high, `8px` radius, white label.
- `Button/Secondary`: white surface, teal border and label.
- `Button/Link`: text action with `44px` touch target.
- `Step Indicator`: pill using `accent-light` background and teal text.
- `Upload Zone`: dashed/outlined surface with camera/file icon and stacked actions.
- `Finding Card`: compact row with verdict dot, title, explanation.
- `Disclaimer`: muted legal callout with info icon.
- `Legal Citation`: teal-tinted legal quote and external link.
- `Legal Summary`: expandable legal basis panel.

## Mobile Contract Flow

Mobile uses a compact, single-column sequence:

1. Contract upload with helper copy and explicit format limits.
2. Legal disclaimer gate before files are submitted.
3. Delivery channel cards: SMS summary, email PDF, or web link.
4. Channel-specific field screen for email or phone.
5. Loading/progress screen with step list and progress bar.
6. Contract result with summary, legal basis, findings, download/share actions.
7. Sent confirmation with reference ID and delivery details.
8. Error states: not analyzable, expired link, failed delivery, retry path.

Primary actions must stay full-width on mobile, use at least `44px` height, and include pressed feedback.

## Desktop Workbench

Desktop at `lg` and wider should not stretch the mobile card. It should become a side-panel workspace:

- Top nav: brand mark, filename/breadcrumb, status pill, contextual actions.
- Left pane: document preview, OCR text highlights, areas of interest, viewer toolbar.
- Right pane: live analysis stream while processing; final score, findings, legal summary, and delivery actions when complete.
- Completed state: visible score, counts by verdict, findings list, download/share actions.
- Loading states: OCR extraction, criteria analysis, report generation, delivery confirmation.

The workbench shell maps directly to the Pencil `ocr`, `rag`, and `done` screens.

## Motion And Interaction

- Use transform and opacity only. Avoid `transition-all`.
- Respect `prefers-reduced-motion`; shimmer and staged animations should pause or simplify.
- Use tactile button feedback (`translate-y-px` or slight scale) without causing layout shift.
- Skeletons should match real layout: document lines, side-panel finding rows, progress timeline rows.
- Long server actions should show a deterministic progress timeline instead of a spinner-only overlay.
- Desktop document highlights should fade/slide in and pulse subtly while analysis is active.

## Accessibility Requirements

- One `main#main-content` per page and preserve the root skip link.
- Buttons for actions, links for navigation.
- Icon-only controls need `aria-label`; decorative icons need `aria-hidden`.
- Progress and result updates need `aria-live`.
- All form fields need visible labels, helper text, inline errors, and correct `type`/`autocomplete`.
- Keep touch targets at least `44px`.
- Keyboard users must be able to reach upload, delivery cards, actions, report controls, and retry paths.

## Implementation Priority

1. Theme tokens and primitive components.
2. Mobile upload and delivery flow parity.
3. Loading/progress state with skeletons.
4. Desktop workbench shell for `/subir` and `/r/[publicShortId]`.
5. Final polish: motion, reduced-motion pass, keyboard/focus verification, responsive checks.
