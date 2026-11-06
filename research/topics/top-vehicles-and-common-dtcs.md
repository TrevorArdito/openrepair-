# Which vehicles and codes come first (Content Program step 2, scope)

*Researched 2026-11-06.*

## Most common vehicles on US roads (all model years)
Experian Automotive Market Trends, Q3 2025 — share of all US light-duty vehicles in operation:

| # | Model | Share |
|---|---|---|
| 1 | Ford F-150 | 3.7% |
| 2 | Chevrolet Silverado 1500 | 2.7% |
| 3 | Toyota Camry | 2.3% |
| 4 | Honda Accord | 2.0% |
| 5 | Honda CR-V | 2.0% |
| 6 | Honda Civic | 1.9% |
| 7 | Toyota RAV4 | 1.9% |
| 8 | Toyota Corolla | 1.8% |
| 9 | Toyota Tacoma | 1.5% |
| 10 | Ford Escape | 1.2% |
| 11–15 | GMC Sierra 1500, Ford Explorer, Ram 1500, Chevrolet Equinox (1.2% each), Nissan Altima (1.1%) | |

Cross-checks:
- iSeeCars, 2024 used-car sales (1–5-year-old vehicles): F-150, Silverado 1500, Ram 1500,
  Equinox, Camry, Tacoma, Rogue, Explorer, RAV4, Civic — same core group.
- Kelley Blue Book, 2024 new sales: F-Series, Silverado, RAV4, Tesla Model Y, CR-V.

**Milestone "top 10 vehicles"** = the Experian top 10 above. They match the owner's priority list
(`backend/app/seed/data/priority_models.json`), which also covers Sierra, Ram, Explorer, Equinox,
Altima and the HD diesels next.

Sources:
1. Experian, *Automotive Market Trends Report* Q3 2025 (PDF), experian.com
2. iSeeCars via Yahoo Autos, "The 100 Most Popular Used Cars in 2024"
3. Experian / Kelley Blue Book, "What Are the Most Popular Cars and Brands in the US?" (2024 sales)

## Most common trouble codes
No public dataset gives exact per-code frequency counts. Lists published by scan-tool and
diagnostic companies, plus repair-shop write-ups, agree on the same core set. The list below is
the working candidate list; the order on each vehicle is set by that vehicle's research note.

Core (appear on essentially every list): P0420/P0430 (catalyst efficiency), P0300–P0308
(misfire), P0171/P0174 (lean), P0172/P0175 (rich), P0442/P0455/P0456 (EVAP leaks),
P0128 (coolant below thermostat temperature), P0401 (EGR flow), P0101 (MAF range),
P0135/P0141 (O2 sensor heater), P0011/P0016 (cam timing/correlation), P0299 (turbo underboost —
EcoBoost/1.5T), P0700 (transmission fault requested MIL), P0496/P0441 (purge flow), P0505 (idle).

Sources seen: Identifix public blog index of code guides (P0420, P0300, P0171, P0128, P0456,
P0442, P0332, P0352, P0172, P0455, P0113, P0174, P0301, P0011, P0299, P0700); several shop and
parts-retailer "most common codes" articles.

## First 5 DTC pages (proposed — highest traffic × biggest vehicles)
1. **P0300 — GM 5.3L V8 (Silverado/Sierra 1500)** — AFM/DFM lifter failures are a known weak spot.
2. **P0420 — Toyota 2.5L (Camry/RAV4)**
3. **P0171 — Ford 3.5L/2.7L EcoBoost (F-150)**
4. **P0299 — Ford EcoBoost (F-150)**
5. **P0456 / P0455 EVAP leak — Honda 1.5T (Civic/CR-V/Accord)**

Each needs its own research note in `research/` (engine-specific causes, tests, specs with two
sources, TSBs from our NHTSA index) before writing.
