# Contributing to ChrystalClear

Thanks for helping build free repair information for everyone.

## Content rules (please read — this keeps the project legal)

**Do:**
- Write guides, specs, and notes **in your own words**, from your own experience and knowledge.
- Share **facts**: torque values, fluid capacities, part numbers, labor time estimates,
  diagnostic tips. Facts aren't copyrightable; someone else's wording, tables, and diagrams are.
- Use your **own photos**, or images with a license that allows reuse (say which).
- Use public and open data: NHTSA vPIC, recalls, complaints, the TSB index, open OBD-II
  code lists with a compatible license, and open-source projects with AGPL-compatible licenses.

**Don't:**
- Copy or closely paraphrase text, images, diagrams, or data from ALLDATA, Mitchell 1,
  Identifix, factory service manuals, or any other paid or copyrighted source.
- Scrape any website or database.
- Post screenshots or photos of copyrighted manuals or software screens.

Copying features, workflows, or layout *ideas* from other repair tools is fine. Copying
their *content* is not. When in doubt, leave it out, or ask in an issue.

**Safety:** double-check torque values and safety-critical specs (brakes, steering,
suspension, airbags, fuel, high-voltage) before submitting. Mark anything you're unsure of.

## Licenses and the Contributor License Agreement
- **Code** is licensed under **AGPL-3.0**.
- **Community content** (guides, specs, notes, photos) is licensed under **CC BY-SA 4.0**.
- Everyone signs our **[Contributor License Agreement](CLA.md)** once. You keep ownership of
  your work, and the project promises your contributions stay openly available forever.
  It also lets the project offer optional paid business tools later, while all repair
  information stays free.

## Code contributions
- Keep pull requests small and focused, with a clear description.
- Add or update tests for what you change. CI must pass.
- All user-facing text goes in translation files (`frontend/src/i18n/locales/`) — no hard-coded strings.
- Never commit secrets (API keys, passwords). Use environment variables; see `.env.example`.
- Update `CHANGELOG.md` for user-visible changes.

### Development setup
- Easiest: install Docker, then run `docker compose up` and open http://localhost:5173.
- Without Docker: `./scripts/dev.sh` (needs Python 3.12+ and Node 22+).
- Backend details: `backend/README.md`. Frontend details: `frontend/README.md`.
- Before opening a pull request: `cd backend && ruff check . && pytest` and
  `cd frontend && npm run typecheck && npm test`. GitHub runs the same checks automatically.

## Conduct
Everyone participating is expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
