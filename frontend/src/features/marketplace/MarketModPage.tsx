import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router-dom";
import { Alert, Button, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { useModule } from "../../lib/modules";
import { ListingCard } from "./MarketPage";
import { price, type ListingSummary, type Order, type Verification } from "./types";

function PaymentsAdmin({ isAdmin }: { isAdmin: boolean }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<{ dispute_id: number; order: Order }[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<{ dispute_id: number; order: Order }[]>("/market/mod/disputes").then(setRows).catch((e) => setError(errorMessage(t, e))), [t]);
  useEffect(() => void load(), [load]);
  const decide = (id: number, decision: "refund" | "release") => {
    const note = window.prompt(t("pay.admin.notePrompt")) ?? "";
    api(`/market/mod/disputes/${id}/decide`, { method: "POST", body: { decision, note: note || null } }).then(load).catch((e) => setError(errorMessage(t, e)));
  };
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-bold">{t("pay.admin.disputes")} ({rows?.length ?? 0})</h2>
      {!isAdmin && <p className="text-base">{t("pay.admin.adminOnly")}</p>}
      {rows?.map(({ dispute_id, order: o }) => {
        const d = o.disputes?.find((x) => x.id === dispute_id);
        return (
          <Card key={dispute_id} className="space-y-2 text-lg">
            <Link className="font-bold underline" to={`/market/orders/${o.id}`}>{t("orders.number", { id: o.id })} · {o.listing_title}</Link>
            <p>{price(o.total_cents, o.currency.toUpperCase())} · {o.seller_name}</p>
            {d && <p><strong>{t(`orders.reasons.${d.reason}`)}</strong>: {d.details}</p>}
            {d?.seller_response && <p><strong>{t("orders.sellerSaid")}</strong> {d.seller_response}</p>}
            {isAdmin && d?.reason !== "chargeback" && (
              <div className="grid grid-cols-2 gap-2">
                <Button variant="danger" onClick={() => decide(dispute_id, "refund")}>{t("pay.admin.refund")}</Button>
                <Button onClick={() => decide(dispute_id, "release")}>{t("pay.admin.release")}</Button>
              </div>
            )}
            {d?.reason === "chargeback" && <p className="text-base">{t("pay.admin.chargebackNote")}</p>}
          </Card>
        );
      })}
      {isAdmin && (
        <Button variant="secondary" className="w-full"
          onClick={() => api<{ released: number }>("/market/mod/payouts/run", { method: "POST" })
            .then((r) => setMsg(t("pay.admin.released", { count: r.released }))).catch((e) => setError(errorMessage(t, e)))}>
          {t("pay.admin.runPayouts")}
        </Button>
      )}
      {msg && <Alert kind="info">{msg}</Alert>}
      {error && <Alert>{error}</Alert>}
    </section>
  );
}

type Queue = {
  pending_listings: ListingSummary[];
  reports: { id: number; listing_id: number; listing_title: string; reason: string; details: string | null; created_at: string }[];
  verifications: (Verification & { seller_id: number; seller_name: string })[];
};

export default function MarketModPage() {
  const { t } = useTranslation();
  const paymentsOn = useModule("market_payments");
  const { user, loading } = useAuth();
  useDocumentTitle(t("market.mod.title"));
  const [q, setQ] = useState<Queue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<Queue>("/market/mod/queue").then(setQ).catch((e) => setError(errorMessage(t, e))), [t]);
  useEffect(() => {
    if (user) void load();
  }, [user, load]);
  const act = (path: string, body: object) => api(path, { method: "POST", body }).then(load).catch((e) => setError(errorMessage(t, e)));
  const removeListing = async (id: number, reportId?: number) => {
    const reason = window.prompt(t("market.mod.reasonPrompt")) ?? "";
    if (!reason.trim()) return;
    await act(`/market/mod/listings/${id}`, { action: "remove", reason });
    if (reportId) await act(`/market/mod/reports/${reportId}`, { action: "resolve" });
  };

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="space-y-5">
      <PageTitle>{t("market.mod.title")}</PageTitle>
      {paymentsOn && <PaymentsAdmin isAdmin={user.role === "admin"} />}
      {error && <Alert>{error}</Alert>}
      {!q && !error && <Spinner label={t("app.loading")} />}
      {q && (
        <>
          <h2 className="text-2xl font-bold">{t("market.mod.pending")} ({q.pending_listings.length})</h2>
          {q.pending_listings.map((l) => (
            <div key={l.id} className="space-y-2">
              <ListingCard l={l} />
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={() => act(`/market/mod/listings/${l.id}`, { action: "approve" })}>{t("mod.approve")}</Button>
                <Button variant="danger" onClick={() => void removeListing(l.id)}>{t("market.mod.remove")}</Button>
              </div>
            </div>
          ))}

          <h2 className="text-2xl font-bold">{t("market.mod.reports")} ({q.reports.length})</h2>
          {q.reports.map((r) => (
            <Card key={r.id} className="space-y-2">
              <p className="font-semibold uppercase text-red-700 dark:text-red-400">{t(`market.reportReasons.${r.reason}`)}</p>
              <Link to={`/market/listings/${r.listing_id}`} className="text-lg font-bold underline">{r.listing_title}</Link>
              {r.details && <p className="text-lg">“{r.details}”</p>}
              <p>{formatDate(r.created_at)}</p>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="danger" onClick={() => void removeListing(r.listing_id, r.id)}>
                  {t("market.mod.removeAndResolve")}
                </Button>
                <Button variant="secondary" onClick={() => act(`/market/mod/reports/${r.id}`, { action: "dismiss" })}>{t("market.mod.dismiss")}</Button>
              </div>
            </Card>
          ))}

          <h2 className="text-2xl font-bold">{t("market.mod.verifications")} ({q.verifications.length})</h2>
          <p className="text-lg">{t("market.mod.verifyHowTo")}</p>
          {q.verifications.map((v) => (
            <Card key={v.id} className="space-y-2 text-lg">
              <p><strong>{v.business_name}</strong> ({v.seller_name})</p>
              <p>{t(`market.verifyKinds.${v.kind}`)}: {v.license_number} · {v.issuing_state}</p>
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={() => act(`/market/mod/verifications/${v.id}`, { action: "approve" })}>{t("mod.approve")}</Button>
                <Button variant="danger" onClick={() => act(`/market/mod/verifications/${v.id}`, { action: "reject", note: window.prompt(t("market.mod.reasonPrompt")) || null })}>
                  {t("mod.reject")}
                </Button>
              </div>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}
