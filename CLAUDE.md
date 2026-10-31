# CLAUDE.md — Project rules for ChrystalClear

Read this first in every session. It records the owner's decisions so work stays on track.
If a request conflicts with this file, ask the owner before proceeding.

## What this is
**ChrystalClear** — a free, open-source alternative to ALLDATA for auto repair information.

## Non-negotiables
1. **Business model: "free core, optional paid business extras later" (Option B).**
   - **Free forever, never paywalled:** all repair information — VIN decoding, vehicle data,
     recalls/TSBs/complaints, trouble codes, every community-written guide/spec/photo, search,
     My Garage, and every v0.1 feature. Safety information is never paywalled.
   - **May be paid later (not now):** optional business tools that cost money to run, e.g.
     shop management, multi-tech team accounts, bulk data/API access for other software.
     Also allowed: ads, sponsorships, donations, parts affiliate links, hardware sales.
   - Never charge for community-written content. The "verified pro" *user role* is a trust
     badge, not a paid tier.
   - Keep paid-capable features as separate modules so the free core never depends on them.
2. **Licenses.** Code: **AGPL-3.0**. Because it's a web app, the UI must always link to the
   source code (AGPL §13). Community content: **CC BY-SA 4.0**. All contributors (code and
   content) agree to the **Contributor License Agreement** (`CLA.md`) so the project owner
   keeps the right to relicense/commercialize; code contributions are checked by a CLA bot,
   content contributors accept it in the sign-up terms.
3. **Stay legal on content.** Matching or improving on the *features, workflows, navigation
   and layout ideas* of ALLDATA, Mitchell, Identifix, etc. is fair game. Never scrape, copy,
   or paraphrase-closely their text, images, diagrams or databases. Use only:
   - Public/open data: NHTSA vPIC, NHTSA recalls, complaints, TSB/manufacturer-communications index
   - Open OBD-II code lists **with a compatible license** (record source + license per row)
   - Open-source projects with AGPL-compatible licenses
   - Community contributions written in the contributor's own words (facts such as torque
     values and capacities are fine; copied manual text is not)
4. **Privacy & security.** Collect the minimum user data (email, password hash, display name,
   preferences). Never sell data. No third-party trackers. Hash passwords with Argon2id.
   Validate all input. Secrets only in environment variables — never committed.
5. **Safety.** Show a visible safety disclaimer on torque and other safety-critical specs.
   Hardware features (OBD-II/ELM327/J2534, key programming, ECU tuning) live in their own
   module, **disabled by default**, with clear warnings and an enforced confirmation step
   before anything writes to a vehicle.

## Stack
- PWA: installable on phones, works on laptops.
- Backend: **Python + FastAPI**, SQLAlchemy 2, Alembic migrations, Pydantic v2.
- Database: **Postgres** (production / Docker), **SQLite** (quick local dev).
- Search: database full-text search (Postgres FTS + pg_trgm; SQLite FTS5 in dev). No extra search server.
- Frontend: **React + Vite + Tailwind**, vite-plugin-pwa (Workbox), react-i18next.
- Setup: **Docker** (`docker compose up` is the one-command dev setup) with seed data.
- CI: GitHub Actions runs tests on every push.

## UI rules (shop use)
Mobile-first; fast; big tap targets (≥48px, primary actions ≥56px); high contrast;
dark mode; readable with greasy hands (18px+ body text, labeled icons, bottom nav).
Offline access to recently viewed vehicles and guides. Metric/imperial toggle
(store SI internally, convert at display). **All UI text goes through i18n keys** in
`frontend/src/i18n/locales/en/` so Spanish can be added later — no hard-coded strings.
Backend errors return stable error codes, not English sentences, for the same reason.

## v0.1 scope (build in this order)
1. VIN decoder (NHTSA vPIC) + manual year/make/model/engine; vehicle profile; My Garage.
2. Recalls, TSB index, complaints per vehicle from NHTSA, with refreshable import scripts.
3. DTC search: generic OBD-II codes — plain-English meaning, symptoms, causes, diagnostic steps, links to guides.
4. Community guides & specs: procedures, torque specs, fluid capacities, part notes, labor
   estimates, photos; tagged by vehicle, system, DTC; revision history; "verified by a pro"
   flag (reviewer role); voting; report-wrong-info; safety disclaimer.
5. Fast search across vehicles, codes, recalls, guides.
6. Accounts: email login; roles user / verified pro / moderator / admin; anti-spam + moderation tools.

## Later (design for, don't build)
OBD-II live data & code reading (ELM327, J2534), community-drawn wiring diagrams, key
programming, ECU tuning, parts price lookup. Each is a separate module under
`backend/app/modules/` + `frontend/src/features/`, toggled by env flags.

## Key design decisions (see docs/PLAN.md for full detail)
- Modular backend: `backend/app/modules/<name>/` each with routes, models, services, tests; registry with env feature flags.
- One unified community content model (`entries` + `entry_revisions` with per-kind validated JSON)
  so history, votes, reports, verification behave identically for guides and specs.
- Every edit stores a full revision snapshot (simple diff/revert).
- "Verified" is tied to a specific revision; later edits show "verified on an earlier version".
- New accounts start on probation: first few contributions go to a review queue.
- Vehicle = year + model + engine row; guides/specs apply via year ranges.
- VIN decodes cached in our DB to limit calls to NHTSA.
- Photos: EXIF/GPS stripped, re-encoded; local disk in dev, S3-compatible storage in prod.
- Auth: server-side sessions via HTTP-only cookie (not JWT in localStorage); CSRF protection.

## How to work
- Owner is a business owner, not a developer: explain decisions in plain English and say
  exactly what they need to do (approve, create an account, add a setting).
- Small, working commits with clear messages. Never commit secrets.
- Required tests: VIN decoder, DTC lookup, guide editing (also add auth/permissions tests).
- Keep `TODO.md` (next steps) and `CHANGELOG.md` (what's done) updated with every change.
- Hosting must stay free or very cheap — see `docs/HOSTING.md`.
- Develop on the designated feature branch; don't open PRs unless the owner asks.

## Decision log
- 2026-10-31: Owner approved docs/PLAN.md.
- 2026-10-31: Business model = Option B (free core forever; optional paid business extras later) + CLA.
- 2026-10-31: Community content license = CC BY-SA 4.0.
- 2026-10-31: Renamed from "OpenRepair" to **ChrystalClear** (owner's spelling — keep the "h").
  Reason: "Open Repair" is already used by the Open Repair Alliance (openrepair.org), a repair-data
  group. Owner's fallback names AnyData/AlphaData/OmegaData were rejected as too close to ALLDATA.

- 2026-10-31: Budget is **$0** for now: no paid services, no domain yet, no lawyer. Use free
  tiers (see docs/FUNDING.md, docs/HOSTING.md). Prefer free legal resources over paid review.
- 2026-10-31: Production = one Docker image (`/Dockerfile`) serving API + built PWA.
  Seed data lives in `backend/app/seed/data/`.

## Open decisions (waiting on owner)
- Project contact email for conduct/privacy reports (referenced in README "Contact").
- Trademark check on "ChrystalClear" (free option: USPTO law school clinic) before spending on branding.
- CLA review: lawyer, free clinic, or switch to a standard template (Apache ICLA / Harmony) before outside contributors join.
