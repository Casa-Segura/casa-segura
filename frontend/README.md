This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the landing route by modifying [`src/app/page.tsx`](src/app/page.tsx). Public legal copy lives at [`src/app/privacy/page.tsx`](src/app/privacy/page.tsx). The page auto-updates as you edit the file.

Format: `npm run format` (writes) or `npm run format:check` (CI-style).

This project uses [`next/font`](https://nextjs.org/docs/app/basic-features/fonts) to load display fonts (**Geist Sans** surfaces as `--font-geist`; **Inter** and **Newsreader** stay wired for serif/display tokens).

**UI kit:** Casa-specific composed components live in [`src/components/casa-ui/`](src/components/casa-ui/). [shadcn/ui](https://ui.shadcn.com/) is initialized at [`components.json`](components.json) with primitives under [`src/components/ui/`](src/components/ui/); Casa semantic colors (`bg-bg`, `text-text-primary`) remain the default in `globals.css`. Add shadcn pieces with `npx shadcn@latest add …` when a stock primitive fits the roadmap.

## BVA — landing (CS-290)

Manual or automated checks should cover boundary cases from the ticket:

| Input             | Boundary                 | Expected                                                                                           |
| ----------------- | ------------------------ | -------------------------------------------------------------------------------------------------- |
| Viewport width    | **360px**                | No horizontal scroll; headline, CTA, footer disclaimer visible; primary CTA height **≥44px**       |
| Viewport width    | **768px+**               | Stays single-column until a future breakpoint ticket adds a desktop grid                           |
| CTA target        | `/subir`                 | Upload + analysis route                                                                            |
| Public `/privacy` | 200, Spanish copy        | Privacy policy for crawlers (e.g. Meta) + footer link from `/`                                     |
| Skip link         | Tab from top of document | Reaches `#main-content` on each route’s `<main>`                                                   |
| Copy              | Spanish **tú**           | No mixed-language UI; no implication that billboard/project verification is required before upload |
| Contrast          | Body vs background       | WCAG **AA** spot-check (e.g. Lighthouse or axe) on primary text                                    |

Future work: add Playwright (or similar) viewport matrix and optional axe CI step.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Vercel deployment (CS-298)

Goal: **`main`** → Production, Pull Requests → Preview. Never put API secrets in `NEXT_PUBLIC_*` variables (server-only for `CASASEGURA_*`).

### Required environment variables (Vercel)

| Variable                  | Production                             | Preview                                                                                                     |
| ------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `CASASEGURA_API_BASE_URL` | Django/DRF base URL, no trailing slash | Point at staging or a dedicated Preview backend (**never** unintended prod bleed without explicit approval) |

`next.config.ts` aborts **`next build`** on Vercel when `VERCEL=1` and `CASASEGURA_API_BASE_URL` is unset, so Preview/Production cannot silently ship without a backend target.

Additional optional toggles mirror [`frontend/src/server/contract-env.ts`](src/server/contract-env.ts) (poll timeouts, path templates).

### Optional project verification (CS-356 / EPIC-12)

| Variable                             | When set                                | Behavior                                                                                                                                                                            |
| ------------------------------------ | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PROJECT_VERIFICATION_ENABLED`       | `true` / `1` / `yes` (case-insensitive) | Enables server-side checks in PV server actions (paired with Django). **Browser:** `/verificacion-proyecto` **always redirects to `/`** — no public hub or footer link.             |
| `PROJECT_VERIFICATION_TELEMETRY_LOG` | `true` / `1` / `yes` (case-insensitive) | Server-only: writes **JSON lines** to stdout for optional PV events (manual form handoff, optional contract CTA impression). **No** OCR text, addresses, filenames, or form bodies. |

**Default:** `PROJECT_VERIFICATION_ENABLED` unset → off in helpers used by legacy server actions. There is **no** user-visible billboard flow in production builds; bookmarks to `/verificacion-proyecto` resolve to the landing page.

**Manual form + stubs (operators):** When `CASASEGURA_API_BASE_URL` is configured and the gate is on, `POST /api/v1/project-verification/manual/` is called from the server action; when the base URL is missing, the action returns a deterministic configuration message instead of calling upstream.

**Segment layout:** [`src/app/verificacion-proyecto/layout.tsx`](src/app/verificacion-proyecto/layout.tsx) uses `redirect("/")` with `dynamic = "force-dynamic"` so behaviour is evaluated per request.

**Backend (optional):** Django mirrors `PROJECT_VERIFICATION_ENABLED` (`backend/.env`). JSON API under `POST/GET /api/v1/project-verification/...` — see [`backend/.env.example`](../../backend/.env.example) and ticket **CS-356**.

### Placeholder `CASASEGURA_API_BASE_URL` (backend not deployed yet)

Use this when Django is not live but you still want Vercel Preview/Production builds to pass.

**Canonical placeholder:** `https://api.backend-pending.invalid`

- **Why this shape:** The [`.invalid`](https://datatracker.ietf.org/doc/html/rfc2606#section-2) suffix is reserved; the hostname must not resolve in the public DNS hierarchy, so you avoid pointing “accidental” traffic at a real org or hitting someone else’s API.
- **HTTPS, no trailing slash:** Matches how you will configure the real API later (`readContractApiBase` strips trailing slashes anyway).
- **Must pair with upload off:** Set **`CASASEGURA_UPLOAD_ENABLED=false`**. The server action returns before any upstream `fetch`, so this URL is never contacted in that mode—only the build gate reads the variable.
- **Do not reuse a real host** (staging/production URLs) as a placeholder. If upload is ever enabled by mistake, you could leak traffic or spam logs toward the wrong environment.
- **When the API is ready:** Replace the placeholder with the real base URL on Preview and Production (and any branch-specific env), then set **`CASASEGURA_UPLOAD_ENABLED=true`** only when upload should actually call Django.

Preview and Production may use the **same** placeholder while upload is disabled; use distinct real URLs later if Preview should hit staging instead of production.

### Without a live backend yet (checklist)

1. Set **`CASASEGURA_API_BASE_URL`** to the canonical placeholder above (or another `.invalid` URL your team agrees on—document that choice in the PR/deploy notes).
2. Set **`CASASEGURA_UPLOAD_ENABLED=false`** so `/subir` short-circuits with the deterministic Spanish message instead of opaque upstream failures.

Replace both when Django is reachable and upload should flow end-to-end.

### Phase 1 upload contract (Django)

Defaults target **`POST /api/v1/submissions/`** and **`GET /api/v1/submissions/{{id}}/`** (see `.env.example`). The serializer expects multipart field **`file`** (singular) and **`disclaimer_accepted`** (required per CS-058). The web UI currently appends multiple **`files`** — multi-file ingestion on the API is still future work; until then treat upload E2E as blocked unless you post a single `file` or add an adapter.

### Verification after deploy

- `curl -sI "https://<deployment-host>/"` → **200**, `content-type` includes `text/html`.
- Responses should include headers `X-Content-Type-Options: nosniff` and `Referrer-Policy` (verified with the same curl).

### Crawling policy

`/robots.txt` emits **disallow `/`** when `VERCEL_ENV=preview` or `DISALLOW_ROBOTS=true`/`1`. Production allows all bots unless those overrides are set (product decision documented per CS-298).

### Rollback (runbook snippet)

In Vercel → Project → Deployments → select the previous **Ready** deployment → **⋯** → **Promote to Production** (or **Redeploy** the known-good commit).

See also [Next.js deployment docs](https://nextjs.org/docs/app/building-your-application/deploying).
