import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Input, Label, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { EngineFamily } from "../../lib/types";

const FILTERS = ["", "light_duty", "heavy_duty"] as const;

export default function EnginesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("engines.title"));
  const [q, setQ] = useState("");
  const [app, setApp] = useState<(typeof FILTERS)[number]>("");
  const [rows, setRows] = useState<EngineFamily[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      const p = new URLSearchParams();
      if (q.trim()) p.set("q", q.trim());
      if (app) p.set("application", app);
      api<EngineFamily[]>(`/engines?${p}`, { signal: ctrl.signal })
        .then(setRows)
        .catch((e) => e.name !== "AbortError" && setError(errorMessage(t, e)));
    }, 200);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [q, app, t]);

  const groups = new Map<string, EngineFamily[]>();
  rows?.forEach((r) => groups.set(r.manufacturer, [...(groups.get(r.manufacturer) ?? []), r]));

  return (
    <div className="space-y-4">
      <PageTitle>{t("engines.title")}</PageTitle>
      <p className="text-lg">{t("engines.intro")}</p>
      <div>
        <Label htmlFor="eng-q">{t("engines.searchLabel")}</Label>
        <Input id="eng-q" type="search" value={q} placeholder={t("engines.searchPlaceholder")} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div role="group" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {FILTERS.map((f) => (
          <button key={f || "all"} type="button" aria-pressed={app === f} onClick={() => setApp(f)}
            className={`min-h-12 shrink-0 rounded-full border-2 px-4 font-bold ${app === f ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-300 dark:border-slate-700"}`}>
            {f ? t(`engines.apps.${f}`) : t("engines.filterAll")}
          </button>
        ))}
      </div>
      {error && <Alert>{error}</Alert>}
      {!rows && !error && <Spinner label={t("app.loading")} />}
      {[...groups.entries()].map(([mfr, list]) => (
        <section key={mfr}>
          <h2 className="mb-2 text-xl font-bold">{mfr}</h2>
          <ul className="divide-y-2 divide-slate-200 rounded-2xl border-2 border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {list.map((e) => (
              <li key={e.id}>
                <Link to={`/engines/${e.id}`} className="flex min-h-16 flex-col justify-center px-4 py-2">
                  <span className="text-lg font-bold">{e.name}</span>
                  <span className="text-base text-slate-600 dark:text-slate-400">
                    {e.codes ? `${e.codes} · ` : ""}
                    {t("engines.vehicles", { count: e.vehicle_count ?? 0 })}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
