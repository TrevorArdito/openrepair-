import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import ExpandableText from "../../components/ExpandableText";
import { Alert, Button, Card, Input, Spinner } from "../../components/ui";
import { formatDate } from "../../lib/format";
import type { Complaint, ComplaintList, Recall, RecallList, Tsb, TsbList } from "../../lib/types";
import { useSafetyList } from "./useSafetyList";

function Badge({ tone, children }: { tone: "red" | "amber" | "slate"; children: ReactNode }) {
  const tones = {
    red: "bg-red-700 text-white",
    amber: "bg-amber-400 text-slate-950",
    slate: "bg-slate-200 text-slate-900 dark:bg-slate-700 dark:text-slate-50",
  };
  return <span className={`inline-block rounded-md px-2 py-1 text-base font-bold ${tones[tone]}`}>{children}</span>;
}

function Shell({
  q,
  setQ,
  data,
  error,
  loading,
  count,
  empty,
  hasMore,
  more,
  note,
  children,
}: {
  q: string;
  setQ: (s: string) => void;
  data: { total: number; source_url: string; stale: boolean } | null;
  error: string | null;
  loading: boolean;
  count: string;
  empty: string;
  hasMore: boolean;
  more: () => void;
  note?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="safety-filter" className="sr-only">
          {t("safety.filterLabel")}
        </label>
        <Input id="safety-filter" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("safety.filterPlaceholder")} />
      </div>
      {data?.stale && <Alert kind="warning">{t("safety.stale")}</Alert>}
      {error && <Alert>{error}</Alert>}
      {data && (
        <p className="text-lg font-bold" aria-live="polite">
          {count}
        </p>
      )}
      {note}
      {data && data.total === 0 && !loading && (
        <Card>
          <p>{empty}</p>
        </Card>
      )}
      {children}
      {loading && <Spinner label={t("safety.loading")} />}
      {hasMore && !loading && (
        <Button variant="secondary" className="w-full" onClick={more}>
          {t("safety.showMore")}
        </Button>
      )}
      {data && (
        <p className="text-base text-slate-600 dark:text-slate-400">
          {t("safety.source")} ·{" "}
          <a href={data.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-12 items-center font-semibold underline">
            {t("safety.viewOnNhtsa")}
          </a>
        </p>
      )}
    </div>
  );
}

function RecallCard({ r }: { r: Recall }) {
  const { t } = useTranslation();
  return (
    <Card className={r.park_it || r.park_outside ? "border-red-600 dark:border-red-500" : ""}>
      <div className="mb-2 flex flex-wrap gap-2">
        {r.park_it && <Badge tone="red">{t("safety.parkIt")}</Badge>}
        {r.park_outside && <Badge tone="red">{t("safety.parkOutside")}</Badge>}
        {r.over_the_air && <Badge tone="slate">{t("safety.ota")}</Badge>}
      </div>
      <h3 className="text-xl font-bold">{r.component}</h3>
      <p className="mb-2 font-mono text-base">
        {t("safety.campaign", { number: r.campaign_number })} · {t("safety.reported", { date: formatDate(r.report_date) })}
      </p>
      {r.group === "aftermarket" && r.manufacturer && (
        <p className="mb-2 text-base font-semibold">{t("safety.filedBy", { name: r.manufacturer })}</p>
      )}
      <ExpandableText text={r.summary} />
      {r.consequence && (
        <div className="mt-3">
          <h4 className="font-bold">{t("safety.consequence")}</h4>
          <ExpandableText text={r.consequence} />
        </div>
      )}
      {r.remedy && (
        <div className="mt-3">
          <h4 className="font-bold">{t("safety.remedy")}</h4>
          <ExpandableText text={r.remedy} />
        </div>
      )}
    </Card>
  );
}

/** Recalls that may not apply to this vehicle, collapsed so they don't inflate the count. */
function RecallGroup({ title, hint, items }: { title: string; hint: string; items: Recall[] }) {
  if (items.length === 0) return null;
  return (
    <details className="rounded-xl border-2 border-slate-300 p-3 dark:border-slate-700">
      <summary className="flex min-h-12 cursor-pointer items-center text-lg font-bold">{title}</summary>
      <p className="mb-3 text-base text-slate-600 dark:text-slate-400">{hint}</p>
      <div className="space-y-4">
        {items.map((r) => (
          <RecallCard key={r.campaign_number} r={r} />
        ))}
      </div>
    </details>
  );
}

export function RecallsTab({ vehicleId }: { vehicleId: string }) {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const list = useSafetyList<Recall, RecallList>(vehicleId, "recalls", q);
  const of = (g: Recall["group"]) => list.items.filter((r) => (r.group ?? "maker") === g);
  const others = (list.data?.other_engine ?? 0) + (list.data?.aftermarket ?? 0);
  return (
    <Shell
      q={q}
      setQ={setQ}
      {...list}
      count={t("safety.recallCount", { count: list.data?.total ?? 0 })}
      empty={others ? t("safety.noMakerRecalls") : t("safety.noRecalls")}
    >
      {of("maker").map((r) => (
        <RecallCard key={r.campaign_number} r={r} />
      ))}
      <RecallGroup title={t("safety.otherEngineRecalls", { count: of("other_engine").length })} hint={t("safety.otherEngineHint")} items={of("other_engine")} />
      <RecallGroup title={t("safety.aftermarketRecalls", { count: of("aftermarket").length })} hint={t("safety.aftermarketHint")} items={of("aftermarket")} />
    </Shell>
  );
}

export function ComplaintsTab({ vehicleId }: { vehicleId: string }) {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const list = useSafetyList<Complaint, ComplaintList>(vehicleId, "complaints", q);
  const top = Object.entries(list.data?.components ?? {}).slice(0, 6);
  return (
    <Shell
      q={q}
      setQ={setQ}
      {...list}
      count={t("safety.complaintCount", { count: list.data?.total ?? 0 })}
      empty={t("safety.noComplaints")}
      note={
        top.length > 0 && !q ? (
          <Card>
            <h3 className="mb-2 font-bold">{t("safety.topComponents")}</h3>
            <div className="flex flex-wrap gap-2">
              {top.map(([name, n]) => (
                <button key={name} type="button" onClick={() => setQ(name.split(":")[0].toLowerCase())} className="min-h-12 rounded-full border-2 border-slate-300 px-3 font-semibold dark:border-slate-600">
                  {name} ({n})
                </button>
              ))}
            </div>
          </Card>
        ) : null
      }
    >
      {list.items.map((c) => (
        <Card key={c.odi_number}>
          <div className="mb-1 flex flex-wrap gap-2">
            {c.crash && <Badge tone="red">{t("safety.crash")}</Badge>}
            {c.fire && <Badge tone="red">{t("safety.fire")}</Badge>}
            {c.injuries > 0 && <Badge tone="amber">{t("safety.injuries", { count: c.injuries })}</Badge>}
            {c.deaths > 0 && <Badge tone="red">{t("safety.deaths", { count: c.deaths })}</Badge>}
          </div>
          <h3 className="text-lg font-bold">{c.components}</h3>
          <p className="mb-2 text-base text-slate-600 dark:text-slate-400">{t("safety.filed", { date: formatDate(c.filed_date) })}</p>
          <ExpandableText text={c.summary} />
        </Card>
      ))}
    </Shell>
  );
}

export function TsbsTab({ vehicleId }: { vehicleId: string }) {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const list = useSafetyList<Tsb, TsbList>(vehicleId, "tsbs", q);
  const notImported = list.data && !list.data.last_import;
  return (
    <Shell
      q={q}
      setQ={setQ}
      {...list}
      count={t("safety.tsbCount", { count: list.data?.total ?? 0 })}
      empty={notImported ? t("safety.tsbsNotImported") : t("safety.noTsbs")}
      note={<p className="text-base text-slate-600 dark:text-slate-400">{t("safety.tsbNote")}</p>}
    >
      {list.items.map((b) => (
        <Card key={b.nhtsa_id}>
          <p className="font-mono text-lg font-bold">{b.bulletin_number}</p>
          <p className="mb-2 text-base text-slate-600 dark:text-slate-400">
            {formatDate(b.bulletin_date)}
            {b.comm_type ? ` · ${b.comm_type}` : ""}
          </p>
          {b.components && <p className="mb-1 font-semibold">{b.components}</p>}
          <ExpandableText text={b.summary} />
        </Card>
      ))}
    </Shell>
  );
}
