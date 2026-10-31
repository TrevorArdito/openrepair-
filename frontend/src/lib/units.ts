// Everything is stored in metric (SI) and converted only for display.

export type UnitSystem = "metric" | "imperial";
export type Quantity = "torque" | "volume" | "pressure" | "length" | "temperature" | "mass";

const IMPERIAL: Record<Quantity, { unit: string; from: (si: number) => number; to: (v: number) => number }> = {
  torque: { unit: "lb·ft", from: (nm) => nm * 0.737562149, to: (v) => v / 0.737562149 },
  volume: { unit: "qt", from: (l) => l * 1.056688209, to: (v) => v / 1.056688209 },
  pressure: { unit: "psi", from: (kpa) => kpa * 0.145037738, to: (v) => v / 0.145037738 },
  length: { unit: "in", from: (mm) => mm / 25.4, to: (v) => v * 25.4 },
  temperature: { unit: "°F", from: (c) => (c * 9) / 5 + 32, to: (f) => ((f - 32) * 5) / 9 },
  mass: { unit: "lb", from: (kg) => kg * 2.204622622, to: (v) => v / 2.204622622 },
};
const METRIC_UNIT: Record<Quantity, string> = {
  torque: "N·m",
  volume: "L",
  pressure: "kPa",
  length: "mm",
  temperature: "°C",
  mass: "kg",
};

export function convert(si: number, q: Quantity, system: UnitSystem): { value: number; unit: string } {
  if (system === "metric") return { value: si, unit: METRIC_UNIT[q] };
  return { value: IMPERIAL[q].from(si), unit: IMPERIAL[q].unit };
}

export function toSI(value: number, q: Quantity, system: UnitSystem): number {
  return system === "metric" ? value : IMPERIAL[q].to(value);
}

export function formatQuantity(si: number, q: Quantity, system: UnitSystem, digits = 1): string {
  const { value, unit } = convert(si, q, system);
  const rounded = Number(value.toFixed(digits));
  return `${rounded} ${unit}`;
}
