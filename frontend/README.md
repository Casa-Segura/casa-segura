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

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to load **Inter** (design token `font-body` from `docs/Design/casa-segura.pen`).

## BVA — landing (CS-290)

Manual or automated checks should cover boundary cases from the ticket:

| Input | Boundary | Expected |
|-------|-----------|----------|
| Viewport width | **360px** | No horizontal scroll; headline, CTA, footer disclaimer visible; primary CTA height **≥44px** |
| Viewport width | **768px+** | Stays single-column until a future breakpoint ticket adds a desktop grid |
| CTA target | `/subir` | Placeholder upload route (CS-291 replaces content) |
| Copy | Spanish **tú** | No mixed-language UI; no implication that billboard/project verification is required before upload |
| Contrast | Body vs background | WCAG **AA** spot-check (e.g. Lighthouse or axe) on primary text |

Future work: add Playwright (or similar) viewport matrix and optional axe CI step.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Vercel deployment (CS-298)

Goal: **`main`** → Production, Pull Requests → Preview. Never put API secrets in `NEXT_PUBLIC_*` variables (server-only for `CASASEGURA_*`).

### Required environment variables (Vercel)

| Variable | Production | Preview |
|----------|-------------|---------|
| `CASASEGURA_API_BASE_URL` | Django/DRF base URL, no trailing slash | Point at staging or a dedicated Preview backend (**never** unintended prod bleed without explicit approval) |

`next.config.ts` aborts **`next build`** on Vercel when `VERCEL=1` and `CASASEGURA_API_BASE_URL` is unset, so Preview/Production cannot silently ship without a backend target.

Additional optional toggles mirror [`frontend/src/server/contract-env.ts`](src/server/contract-env.ts) (poll timeouts, path templates).

### Without a live backend yet

You can still ship the marketing shell (landing + gated `/subir` UX):

1. Set **`CASASEGURA_API_BASE_URL`** to a placeholder or future staging origin (must be non-empty — build gate).
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
