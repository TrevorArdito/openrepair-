# Vehicle & engine catalog

Goal (owner): **every vehicle and every commonly used engine**, eventually including
heavy-equipment engines. This is how the catalog is built and how it grows.

## Where vehicles come from
| Source | Covers | How |
|---|---|---|
| **EPA fuel economy data** | Every car, SUV, minivan and light pickup sold in the US, 1984 → next model year (~50,000 rows → ~21,000 year/model/engine combos), with displacement, cylinders, fuel, turbo/supercharger, hybrid/EV | `python -m app.importers.epa` (weekly) |
| **NHTSA vPIC** | Every make/model registered with NHTSA (including heavy trucks, vans, motorcycles); used for VIN decoding and the year/make/model picker | Live, on demand, cached |
| **Engine catalog** (`engine_families.json`) | Named engine families (e.g. "GM 5.3L V8", "Cummins 6.7L I6 Turbo Diesel") and where they were used; creates the heavy-duty diesel pickups that EPA data doesn't cover (Ford Super Duty Power Strokes, Ram Cummins, GM Duramax) | Seed script (every start) |
| **VIN decodes** | Anything a user decodes that isn't already known | Automatic |

A "vehicle" in our database = **year + model + engine** (displacement, cylinders, fuel,
turbo/supercharged). 2WD/4WD and flex-fuel variants of the same engine are one vehicle.

## Accuracy rules
- Engine families only contain well-established facts. An engine is linked to a vehicle only
  when make, model, year, displacement, cylinders, fuel and turbo **all** match a known
  application — otherwise the vehicle simply shows "3.6L 6-cyl" with no family name.
- Cylinder layout (V6 vs I6) is only shown when certain.
- Catalog-created vehicles never go past the current calendar year (no assumed future models).
- Year ranges are typical model years; the app tells users to confirm with the VIN.

## Priority vehicles (owner's list, 2026-10-31)
`backend/app/seed/data/priority_models.json` — these get detailed guides/specs first:
1 F-150 · 2 Silverado 1500 · 3 Ram 1500 · 4 Sierra 1500 · 5 Camry · 6 Accord · 7 Civic ·
8 Corolla · 9 RAV4 · 10 CR-V · 11 Altima · 12 Tacoma · 13 Explorer · 14 Equinox ·
15 Grand Cherokee · 16 Wrangler · 17 Escape · 18 Rogue · 19 Elantra · 20 Malibu.
Next tier: Super Duty / HD diesel trucks (F-250/F-350 Power Stroke, Ram 2500/3500 Cummins,
Silverado/Sierra HD Duramax). Focus years: roughly 1990–2024.

## Adding an engine family
Add an entry to `engine_families.json` (name, maker, displacement, cylinders, layout, fuel,
aspiration, codes, years, `fitment` list of make/model/years; `"create": true` only for vehicles
missing from EPA data). Re-run the seed — linking happens automatically. Only add facts you can
confirm from public sources (manufacturer press/spec pages, owner's manuals).

## Heavy equipment & other engines (planned)
Engine families already have an `applications` field (`light_duty`, `heavy_duty`, and later
`off_road`, `marine`, `generator`). The plan:
- **Engine families** for common diesel/industrial engines (e.g. Cummins B/L/X series,
  Caterpillar C-series, John Deere PowerTech, Kubota, Perkins, Isuzu, Yanmar, Detroit Diesel,
  Navistar/International, PACCAR), facts from manufacturers' public spec sheets.
- **Equipment table** (no VINs): manufacturer, model, type (excavator, skid steer, tractor,
  loader, generator…), years, serial-number ranges, engine family — so guides, specs and
  labor times can target equipment the same way they target vehicles.
- **Medium/heavy trucks** (class 4–8): from NHTSA vPIC plus engine families above.
