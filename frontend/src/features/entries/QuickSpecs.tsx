// ALLDATA-style "common specs" box on the vehicle overview: the numbers techs need most.
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui";
import { api } from "../../lib/api";
import { usePrefs } from "../../lib/prefs";
import type { EntrySummary } from "../../lib/types";
import { entryValue } from "./specFormat";

type Row = { key: string; entry: EntrySummary; value: string; sub?: string };

function pick(items: EntrySummary[]): { key: string; entry: EntrySummary; sub?: (e: EntrySummary) => string | undefined }[] {
  const find = (fn: (e: EntrySummary) => boolean) => items.find(fn);
  const d = (e: EntrySummary) => e.data ?? {};
  const out = [
    { key: "oil", entry: find((e) => e.kind === "fluid_capacity" && d(e).system === "engine_oil"), sub: (e: EntrySummary) => d(e).fluid_spec },
    { key: "coolant", entry: find((e) => e.kind === "fluid_capacity" && d(e).system === "coolant") },
    { key: "atf", entry: find((e) => e.kind === "fluid_capacity" && ["automatic_transmission", "cvt"].includes(d(e).system)), sub: (e: EntrySummary) => d(e).fluid_spec },
    { key: "lug", entry: find((e) => e.kind === "torque_spec" && /lug/i.test(d(e).component ?? "")) },
    { key: "gap", entry: find((e) => e.kind === "spec" && /spark plug gap/i.test(d(e).name ?? "")) },
    { key: "firing", entry: find((e) => e.kind === "spec" && /firing order/i.test(d(e).name ?? "")) },
    { key: "oilFilter", entry: find((e) => e.kind === "part_note" && /oil filter/i.test(d(e).part_name ?? "")) },
  ];
  return out.filter((x): x is { key: string; entry: EntrySummary; sub?: (e: EntrySummary) => string | undefined } => !!x.entry);
}

export default function QuickSpecs({ vehicleId, onShowAll }: { vehicleId: string; onShowAll: () => void }) {
  const { t } = useTranslation();
  const { units } = usePrefs();
  const [rows, setRows] = useState<Row[] | null>(null);

  useEffect(() => {
    const p = new URLSearchParams({ vehicle_id: vehicleId, include_generic: "false", limit: "100" });
    ["fluid_capacity", "torque_spec", "spec", "part_note"].forEach((k) => p.append("kind", k));
    api<{ items: EntrySummary[] }>(`/entries?${p}`)
      .then((r) =>
        setRows(
          pick(r.items).map(({ key, entry, sub }) => ({
            key,
            entry,
            value: entryValue(entry.kind, entry.data, units) ?? "",
            sub: sub?.(entry),
          })),
        ),
      )
      .catch(() => setRows([]));
  }, [vehicleId, units]);

  if (!rows || rows.length === 0) return null; // nothing written for this vehicle yet: no blank box
  return (
    <Card>
      <h2 className="mb-2 text-xl font-bold">{t("vehicle.quickSpecs")}</h2>
      <ul className="divide-y-2 divide-slate-200 dark:divide-slate-800">
        {rows.map((r) => (
          <li key={r.key}>
            <Link to={`/entries/${r.entry.id}`} className="flex min-h-14 items-center gap-3 py-2">
              <span className="flex-1">
                <span className="block text-lg font-semibold">{t(`vehicle.quick.${r.key}`)}</span>
                {r.sub && <span className="block text-base text-slate-600 dark:text-slate-400">{r.sub}</span>}
              </span>
              <span className="max-w-[50%] text-right font-mono text-lg font-bold">{r.value}</span>
            </Link>
          </li>
        ))}
      </ul>
      <button type="button" onClick={onShowAll} className="mt-2 flex min-h-12 items-center font-bold text-amber-700 underline dark:text-amber-400">
        {t("vehicle.allSpecs")}
      </button>
    </Card>
  );
}
