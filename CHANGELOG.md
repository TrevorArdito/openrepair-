# Changelog

All notable changes to this project are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
### Added
- **VIN decoder**: instant typo checks (length, I/O/Q, check digit), live decoding via NHTSA vPIC,
  results cached in our database.
- **Year / make / model / engine picker** with 45 common makes; model lists fetched once from NHTSA.
- **Vehicle profile** page (details from the VIN; tabs ready for recalls, TSBs, codes, guides).
- **My Garage**: save vehicles with nickname, VIN and notes.
- **Accounts**: sign up / log in with email; Argon2id password hashing; secure cookies with CSRF
  protection; spam honeypot; rate limits; download-my-data and delete-my-account.
- **Phone-first app**: installable PWA, big buttons, dark/light mode, metric/imperial setting,
  offline access to recently viewed vehicles. All text in translation files (Spanish-ready).
- **About page** with safety disclaimer, privacy summary, licenses and source-code link.
- Hardware module placeholder (disabled) with an enforced confirm-before-write safety contract.
- One-command dev setup (`docker compose up`), no-Docker script (`scripts/dev.sh`), sample data.
- Single-container production image (`Dockerfile`).
- GitHub Actions CI: lint, backend + frontend tests, Postgres migration check, Docker build.
- `docs/FUNDING.md`: running on $0, donation options, free legal help.
- Project skeleton: AGPL-3.0 license, README, CONTRIBUTING (with content rules),
  Code of Conduct (Contributor Covenant 2.1), CLAUDE.md (project decisions), TODO, CHANGELOG.
- v0.1 technical plan in `docs/PLAN.md` (folder structure, database schema, API routes, pages).
- `docs/HOSTING.md` with free / low-cost hosting options.
- `.gitignore` and `.env.example`.
- Contributor License Agreement draft (`CLA.md`); community content licensed CC BY-SA 4.0.
### Changed
- Project renamed from OpenRepair to **ChrystalClear**.
- Business model clarified: all repair information free forever; optional paid business tools may come later.
