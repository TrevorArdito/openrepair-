// Everything is stored in metric (SI) and converted only for display.

export type UnitSystem = "metric" | "imperial";
export type Quantity = "torque" | "volume" | "volume_ml" | "volume_gal" | "pressure" | "length" | "temperature" | "mass" | "mass_g";

const IMPERIAL: Record<Quantity, { unit: string; from: (si: number) => number; to: (v: number) => number }> = {
  torque: { unit: "lb·ft", from: (nm) => nm * 0.737562149, to: (v) => v / 0.737562149 },
  volume: { unit: "qt", from: (l) => l * 1.056688209, to: (v) => v / 1.056688209 },
  pressure: { unit: "psi", from: (kpa) => kpa * 0.145037738, to: (v) => v / 0.145037738 },
  length: { unit: "in", from: (mm) => mm / 25.4, to: (v) => v * 25.4 },
  temperature: { unit: "°F", from: (c) => (c * 9) / 5 + 32, to: (f) => ((f - 32) * 5) / 9 },
  mass: { unit: "lb", from: (kg) => kg * 2.204622622, to: (v) => v / 2.204622622 },
  mass_g: { unit: "oz", from: (g) => g / 28.349523125, to: (v) => v * 28.349523125 },
  volume_ml: { unit: "fl oz", from: (ml) => ml / 29.5735295625, to: (v) => v * 29.5735295625 },
  volume_gal: { unit: "gal", from: (l) => l / 3.785411784, to: (v) => v * 3.785411784 },
};
const METRIC_UNIT: Record<Quantity, string> = {
  torque: "N·m",
  volume: "L",
  pressure: "kPa",
  length: "mm",
  temperature: "°C",
  mass: "kg",
  mass_g: "g",
  volume_ml: "mL",
  volume_gal: "L",
};

export function convert(si: number, q: Quantity, system: UnitSystem): { value: number; unit: string } {
  if (system === "metric") return { value: si, unit: METRIC_UNIT[q] };
  return { value: IMPERIAL[q].from(si), unit: IMPERIAL[q].unit };
}

export function toSI(value: number, q: Quantity, system: UnitSystem): number {
  return system === "metric" ? value : IMPERIAL[q].to(value);
}

export function formatQuantity(si: number, q: Quantity, system: UnitSystem, digits = 1, fixed = false): string {
  const { value, unit } = convert(si, q, system);
  // fixed=true keeps trailing zeros (".030 in", "6.0 qt") the way manuals print them.
  const text = fixed ? value.toFixed(digits) : String(Number(value.toFixed(digits)));
  return `${text} ${unit}`;
}

/** Units that are the same in both systems (volts, ohms, ...). */
export const FIXED_UNITS: Record<string, string> = {
  voltage: "V",
  resistance: "Ω",
  current: "A",
  speed_rpm: "rpm",
  percent: "%",
  time_s: "s",
};

export const CONVERTIBLE = new Set<string>(["length", "pressure", "temperature", "mass", "volume"]);

export function unitFor(q: Quantity, system: UnitSystem): string {
  return convert(1, q, system).unit;
}
