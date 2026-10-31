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
- [ ] Step 3: DTC search + seed generic OBD-II codes (our own wording)
- [ ] Step 4: Community guides & specs (revisions, verify, votes, reports, photos, safety disclaimer)
- [ ] Step 5: Unified search
- [ ] Step 6: Roles, pro requests, moderation queue, anti-spam
- [ ] Step 7: PWA offline polish, seed data, docs (DATA_SOURCES.md, deploy guide)

## Known follow-ups
- NHTSA's complaints API returns nothing for some popular models (e.g. 2015 F-150); add a bulk importer for FLAT_CMPL / COMPLAINTS_RECEIVED_* files as a fallback
- TSB model-name matching: NHTSA sometimes uses names like "F150 PICKUP" or "SILVERADO 1500"; add a model alias table
- Schedule the NHTSA refresh (e.g. free GitHub Actions cron or host cron): `python -m app.importers.nhtsa refresh` weekly, `tsbs --period 2025-2026` monthly
- Engine list per model only knows engines we've seen (seed data + VIN decodes); community-added engines come with step 4
- Email verification + password reset (needs a free email-sending account) — step 6
- Suppress the harmless 401 console message when logged out
- Docker Hub rate-limits anonymous image pulls on some networks; mirror.gcr.io/library/<image> works as a fallback

## Ideas for later (not v0.1)
- VIN barcode scanning with the phone camera
- Spanish translation
- Hardware module: ELM327 / J2534 live data and code reading (disabled by default)
- Community-drawn wiring diagrams, key programming, ECU tuning, parts price lookup
