# CLAUDE.md — Project rules for OpenRepair

Read this first in every session. It records the owner's decisions so work stays on track.
If a request conflicts with this file, ask the owner before proceeding.

## What this is
**OpenRepair** — a free, open-source alternative to ALLDATA for auto repair information.

## Non-negotiables
1. **Free forever.** Every feature stays 100% free. Ads *may* be added later, but only if
   nothing is paywalled — no "pro" tier, no premium features, no locked content.
   (The "verified pro" *user role* is a trust badge, not a paid tier.)
2. **License: AGPL-3.0** for code. Because it's a web app, the UI must always link to the
   source code (AGPL §13). Community content license: see "Open decisions".
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

## Open decisions (waiting on owner)
- Business model: keep "free forever, no pro tier" as-is, or leave room to charge later
  for optional business add-ons (core repair info stays free). Affects whether we require
  a Contributor License Agreement (CLA). Do not change the "Free forever" rule until decided.
- Possible rename from "OpenRepair" to "ChrystalClear" (spelling + trademark check pending).
- License for community-contributed content (recommended: **CC BY-SA 4.0**).
- Project contact email for conduct/privacy reports (referenced in README "Contact").
