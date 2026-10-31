// Turn nested JSON into "path: value" lines so two versions can be compared line by line.

export function flatten(value: unknown, prefix = ""): string[] {
  if (value === null || value === undefined || value === "") return [];
  if (Array.isArray(value)) return value.flatMap((v, i) => flatten(v, `${prefix}[${i + 1}]`));
  if (typeof value === "object")
    return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) => flatten(v, prefix ? `${prefix}.${k}` : k));
  return [`${prefix}: ${String(value)}`];
}

export function diffLines(before: string[], after: string[]) {
  const a = new Set(before);
  const b = new Set(after);
  return { removed: before.filter((l) => !b.has(l)), added: after.filter((l) => !a.has(l)) };
}
