# Casa Segura — AI & contributor playbook

Instructions here apply to **Claude**, **Cursor**, and anyone merging roadmap-related work—keep behavior consistent across tools.

## Roadmap authority

| Layer | Role |
|---|---|
| **`docs/Roadmap/tickets/CS-*.md`** | **Source of truth** for scope, `depends_on`, acceptance criteria, and ticket **`status`**. |
| **`docs/Roadmap/EPIC-*.md`** | Summary + **Definition of done**; must reflect shipped reality. |
| **`docs/Roadmap/phases/`**, **`PARALLEL_WORK_PLAN.md`** | **Navigation / pickup only** — not authoritative for status. |

## When work meets a ticket’s acceptance criteria

1. Edit that **`docs/Roadmap/tickets/CS-*.md`** file: **`status` → `done`** (or repo-standard terminal state) only if **every** AC is met **and** verified.
2. Set acceptance checklist items to **`[x]`** for what you verified.
3. If verification is incomplete, leave ticket **`status`** intermediate (`backlog`, `ready`, etc.) — do not silently mark **`done`**.
4. If the ticket **`epic:`** field points at an epic (e.g. `EPIC-10`), update the owning **`docs/Roadmap/EPIC-<nn>-*.md`** in **the same change** where practical:

   - Tick **Definition of done** bullets with **`[x]`** only when implemented and verified.
   - Adjust epic **`status`** when the checklist truly reflects epic completion.
   - Tighten or remove **stub / “thin until…”** wording once the epic has real shipped surface.

5. Phase / plan docs: bump **`last_updated`** and adjust “Ready picks” lists when pickups change (**`phase-roadmap-hygiene`** norms).

Detailed split for automation:

- Epic checklist rules: **`.cursor/rules/epic-status-hygiene.mdc`**
- Ticket rules: **`.cursor/rules/ticket-status-hygiene.mdc`**
- Phase pickup sync: **`.cursor/rules/phase-roadmap-hygiene.mdc`**
- Parallel lanes (`FE WORK`, paths): **`.cursor/rules/parallel-roadmap-work.mdc`**

If you change process, update **both** this file and those rules so Cursor and Claude stay aligned.

## Codebase lanes

- **Backend:** Django / DRF-first under **`backend/`** (canonical).
- **Frontend:** Next.js App Router under **`frontend/`** (canonical — not legacy `apps/web` unless README says otherwise).

## Product / privacy

Treat OCR payloads, delivery targets (email/WhatsApp), report text, prompts, logs, and error bodies as **sensitive**. Do not log PII/raw files in frontend server actions beyond what APIs require.
