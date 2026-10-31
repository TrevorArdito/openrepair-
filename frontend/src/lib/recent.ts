import { load, save } from "./storage";
import type { Vehicle } from "./types";

const KEY = "cc.recentVehicles";
const MAX = 12;
export type RecentVehicle = Pick<Vehicle, "id" | "label">;

export function recentVehicles(): RecentVehicle[] {
  return load<RecentVehicle[]>(KEY, []);
}

export type RecentEntry = { id: number; title: string; kind: string };
const ENTRY_KEY = "cc.recentEntries";

export function recentEntries(): RecentEntry[] {
  return load<RecentEntry[]>(ENTRY_KEY, []);
}

export function rememberEntry(e: RecentEntry): void {
  const list = recentEntries().filter((r) => r.id !== e.id);
  save(ENTRY_KEY, [{ id: e.id, title: e.title, kind: e.kind }, ...list].slice(0, MAX));
}

export function rememberVehicle(v: RecentVehicle): void {
  const list = recentVehicles().filter((r) => r.id !== v.id);
  save(KEY, [{ id: v.id, label: v.label }, ...list].slice(0, MAX));
}
