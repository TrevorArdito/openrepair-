import { describe, expect, it } from "vitest";
import { diffLines, flatten } from "./diff";

describe("revision diff", () => {
  it("flattens nested content", () => {
    expect(flatten({ title: "A", steps: [{ text: "x", torque_nm: 50 }] })).toEqual(["title: A", "steps[1].text: x", "steps[1].torque_nm: 50"]);
  });
  it("finds added and removed lines", () => {
    const d = diffLines(flatten({ a: 1, b: 2 }), flatten({ a: 1, b: 3, c: 4 }));
    expect(d.removed).toEqual(["b: 2"]);
    expect(d.added).toEqual(["b: 3", "c: 4"]);
  });
});
