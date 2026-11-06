import { useEffect, useState } from "react";
import { api } from "./api";

// Which optional modules the server has switched on (e.g. "marketplace"). Fetched once.
let cached: Promise<string[]> | null = null;

export function loadModules(): Promise<string[]> {
  cached ??= api<{ modules: string[] }>("/meta")
    .then((m) => m.modules)
    .catch(() => {
      cached = null; // offline: try again next time
      return [];
    });
  return cached;
}

/** "loading" until the server answers, then "on" or "off". */
export function useModuleState(name: string): "loading" | "on" | "off" {
  const [state, setState] = useState<"loading" | "on" | "off">("loading");
  useEffect(() => {
    let live = true;
    void loadModules().then((m) => live && setState(m.includes(name) ? "on" : "off"));
    return () => {
      live = false;
    };
  }, [name]);
  return state;
}

export function useModule(name: string): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let live = true;
    void loadModules().then((m) => live && setOn(m.includes(name)));
    return () => {
      live = false;
    };
  }, [name]);
  return on;
}
