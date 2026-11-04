import { describe, expect, it } from "vitest";
import { convert, formatQuantity, toSI } from "./units";

describe("unit conversion", () => {
  it("torque N·m <-> lb·ft", () => {
    expect(formatQuantity(100, "torque", "imperial")).toBe("73.8 lb·ft");
    expect(formatQuantity(100, "torque", "metric")).toBe("100 N·m");
    expect(toSI(73.756, "torque", "imperial")).toBeCloseTo(100, 2);
  });
  it("volume L <-> US quarts", () => {
    expect(convert(4.7, "volume", "imperial").value).toBeCloseTo(4.97, 2);
  });
  it("temperature °C <-> °F", () => {
    expect(formatQuantity(100, "temperature", "imperial", 0)).toBe("212 °F");
    expect(toSI(32, "temperature", "imperial")).toBe(0);
  });
  it("pressure kPa <-> psi", () => {
    expect(convert(240, "pressure", "imperial").value).toBeCloseTo(34.8, 1);
  });
});
