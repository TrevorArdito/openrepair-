import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Card, LinkButton, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { usePrefs } from "../../lib/prefs";
import type { EntrySummary, Kind } from "../../lib/types";
import { entryValue, shortTitle, specSortKey } from "./specFormat";

/** Guides or specs for a vehicle (vehicle-specific first, then general ones). */
export default function EntryList({ vehicleId, kinds, addKind }: { vehicleId: string; kinds: Kind[]; addKind: Kind | null }) {
  const { t } = useTranslation();
  const { units } = usePrefs();
  const [items, setItems] = useState<EntrySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = kinds.join(",");

  useEffect(() => {
    const params = new URLSearchParams({ vehicle_id: vehicleId, limit: "100" });
    key.split(",").forEach((k) => params.append("kind", k));
    api<{ items: EntrySummary[] }>(`/entries?${params}`).then((r) => setItems(r.items)).catch((e) => setError(errorMessage(t, e)));
  }, [vehicleId, key, t]);

  if (error) return <Alert>{error}</Alert>;
  if (!items) return <Spinner label={t("app.loading")} />;
  const grouped = kinds
    .map((k) => {
      const list = items.filter((i) => i.kind === k);
      if (k !== "procedure") list.sort((a, b) => specSortKey(a).localeCompare(specSortKey(b)));
      return [k, list] as const;
    })
    .filter(([, list]) => list.length);

  return (
    <div className="space-y-4">
      <LinkButton to={`/entries/new?vehicle_id=${vehicleId}${addKind ? `&kind=${addKind}` : ""}`} className="w-full">
        + {addKind === "procedure" ? t("entry.addGuide") : t("entry.addSpec")}
      </LinkButton>
      {items.length === 0 && (
        <Card>
          <p className="text-lg">{t("entry.none")}</p>
        </Card>
      )}
      {grouped.map(([k, list]) => (
        <section key={k}>
          {kinds.length > 1 && <h2 className="mb-2 text-xl font-bold">{t(`kindsPlural.${k}`)}</h2>}
          <ul className="divide-y-2 divide-slate-200 rounded-2xl border-2 border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {list.map((e) => {
              const value = entryValue(e.kind, e.data, units);
              return (
                <li key={e.id}>
                  {value ? (
                    // Spec row: name on the left, value on the right (like a spec table).
                    <Link to={`/entries/${e.id}`} className="flex min-h-14 items-center gap-3 px-4 py-2">
                      <span className="flex-1">
                        <span className="block text-lg font-semibold">
                          {e.verified && <span className="mr-1 text-green-600" aria-label={t("entry.verified")}>✓</span>}
                          {shortTitle(e.title)}
                          {e.generic && <span className="ml-2 rounded bg-slate-200 px-2 text-sm font-semibold text-slate-800 dark:bg-slate-700 dark:text-slate-100">{t("entry.generalBadge")}</span>}
                        </span>
                        {e.data?.fluid_spec && <span className="block text-base text-slate-600 dark:text-slate-400">{e.data.fluid_spec}</span>}
                        {e.data?.amount == null && e.data?.condition && <span className="block text-base text-slate-600 dark:text-slate-400">{e.data.condition}</span>}
                      </span>
                      <span className="max-w-[45%] text-right font-mono text-lg font-bold">{value}</span>
                    </Link>
                  ) : (
                    <Link to={`/entries/${e.id}`} className="flex min-h-16 flex-col justify-center px-4 py-3">
                      <span className="flex flex-wrap items-center gap-2 text-lg font-bold">
                        {e.verified && <span className="rounded bg-green-700 px-2 text-sm text-white">✓ {t("entry.verified")}</span>}
                        {e.safety_critical && <span aria-hidden="true">⚠</span>}
                        {e.title}
                        {e.generic && <span className="rounded bg-slate-200 px-2 text-sm font-semibold text-slate-800 dark:bg-slate-700 dark:text-slate-100">{t("entry.generalBadge")}</span>}
                      </span>
                      {e.summary && <span className="text-base text-slate-600 dark:text-slate-400">{e.summary}</span>}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
