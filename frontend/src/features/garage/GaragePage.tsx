import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { GarageItem } from "../../lib/types";

function GarageRow({ item, onChange, onRemove }: { item: GarageItem; onChange: (g: GarageItem) => void; onRemove: () => void }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [nickname, setNickname] = useState(item.nickname ?? "");
  const [notes, setNotes] = useState(item.notes ?? "");
  const [error, setError] = useState<string | null>(null);

  async function save() {
    try {
      onChange(await api<GarageItem>(`/garage/${item.id}`, { method: "PATCH", body: { nickname: nickname || null, notes: notes || null } }));
      setEditing(false);
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  async function remove() {
    if (!window.confirm(t("garage.confirmRemove"))) return;
    try {
      await api(`/garage/${item.id}`, { method: "DELETE" });
      onRemove();
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  return (
    <Card>
      {item.nickname && <p className="font-bold text-amber-700 dark:text-amber-400">{item.nickname}</p>}
      <Link to={`/vehicle/${item.vehicle.id}`} className="block text-xl font-bold underline-offset-4 hover:underline">
        {item.vehicle.label}
      </Link>
      {item.vin && <p className="font-mono">{item.vin}</p>}
      {item.notes && !editing && <p className="mt-1 whitespace-pre-line">{item.notes}</p>}
      {editing ? (
        <div className="mt-3 space-y-3">
          <div>
            <Label htmlFor={`nick-${item.id}`}>{t("garage.nickname")}</Label>
            <Input id={`nick-${item.id}`} value={nickname} maxLength={60} placeholder={t("garage.nicknamePlaceholder")} onChange={(e) => setNickname(e.target.value)} />
          </div>
          <div>
            <Label htmlFor={`notes-${item.id}`}>{t("garage.notes")}</Label>
            <textarea
              id={`notes-${item.id}`}
              value={notes}
              maxLength={2000}
              onChange={(e) => setNotes(e.target.value)}
              className="min-h-28 w-full rounded-xl border-2 border-slate-400 bg-white p-3 text-lg dark:border-slate-600 dark:bg-slate-900"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Button onClick={save}>{t("garage.save")}</Button>
            <Button variant="secondary" onClick={() => setEditing(false)}>
              {t("garage.cancel")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <LinkButton to={`/vehicle/${item.vehicle.id}`}>{t("garage.open")}</LinkButton>
          <Button variant="secondary" onClick={() => setEditing(true)}>
            {t("garage.edit")}
          </Button>
          <Button variant="danger" onClick={remove}>
            {t("garage.remove")}
          </Button>
        </div>
      )}
      {error && <div className="mt-3"><Alert>{error}</Alert></div>}
    </Card>
  );
}

export default function GaragePage() {
  const { t } = useTranslation();
  const { user, loading } = useAuth();
  const [items, setItems] = useState<GarageItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle(t("garage.title"));

  useEffect(() => {
    if (!user) return;
    api<GarageItem[]>("/garage")
      .then(setItems)
      .catch((e) => setError(errorMessage(t, e)));
  }, [user, t]);

  if (loading) return <Spinner label={t("app.loading")} />;
  return (
    <div className="space-y-4">
      <PageTitle>{t("garage.title")}</PageTitle>
      {!user ? (
        <Card>
          <p className="mb-3">{t("garage.loginPrompt")}</p>
          <LinkButton to="/login" state={{ from: "/garage" }} className="w-full">
            {t("auth.login")}
          </LinkButton>
        </Card>
      ) : error ? (
        <Alert>{error}</Alert>
      ) : items === null ? (
        <Spinner label={t("app.loading")} />
      ) : items.length === 0 ? (
        <Card>
          <p>{t("garage.empty")}</p>
        </Card>
      ) : (
        items.map((g) => (
          <GarageRow
            key={g.id}
            item={g}
            onChange={(updated) => setItems((list) => list!.map((x) => (x.id === updated.id ? updated : x)))}
            onRemove={() => setItems((list) => list!.filter((x) => x.id !== g.id))}
          />
        ))
      )}
    </div>
  );
}
