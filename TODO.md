# TODO

## Waiting on the owner
- [x] Approve the plan in `docs/PLAN.md` (approved 2026-10-31)
- [x] Business model: Option B — free core forever, optional paid business extras later
- [x] Community content license: CC BY-SA 4.0
- [x] Name: ChrystalClear
- [ ] Register a domain (chrystalclear.app and chrystalclearrepair.com looked unregistered on 2026-10-31; chrystalclear.com is taken)
- [ ] Optional but smart before spending on branding: USPTO search at tmsearch.uspto.gov for "ChrystalClear" and "Crystal Clear" in software (class 9/42), or a one-hour attorney check
- [ ] Create a project contact email (e.g. on the new domain, or a free Gmail/Proton address)
- [ ] Have a lawyer glance at CLA.md before outside contributors join
- [ ] When outside code contributors arrive: install the free CLA Assistant GitHub app (cla-assistant.io)
- [ ] Optional: rename the GitHub repo from `openrepair-` to `chrystalclear` (Settings → General → Repository name), then start a new Claude session on the renamed repo

## Next up — v0.1 build order
- [ ] Step 0: Docker Compose, backend + frontend skeletons, health check, GitHub Actions CI
- [ ] Step 1: VIN decoder (vPIC) + YMM/engine picker + vehicle profile + My Garage (minimal accounts)
- [ ] Step 2: Recalls, TSB index, complaints + NHTSA import scripts
- [ ] Step 3: DTC search + seed generic OBD-II codes (our own wording)
- [ ] Step 4: Community guides & specs (revisions, verify, votes, reports, photos, safety disclaimer)
- [ ] Step 5: Unified search
- [ ] Step 6: Roles, pro requests, moderation queue, anti-spam
- [ ] Step 7: PWA offline cache, units toggle, dark mode polish, seed data, docs (HOSTING.md, DATA_SOURCES.md)

## Ideas for later (not v0.1)
- VIN barcode scanning with the phone camera
- Spanish translation
- Hardware module: ELM327 / J2534 live data and code reading (disabled by default)
- Community-drawn wiring diagrams, key programming, ECU tuning, parts price lookup
