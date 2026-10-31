import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { KINDS, type Entry, type EntryTags, type Kind, type Vehicle } from "../../lib/types";
import { emptyData, KindForm, SourcesForm } from "./KindForms";
import TagsForm from "./TagsForm";
import { TextField } from "./fields";

/* eslint-disable @typescript-eslint/no-explicit-any */

export default function EntryEditPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const editing = !!id;
  const [kind, setKind] = useState<Kind | null>((params.get("kind") as Kind) || null);
  const [title, setTitle] = useState("");
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [tags, setTags] = useState<EntryTags>({ applies_to: [], systems: [], dtcs: [] });
  const [base, setBase] = useState(0);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (editing) {
      api<Entry>(`/entries/${id}`).then((e) => {
        setKind(e.kind);
        setTitle(e.revision?.title ?? e.title);
        setData(e.revision?.data ?? emptyData(e.kind));
        setTags(e.revision?.tags ?? { applies_to: [], systems: [], dtcs: [] });
        setBase(e.revision?.status === "approved" ? e.revision.number : 0);
      }).catch((e) => setError(errorMessage(t, e)));
      return;
    }
    if (kind) setData(emptyData(kind));
    const vid = params.get("vehicle_id");
    if (vid) {
      api<Vehicle>(`/vehicles/${vid}`).then((v) => setTags((tg) => ({
        ...tg,
        applies_to: [{ make_id: v.make.id, model_id: v.model.id, year_from: v.year, year_to: v.year, displacement_l: v.engine.displacement_l }],
      }))).catch(() => undefined);
    }
  }, [id, editing, kind, params, t]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const saved = editing
        ? await api<Entry>(`/entries/${id}/revisions`, { method: "POST", body: { base_revision: base, title, data, tags, edit_summary: summary } })
        : await api<Entry>("/entries", { method: "POST", body: { kind, title, data, tags, edit_summary: summary || null } });
      navigate(`/entries/${saved.id}`);
    } catch (err) {
      setError(err instanceof ApiError && err.code === "edit_conflict" ? t("editor.conflict") : errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user)
    return (
      <Card>
        <p className="mb-3">{t("editor.loginRequired")}</p>
        <LinkButton to="/login" className="w-full">{t("auth.login")}</LinkButton>
      </Card>
    );

  if (!kind)
    return (
      <div className="space-y-3">
        <PageTitle>{t("editor.chooseKind")}</PageTitle>
        {KINDS.map((k) => (
          <Button key={k} variant="secondary" className="w-full justify-start" onClick={() => setKind(k)}>
            {t(`kinds.${k}`)}
          </Button>
        ))}
      </div>
    );
  if (!data) return error ? <Alert>{error}</Alert> : <Spinner label={t("app.loading")} />;

  const set = (patch: Record<string, any>) => setData((d) => ({ ...d, ...patch }));
  return (
    <form onSubmit={submit} className="space-y-5">
      <PageTitle>{editing ? t("editor.editTitle", { title }) : t("editor.newTitle", { kind: t(`kinds.${kind}`) })}</PageTitle>
      {user.status === "probation" && <Alert kind="info">{t("editor.probationNote")}</Alert>}
      <TextField id="f-title" label={t("editor.title")} hint={t("editor.titleHint")} value={title} required onChange={setTitle} />
      <KindForm kind={kind} d={data} set={set} />
      {kind !== "labor_time" && <SourcesForm d={data} set={set} />}
      <TagsForm tags={tags} set={setTags} />
      <TextField id="f-summary-edit" label={t("editor.editSummary")} hint={t("editor.editSummaryHint")} value={summary} max={300} required={editing} onChange={setSummary} />
      <p className="text-base text-slate-600 dark:text-slate-400">{t("editor.contentRules")}</p>
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <Button type="submit" disabled={busy}>{busy ? t("editor.saving") : t("editor.save")}</Button>
        <Link to={editing ? `/entries/${id}` : "/"} className="inline-flex min-h-14 items-center justify-center rounded-xl border-2 border-slate-400 text-lg font-bold">
          {t("editor.cancel")}
        </Link>
      </div>
    </form>
  );
}
