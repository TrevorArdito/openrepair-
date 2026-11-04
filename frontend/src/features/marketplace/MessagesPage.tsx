import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router-dom";
import { Alert, Button, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { TextArea } from "../entries/fields";
import type { Conversation } from "./types";

export function MessagesPage() {
  const { t } = useTranslation();
  const { user, loading } = useAuth();
  useDocumentTitle(t("market.messages"));
  const [list, setList] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (user) api<Conversation[]>("/market/conversations").then(setList).catch((e) => setError(errorMessage(t, e)));
  }, [user, t]);

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="space-y-4">
      <PageTitle>{t("market.messages")}</PageTitle>
      {error && <Alert>{error}</Alert>}
      {!list && !error && <Spinner label={t("app.loading")} />}
      {list?.length === 0 && <p className="text-lg">{t("market.noMessages")}</p>}
      {list?.map((c) => (
        <Link key={c.id} to={`/market/messages/${c.id}`} className="block rounded-2xl border-2 border-slate-200 p-3 hover:border-amber-400 dark:border-slate-800">
          <p className="text-lg font-bold">
            {c.other_name} · <span className="font-semibold">{t(`market.roles.${c.role}`)}</span>
            {c.unread > 0 && <span className="ml-2 rounded-full bg-amber-400 px-2 text-slate-950">{c.unread}</span>}
          </p>
          <p className="truncate text-lg">{c.listing_title}</p>
          {c.last_message && <p className="truncate text-base">{c.last_message}</p>}
          <p className="text-base">{formatDate(c.updated_at)}</p>
        </Link>
      ))}
    </div>
  );
}

export function ConversationPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const { user, loading } = useAuth();
  const [c, setC] = useState<Conversation | null>(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useDocumentTitle(c ? `${c.other_name} — ${c.listing_title}` : t("market.messages"));
  const load = useCallback(() => {
    api<Conversation>(`/market/conversations/${id}`).then(setC).catch((e) => setError(errorMessage(t, e)));
  }, [id, t]);
  useEffect(() => {
    if (user) load();
  }, [user, load]);
  useEffect(() => end.current?.scrollIntoView?.({ block: "end" }), [c]);

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  if (error && !c) return <Alert>{error}</Alert>;
  if (!c) return <Spinner label={t("app.loading")} />;
  return (
    <div className="space-y-4">
      <Link to="/market/messages" className="inline-flex min-h-12 items-center font-semibold underline">← {t("market.messages")}</Link>
      <PageTitle>{c.other_name}</PageTitle>
      <Link to={`/market/listings/${c.listing_id}`} className="block text-lg font-semibold underline">{c.listing_title}</Link>
      <ol className="space-y-2">
        {c.messages?.map((m) => (
          <li key={m.id} className={`max-w-[85%] rounded-2xl p-3 text-lg ${m.mine ? "ml-auto bg-amber-100 dark:bg-amber-900" : "bg-slate-100 dark:bg-slate-800"}`}>
            <p className="whitespace-pre-line">{m.body}</p>
            <p className="text-sm">{formatDate(m.created_at)}</p>
          </li>
        ))}
      </ol>
      <div ref={end} />
      <form
        className="space-y-2"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            setC(await api<Conversation>(`/market/conversations/${c.id}/messages`, { method: "POST", body: { body } }));
            setBody("");
          } catch (err) {
            setError(errorMessage(t, err));
          }
        }}
      >
        <TextArea id="reply" label={t("market.reply")} value={body} onChange={setBody} rows={3} max={2000} />
        {error && <Alert>{error}</Alert>}
        <Button type="submit" className="w-full" disabled={!body.trim()}>{t("market.send")}</Button>
      </form>
      <Alert kind="info">{t("market.safetyTips")}</Alert>
    </div>
  );
}
