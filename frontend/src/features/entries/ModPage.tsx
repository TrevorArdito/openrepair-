import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Button, Card, Input, Label, PageTitle, Select, Spinner } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import type { Revision } from "../../lib/types";

type Queue = {
  pending_revisions: (Revision & { entry_id: number; kind: string })[];
  reports: { id: number; entry_id: number; reason: string; details: string | null; reporter: { display_name: string }; created_at: string }[];
};

function ReviewQueue() {
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

type UserRow = { id: number; display_name: string; email: string; role: string; status: string; email_verified: boolean; created_at: string };

function ProTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<{ id: number; statement: string; created_at: string; user: UserRow }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<typeof rows>("/mod/pro-requests").then(setRows).catch((e) => setError(errorMessage(t, e))), [t]);
  useEffect(() => void load(), [load]);
  const act = (id: number, action: string) => {
    const note = window.prompt(t("mod.reasonPrompt")) ?? undefined;
    api(`/mod/pro-requests/${id}/${action}`, { method: "POST", body: { note: note || null } }).then(load).catch((e) => setError(errorMessage(t, e)));
  };
  if (error) return <Alert>{error}</Alert>;
  if (!rows) return <Spinner label={t("app.loading")} />;
  if (!rows.length) return <p>{t("mod.empty")}</p>;
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <Card key={r.id} className="space-y-2">
          <p className="break-all text-lg font-bold">{r.user.display_name} · {r.user.email}</p>
          <p className="text-base">{formatDate(r.created_at)} · {r.user.email_verified ? t("mod.verifiedEmail") : t("mod.unverifiedEmail")}</p>
          <p className="whitespace-pre-line text-lg">{r.statement}</p>
          <div className="grid grid-cols-2 gap-2">
            <Button onClick={() => act(r.id, "approve")}>{t("mod.approve")}</Button>
            <Button variant="danger" onClick={() => act(r.id, "reject")}>{t("mod.reject")}</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

function UsersTab() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<UserRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<UserRow[]>(`/mod/users?q=${encodeURIComponent(q)}`).then(setRows).catch((e) => setError(errorMessage(t, e))), [q, t]);
  useEffect(() => {
    const timer = setTimeout(() => void load(), 250);
    return () => clearTimeout(timer);
  }, [load]);
  const withReason = (fn: (reason: string) => Promise<unknown>) => {
    const reason = window.prompt(t("mod.reasonPrompt"));
    if (reason && reason.trim().length >= 3) fn(reason.trim()).then(load).catch((e) => setError(errorMessage(t, e)));
  };
  return (
    <div className="space-y-3">
      <Label htmlFor="mod-users-q">{t("mod.searchUsers")}</Label>
      <Input id="mod-users-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} />
      {error && <Alert>{error}</Alert>}
      {!rows ? <Spinner label={t("app.loading")} /> : rows.map((u) => (
        <Card key={u.id} className="space-y-2">
          <p className="text-lg font-bold">{u.display_name}</p>
          <p className="break-all text-base">{u.email} · {u.email_verified ? t("mod.verifiedEmail") : t("mod.unverifiedEmail")}</p>
          <p className="text-base">{t("mod.role")}: <b>{t(`account.role.${u.role}`)}</b> · {t("mod.status")}: <b>{t(`mod.statusLabels.${u.status}`)}</b></p>
          {u.id !== user?.id && (
            <>
              <div className="grid grid-cols-2 gap-2">
                {(["active", "probation", "suspended", "banned"] as const).filter((st) => st !== u.status).map((st) => (
                  <Button key={st} variant={st === "banned" || st === "suspended" ? "danger" : "secondary"}
                    onClick={() => withReason((reason) => api(`/mod/users/${u.id}/status`, { method: "POST", body: { status: st, reason } }))}>
                    {t(`mod.setStatus.${st}`)}
                  </Button>
                ))}
              </div>
              {user?.role === "admin" && (
                <div>
                  <Label htmlFor={`role-${u.id}`}>{t("mod.setRole")}</Label>
                  <Select id={`role-${u.id}`} value={u.role}
                    onChange={(e) => { const role = e.target.value; withReason((reason) => api(`/admin/users/${u.id}/role`, { method: "POST", body: { role, reason } })); }}>
                    {["user", "pro", "moderator", "admin"].map((r) => <option key={r} value={r}>{t(`account.role.${r}`)}</option>)}
                  </Select>
                </div>
              )}
            </>
          )}
        </Card>
      ))}
    </div>
  );
}

function LogTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<{ id: number; actor: string; action: string; target_type: string; target_id: number; reason: string | null; created_at: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<typeof rows>("/mod/log").then(setRows).catch((e) => setError(errorMessage(t, e)));
  }, [t]);
  if (error) return <Alert>{error}</Alert>;
  if (!rows) return <Spinner label={t("app.loading")} />;
  if (!rows.length) return <p>{t("mod.empty")}</p>;
  return (
    <ul className="divide-y-2 divide-slate-200 dark:divide-slate-800">
      {rows.map((r) => (
        <li key={r.id} className="py-2">
          <p className="font-semibold">{t("mod.logEntry", { actor: r.actor, action: r.action, target: r.target_type, id: r.target_id })}</p>
          <p className="text-base text-slate-600 dark:text-slate-400">{formatDate(r.created_at)}{r.reason ? ` · ${r.reason}` : ""}</p>
        </li>
      ))}
    </ul>
  );
}

const TABS = ["queue", "pro", "users", "log"] as const;

export default function ModPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<(typeof TABS)[number]>("queue");
  return (
    <div className="space-y-4">
      <PageTitle>{t("mod.title")}</PageTitle>
      <div role="tablist" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {TABS.map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`min-h-12 shrink-0 rounded-full border-2 px-4 font-bold ${tab === k ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-300 dark:border-slate-700"}`}>
            {t(`mod.tabs.${k}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "queue" && <ReviewQueue />}
        {tab === "pro" && <ProTab />}
        {tab === "users" && <UsersTab />}
        {tab === "log" && <LogTab />}
      </div>
    </div>
  );
}
