import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Alert, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { EngineDetail } from "../../lib/types";

function YearPicker({ engineId, modelId }: { engineId: number; modelId: number }) {
  const { t } = useTranslation();
  const [years, setYears] = useState<{ vehicle_id: number; year: number }[] | null>(null);
  useEffect(() => {
    api<{ vehicle_id: number; year: number }[]>(`/engines/${engineId}/vehicles?model_id=${modelId}`).then(setYears).catch(() => setYears([]));
  }, [engineId, modelId]);
  if (!years) return <Spinner label={t("app.loading")} />;
  return (
    <div className="mt-2 flex flex-wrap gap-2" aria-label={t("engines.pickYear")}>
      {years.map((y) => (
        <Link key={y.vehicle_id} to={`/vehicle/${y.vehicle_id}`} className="inline-flex min-h-12 min-w-16 items-center justify-center rounded-lg border-2 border-slate-300 px-3 font-bold dark:border-slate-600">
          {y.year}
        </Link>
      ))}
    </div>
  );
}

export default function EngineDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [e, setE] = useState<EngineDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  useDocumentTitle(e?.name);

  useEffect(() => {
    setE(null);
    api<EngineDetail>(`/engines/${id}`).then(setE).catch((err) => setError(errorMessage(t, err)));
  }, [id, t]);

  if (error) return <Alert>{error}</Alert>;
  if (!e) return <Spinner label={t("app.loading")} />;
  const fact = (label: string, value: string | number | null | undefined) =>
    value === null || value === undefined || value === "" ? null : (
      <>
        <dt className="font-semibold">{label}</dt>
        <dd>{value}</dd>
      </>
    );

  return (
    <div className="space-y-4">
      <p className="font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">{e.manufacturer}</p>
      <PageTitle>{e.name}</PageTitle>
      <div className="flex flex-wrap gap-2">
        {e.applications.map((a) => (
          <span key={a} className="rounded-lg bg-slate-200 px-3 py-1 font-semibold text-slate-900 dark:bg-slate-700 dark:text-slate-50">{t(`engines.apps.${a}`, { defaultValue: a })}</span>
        ))}
      </div>
      <Card>
        <h2 className="mb-2 text-xl font-bold">{t("engines.facts")}</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-lg">
          {fact(t("engines.displacement"), e.displacement_l ? `${e.displacement_l.toFixed(1)} L` : null)}
          {fact(t("engines.cylinders"), e.cylinders)}
          {fact(t("engines.layout"), e.layout ? t(`engines.layouts.${e.layout}`) : null)}
          {fact(t("engines.fuel"), e.fuel_type ? t(`fuel.${e.fuel_type}`) : null)}
          {fact(t("engines.induction"), t(`engines.aspiration.${e.aspiration ?? "none"}`))}
          {fact(t("engines.codes"), e.codes)}
          {fact(t("engines.years"), e.year_from ? t("engines.yearsValue", { from: e.year_from, to: e.year_to ?? t("engines.present") }) : null)}
        </dl>
        {e.notes && <p className="mt-3 text-lg">{e.notes}</p>}
      </Card>
      <section>
        <h2 className="mb-2 text-xl font-bold">
          {t("engines.usedIn")} · {t("engines.vehicles", { count: e.vehicle_count ?? 0 })}
        </h2>
        <ul className="divide-y-2 divide-slate-200 rounded-2xl border-2 border-slate-200 dark:divide-slate-800 dark:border-slate-800">
          {e.used_in.map((u) => (
            <li key={u.model_id} className="px-4 py-3">
              <button type="button" aria-expanded={open === u.model_id} onClick={() => setOpen(open === u.model_id ? null : u.model_id)} className="flex min-h-12 w-full items-center justify-between text-left">
                <span className="text-lg font-bold">{u.make} {u.model}</span>
                <span className="font-mono">{u.year_from === u.year_to ? u.year_from : `${u.year_from}–${u.year_to}`}</span>
              </button>
              {open === u.model_id && <YearPicker engineId={e.id} modelId={u.model_id} />}
            </li>
          ))}
        </ul>
      </section>
      <Alert kind="info">{t("engines.yearsNote")}</Alert>
    </div>
  );
}
