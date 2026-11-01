import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { Alert, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import { ListingCard } from "./MarketPage";
import type { ListingSummary } from "./types";

export default function SavedPage() {
  const { t } = useTranslation();
  const { user, loading } = useAuth();
  useDocumentTitle(t("market.savedTitle"));
  const [items, setItems] = useState<ListingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (user) api<ListingSummary[]>("/market/saved").then(setItems).catch((e) => setError(errorMessage(t, e)));
  }, [user, t]);
  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="space-y-4">
      <PageTitle>{t("market.savedTitle")}</PageTitle>
      {error && <Alert>{error}</Alert>}
      {!items && !error && <Spinner label={t("app.loading")} />}
      {items?.length === 0 && <p className="text-lg">{t("market.savedNone")}</p>}
      <div className="space-y-3">{items?.map((l) => <ListingCard key={l.id} l={l} />)}</div>
    </div>
  );
}
