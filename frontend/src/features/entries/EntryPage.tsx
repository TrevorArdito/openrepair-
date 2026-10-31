import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Alert, Button, Card, Label, LinkButton, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import type { Entry, Source } from "../../lib/types";
import { EntryBody } from "./Renderers";

const REASONS = ["wrong_info", "unsafe", "spam", "copyright", "other"] as const;

function ReportForm({ entryId, onDone }: { entryId: number; onDone: () => void }) {
  const { t } = useTranslation();
  const [reason, setReason] = useState<string>("wrong_info");
  const [details, setDetails] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/entries/${entryId}/reports`, { method: "POST", body: { reason, details: details || null } });
      onDone();
    } catch (err) {
      setError(errorMessage(t, err));
    }
  }
  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <h2 className="text-xl font-bold">{t("entry.reportTitle")}</h2>
        <Select aria-label={t("entry.reportTitle")} value={reason} onChange={(e) => setReason(e.target.value)}>
          {REASONS.map((r) => (
            <option key={r} value={r}>
              {t(`entry.reportReasons.${r}`)}
            </option>
          ))}
        </Select>
        <Label htmlFor="rep-details">{t("entry.reportDetails")}</Label>
        <textarea id="rep-details" maxLength={2000} value={details} onChange={(e) => setDetails(e.target.value)}
          className="min-h-28 w-full rounded-xl border-2 border-slate-400 bg-white p-3 text-lg dark:border-slate-600 dark:bg-slate-900" />
        {error && <Alert>{error}</Alert>}
        <Button type="submit" className="w-full">{t("entry.reportSend")}</Button>
      </form>
    </Card>
  );
}

export default function EntryPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const { user } = useAuth();
  const [entry, setEntry] = useState<Entry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState(false);

  useEffect(() => {
    setEntry(null);
    api<Entry>(`/entries/${id}`).then(setEntry).catch((e) => setError(errorMessage(t, e)));
  }, [id, t, user]);

  async function act(path: string, body?: unknown) {
    setActionError(null);
    try {
      setEntry(await api<Entry>(`/entries/${id}/${path}`, { method: "POST", body }));
    } catch (e) {
      setActionError(errorMessage(t, e));
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!entry) return <Spinner label={t("app.loading")} />;
  const rev = entry.revision;
  const v = entry.verification;
  const isPro = !!user && ["pro", "moderator", "admin"].includes(user.role);
  const sources: Source[] = rev?.data.sources ?? [];

  return (
    <div className="space-y-4">
      <div>
        <p className="font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">{t(`kinds.${entry.kind}`)}</p>
        <PageTitle>{entry.title}</PageTitle>
        {v.state === "verified" ? (
          <p className="inline-flex items-center gap-2 rounded-lg bg-green-700 px-3 py-2 text-lg font-bold text-white">
            ✓ {t("entry.verifiedBy", { name: v.by?.display_name, date: formatDate(v.at) })}
          </p>
        ) : v.state === "verified_older" ? (
          <Alert kind="warning">{t("entry.verifiedOlder", { n: v.revision_number })}</Alert>
        ) : (
          <p className="text-lg text-slate-600 dark:text-slate-400">{t("entry.unverified")}</p>
        )}
      </div>

      {entry.status === "pending" && <Alert kind="info">{t("entry.pending")}</Alert>}
      {entry.status === "hidden" && <Alert>{t("entry.hidden")}</Alert>}
      {entry.open_reports > 0 && <Alert kind="warning">{t("entry.openReports", { count: entry.open_reports })}</Alert>}
      {entry.safety_critical && (
        <Alert kind="error">
          <h2 className="text-lg font-bold">⚠ {t("entry.safetyTitle")}</h2>
          <p>{t("entry.safetyBody")}</p>
        </Alert>
      )}

      <EntryBody entry={entry} onChange={setEntry} loggedIn={!!user} />

      <Card>
        <h2 className="mb-2 text-xl font-bold">{t("entry.appliesTo")}</h2>
        {entry.tags_display.applies_to.length === 0 ? (
          <p className="text-lg">{t("entry.allVehicles")}</p>
        ) : (
          <ul className="space-y-1 text-lg">
            {entry.tags_display.applies_to.map((a, i) => (
              <li key={i}>
                {a.year_from === a.year_to ? a.year_from : `${a.year_from}–${a.year_to}`} {a.make} {a.model ?? t("entry.allModels")}
                {a.displacement_l ? ` · ${t("entry.engineSize", { l: a.displacement_l })}` : ""}
              </li>
            ))}
          </ul>
        )}
        {entry.tags_display.systems.length > 0 && (
          <p className="mt-3 text-lg">
            <b>{t("entry.systemsLabel")}:</b> {entry.tags_display.systems.map((s) => t(`systems.${s}`)).join(", ")}
          </p>
        )}
        {entry.tags_display.dtcs.length > 0 && (
          <p className="mt-2 flex flex-wrap items-center gap-2 text-lg">
            <b>{t("entry.codes")}:</b>
            {entry.tags_display.dtcs.map((c) => (
              <Link key={c} to={`/codes/${c}`} className="inline-flex min-h-12 items-center rounded-lg border-2 border-slate-300 px-3 font-mono font-bold dark:border-slate-600">
                {c}
              </Link>
            ))}
          </p>
        )}
      </Card>

      {sources.length > 0 && (
        <p className="text-base text-slate-600 dark:text-slate-400">
          {t("entry.sourceLine")}{" "}
          {sources.map((src) => t(`entry.sourceTypes.${src.type}`) + (src.citation ? ` (${src.citation})` : "")).join(" · ")}
        </p>
      )}

      {rev && (
        <p className="text-base text-slate-600 dark:text-slate-400">
          {t("entry.lastEdit", { n: rev.number, name: rev.author.display_name, date: formatDate(rev.created_at) })}
          {entry.pending_revisions > 0 && ` · ${t("entry.pendingEdits", { count: entry.pending_revisions })}`}
        </p>
      )}

      {actionError && <Alert>{actionError}</Alert>}
      {user ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Button variant={entry.my_vote === 1 ? "primary" : "secondary"} onClick={() => act("vote", { value: entry.my_vote === 1 ? 0 : 1 })} aria-pressed={entry.my_vote === 1}>
              👍 {t("entry.helpful")}
            </Button>
            <Button variant={entry.my_vote === -1 ? "primary" : "secondary"} onClick={() => act("vote", { value: entry.my_vote === -1 ? 0 : -1 })} aria-pressed={entry.my_vote === -1}>
              👎 {t("entry.notHelpful")}
            </Button>
          </div>
          <p className="text-center text-base">{t("entry.score", { score: entry.score })}</p>
          <div className="grid grid-cols-2 gap-3">
            <LinkButton to={`/entries/${entry.id}/edit`} variant="secondary">
              {t("entry.edit")}
            </LinkButton>
            <LinkButton to={`/entries/${entry.id}/history`} variant="secondary">
              {t("entry.history")}
            </LinkButton>
          </div>
          {isPro && v.state !== "verified" && entry.status === "published" && (
            <Button className="w-full" onClick={() => window.confirm(t("entry.verifyConfirm")) && act("verify")}>
              ✓ {t("entry.verify")}
            </Button>
          )}
          {reported ? (
            <Alert kind="info">{t("entry.reportThanks")}</Alert>
          ) : reporting ? (
            <ReportForm entryId={entry.id} onDone={() => { setReported(true); setReporting(false); }} />
          ) : (
            <Button variant="danger" className="w-full" onClick={() => setReporting(true)}>
              ⚑ {t("entry.report")}
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <Link to="/login" className="flex min-h-12 items-center font-bold underline">{t("entry.loginToHelp")}</Link>
          <LinkButton to={`/entries/${entry.id}/history`} variant="secondary" className="w-full">
            {t("entry.history")}
          </LinkButton>
        </div>
      )}
    </div>
  );
}
