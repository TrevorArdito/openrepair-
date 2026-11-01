# Owner's-manual specs — how we do it, and progress

**Goal:** every vehicle gets the maintenance facts from its manufacturer's own owner's manual:
capacities, fluid types (with the maker's spec numbers), torque values, engine/tune-up specs
(spark plug gap, firing order, compression ratio, required fuel), part numbers (filters, plugs,
batteries, wipers), and more as each manual provides.

## Rules
1. **Only the manufacturer's own free manual** (e.g. fordservicecontent.com, assets.sia.toyota.com,
   owners.honda.com…). Never third-party "manual download" sites.
2. **Facts only**, transcribed exactly (we store the "as printed" value too), each with the
   manual's printed page number. No copied paragraphs, images or tables layout.
3. **One manual = one model year.** Capacities and specs change between years, so each year is
   transcribed from its own manual (or a later manual that explicitly covers it).
4. **Per engine.** Engine-specific facts are tied to the exact engine family; facts identical in
   every engine section are stored once for the whole model year — only after checking they really
   are identical.
5. **Re-check every file** against the manual before committing; fix mistakes immediately.

## How to add a manual
1. Download the official PDF, run `pdftotext -layout`, find the "Capacities and Specifications"
   (Ford), "Specifications"/"Maintenance data" (Toyota/Honda) and wheel/tire chapters.
2. Write `backend/app/seed/data/manual_specs/<make>-<model>-<year>.json` (see the F-150 file).
3. `python -m app.seed` loads it; `pytest tests/test_manual_specs.py` checks it.

## Progress (owner's top 20, ~1990–2024)
| Vehicle | Years done |
|---|---|
| Ford F-150 | 2015 |
| Chevrolet Silverado 1500 | — |
| Ram 1500 | — |
| GMC Sierra 1500 | — |
| Toyota Camry | — |
| Honda Accord | — |
| Honda Civic | — |
| Toyota Corolla | — |
| Toyota RAV4 | — |
| Honda CR-V | — |
| Nissan Altima | — |
| Toyota Tacoma | — |
| Ford Explorer | — |
| Chevrolet Equinox | — |
| Jeep Grand Cherokee | — |
| Jeep Wrangler | — |
| Ford Escape | — |
| Nissan Rogue | — |
| Hyundai Elantra | — |
| Chevrolet Malibu | — |

Scale: 20 vehicles × ~30 years ≈ 600 manuals. Each takes careful reading; this is an ongoing
effort (and a great job for verified-pro volunteers once the site is live).
