# TODO

## Waiting on the owner
- [x] Approve the plan in `docs/PLAN.md` (approved 2026-10-31)
- [x] Business model: Option B — free core forever, optional paid business extras later
- [x] Community content license: CC BY-SA 4.0
- [x] Name: ChrystalClear
- [ ] Create a free project contact email (Gmail/Proton) and send it over
- [ ] Optional, free: set up GitHub Sponsors (see docs/FUNDING.md)
- [ ] Later (when funds allow): domain — chrystalclear.app / chrystalclearrepair.com looked free on 2026-10-31
- [ ] Before branding spend: free trademark check via a USPTO law school clinic
- [ ] Before outside contributors: CLA review (free clinic) or switch to a standard template
- [ ] When outside code contributors arrive: install the free CLA Assistant GitHub app (cla-assistant.io)
- [ ] Optional: rename the GitHub repo from `openrepair-` to `chrystalclear` (Settings → General → Repository name), then start a new Claude session on the renamed repo

## Next up — v0.1 build order
- [x] Step 0: Docker Compose, backend + frontend skeletons, health check, GitHub Actions CI
- [x] Step 1: VIN decoder (vPIC) + YMM/engine picker + vehicle profile + My Garage (minimal accounts)
- [x] Step 2: Recalls, TSB index, complaints + NHTSA import scripts
- [x] Step 3: DTC search + seed generic OBD-II codes (our own wording) — 57 codes so far
- [x] Step 4: Community guides & specs (revisions, verify, votes, reports, photos, safety disclaimer, multi-source labor times)
- [x] Step 5: Unified search (VINs, codes, vehicles, guides/specs, recalls/TSBs within a vehicle)
- [x] Step 6: Email verification, password reset, pro applications, moderator user tools (suspend/ban/roles), action log
- [x] Step 7: offline polish, Google-friendly pages + sitemap, free deployment (render.yaml, docs/DEPLOY.md), weekly NHTSA refresh workflow
- **v0.1.0 complete.**

## Go live (owner, ~45 min — follow docs/DEPLOY.md)
- [ ] Decide: merge to `main` (Claude opens a pull request when asked) or deploy from the feature branch
- [ ] Neon account + database; Render account + Blueprint deploy; sign up with your ADMIN_EMAILS address
- [ ] Optional: Brevo email; GitHub secret PROD_DATABASE_URL; Google Search Console

## Vehicle catalog (owner: "as extensive as possible")
- [x] Every light-duty vehicle + engine 1984 → now from EPA data (~21,000), weekly refresh
- [x] Engine family catalog (48 families) linked to vehicles; engine pages; engines in search
- [x] Heavy-duty diesel pickups (Power Stroke, Cummins, Duramax) from the engine catalog
- [x] Owner's top-20 priority vehicles recorded (priority_models.json)
- [ ] More engine families: every engine in the top-20 vehicles 1990–2024 (incl. hybrids, older 1990s engines)
- [ ] Gas engines in HD pickups (Ford 6.2/7.3 gas, GM 6.0/6.6 gas, Ram 6.4 HEMI) — vehicles come from VIN decodes until added
- [ ] Medium/heavy trucks (class 4–8) + their diesel engines
- [ ] Heavy-equipment engines + equipment table (see docs/VEHICLE_CATALOG.md)
- [ ] Bulk-prefetch NHTSA model lists for all makes/years (so the picker never waits on NHTSA)

## Owner's-manual specs (owner priority — see docs/OWNER_MANUAL_SPECS.md for the tracker)
- [x] Pipeline: transcribed manual files → per-engine entries with page refs; Quick Specs; spec tables
- [x] Ford F-150 2015, 2017, 2022 (every engine, 185 facts)
- [ ] Ford F-150: other years (2013 manual downloaded; 2018–2021, 2023–2024; 1990s–2000s)
- [x] 2024 Silverado 1500, Ram 1500, Camry
- [ ] PAUSED by owner (2026-11-01) until a better way to get accurate data is set up; then the rest of the top 20
- [ ] Then: diagnostic & repair guides per vehicle (known problems from TSB/complaint patterns + system diagnostics)
- [ ] ALLDATA-style component tree on the vehicle page (system → specs / testing & diagnosis / repair / TSBs / codes)

## Next big modules (owner priorities)
- [ ] **Wiring diagrams module**: structured circuit format (components, connectors, pins, wires
      with real color codes, splices, grounds) + interactive SVG viewer (tap to highlight a
      circuit, color legend, pinout tables, zoom) + editor. Seed with standard circuits
      (OBD-II DLC pinout, CAN bus, 2/3/4/5-wire sensors, O2 heater, starter, charging, relay).
- [ ] More generic diagnostic guides (target 100+): compression/leak-down, relative compression,
      CAN bus diagnosis, relay testing, scope basics, ABS sensor test, brake jobs, etc.
- [ ] Diagrams/illustrations for guides (our own SVGs in standard conventions)

## Planned commerce & compliance modules (after v0.1 — design in docs/COMMERCE_DESIGN.md)
- [ ] **Affiliate parts links**: disclosed links from part notes / guide parts lists (first money-maker)
- [ ] **Parts catalog**: categories linked to systems, brands, part numbers, interchange, fitment, compliance
- [x] **Parts marketplace v1** (off by default, ENABLE_MARKETPLACE): sellers, license verification,
      listings with fitment + photos, search, messages, reports, review queue, prohibited-item rules
- [ ] Marketplace next: email alert for new messages; distance search by ZIP; buyer reviews;
      payments through a payment provider (Stripe Connect or similar — we never store card data);
      turn it on in production (owner decision)
- [ ] **State emissions info**: programs by state/area, test types, model years, readiness rules,
      "will my vehicle pass?" checklist, official links
- [ ] **Tune store**: emissions-legal tunes only (CARB EO / EPA-compliant), fitment by vehicle + ECU
- [ ] **Catalytic converter section**: diagnosis guides, legality finder (EPA vs CARB by state),
      theft prevention, compliant replacement listings

## Growth items (see docs/BUSINESS_IDEAS.md)
- [ ] Google-friendly public pages (pre-render codes, guides, specs with titles/descriptions, sitemap)
- [ ] Contributor reputation, badges and "top contributors"
- [ ] Spanish translation
- [ ] "Supported by" sponsor slot + disclosed affiliate links (no paywalls, never inside steps/specs)

## Known follow-ups
- Photo storage on S3-compatible storage (Cloudflare R2) once the 0.5 GB free database fills up
- Update the TSB period in .github/workflows/nhtsa-refresh.yml when NHTSA publishes a new file name (currently 2025-2026)
- Offline: logged-in state isn't remembered offline (My Garage needs a connection)
- Search: upgrade to Postgres full-text ranking (tsvector) if results need better ordering at scale; today it's all-words matching + trigram indexes
- Search: typo tolerance ("camery" → Camry) using pg_trgm similarity on Postgres
- Write up more generic codes (target: the ~300 most common); community can add/edit once step 4 lands
- NHTSA's complaints API returns nothing for some popular models (e.g. 2015 F-150); add a bulk importer for FLAT_CMPL / COMPLAINTS_RECEIVED_* files as a fallback
- TSB model-name matching: NHTSA sometimes uses names like "F150 PICKUP" or "SILVERADO 1500"; add a model alias table
- Schedule the NHTSA refresh (e.g. free GitHub Actions cron or host cron): `python -m app.importers.nhtsa refresh` weekly, `tsbs --period 2025-2026` monthly
- Engine list per model only knows engines we've seen (seed data + VIN decodes); community-added engines come with step 4
- Email sending in production needs a free SMTP account (owner); then set EMAIL_BACKEND=smtp and REQUIRE_VERIFIED_EMAIL=true
- Optional captcha (Cloudflare Turnstile, free) on sign-up if spam becomes a problem
- Docker Hub rate-limits anonymous image pulls on some networks; mirror.gcr.io/library/<image> works as a fallback

## Ideas for later (not v0.1)
- VIN barcode scanning with the phone camera
- Spanish translation
- Hardware module: ELM327 / J2534 live data and code reading (disabled by default)
- Community-drawn wiring diagrams, key programming, ECU tuning (see tune store rules), parts price lookup
