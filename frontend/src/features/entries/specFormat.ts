// One-line value text for specs, used in lists, Quick Specs and the full spec pages.
import type { UnitSystem } from "../../lib/units";
import { CONVERTIBLE, FIXED_UNITS, formatQuantity, type Quantity } from "../../lib/units";

/* eslint-disable @typescript-eslint/no-explicit-any */
type D = Record<string, any>;

export function fluidQuantity(d: D): Quantity {
  if (d.amount_unit === "kg") return "mass";
  if (d.amount_unit === "g") return "mass_g";
  if (d.amount_unit === "mL") return "volume_ml";
  return d.system === "fuel_tank" ? "volume_gal" : "volume";
}

export function fluidAmount(d: D, units: UnitSystem): string | null {
  if (d.amount == null) return null;
  const q = fluidQuantity(d);
  if (d.amount_max != null) {
    const [lo, hi] = [formatQuantity(d.amount, q, units, 1, true), formatQuantity(d.amount_max, q, units, 1, true)];
    return `${lo.split(" ")[0]}–${hi}`; // "2.0–2.1 qt"
  }
  return formatQuantity(d.amount, q, units, 1, true);
}

export function specValue(d: D, units: UnitSystem): string {
  if (d.value == null) return d.text ?? "";
  const q = d.quantity as string;
  // Small lengths (gaps, clearances) need thousandths of an inch.
  const digits = q === "length" ? (units === "imperial" && d.value < 5 ? 3 : 2) : 1;
  const fmt = (v: number) =>
    CONVERTIBLE.has(q) ? formatQuantity(v, q as Quantity, units, digits, q === "length") : `${v} ${FIXED_UNITS[q] ?? d.unit_other ?? ""}`.trim();
  const main = d.value_max != null ? `${fmt(d.value)} – ${fmt(d.value_max)}` : fmt(d.value);
  return d.text ? `${main} (${d.text})` : main;
}

export function torqueValue(d: D, units: UnitSystem): string {
  const first = d.stages?.[0];
  if (!first?.value_nm) return "";
  const rest = (d.stages as D[]).slice(1).map((s) => (s.type === "angle" ? ` + ${s.degrees}°` : ` → ${formatQuantity(s.value_nm, "torque", units, 0)}`));
  return formatQuantity(first.value_nm, "torque", units, 0) + rest.join("");
}

/** Short value text for any spec-like entry. */
export function entryValue(kind: string, d: D | null | undefined, units: UnitSystem): string | null {
  if (!d) return null;
  switch (kind) {
    case "fluid_capacity": {
      return fluidAmount(d, units) ?? "—";
    }
    case "spec":
      return specValue(d, units);
    case "torque_spec":
      return torqueValue(d, units);
    case "part_note":
      return (d.oem_numbers as string[] | undefined)?.join(", ") || null;
    default:
      return null;
  }
}

/** "2015 Ford F-150 3.5L EcoBoost — Engine oil" -> "Engine oil" */
export function shortTitle(title: string): string {
  const i = title.lastIndexOf(" — ");
  return i >= 0 ? title.slice(i + 3) : title;
}

const FLUID_ORDER = ["engine_oil", "coolant", "automatic_transmission", "cvt", "manual_transmission", "transfer_case",
  "front_differential", "rear_differential", "brake", "power_steering", "refrigerant", "refrigerant_oil", "fuel_tank", "washer", "other"];

/** Shop order for spec lists: this vehicle's specs first, fluids in service order, then by name. */
export function specSortKey(e: { kind: string; title: string; generic?: boolean; data?: Record<string, any> | null }): string { // eslint-disable-line @typescript-eslint/no-explicit-any
  const fluid = e.kind === "fluid_capacity" ? FLUID_ORDER.indexOf(e.data?.system ?? "other") : 99;
  return `${e.generic ? 1 : 0}-${String(fluid < 0 ? 98 : fluid).padStart(2, "0")}-${shortTitle(e.title).toLowerCase()}`;
}
