# Casa Segura — AI & contributor playbook

Instructions here apply to **Claude**, **Cursor**, and anyone merging roadmap-related work—keep behavior consistent across tools.

## Roadmap authority

| Layer                                                   | Role                                                                                       |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **`docs/Roadmap/tickets/CS-*.md`**                      | **Source of truth** for scope, `depends_on`, acceptance criteria, and ticket **`status`**. |
| **`docs/Roadmap/EPIC-*.md`**                            | Summary + **Definition of done**; must reflect shipped reality.                            |
| **`docs/Roadmap/phases/`**, **`PARALLEL_WORK_PLAN.md`** | **Navigation / pickup only** — not authoritative for status.                               |

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

## Canonical repository URL

Public source of truth: **[github.com/Casa-Segura/casa-segura](https://github.com/Casa-Segura/casa-segura)** — readable and cloneable without authentication.

## Commit signing policy

**Decision (CS-001):** Cryptographic commit signing (SSH or OpenPGP) is **recommended for maintainers and anyone merging to `main`**, and **optional for all other contributors**. Merge eligibility does **not** depend on verified signatures unless CI is changed later to require them. This project does **not** require DCO `Signed-off-by` lines unless we adopt that in a separate decision.

**Why optional:** Keeps contribution friction low while still allowing stronger attribution when people opt in.

**How to sign:** Follow GitHub’s guide [Managing commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification) (SSH signing or GPG). After setup, enable signing by default, for example:

```bash
# SSH signing (after configuring a signing key in GitHub settings)
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub   # or your signing public key path
git config --global commit.gpgsign true
```

Use `git log --show-signature -1` locally to confirm a commit verifies.

## Codebase lanes

- **Backend:** Django / DRF-first under **`backend/`** (canonical).
- **Frontend:** Next.js App Router under **`frontend/`** (canonical — not legacy `apps/web` unless README says otherwise).

## Product / privacy

Treat OCR payloads, delivery targets (SMS/email/link), report text, prompts, logs, and error bodies as **sensitive**. Do not log PII/raw files in frontend server actions beyond what APIs require.
