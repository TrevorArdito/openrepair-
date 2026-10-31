import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Button, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import type { Revision } from "../../lib/types";

type Queue = {
  pending_revisions: (Revision & { entry_id: number; kind: string })[];
  reports: { id: number; entry_id: number; reason: string; details: string | null; reporter: { display_name: string }; created_at: string }[];
};

export default function ModPage() {
  const { t } = useTranslation();
  const [q, setQ] = useState<Queue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<Queue>("/mod/queue").then(setQ).catch((e) => setError(errorMessage(t, e))), [t]);
  useEffect(() => void load(), [load]);
  const act = (path: string) => api(path, { method: "POST" }).then(load).catch((e) => setError(errorMessage(t, e)));

  if (error) return <Alert>{error}</Alert>;
  if (!q) return <Spinner label={t("app.loading")} />;
  return (
    <div className="space-y-5">
      <PageTitle>{t("mod.title")}</PageTitle>
      <h2 className="text-2xl font-bold">{t("mod.pending")} ({q.pending_revisions.length})</h2>
      {q.pending_revisions.length === 0 && <p>{t("mod.empty")}</p>}
      {q.pending_revisions.map((r) => (
        <Card key={r.id} className="space-y-2">
          <p className="font-semibold uppercase text-amber-700 dark:text-amber-400">{t(`kinds.${r.kind}`)} · v{r.number}</p>
          <h3 className="text-xl font-bold">{r.title}</h3>
          <p>{t("mod.by", { name: r.author.display_name })} · {formatDate(r.created_at)}</p>
          {r.edit_summary && <p>“{r.edit_summary}”</p>}
          <pre className="max-h-64 overflow-auto rounded-lg bg-slate-100 p-2 text-sm dark:bg-slate-900">{JSON.stringify(r.data, null, 2)}</pre>
          <div className="grid grid-cols-3 gap-2">
            <Button onClick={() => act(`/mod/revisions/${r.id}/approve`)}>{t("mod.approve")}</Button>
            <Button variant="danger" onClick={() => act(`/mod/revisions/${r.id}/reject`)}>{t("mod.reject")}</Button>
            <Link to={`/entries/${r.entry_id}/history`} className="inline-flex min-h-14 items-center justify-center rounded-xl border-2 border-slate-400 font-bold">{t("mod.view")}</Link>
          </div>
        </Card>
      ))}
      <h2 className="text-2xl font-bold">{t("mod.reports")} ({q.reports.length})</h2>
      {q.reports.length === 0 && <p>{t("mod.empty")}</p>}
      {q.reports.map((r) => (
        <Card key={r.id} className="space-y-2">
          <p className="font-bold">{t(`entry.reportReasons.${r.reason}`)} · {t("mod.by", { name: r.reporter.display_name })} · {formatDate(r.created_at)}</p>
          {r.details && <p className="whitespace-pre-line">{r.details}</p>}
          <div className="grid grid-cols-3 gap-2">
            <Link to={`/entries/${r.entry_id}`} className="inline-flex min-h-14 items-center justify-center rounded-xl border-2 border-slate-400 font-bold">{t("mod.view")}</Link>
            <Button onClick={() => act(`/mod/reports/${r.id}/resolve`)}>{t("mod.resolve")}</Button>
            <Button variant="secondary" onClick={() => act(`/mod/reports/${r.id}/dismiss`)}>{t("mod.dismiss")}</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
