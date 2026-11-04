import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { diffLines, flatten } from "../../lib/diff";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import type { Entry, Revision } from "../../lib/types";

const asLines = (r: Revision) => flatten({ title: r.title, ...r.data, tags: r.tags });

export default function HistoryPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [entry, setEntry] = useState<Entry | null>(null);
  const [revs, setRevs] = useState<Revision[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<Entry>(`/entries/${id}`), api<Revision[]>(`/entries/${id}/revisions`)])
      .then(([e, r]) => { setEntry(e); setRevs(r); })
      .catch((e) => setError(errorMessage(t, e)));
  }, [id, t]);

  async function restore(n: number) {
    if (!window.confirm(t("history.revertConfirm", { n }))) return;
    try {
      await api(`/entries/${id}/revert/${n}`, { method: "POST" });
      navigate(`/entries/${id}`);
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!entry || !revs) return <Spinner label={t("app.loading")} />;
  const approved = revs.filter((r) => r.status === "approved");
  const canRevert = !!user && ["pro", "moderator", "admin"].includes(user.role);

  return (
    <div className="space-y-4">
      <PageTitle>{t("history.title", { title: entry.title })}</PageTitle>
      <Link to={`/entries/${id}`} className="font-bold underline">← {entry.title}</Link>
      {revs.map((r) => {
        const prev = approved.find((p) => p.number < r.number);
        const d = diffLines(prev ? asLines(prev) : [], asLines(r));
        const isCurrent = entry.revision?.id === r.id;
        return (
          <Card key={r.id}>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold">{t("history.version", { n: r.number })}</h2>
              {isCurrent && <span className="rounded bg-green-700 px-2 py-1 text-sm font-bold text-white">{t("history.current")}</span>}
              {r.status === "pending" && <span className="rounded bg-amber-400 px-2 py-1 text-sm font-bold text-slate-950">{t("history.pending")}</span>}
              {r.status === "rejected" && <span className="rounded bg-red-700 px-2 py-1 text-sm font-bold text-white">{t("history.rejected")}</span>}
            </div>
            <p className="text-base text-slate-600 dark:text-slate-400">
              {t("history.by", { name: r.author.display_name })} · {formatDate(r.created_at)}
            </p>
            {r.edit_summary && <p className="mt-1 text-lg">“{r.edit_summary}”</p>}
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => setOpen(open === r.id ? null : r.id)}>
                {open === r.id ? t("history.hideChanges") : t("history.showChanges")}
              </Button>
              {canRevert && !isCurrent && r.status === "approved" && (
                <Button variant="secondary" onClick={() => restore(r.number)}>{t("history.revert")}</Button>
              )}
            </div>
            {open === r.id && (
              <div className="mt-3 space-y-1 font-mono text-base">
                {d.added.length + d.removed.length === 0 && <p>{t("history.noChanges")}</p>}
                {d.removed.map((l) => (
                  <p key={`-${l}`} className="break-words rounded bg-red-100 px-2 text-red-900 dark:bg-red-950 dark:text-red-200">− {l}</p>
                ))}
                {d.added.map((l) => (
                  <p key={`+${l}`} className="break-words rounded bg-green-100 px-2 text-green-900 dark:bg-green-950 dark:text-green-200">+ {l}</p>
                ))}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
