import { describe, expect, it } from "vitest";
import { entryValue, shortTitle, specValue } from "./specFormat";

describe("spec formatting", () => {
  it("shows spark plug gaps in thousandths of an inch", () => {
    expect(specValue({ quantity: "length", value: 0.7, value_max: 0.8 }, "imperial")).toBe("0.028 in – 0.031 in");
    expect(specValue({ quantity: "length", value: 1.25, value_max: 1.35 }, "metric")).toBe("1.25 mm – 1.35 mm");
    expect(specValue({ quantity: "length", value: 0.75, value_max: 0.85 }, "imperial")).toBe("0.030 in – 0.033 in");
  });
  it("shows text specs as-is", () => {
    expect(specValue({ quantity: "other", text: "1-3-7-2-6-5-4-8" }, "imperial")).toBe("1-3-7-2-6-5-4-8");
  });
  it("matches the manual's printed fluid capacities", () => {
    expect(entryValue("fluid_capacity", { system: "engine_oil", amount: 5.7, amount_unit: "L" }, "imperial")).toBe("6.0 qt");
    expect(entryValue("fluid_capacity", { system: "engine_oil", amount: 7.3, amount_unit: "L" }, "imperial")).toBe("7.7 qt");
    expect(entryValue("fluid_capacity", { system: "fuel_tank", amount: 87.1, amount_unit: "L" }, "imperial")).toBe("23.0 gal");
    expect(entryValue("fluid_capacity", { system: "refrigerant", amount: 0.68, amount_unit: "kg" }, "imperial")).toBe("1.5 lb");
    expect(entryValue("fluid_capacity", { system: "rear_differential", amount: 1.9, amount_max: 2.0, amount_unit: "L" }, "imperial")).toBe("2.0–2.1 qt");
    expect(entryValue("fluid_capacity", { system: "brake", condition: "Between MIN and MAX" }, "imperial")).toBe("—");
  });
  it("torque with angle stages and short titles", () => {
    expect(entryValue("torque_spec", { stages: [{ type: "torque", value_nm: 204 }] }, "imperial")).toBe("150 lb·ft");
    expect(entryValue("torque_spec", { stages: [{ type: "torque", value_nm: 30 }, { type: "angle", degrees: 90 }] }, "metric")).toBe("30 N·m + 90°");
    expect(shortTitle("2015 Ford F-150 3.5L EcoBoost — Engine oil")).toBe("Engine oil");
  });
});
