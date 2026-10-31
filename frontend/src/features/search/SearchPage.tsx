import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { rememberVehicle } from "../../lib/recent";
import type { Kind, Vehicle } from "../../lib/types";
import { useDocumentTitle } from "../../lib/title";
import { SEVERITY_STYLE } from "../codes/CodeSearch";

type Results = {
  query: string;
  vin: { vin: string; check_digit_valid: boolean } | null;
  codes: { code: string; title: string | null; severity: "low" | "medium" | "high" | null }[];
  vehicles: { model_id: number; make: string; model: string; year: number | null; years: number[] }[];
  entries: { id: number; kind: Kind; title: string; safety_critical: boolean; verified: boolean }[];
  recalls: { campaign_number: string; component: string | null; summary: string; report_date: string | null; park_it: boolean; park_outside: boolean }[];
  tsbs: { nhtsa_id: number; bulletin_number: string | null; date: string | null; summary: string }[];
  vehicle?: Vehicle;
};

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-xl font-bold">{title}</h2>
      <ul className="divide-y-2 divide-slate-200 rounded-2xl border-2 border-slate-200 dark:divide-slate-800 dark:border-slate-800">{children}</ul>
    </section>
  );
}

const rowCls = "flex min-h-16 flex-col justify-center px-4 py-3";

export default function SearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const vehicleId = params.get("vehicle_id");
  const [q, setQ] = useState(params.get("q") ?? "");
  const [res, setRes] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle(t("search.title"));

  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setRes(null);
      return;
    }
    const ctrl = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      const p = new URLSearchParams({ q: query });
      if (vehicleId) p.set("vehicle_id", vehicleId);
      try {
        setRes(await api<Results>(`/search?${p}`, { signal: ctrl.signal }));
        setParams((old) => {
          const next = new URLSearchParams(old);
          next.set("q", query);
          return next;
        }, { replace: true });
      } catch (e) {
        if ((e as Error).name !== "AbortError") setError(errorMessage(t, e));
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [q, vehicleId, t, setParams]);

  async function openVehicle(modelId: number, year: number) {
    try {
      const v = await api<Vehicle>("/vehicles", { method: "POST", body: { year, model_id: modelId } });
      rememberVehicle(v);
      navigate(`/vehicle/${v.id}`);
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  const empty = res && !res.vin && !res.codes.length && !res.vehicles.length && !res.entries.length && !res.recalls.length && !res.tsbs.length;

  return (
    <div className="space-y-5">
      <PageTitle>{t("search.title")}</PageTitle>
      {res?.vehicle && (
        <Alert kind="info">
          <p className="font-bold">{t("search.within", { vehicle: res.vehicle.label })}</p>
          <button type="button" className="min-h-12 font-semibold underline" onClick={() => setParams({ q })}>
            {t("search.clearVehicle")}
          </button>
        </Alert>
      )}
      <div>
        <Label htmlFor="search-q">{t("search.label")}</Label>
        <Input id="search-q" type="search" autoFocus autoCorrect="off" spellCheck={false} value={q} placeholder={t("search.placeholder")} onChange={(e) => setQ(e.target.value)} />
        {!q && <p className="mt-2 text-base text-slate-600 dark:text-slate-400">{t("search.hint")}</p>}
      </div>
      {error && <Alert>{error}</Alert>}
      {loading && !res && <Spinner label={t("search.searching")} />}
      {empty && <p className="text-lg">{t("search.noResults", { q: res.query })}</p>}

      {res?.vin && (
        <Card>
          <p className="font-semibold">{t("search.vin")}</p>
          <p className="mb-3 font-mono text-xl">{res.vin.vin}</p>
          <LinkButton to={`/?vin=${res.vin.vin}`} className="w-full">{t("search.decodeVin")}</LinkButton>
        </Card>
      )}

      {res && res.codes.length > 0 && (
        <Group title={t("search.codes")}>
          {res.codes.map((c) => (
            <li key={c.code}>
              <Link to={`/codes/${c.code}`} className="flex min-h-16 items-center gap-3 px-4 py-2">
                <span className="w-20 shrink-0 font-mono text-lg font-bold">{c.code}</span>
                <span className="flex-1 text-lg">{c.title ?? t("search.unknownCode")}</span>
                {c.severity && <span className={`size-3 shrink-0 rounded-full ${SEVERITY_STYLE[c.severity]}`} aria-label={t(`codes.severity.${c.severity}`)} />}
              </Link>
            </li>
          ))}
        </Group>
      )}

      {res && res.vehicles.length > 0 && (
        <Group title={t("search.vehicles")}>
          {res.vehicles.map((v) => (
            <li key={v.model_id} className="px-4 py-3">
              {v.year ? (
                <Button variant="secondary" className="w-full justify-start" onClick={() => openVehicle(v.model_id, v.year!)}>
                  {v.year} {v.make} {v.model}
                </Button>
              ) : (
                <>
                  <p className="text-lg font-bold">{v.make} {v.model}</p>
                  <p className="text-base">{t("search.pickYear")}</p>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {v.years.slice(0, 16).map((y) => (
                      <button key={y} type="button" onClick={() => openVehicle(v.model_id, y)} className="min-h-12 min-w-16 rounded-lg border-2 border-slate-300 px-3 font-bold dark:border-slate-600">
                        {y}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </li>
          ))}
        </Group>
      )}

      {res && res.entries.length > 0 && (
        <Group title={t("search.entries")}>
          {res.entries.map((e) => (
            <li key={e.id}>
              <Link to={`/entries/${e.id}`} className={rowCls}>
                <span className="text-sm font-semibold uppercase text-amber-700 dark:text-amber-400">{t(`kinds.${e.kind}`)}</span>
                <span className="flex flex-wrap items-center gap-2 text-lg font-bold">
                  {e.verified && <span className="rounded bg-green-700 px-2 text-sm text-white">✓</span>}
                  {e.safety_critical && <span aria-hidden="true">⚠</span>}
                  {e.title}
                </span>
              </Link>
            </li>
          ))}
        </Group>
      )}

      {res && res.recalls.length > 0 && (
        <Group title={t("search.recalls")}>
          {res.recalls.map((r) => (
            <li key={r.campaign_number} className={rowCls}>
              <span className="font-mono font-bold">{r.campaign_number} · {formatDate(r.report_date)}</span>
              <span className="text-lg font-bold">{r.component}</span>
              <span className="text-base">{r.summary}</span>
            </li>
          ))}
        </Group>
      )}

      {res && res.tsbs.length > 0 && (
        <Group title={t("search.tsbs")}>
          {res.tsbs.map((b) => (
            <li key={b.nhtsa_id} className={rowCls}>
              <span className="font-mono font-bold">{b.bulletin_number} · {formatDate(b.date)}</span>
              <span className="text-base">{b.summary}</span>
            </li>
          ))}
        </Group>
      )}
    </div>
  );
}
