import { load, save } from "./storage";
import type { Vehicle } from "./types";

const KEY = "cc.recentVehicles";
const MAX = 12;
export type RecentVehicle = Pick<Vehicle, "id" | "label">;

export function recentVehicles(): RecentVehicle[] {
  return load<RecentVehicle[]>(KEY, []);
}

export function rememberVehicle(v: RecentVehicle): void {
  const list = recentVehicles().filter((r) => r.id !== v.id);
  save(KEY, [{ id: v.id, label: v.label }, ...list].slice(0, MAX));
}
