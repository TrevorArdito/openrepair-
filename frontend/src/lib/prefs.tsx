import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { load, save } from "./storage";
import type { UnitSystem } from "./units";

export type Theme = "system" | "light" | "dark";

type Prefs = {
  units: UnitSystem;
  theme: Theme;
  setUnits: (u: UnitSystem) => void;
  setTheme: (t: Theme) => void;
};

const PrefsContext = createContext<Prefs | null>(null);

function applyTheme(theme: Theme) {
  const dark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", !!dark);
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [units, setUnitsState] = useState<UnitSystem>(() => load("cc.units", "imperial"));
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      return (localStorage.getItem("cc.theme") as Theme) || "system";
    } catch {
      return "system";
    }
  });

  useEffect(() => {
    applyTheme(theme);
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme(theme);
    mq?.addEventListener?.("change", onChange);
    return () => mq?.removeEventListener?.("change", onChange);
  }, [theme]);

  const setUnits = useCallback((u: UnitSystem) => {
    setUnitsState(u);
    save("cc.units", u);
  }, []);
  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem("cc.theme", t);
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <PrefsContext.Provider value={{ units, theme, setUnits, setTheme }}>{children}</PrefsContext.Provider>
  );
}

export function usePrefs(): Prefs {
  const ctx = useContext(PrefsContext);
  if (!ctx) throw new Error("usePrefs outside PrefsProvider");
  return ctx;
}
