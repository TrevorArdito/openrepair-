# Changelog

All notable changes to this project are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
### Added
- Vehicle listings take yard details buyers look for first: row / stock #, date it arrived on the
  lot, keys yes/no, main damage, and for tow yards "Lien sale — available after [date]". They show
  on the search card and the listing page. Demo stock includes them (plus one lien-sale example).
- **Content Research Program** adopted (`CONTENT_PROGRAM.md`): `research/` knowledge base
  (format review, owner lookups, blocked sources, review log) and `content/` for team-written pages.
- **Diagnostic guide pages** (engine-specific DTC pages): what the computer monitors, enable
  criteria, causes ranked for that engine with known weak spots, tests with spec values, pins and
  good/bad results, related TSBs/recalls, common misdiagnoses, repair time and parts cost, numbered
  sources with per-claim references, UNVERIFIED marks. Repair procedures gain applications, special
  tools, fluids with capacities, per-step specs and sequences, and techs' gotchas.
- Every guide shows "Work at your own risk" first, "Fact-checked by the ChrystalClear reviewer",
  "Last revised", and an "under review" notice while a reported mistake is open. Report-a-mistake
  takes the page section and emails the admins. Team pages in `content/` publish only after a
  different reviewer agent signs off.
### Changed
- Make dropdowns (vehicle picker, marketplace filter, listing form, guide tags) list the 20
  most common makes first (Ford, Chevrolet, Toyota, Honda, ...), then every make A–Z.
- Vehicle page hides empty sections instead of showing blanks: the TSB and Specs tabs only
  appear when there's something in them, the quick-specs box only when it has numbers, and the
  "Common codes" heading only above a list. Diagnostic guide pages now count in the Guides tab.
- Recall count now counts only the vehicle maker's own recalls for that model and engine.
  Recalls filed by other companies (upfitters, equipment makers) and maker recalls that name a
  different engine size go in collapsed groups below. NHTSA's ALL-CAPS text is shown in normal
  sentence case (acronyms like ABS kept).
- Demo stock for showing yards (`MARKET_DEMO_DATA`): a sample recycler with whole vehicles first,
  then transmissions and parts, each with donor VIN and mileage; every title starts "DEMO —".
- Marketplace switched on in `render.yaml` (payments stay off). Pages of a switched-off module
  show a friendly "Coming soon" instead of "Not found".
- **Repair content is now proprietary** — free to read, all rights reserved (`content/LICENSE`,
  Content License page, README, CONTRIBUTING, CLA §5, Terms). The code stays AGPL-3.0; content
  published before 2026-11-06 stays CC BY-SA 4.0 for those who received it.
- **Every vehicle since 1984**: importer for EPA fuel-economy data — every car, SUV, minivan and
  light pickup with each engine (~21,000 year/model/engine combinations, 145 makes), matched to
  NHTSA's make/model names; refreshed weekly. Turbo/supercharged engines are kept separate.
- **Engine catalog**: 48 named engine families (GM 5.3/6.2/4.3, Ford Coyote/EcoBoost/Modular,
  HEMI, Pentastar, Toyota, Honda, Nissan, Hyundai, Power Stroke, Cummins, Duramax, EcoDiesel…)
  linked to the vehicles that use them; engine pages, "Browse engines", engines in search, engine
  names in the picker and on vehicle pages; Google-friendly engine pages.
- **Heavy-duty diesel trucks** (F-250/F-350 Power Stroke, Ram 2500/3500 Cummins, Silverado/Sierra
  HD Duramax) added from the engine catalog.
- Owner's top-20 priority vehicles recorded for content planning.
- **Owner's-manual specs**: facts transcribed from the manufacturer's own manual with page numbers
  — Ford F-150 2015, 2017 and 2022, every engine (capacities, fluid types with Ford spec numbers,
  firing order, spark plug gap, compression ratio, Motorcraft part numbers, lug nut torque;
  185 facts); 2024 Chevrolet Silverado 1500, Ram 1500 and Toyota Camry (gas + hybrid). Facts can apply to several engines at once and capacities can be ranges ("2.0–2.1 qt").
- Engine families: GM 2.7L Turbo and 3.0L Duramax, Ram eTorque 3.6/5.7 and 6.2 supercharged,
  Toyota 2.5L hybrid, Ford 3.3L V6, 3.5L PowerBoost hybrid and 3.0L Power Stroke diesel (F-150).
- **Quick Specs** box on the vehicle overview and table-style Specs tab (values shown inline, shop
  order, "General" tags); specs can target an exact engine; specs can be text (firing order) and
  fluids can be type-only (brake fluid); "as printed in the manual" values.
- **Parts marketplace (off by default)**: buy and sell new and used parts matched to vehicles —
  seller profiles, listings with photos and fitment, "fits my vehicle" search, buyer-seller
  messages, reports, moderator review queue, licensed-seller verification, and built-in rules
  that block illegal items (emissions delete parts, used airbags, unverified used catalytic
  converters). Turn on with `ENABLE_MARKETPLACE=true`.
- Marketplace: **whole vehicles in any condition** — VIN look-up fills year/make/model from NHTSA,
  title status, runs/drives, odometer, links to our repair info and free recall/theft checks;
  "Saved" watch list; email alert when someone messages you (no message text in the email).
- Marketplace: **search within N miles of a ZIP code** (US Census ZIP centre points, public domain)
  with "nearest first"; **seller star ratings and reviews** from people who actually dealt with
  the seller; moderators can hide reviews.
- **Marketplace payments (Stripe Connect, test mode, off by default)** — see docs/PAYMENTS.md:
  sellers set up payouts through Stripe Express (Stripe verifies identity/bank, sends tax forms);
  *Buy now* for shipped items via Stripe's hosted checkout; 6% platform fee as a Stripe
  application fee (setting `MARKET_FEE_PERCENT`), Stripe's fee paid by the seller; fee breakdown
  shown before listing; money held until the buyer confirms or 3 days after delivery, released
  daily; report-a-problem flow (seller responds, admin refunds or pays out); chargebacks freeze
  orders; order history and printable receipts; switchable Stripe Tax; INFORM Consumers Act
  high-volume seller check; vehicles stay contact-seller only; PayPal-ready provider layer.
- **DRAFT legal documents** (for lawyer review): Terms of Service, Seller Agreement, Prohibited
  Items — shown at /legal/… and linked from About and the marketplace.
### Changed
- TSB import now covers the priority models plus any model someone has looked up (not the whole
  21,000-vehicle catalog, which would outgrow the free database), and writes in batches — the
  first live run had taken hours.
- Flex-fuel engines are treated as the same engine as their gasoline version.
- The weekly recall/complaint refresh only re-checks vehicles people have looked up.

## [0.1.0] — 2026-10-31
First complete version: every v0.1 feature from the plan works, is tested, and can be deployed for free.

### Added
- **VIN decoder**: instant typo checks (length, I/O/Q, check digit), live decoding via NHTSA vPIC,
  results cached in our database.
- **Year / make / model / engine picker** with 45 common makes; model lists fetched once from NHTSA.
  Vehicle pages without an engine offer the known engines as one-tap choices.
- **Vehicle profile** with tabs for recalls, TSBs, complaints, codes, guides and specs.
- **My Garage**: save vehicles with nickname, VIN and notes.
- **Recalls, TSBs and complaints** per vehicle from NHTSA: recall alert banner, "do not drive" /
  "park outside" warnings, filter by part, most-reported problems, links to NHTSA.gov.
  Refresh scripts: `python -m app.importers.nhtsa refresh` and `... tsbs`; every run is logged.
- **Trouble code lookup**: 57 common generic OBD-II codes written in our own words (meaning,
  symptoms, likely causes, tap-to-check diagnosis steps, urgency); any valid code is decoded by
  structure even without a write-up; source and license recorded per code.
- **Community guides & specs**: repair guides, torque specs (multi-stage, torque-to-yield), fluid
  capacities, other specs, part notes and labor times — revision history, restore, "verified by a
  pro", votes, report-wrong-info, moderation queue, photos (location data stripped), and safety
  banners on safety-critical items.
- **Labor times from several sources**: warranty time, labor-guide time, real pro time and real DIY
  time, each split by rust level, built from individual tech reports.
- **15 built-in general guides and specs** (misfire swap test, smoke testing, battery/charging,
  voltage drop, parasitic draw, cooling pressure + block test, thermostat, fuel pressure, O2 heater,
  MAF, fuel trims, electrical reference specs), linked to the codes they help diagnose.
- **Search everything** from one box: VINs, codes (by code or words), vehicles typed naturally
  ("2015 f150"), guides/specs (including words inside steps), and recalls/TSBs within a vehicle.
- **Accounts & moderation**: email sign-up/login (Argon2id, secure cookies, CSRF protection,
  honeypot, rate limits), email confirmation, password reset, "apply to be a verified pro",
  moderator tools (probation / active / suspended / banned), admin role changes, action log,
  optional "confirm email before contributing", download-my-data and delete-my-account.
- **Phone-first installable app**: big buttons, dark/light mode, metric/imperial, all text in
  translation files (Spanish-ready). **Works offline** for recently viewed vehicles, codes, guides
  and their photos; home page lists recently viewed guides.
- **Google-friendly pages**: titles, descriptions, link previews and readable content for code,
  guide and vehicle pages; `sitemap.xml`, `robots.txt`; Search Console verification setting.
- **Free deployment**: `render.yaml` (Render) + Neon Postgres, step-by-step `docs/DEPLOY.md`;
  `ADMIN_EMAILS` to become admin without a command line; photos stored in the database on hosts
  without a permanent disk; host-provided `PORT`; weekly NHTSA refresh via GitHub Actions.
- About page with safety disclaimer, privacy summary, licenses and source-code link (AGPL).
- Hardware module placeholder (disabled) with an enforced confirm-before-write safety contract.
- Planned modules designed: parts catalog, affiliate links, marketplace, state emissions info,
  tune store, catalytic converter section (`docs/COMMERCE_DESIGN.md`), with a shared vehicle
  fitment matcher already in use.
- Developer setup: `docker compose up`, `scripts/dev.sh`, `scripts/check.sh`, sample data,
  single-container production image, GitHub Actions CI (lint, tests on SQLite and Postgres,
  migration check, Docker build).
- Project documents: AGPL-3.0 license, README, CONTRIBUTING (content rules), Code of Conduct,
  CLAUDE.md, CLA draft, PLAN, HOSTING, FUNDING, DATA_SOURCES, BUSINESS_IDEAS.

### Changed
- Project renamed from OpenRepair to **ChrystalClear**.
- Business model: all repair information free forever; optional paid business tools may come later.
- Sources on specs are a single small "Source:" line; only numeric specs ask for one.

### Fixed
- P0101 write-up: corrected the MAF airflow rule of thumb (about 1 g/s per liter at warm idle).
