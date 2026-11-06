import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useModule } from "../lib/modules";

const NAV: { to: string; key: string; icon: string; module?: string }[] = [
  { to: "/", key: "home", icon: "M3 11 12 3l9 8v10h-6v-6H9v6H3z" },
  { to: "/garage", key: "garage", icon: "M3 21V9l9-6 9 6v12M7 21v-6h10v6M7 17h10" },
  { to: "/codes", key: "codes", icon: "M4 6h16M4 12h10M4 18h7M17 15l3 3-3 3" },
  { to: "/search", key: "search", icon: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5" },
  { to: "/market", key: "parts", icon: "M3 7h18l-2 13H5zM8 7V5a4 4 0 0 1 8 0v2", module: "marketplace" },
  { to: "/account", key: "account", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" },
];

function useOnline() {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

export default function Layout() {
  const { t } = useTranslation();
  const online = useOnline();
  const market = useModule("marketplace");
  const nav = NAV.filter((n) => !n.module || (n.module === "marketplace" && market));
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:p-3">
        {t("app.skipToContent")}
      </a>
      <header className="sticky top-0 z-10 border-b-2 border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-4 px-4 md:h-16 lg:max-w-5xl">
          {/* Long name: stacked so it fits next to the menu on every screen size. */}
          <Link to="/" aria-label={t("app.name")} className="flex min-w-0 shrink-0 items-center gap-2">
            <img src="/icon.svg" alt="" className="size-8 shrink-0" />
            <span className="leading-tight" aria-hidden="true">
              <span className="block text-xl font-extrabold">{t("app.shortName")}</span>
              <span className="block text-sm font-semibold text-slate-600 dark:text-slate-400">{t("app.nameRest")}</span>
            </span>
          </Link>
          {/* Wide screens: the main menu sits up here instead of the bottom tab bar. */}
          <nav aria-label="Main" className="hidden lg:block">
            <ul className="flex items-center gap-1">
              {nav.map((n) => (
                <li key={n.to}>
                  <NavLink
                    to={n.to}
                    end={n.to === "/"}
                    className={({ isActive }) =>
                      `flex min-h-12 items-center gap-2 rounded-lg px-2 text-base font-semibold xl:px-3 ${
                        isActive ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                      }`
                    }
                  >
                    <svg viewBox="0 0 24 24" className="hidden size-5 xl:block" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d={n.icon} />
                    </svg>
                    {t(`nav.${n.key}`)}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <Link to="/about" className="flex min-h-12 shrink-0 items-center px-2 font-semibold underline-offset-4 hover:underline">
            {t("nav.about")}
          </Link>
        </div>
        {!online && (
          <div role="status" className="bg-amber-400 px-4 py-2 text-center font-bold text-slate-950">
            {t("app.offline")}
          </div>
        )}
      </header>

      <main id="main" className="mx-auto w-full max-w-3xl flex-1 px-4 pt-5 pb-28 lg:max-w-5xl lg:pb-10">
        <Outlet />
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-10 lg:hidden border-t-2 border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] dark:border-slate-800 dark:bg-slate-950"
      >
        <ul className={`mx-auto grid max-w-3xl ${nav.length > 5 ? "grid-cols-6" : "grid-cols-5"}`}>
          {nav.map((n) => (
            <li key={n.to}>
              <NavLink
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `flex min-h-16 flex-col items-center justify-center gap-1 text-sm font-semibold ${
                    isActive ? "text-amber-600 dark:text-amber-400" : "text-slate-600 dark:text-slate-300"
                  }`
                }
              >
                <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d={n.icon} />
                </svg>
                {t(`nav.${n.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
