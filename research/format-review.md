# Step 1 — How content is stored and shown today, and what changes

*(Content Program, Process step 1. Written 2026-11-06.)*

## What exists
| Content | Stored | Shown | Depth today |
|---|---|---|---|
| Generic trouble codes (57) | `dtcs` table, seeded from `backend/app/seed/data/dtcs.json` | `/codes/:code` | One page per code for all vehicles: plain lists of symptoms, causes, steps. No engine, no specs, no ranking, no sources per claim. |
| Guides & specs (community + team) | `entries` + full-snapshot `entry_revisions`; per-kind JSON validated in `community/kinds.py` (procedure, torque_spec, fluid_capacity, spec, part_note, labor_time) | Vehicle page tabs, entry page, history, search | Tagged by vehicle fitment (make/model/years/engine), system, DTC. Revisions, restore, "verified by a pro" tied to a revision, votes, "report wrong info", moderation queue, safety banner on safety-critical items. |
| Owner's-manual facts (~400) | `backend/app/seed/data/manual_specs/*.json` → entries by "ChrystalClear Team" | Quick Specs, Specs tab | Facts with manual page citations. |
| Recalls, complaints, TSB index | NHTSA tables | Vehicle page tabs | Public data, linked by make/model/year. |

## What the program needs that today's format can't hold
1. **Engine-specific DTC pages.** The `dtcs` row is one generic page per code. The program wants
   causes *ranked for that engine*, pattern failures, enable criteria, test steps with spec values
   and connector/pin info, good-vs-bad readings, related TSBs/recalls, misdiagnoses, repair time and
   parts cost, and a sources list. → **New entry kind `dtc_guide`**, tagged to the code and to the
   vehicles/engines it covers with the shared fitment matcher. The generic code page keeps its short
   definition and lists the engine-specific guides that match the code (and the user's vehicle).
   Using `entries` gives us revisions, change history, "last revised", reports and review for free.
2. **Deeper procedures.** `procedure` lacks special tools, fluids with spec+capacity, "known
   gotchas", and per-step specs other than torque. → Extend `procedure` with `special_tools`,
   `fluids`, `gotchas`, per-step `spec` values and `sequence` text; keep existing data valid.
3. **Per-claim sources and UNVERIFIED marks.** Sources today are one list per entry. → Each numeric
   value can carry `source_refs` (indexes into the page's sources) and `unverified: true`; pages with
   any UNVERIFIED value show a visible banner and are counted in `research/review-log.md`.
4. **Sign-off tracking.** Today: author + optional "verified by a pro" on a revision. → Add a
   **review record** per revision: written by, reviewed by (reviewer agent per owner decision
   2026-11-06), date, checklist result, UNVERIFIED count. Team content is published only after that
   review; the page shows "Fact-checked by the ChrystalClear reviewer on <date>".
5. **Disclaimer and safety first.** Safety banners exist for safety-critical items only. → Every
   guide gets "Work at your own risk" plus its safety warnings at the top, before step 1.
6. **Report a mistake.** "Report wrong info" exists. → Add *which section* the report is about, email
   the owner, and show "Under review" on the page while a spec report is open.
7. **Where authored content lives.** Program: under `/content/` with its own LICENSE. → Team-written
   guides are files in `content/` (one JSON file per page, same shape as the entry kinds), loaded
   into `entries` by the seed like the owner's-manual files. Research notes stay in `research/`.

## Decisions recorded (owner, 2026-11-06)
- Repair content proprietary (all rights reserved, free to read): `content/LICENSE`.
- Paid/owner lookups as written in the program: `research/owner-lookups.md`, `research/owner-notes/`.
- Reviewer agent signs off instead of a mechanic.

## Flag for the owner
**The GitHub repository is public.** Anything in `content/` and `research/` — including notes and
screenshots from paid services in `research/owner-notes/` — can be read and copied by anyone. The
program says to flag this: decide whether to move `content/` and `research/` into a private repo.
