# OpenRepair v0.1 Plan

Status: **Waiting for owner approval** before any app code is written.

This is the technical plan for v0.1. Plain-English notes are in *italics*.

---

## 1. Big-picture architecture

```
 Phone / laptop browser (installable PWA, works offline for recent items)
        │  HTTPS (JSON)
        ▼
 FastAPI backend (Python)  ──►  Postgres (production) / SQLite (local dev)
        │                         └─ full-text search lives here too (no extra service)
        ├──► NHTSA vPIC API (VIN decode, makes/models)   — cached in our DB
        ├──► NHTSA recalls / complaints / TSB data       — imported by scripts
        └──► File storage for photos (local disk in dev, S3-compatible in prod)
```

*We keep it to two moving parts (the app and the database) so hosting stays cheap
and there's little to break. Search uses the database's built-in text search
instead of a separate search server.*

### Module design (so future features plug in)

Every feature is a self-contained **module** in `backend/app/modules/<name>/` with
its own routes, database tables, and tests, plus a matching folder in
`frontend/src/features/<name>/`. A small registry turns modules on/off with
environment flags.

- v0.1 modules (on): `accounts`, `vehicles`, `safety` (recalls/TSBs/complaints),
  `dtc`, `community` (guides & specs), `search`, `moderation`.
- Later modules (designed for, not built): `hardware` (ELM327/J2534 live data &
  code reading), `wiring` (community-drawn diagrams), `keys` (key programming),
  `tuning` (ECU), `parts` (price lookup).
- **Hardware modules are off by default** (`ENABLE_HARDWARE=false`), show safety
  warnings, and any action that *writes* to a vehicle (clear codes, program keys,
  flash an ECU) requires an explicit confirmation step that the module interface
  enforces — a module can't skip it.

---

## 2. Folder structure

```
openrepair/
├── backend/
│   ├── app/
│   │   ├── main.py              # builds the app, loads enabled modules
│   │   ├── config.py            # all settings come from environment variables
│   │   ├── db.py                # database connection (Postgres or SQLite)
│   │   ├── core/                # security, permissions, rate limits, units, errors
│   │   ├── modules/
│   │   │   ├── accounts/        # register, login, roles, sessions
│   │   │   ├── vehicles/        # VIN decode, year/make/model/engine, My Garage
│   │   │   ├── safety/          # recalls, TSB index, complaints + importers
│   │   │   ├── dtc/             # trouble codes
│   │   │   ├── community/       # guides, specs, revisions, votes, reports, photos
│   │   │   ├── search/          # one search box across everything
│   │   │   ├── moderation/      # review queue, reports, bans, audit log
│   │   │   └── hardware/        # placeholder only (disabled), interface + README
│   │   └── importers/           # CLI: refresh NHTSA data, load seed data
│   ├── alembic/                 # database migrations (versioned schema changes)
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # routing, layout, theme (dark mode), providers
│   │   ├── components/          # big-button UI kit, cards, tabs, unit display
│   │   ├── features/            # vehicles, garage, safety, codes, guides,
│   │   │                        # search, account, moderation
│   │   ├── i18n/locales/en/     # ALL user-facing text lives here (Spanish later)
│   │   ├── lib/                 # api client, unit conversion, offline cache
│   │   └── main.tsx
│   ├── public/                  # app icons, manifest
│   ├── vite.config.ts           # includes PWA/offline setup
│   └── Dockerfile
├── data/seed/                   # sample vehicles, DTCs, guides, specs (our own words)
├── docs/                        # PLAN.md, HOSTING.md, DATA_SOURCES.md, ARCHITECTURE.md
├── scripts/                     # dev.sh (one-command setup), helpers
├── .github/workflows/ci.yml     # tests on every push
├── docker-compose.yml           # one command: `docker compose up`
├── .env.example                 # every setting, with safe dev defaults
└── CLAUDE.md, README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, TODO.md, CHANGELOG.md, LICENSE
```

---

## 3. Database schema

Conventions: integer `id` primary keys, `created_at`/`updated_at` on everything,
measurements stored in **metric (SI) internally** and converted for display.

### Accounts
| Table | Key columns | Notes |
|---|---|---|
| `users` | email (unique), password_hash, display_name, role (`user`/`pro`/`moderator`/`admin`), status (`active`/`probation`/`suspended`/`banned`), reputation, unit_pref, locale, theme, email_verified_at | *No name, phone, address, or birthday — we don't need them.* |
| `sessions` | token_hash, user_id, expires_at | Login cookie; we store only a hash of the token. |
| `email_tokens` | user_id, purpose (`verify`/`reset`), token_hash, expires_at, used_at | One-time links. |
| `pro_requests` | user_id, statement, status, reviewed_by, reviewed_at | How someone asks to become "verified pro". |

### Vehicles
| Table | Key columns | Notes |
|---|---|---|
| `makes` | name, vpic_make_id | From NHTSA vPIC. |
| `models` | make_id, name, vpic_model_id | |
| `vehicles` | year, model_id, trim, engine_displacement_l, cylinders, fuel_type, engine_code, drive_type, transmission, body_class | One row per year + model + engine combo — the thing guides/specs attach to. |
| `vin_decodes` | vin (unique), vehicle_id, raw_json, decoded_at | Cache so we don't re-ask NHTSA. |
| `garage_vehicles` | user_id, vehicle_id, vin (optional), nickname, notes | "My Garage". |

### Safety data (NHTSA, public domain)
| Table | Key columns |
|---|---|
| `recalls` | campaign_number (unique), manufacturer, component, summary, consequence, remedy, report_date |
| `recall_vehicles` | recall_id, make, model, year |
| `complaints` | odi_number (unique), make, model, year, component, summary, crash, fire, injuries, deaths, date_received |
| `tsbs` | nhtsa_id (unique), bulletin_number, make, model, year, component, summary, bulletin_date |
| `data_imports` | source, started_at, finished_at, rows_added, rows_updated, status, error |

### Trouble codes
| Table | Key columns | Notes |
|---|---|---|
| `dtcs` | code (e.g. `P0301`), system (P/B/C/U), make_id (null = generic), title, description, symptoms[], causes[], diagnostic_steps[], severity, source, source_license | Written in our own words; source + license tracked per row. |

### Community content (guides & specs)
One shared system for every kind of contribution so history, voting, reporting
and "verified" work the same everywhere.

| Table | Key columns | Notes |
|---|---|---|
| `entries` | kind (`procedure`/`torque_spec`/`fluid_capacity`/`part_note`/`labor_time`), slug, status (`published`/`pending`/`hidden`), current_revision_id, verified_revision_id, verified_by, verified_at, score, safety_critical, created_by | The "thing" users see. |
| `entry_revisions` | entry_id, number, author_id, title, data (JSON, validated per kind), edit_summary, status (`approved`/`pending`/`rejected`) | Full snapshot each edit → easy history, diff, and revert. |
| `entry_vehicles` | entry_id, make_id, model_id, year_from, year_to, engine filter | Which vehicles it applies to (ranges, since a guide often covers many years). |
| `systems` | slug, parent_id, name_key | Category tree: Engine › Cooling › Water pump, etc. |
| `entry_systems` | entry_id, system_id | |
| `entry_dtcs` | entry_id, dtc_code | Links guides to codes. |
| `photos` | entry_id, revision_id, uploader_id, storage_key, width, height, caption, status | Location data (GPS) stripped from photos on upload. |
| `votes` | user_id, entry_id, value (+1/-1) | One vote per person per entry. |
| `reports` | entry_id, revision_id, reporter_id, reason (`wrong_info`/`unsafe`/`spam`/`copyright`/`other`), details, status, resolved_by | "Report wrong info" button. |
| `moderation_log` | actor_id, action, target_type, target_id, reason | Audit trail for every moderator action. |

**What's inside `data` for each kind** (validated by the backend):
- `procedure`: summary, difficulty, time estimate, tools[], parts[], warnings[], steps[] (text + optional photo + optional torque reference)
- `torque_spec`: component, fastener, value (N·m), optional range/angle-step ("30 N·m + 90°"), sequence notes, one-time-use bolt flag
- `fluid_capacity`: system, capacity (L), fluid spec, with/without filter
- `part_note`: part description, OEM/aftermarket numbers, fitment notes
- `labor_time`: job, hours (community estimate), notes

**"Verified by a pro"** points at a *specific revision*. If someone edits after
verification, the page shows "Verified on an earlier version" until a pro
re-checks it. *So a bad edit can't ride on someone else's verification.*

### Search
`search_documents` (doc_type, doc_id, title, body, vehicle keys) — one index for
vehicles, codes, recalls, TSBs, and community entries. Postgres full-text search +
trigram fuzzy matching in production; SQLite FTS5 in local dev.

---

## 4. API routes (all under `/api/v1`)

**Health:** `GET /health`

**Vehicles**
- `GET /vehicles/decode/{vin}` — decode VIN (validates check digit first)
- `GET /vehicles/years` · `GET /vehicles/makes?year=` · `GET /vehicles/models?year=&make_id=` · `GET /vehicles/engines?year=&model_id=`
- `GET /vehicles/{id}` — profile with counts (recalls, TSBs, complaints, guides, specs)
- `GET /vehicles/{id}/recalls` · `/tsbs` · `/complaints` · `/entries?kind=&system=`

**My Garage** (logged in): `GET /garage` · `POST /garage` · `PATCH /garage/{id}` · `DELETE /garage/{id}`

**Codes:** `GET /dtcs?q=` · `GET /dtcs/{code}` (includes linked guides)

**Community**
- `GET /entries?vehicle_id=&kind=&system=&dtc=&sort=` · `GET /entries/{id}`
- `POST /entries` — create (goes to review if the author is new/on probation)
- `POST /entries/{id}/revisions` — edit
- `GET /entries/{id}/revisions` · `GET /entries/{id}/revisions/{n}` · `POST /entries/{id}/revert/{n}`
- `POST /entries/{id}/vote` · `POST /entries/{id}/reports` · `POST /entries/{id}/verify` (pro+)
- `POST /entries/{id}/photos`
- `GET /systems`

**Search:** `GET /search?q=&types=&vehicle_id=`

**Accounts**
- `POST /auth/register` · `/auth/login` · `/auth/logout` · `/auth/verify-email` · `/auth/forgot-password` · `/auth/reset-password`
- `GET /me` · `PATCH /me` (units, theme, language) · `GET /me/export` (download my data) · `DELETE /me` (delete my account)
- `POST /pro-requests`

**Moderation** (moderator+)
- `GET /mod/queue` (pending edits + open reports) · `POST /mod/revisions/{id}/approve|reject`
- `POST /mod/reports/{id}/resolve` · `POST /mod/entries/{id}/hide|restore`
- `POST /mod/users/{id}/status` (probation/suspend/ban) · `GET /mod/log`
- Admin only: `POST /admin/users/{id}/role` · `GET /admin/imports`

---

## 5. Pages (frontend)

| Page | What it does |
|---|---|
| **Home** `/` | Giant VIN box (paste or type), Year › Make › Model › Engine picker, recent vehicles, My Garage shortcuts, code search |
| **Vehicle profile** `/vehicle/:id` | Header with Y/M/M/engine + "Add to garage". Tabs: Overview (key specs: oil capacity, lug-nut torque, etc.), Recalls, TSBs, Complaints, Codes, Repair Guides, Specs & Fluids, Labor. Browse-by-system tree (Engine › Cooling › …) |
| **My Garage** `/garage` | Saved vehicles with nicknames/VINs, one tap to open |
| **Codes** `/codes`, `/codes/:code` | Search; meaning, symptoms, causes, step-by-step diagnosis, related guides |
| **Guide/spec view** `/entries/:id` | Big readable steps, tools/parts list, warnings, safety disclaimer on torque/safety items, verified badge, votes, "Report wrong info" |
| **Edit / New** `/entries/:id/edit`, `/new` | Form per kind, photo upload, vehicle/system/code tagging |
| **History** `/entries/:id/history` | Revisions, side-by-side diff, revert (mods) |
| **Search** `/search` | One box, grouped results |
| **Login / Register / Reset** | Email + password |
| **Account** `/account` | Units (metric/imperial), dark/light, language, request pro status, export data, delete account |
| **Moderation** `/mod` | Review queue, reports, users, log |
| **About / Legal** `/about`, `/legal` | Disclaimer, privacy policy, content policy, **link to source code** (required by AGPL) |
| **Offline** | Shown when there's no signal; lists what's saved on the device |

**Shop-friendly UI rules:** minimum 48px tap targets (most buttons 56px+), 18px+
body text, high contrast, dark mode default-on-request (follows phone setting,
toggle in header), no tiny icons without labels, one-hand reachable bottom nav
(Home, Garage, Codes, Search, Account).

**Offline:** app shell is cached; every vehicle, code, and guide you open is saved
on the device (last ~50 items) and readable with no signal.

---

## 6. Security & privacy approach
- Passwords hashed with **Argon2id** (current best practice).
- Login via secure, HTTP-only cookie; CSRF protection on all changes.
- Every input validated by strict schemas; VINs checked (17 chars, no I/O/Q, check digit).
- Rate limits on login, registration, posting, reporting.
- Anti-spam: hidden honeypot field, new accounts on "probation" (first few
  contributions reviewed), optional free Cloudflare Turnstile captcha, links in
  posts limited for new users.
- Photos: type/size checked, re-encoded, location data stripped.
- No IP addresses stored long-term; no third-party trackers; no data selling (ever).
- All secrets in environment variables; `.env` is git-ignored.

## 7. Build order (each step = small, working commits)
0. Tooling: Docker, CI, backend/frontend skeletons, health check
1. VIN decoder + YMM picker + vehicle profile + My Garage (needs accounts → minimal accounts land here)
2. Recalls / TSBs / complaints + import scripts
3. DTC search + seed codes
4. Community guides & specs (revisions, verify, votes, reports, photos, disclaimer)
5. Search
6. Accounts polish: roles, pro requests, moderation tools, anti-spam
7. PWA offline, units toggle, dark mode polish, seed data, docs

Tests required: VIN decoder, DTC lookup, guide editing (plus auth & permissions).
