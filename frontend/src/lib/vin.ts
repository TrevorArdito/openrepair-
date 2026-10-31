// Same rules as the backend (backend/app/modules/vehicles/vin.py), so people get
// instant feedback while typing — before anything is sent to the server.

const VALUES: Record<string, number> = {
  A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8,
  J: 1, K: 2, L: 3, M: 4, N: 5, P: 7, R: 9,
  S: 2, T: 3, U: 4, V: 5, W: 6, X: 7, Y: 8, Z: 9,
};
const WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2];

export function normalizeVin(raw: string): string {
  return raw.replace(/[\s-]/g, "").toUpperCase();
}

export type VinProblem = "vin_wrong_length" | "vin_invalid_letters" | "vin_invalid_characters";

export function vinProblem(vin: string): VinProblem | null {
  if (/[IOQ]/.test(vin)) return "vin_invalid_letters";
  if (!/^[A-HJ-NPR-Z0-9]*$/.test(vin)) return "vin_invalid_characters";
  if (vin.length !== 17) return "vin_wrong_length";
  return null;
}

export function checkDigitValid(vin: string): boolean {
  if (vinProblem(vin)) return false;
  let total = 0;
  for (let i = 0; i < 17; i++) {
    const c = vin[i];
    const v = /\d/.test(c) ? Number(c) : VALUES[c];
    total += v * WEIGHTS[i];
  }
  const r = total % 11;
  return (r === 10 ? "X" : String(r)) === vin[8];
}
