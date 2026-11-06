# CLAUDE.md — Project rules for ChrystalClear

Read this first in every session. It records the owner's decisions so work stays on track.
If a request conflicts with this file, ask the owner before proceeding.

For any repair content work, follow CONTENT_PROGRAM.md.
(Owner amendments to it are in the decision log below, 2026-11-06, and take precedence.)

## What this is
**ChrystalClear** — a free, open-source alternative to ALLDATA for auto repair information.

**Purpose (owner, 2026-11-01):** give EVERY mechanic and technician — and everyone else — the
knowledge and tools the service-information monopolies keep behind expensive paywalls. The
database exists to help people **maintain and repair vehicles correctly**, not just list them.
- **Diagnostics come first** — it's the most important and most challenging part of the job.
  Every vehicle should get diagnostic and repair guidance for anything that can go wrong.
- **Follow the ALLDATA playbook** for layout and workflow so anyone who knows ALLDATA feels at
  home (vehicle → system/component tree → specs, diagnostics/testing, repair procedures, TSBs,
  DTCs, labor) — then improve on every part of it.
- **Every vehicle gets its owner's-manual facts** (capacities, fluid types, torque, engine and
  tune-up specs, part numbers) transcribed from the manufacturer's own free manuals with page
  references (`backend/app/seed/data/manual_specs/`, see `docs/OWNER_MANUAL_SPECS.md`).

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
   source code (AGPL §13). Repair content (guides, specs, research, diagrams): **proprietary,
   all rights reserved, free to read** (owner decision 2026-11-06, replacing CC BY-SA 4.0 —
   see `content/LICENSE`). All contributors (code and
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
- Search: all-words matching in the database with light stemming; Postgres uses pg_trgm
  trigram indexes (Postgres-only indexes are created by hand in migrations and ignored by
  `alembic check`). Full-text ranking/typo tolerance can be added later. No extra search server.
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

## Later (design for, don't build until v0.1 is finished)
OBD-II live data & code reading (ELM327, J2534), community-drawn wiring diagrams, key
programming, ECU tuning, parts price lookup — plus (owner, 2026-10-31):
**affiliate parts links, a parts marketplace (new and used, with vehicle fitment), state
emissions info, a tune store, and a catalytic converter section.**
Each is a separate module under `backend/app/modules/` + `frontend/src/features/`,
toggled by env flags (off by default). Database design: `docs/COMMERCE_DESIGN.md`.
Anything that targets vehicles (guides, parts, listings, tunes) uses the shared fitment
shape + matcher in `backend/app/modules/vehicles/fitment.py` — don't invent a second one.

Legal guardrails for these modules (non-negotiable):
- **Tune store:** only emissions-legal tunes (CARB EO number or documented EPA compliance).
  Never list or sell anything that removes, disables or defeats emissions equipment
  (EGR/DPF/catalyst deletes, O2 simulators) — federal Clean Air Act tampering rules.
- **Marketplace prohibited items:** used airbags/SRS parts, delete/defeat parts, counterfeit
  parts, parts with an unremedied safety recall; used catalytic converters only from
  verified licensed sellers with the documentation their state requires.
- **Affiliate links:** always disclosed; never inside safety steps or specs; never change
  what repair information is shown.
- **Payments:** a payment provider handles card data; we never store it. Seller identity
  documents are deleted after review.

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
- Run `./scripts/check.sh` (same checks as CI) before every push.
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

- 2026-10-31: Owner wants content to be **EXTENSIVE** and match the depth techs expect from
  ALLDATA/Mitchell/Identifix. Industry-standard procedures, step order, terminology and
  diagram conventions are fine to follow (they're the trade's standard, not anyone's
  copyright). Don't water down or make content counterintuitive out of caution — just
  never copy competitors' or OEM text, images, diagrams or databases.
- **Accuracy policy (owner: "no mistakes"):** general procedures are written to standard
  shop practice with typical values clearly labeled "typical — check the manufacturer's
  spec". Vehicle-specific numbers (torque, capacities, gaps, pressures) are NEVER invented
  or recalled from memory. Re-check seeded content for errors; fix immediately.
- **Sources (clarified by owner 2026-10-31):** the owner does NOT require citing sources
  everywhere. Keep it light: numeric specs (torque, fluids, other specs) ask for one source
  pick (details optional), shown as a single small "Source:" line — it helps pros verify and
  shows facts came from legitimate places. Guides/part notes don't ask for sources.
- **Units (clarified by owner 2026-10-31):** "manufacturer's standard metric" meant the
  manufacturer's standard *measure* of labor (warranty/book time), not the metric system.
  Units stay as built: imperial by default, metric/imperial toggle, stored metric internally.
- **Labor times:** shown from several sources side by side — warranty time and labor-guide
  time (as reported by techs), real pro time, real DIY time — each split by rust level
  (none / some / heavy). Numbers come from many individual reports (median, range,
  count), never a copied labor database.
- **Wiring diagrams:** owner wants interactive, color-coded circuit schematics (tap a
  wire/circuit to highlight it, real wire colors, connector pinouts) for as many vehicles
  as possible. Build as the `wiring` module: our own structured circuit format + SVG viewer.
  Content = standard/generic circuits we draw + community-traced vehicle circuits
  (pinouts/colors are facts). Never trace or redraw OEM diagrams.

- 2026-10-31: Business ideas and priorities are tracked in `docs/BUSINESS_IDEAS.md`.
- 2026-10-31: **v0.1.0 complete.** Free deployment target: Render (render.yaml, Docker) + Neon
  Postgres, guide in `docs/DEPLOY.md`. Production stores photos in the database
  (`STORAGE_BACKEND=database`) because free hosts wipe their disk; admins are bootstrapped with
  `ADMIN_EMAILS`. Google-friendly pages are rendered server-side by `backend/app/seo.py`
  (titles, descriptions, content, sitemap) — keep new public page types in sync with it.

- 2026-10-31: Owner wants the **most extensive vehicle database possible — every vehicle and
  every commonly used engine, eventually heavy-equipment engines.** Built from EPA fuel economy
  data (every light-duty vehicle/engine 1984+), NHTSA vPIC (all makes/models, VINs) and our
  engine-family catalog (named engines + heavy-duty diesel pickups). Engines are first-class
  (`engine_families`). Strict linking rules; never assume future model years. See
  `docs/VEHICLE_CATALOG.md`.
- 2026-10-31: **Owner's priority vehicles** (detailed content first, ~1990–2024):
  F-150, Silverado 1500, Ram 1500, Sierra 1500, Camry, Accord, Civic, Corolla, RAV4, CR-V,
  Altima, Tacoma, Explorer, Equinox, Grand Cherokee, Wrangler, Escape, Rogue, Elantra, Malibu;
  their common engines (GM 5.3, Ford 5.0 & 3.5 EcoBoost, Ram 5.7 HEMI, Toyota 2.5, Honda 1.5T/2.4).
  Next tier: Super Duty / HD diesels (Power Stroke, Cummins, Duramax). Stored in
  `backend/app/seed/data/priority_models.json`.

- 2026-11-01: Owner paused owner's-manual transcription until a better data workflow exists.
- 2026-11-01: Marketplace also sells **whole vehicles in any condition** (VIN required 1981+,
  decoded via NHTSA; title status; private sellers max 5 open vehicle listings, more needs a
  verified dealer license). **Used catalytic converters:** owner wants them allowed wherever
  legal (cheap smog repairs). For now only verified licensed sellers; later a state-aware rule
  (EPA tested-and-labeled policy + each state's law), never where state law forbids.

- 2026-11-02: **Marketplace payments**: Stripe Connect Express, Stripe handles pricing (seller pays
  Stripe fees, Stripe covers losses), direct charges + application fee (`MARKET_FEE_PERCENT`,
  6%); local pickup free; funds held (manual payouts) until buyer confirms / N days after
  delivery; disputes decided by admins; INFORM Consumers Act check; Stripe Tax switchable (CPA);
  vehicles contact-seller only (`MARKET_CONTACT_ONLY_CATEGORIES`); PayPal later via
  `PaymentProvider`. Legal docs in `backend/app/legal/` are DRAFTS. Delete/defeat parts stay
  prohibited (Clean Air Act). Details: docs/PAYMENTS.md.

- 2026-11-06: **Content Research Program adopted** (`CONTENT_PROGRAM.md`). Owner's decisions on it:
  1. **License: all repair content proprietary** (all rights reserved, free to read in the app),
     including team and community content going forward. The code stays AGPL-3.0. Copies
     already published under CC BY-SA 4.0 stay CC BY-SA for whoever received them (can't be
     revoked); the CLA lets the owner relicense contributions from here on.
  2. **Paid/login-only sources: as written in the program** (owner looks things up in ALLDATA
     DIY, Mitchell1 DIY and OEM sites; notes/screenshots go in `research/owner-notes/`; cited as
     "owner lookup"). Owner accepted the risk that those services' terms may forbid this.
     Still never copy their text, images or diagrams into our pages (facts only, our words).
  3. **Sign-off: a designated reviewer agent** (separate from the writer) fact-checks and signs
     off each page when the batch is finished, in place of the program's mechanic sign-off.

## Open decisions (waiting on owner)
- Project contact email for conduct/privacy reports (referenced in README "Contact").
- Trademark check on "ChrystalClear" (free option: USPTO law school clinic) before spending on branding.
- CLA review: lawyer, free clinic, or switch to a standard template (Apache ICLA / Harmony) before outside contributors join.
- Stripe account + keys (owner), lawyer review of the legal drafts, CPA answer on sales tax.
- The GitHub repo is public: whether to move `content/` and `research/` (incl. owner notes and
  screenshots from paid services) into a private repo.
