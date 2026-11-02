# Future modules: parts, marketplace, emissions, tunes, catalytic converters

Status: **designed, not built.** v0.1 comes first. This document fixes the database shape
now so these features plug in later without reworking vehicles, guides or accounts.

Every module below is optional and lives in its own folder (`backend/app/modules/<name>/`,
`frontend/src/features/<name>/`) behind an env flag that is **off by default**. The free
repair core never depends on them (CLAUDE.md, Option B).

---

## 1. The shared idea: "fitment"

A part, a tune, a guide and a spec all need the same answer: *which vehicles does this fit?*
We already store that for guides (`entry_vehicles`: make, optional model, year range,
optional engine size). Parts and tunes reuse **the exact same shape and matching code**
(`app/modules/vehicles/fitment.py`), so "show parts that fit my 2015 F-150 3.5L" works the
same way as "show guides for my 2015 F-150 3.5L".

```
fitment row = make_id, model_id (null = all models), year_from, year_to,
              displacement_l (null = all engines), notes (e.g. "4WD only")
```

Later, fitment can get finer (trim, drive type, body, VIN range) by adding optional
columns — existing rows keep working because empty = "any".

---

## 2. Parts catalog (`parts` module)

| Table | Key columns | Notes |
|---|---|---|
| `part_categories` | slug, parent_id, system_slug | Tree (Brakes › Pads). Linked to our `systems` tree so a brake guide can show brake parts. |
| `brands` | name, kind (`oem` / `aftermarket` / `remanufactured`) | |
| `parts` | category_id, brand_id, part_number, name, description, attributes (JSON), status | One row per brand + part number. Attributes = position (front/rear), dimensions, etc. |
| `part_interchange` | part_id, other_part_id, relation (`same`, `replaces`, `replaced_by`, `equivalent`) | Supersessions and cross-references. Community-contributed, moderated. |
| `part_fitment` | part_id + fitment row | Same shape as `entry_vehicles`. |
| `entry_parts` | entry_id, part_id, quantity | Links repair guides to the parts they use ("parts for this job"). |
| `part_compliance` | part_id, epa_status, carb_eo_number, states_allowed (JSON), notes | Required for emissions-related parts (catalytic converters, tunes, intakes, exhaust). |

**Data sources (legal):** manufacturers'/suppliers' own catalog feeds offered for resale
or affiliate use (under their terms), community contributions, and seller listings.
Never scrape competitor catalogs.

---

## 3. Affiliate parts links (`affiliates` module) — the first money-maker

| Table | Key columns | Notes |
|---|---|---|
| `affiliate_programs` | name, network, base_url, commission_note, active, disclosure_text | e.g. a parts retailer's or tool brand's affiliate program. |
| `affiliate_offers` | program_id, part_id (nullable), search_url_template, label | Either a specific part, or a search link built from the part number + vehicle. |
| `affiliate_clicks` | offer_id, created_at, entry_id (nullable) | **No user id, no IP.** Only counts, for revenue reporting. |

Rules: links are clearly labeled and disclosed (FTC), never inside safety steps or specs,
never change what information is shown, and never paywall anything.

---

## 4. Parts marketplace (`marketplace` module) — new and used, with fitment

**Status: v1 built (2026-11-01), off by default (`ENABLE_MARKETPLACE`).** See
`backend/app/modules/marketplace/README.md`. Tables are prefixed `market_`. Payments, orders and
reviews are built too (see docs/PAYMENTS.md for payments); seller verification stores a license
number only (no documents).

| Table | Key columns | Notes |
|---|---|---|
| `sellers` | user_id, type (`individual` / `shop` / `recycler` / `retailer`), display_name, location (city/state/ZIP only), verified_at, status, rating | One account can be a seller. Business details only if they choose. |
| `seller_verifications` | seller_id, kind (`id`, `business_license`, `dismantler_license`), status, reviewed_by | Needed for used catalytic converters and high-theft parts. Documents stored privately, deleted after review. |
| `listings` | seller_id, part_id (nullable), title, description, condition (`new` / `used` / `reman` / `for_parts`), price_cents, currency, quantity, location, shipping_options (JSON), status (`draft` / `active` / `sold` / `removed`), source_vin (used parts, optional), mileage (used), created_at | A listing can point at a catalog part or be free-form. |
| `listing_fitment` | listing_id + fitment row | Same shape again. Used parts pulled from a known VIN inherit that vehicle's fitment. |
| `listing_photos` | listing_id, photo_id | Reuses the existing photo pipeline (EXIF/GPS stripped). |
| `listing_reports` | listing_id, reporter_id, reason (`stolen`, `prohibited`, `scam`, `wrong_fitment`, `other`) | Same moderation queue as guides. |
| `orders` (later) | listing_id, buyer_id, amount_cents, fee_cents, payment_ref, status | Only when payments are added (a payment provider handles card data — we never store it). |
| `seller_reviews` (later) | order_id, rating, comment | Only buyers with a completed order can review. |

**Prohibited listings (enforced by category rules + moderation):** used airbags/SRS parts,
"delete" or defeat parts/tunes (EGR/DPF/catalyst deletes, O2 simulators), counterfeit parts,
parts with an open safety recall unless remedied, and used catalytic converters except from
verified licensed sellers with the documentation their state requires.

---

## 5. State emissions info (`emissions` module)

| Table | Key columns | Notes |
|---|---|---|
| `states` | code, name | 50 states + DC. |
| `emissions_programs` | state_code, area (statewide / county list / metro), test_type (`obd`, `tailpipe`, `visual`, `none`), model_years_covered, fuel_types, frequency, exemptions, official_url, last_checked | Facts from each state agency's public site, written in our words, with the official link. |
| `emissions_rules` | program_id, rule (`readiness_monitors_allowed_incomplete`, `carb_parts_required`, ...), value, notes | e.g. how many incomplete OBD monitors are allowed for a given model year. |

Feature ideas: "Will my vehicle pass?" checklist (readiness monitors, check-engine light,
recent battery disconnect / code clear), and which aftermarket parts are legal in each state
(ties into `part_compliance`).

---

## 6. Tune store (`tunes` module) — emissions-legal tunes only

| Table | Key columns | Notes |
|---|---|---|
| `tune_vendors` | seller_id, name, verified_at | Vendors are marketplace sellers with extra verification. |
| `tunes` | vendor_id, name, description, platform (handheld device / ECU flash tool), stage, price_cents, legal_status (`carb_eo` / `epa_compliant` / `race_only_not_sold`), carb_eo_number, status | Only `carb_eo` or documented `epa_compliant` tunes can be listed. |
| `tune_fitment` | tune_id + fitment row (+ ECU/calibration id) | |

**Hard rule:** no tune that removes, disables or defeats emissions equipment (EGR, DPF,
catalyst, O2 monitoring, etc.) can be listed or sold — US federal law (Clean Air Act tampering
and defeat-device rules) prohibits it, and regulators have issued large penalties to sellers.
California requires a CARB Executive Order (EO) number for street-legal emissions-related
parts and tunes. Anything that writes to a vehicle goes through the hardware module's
confirmation step (CLAUDE.md non-negotiable 5).

---

## 7. Catalytic converter section (`catalytic` content + marketplace category)

Mostly content and tools, built on existing pieces:
- **Guides & codes:** P0420/P0430 diagnosis (already written), converter replacement guides,
  why converters fail (misfire, oil burning, coolant) — community + team content.
- **Legality finder:** which converter is legal for this vehicle in this state —
  federal (EPA) vs CARB-compliant (EO number), using `part_compliance` + `emissions_programs`.
- **Theft prevention:** shields, VIN etching, high-theft vehicle list (from public data only).
- **Marketplace category:** new EPA/CARB-compliant converters with fitment; **used converters
  only from verified licensed sellers** (many states restrict used converter sales to fight theft).

---

## 8. What already exists that these plug into
- `makes` / `models` / `vehicles` — fitment targets.
- `systems` tree — parts categories link to it.
- `entries` (guides/specs) — guides can list parts (`entry_parts`).
- `photos` — listing photos reuse the same safe upload pipeline.
- `users` + roles + moderation queue + reports — sellers, review of listings.
- `app/modules/vehicles/fitment.py` — one matching function for guides, parts, listings, tunes.
