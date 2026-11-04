import { describe, expect, it } from "vitest";
import { checkDigitValid, normalizeVin, vinProblem } from "./vin";

describe("VIN checks (match the backend rules)", () => {
  it("normalizes spaces, dashes and case", () => {
    expect(normalizeVin(" 1hgcm8-2633a 004352 ")).toBe("1HGCM82633A004352");
  });
  it("accepts valid check digits including X", () => {
    expect(checkDigitValid("1HGCM82633A004352")).toBe(true);
    expect(checkDigitValid("1M8GDM9AXKP042788")).toBe(true);
  });
  it("detects a typo via the check digit", () => {
    expect(checkDigitValid("1HGCM82643A004352")).toBe(false);
  });
  it("explains what's wrong", () => {
    expect(vinProblem("1HGCM82633A00435")).toBe("vin_wrong_length");
    expect(vinProblem("1HGCM82633A00435O")).toBe("vin_invalid_letters");
    expect(vinProblem("1HGCM82633A00435!")).toBe("vin_invalid_characters");
    expect(vinProblem("1HGCM82633A004352")).toBeNull();
  });
});
