import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { TextArea } from "../entries/fields";
import { price, type Order } from "./types";

const REASONS = ["not_received", "not_as_described", "damaged", "wrong_part", "other"];

function StatusBadge({ s }: { s: Order["status"] }) {
  const { t } = useTranslation();
  const tone = s === "completed" ? "text-emerald-700 dark:text-emerald-400" : s === "disputed" || s === "refunded" ? "text-red-700 dark:text-red-400" : "text-amber-700 dark:text-amber-400";
  return <span className={`font-bold uppercase ${tone}`}>{t(`orders.statuses.${s}`)}</span>;
}

export function OrdersPage() {
  const { t } = useTranslation();
  const { user, loading } = useAuth();
  const [params, setParams] = useSearchParams();
  const as = params.get("as") === "seller" ? "seller" : "buyer";
  useDocumentTitle(t("orders.title"));
  const [list, setList] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!user) return;
    setList(null);
    api<Order[]>(`/market/orders?as=${as}`).then(setList).catch((e) => setError(errorMessage(t, e)));
  }, [user, as, t]);
  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="space-y-4">
      <PageTitle>{t("orders.title")}</PageTitle>
      <div role="tablist" className="grid grid-cols-2 gap-2">
        {(["buyer", "seller"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={as === k} onClick={() => setParams(k === "seller" ? { as: "seller" } : {}, { replace: true })}
            className={`min-h-14 rounded-xl border-2 text-lg font-bold ${as === k ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-400"}`}>
            {t(k === "seller" ? "orders.sold" : "orders.bought")}
          </button>
        ))}
      </div>
      {error && <Alert>{error}</Alert>}
      {!list && !error && <Spinner label={t("app.loading")} />}
      {list?.length === 0 && <p className="text-lg">{t("orders.none")}</p>}
      {list?.map((o) => (
        <Link key={o.id} to={`/market/orders/${o.id}`} className="block rounded-2xl border-2 border-slate-200 p-3 hover:border-amber-400 dark:border-slate-800">
          <p className="text-lg font-bold">{o.listing_title}</p>
          <p className="text-lg">{price(o.total_cents, o.currency.toUpperCase())} · <StatusBadge s={o.status} /></p>
          <p className="text-base">{t("orders.number", { id: o.id })} · {formatDate(o.paid_at ?? o.created_at)} · {o.seller_name}</p>
        </Link>
      ))}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 py-2 text-lg">
      <dt className="font-semibold">{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}

export function OrderPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [search] = useSearchParams();
  const { user, loading } = useAuth();
  const [o, setO] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [carrier, setCarrier] = useState("");
  const [tracking, setTracking] = useState("");
  const [reason, setReason] = useState("not_received");
  const [details, setDetails] = useState("");
  const [reply, setReply] = useState("");
  const [showDispute, setShowDispute] = useState(false);
  useDocumentTitle(o ? t("orders.number", { id: o.id }) : t("orders.title"));
  const load = useCallback(() => {
    api<Order>(`/market/orders/${id}`).then(setO).catch((e) => setError(errorMessage(t, e)));
  }, [id, t]);
  useEffect(() => {
    if (!user) return;
    load();
    // Right after paying, Stripe's confirmation can take a few seconds to reach us.
    if (search.get("paid")) {
      const timer = window.setTimeout(load, 4000);
      return () => window.clearTimeout(timer);
    }
  }, [user, load, search]);
  const act = (path: string, body?: object) =>
    api<Order>(path, { method: "POST", body }).then((x) => { setO(x); setError(null); }).catch((e) => setError(errorMessage(t, e)));

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  if (error && !o) return <Alert>{error}</Alert>;
  if (!o) return <Spinner label={t("app.loading")} />;
  const cur = o.currency.toUpperCase();
  const openDispute = o.disputes?.find((d) => d.status === "open" || d.status === "responded");
  const held = ["paid", "shipped", "delivered"].includes(o.status);

  return (
    <div className="space-y-5">
      <Link to={`/market/orders${o.role === "seller" ? "?as=seller" : ""}`} className="inline-flex min-h-12 items-center font-semibold underline print:hidden">← {t("orders.title")}</Link>
      <PageTitle>{t("orders.receipt")}</PageTitle>
      {o.status === "pending_payment" && <Alert kind="info">{t("orders.waitingPayment")}</Alert>}
      <Card>
        <p className="text-lg"><StatusBadge s={o.status} /></p>
        <h2 className="text-xl font-bold">{o.listing_title}</h2>
        <p className="text-lg">{t("orders.number", { id: o.id })} · {t("orders.soldBy", { name: o.seller_name })}</p>
        <dl className="mt-2 divide-y divide-slate-200 dark:divide-slate-800">
          <Row k={t("orders.item")} v={price(o.item_cents, cur)} />
          <Row k={t("orders.shipping")} v={price(o.shipping_cents, cur)} />
          {o.tax_cents > 0 && <Row k={t("orders.tax")} v={price(o.tax_cents, cur)} />}
          <Row k={t("orders.total")} v={price(o.total_cents, cur)} />
          {o.role === "seller" && o.fee_cents != null && (
            <Row k={t("orders.ourFee", { percent: o.fee_percent })} v={`− ${price(o.fee_cents, cur)}`} />
          )}
          {o.paid_at && <Row k={t("orders.paidOn")} v={formatDate(o.paid_at)} />}
          {o.shipped_at && <Row k={t("orders.shippedOn")} v={formatDate(o.shipped_at)} />}
          {o.tracking_number && <Row k={t("orders.tracking")} v={`${o.carrier ?? ""} ${o.tracking_number}`} />}
          {o.delivered_at && <Row k={t("orders.deliveredOn")} v={formatDate(o.delivered_at)} />}
          {o.released_at && <Row k={t("orders.releasedOn")} v={formatDate(o.released_at)} />}
          {o.refunded_at && <Row k={t("orders.refundedOn")} v={formatDate(o.refunded_at)} />}
        </dl>
        {o.role === "seller" && <p className="mt-2 text-base">{t("orders.stripeFeeNote")}</p>}
        {held && o.release_due_at && (
          <p className="mt-2 text-base">{t(o.role === "seller" ? "orders.releaseSeller" : "orders.releaseBuyer", { date: formatDate(o.release_due_at) })}</p>
        )}
      </Card>
      {o.ship_address && (
        <Card>
          <h2 className="text-xl font-bold">{t("orders.shipTo")}</h2>
          <p className="whitespace-pre-line text-lg">{o.ship_name}{"\n"}{o.ship_address}</p>
        </Card>
      )}
      {error && <Alert>{error}</Alert>}

      {o.role === "seller" && (o.status === "paid" || o.status === "shipped") && (
        <Card className="space-y-3 print:hidden">
          <h2 className="text-xl font-bold">{t(o.status === "paid" ? "orders.shipIt" : "orders.updateTracking")}</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="oc">{t("orders.carrier")}</Label>
              <Input id="oc" value={carrier} maxLength={40} placeholder="USPS, UPS, FedEx…" onChange={(e) => setCarrier(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="ot">{t("orders.trackingNumber")}</Label>
              <Input id="ot" value={tracking} maxLength={60} onChange={(e) => setTracking(e.target.value)} />
            </div>
          </div>
          <Button className="w-full" disabled={carrier.trim().length < 2 || tracking.trim().length < 4}
            onClick={() => act(`/market/orders/${o.id}/ship`, { carrier, tracking_number: tracking })}>{t("orders.markShipped")}</Button>
        </Card>
      )}
      {o.status === "shipped" && (
        <Button variant="secondary" className="w-full print:hidden" onClick={() => act(`/market/orders/${o.id}/delivered`)}>{t("orders.markDelivered")}</Button>
      )}
      {o.role === "buyer" && (o.status === "shipped" || o.status === "delivered") && (
        <Button className="w-full print:hidden" onClick={() => act(`/market/orders/${o.id}/confirm`)}>{t("orders.confirmReceived")}</Button>
      )}

      {o.disputes?.map((d) => (
        <Card key={d.id} className="space-y-2">
          <h2 className="text-xl font-bold">{t("orders.problem")}: {t(`orders.reasons.${d.reason}`)}</h2>
          <p className="text-base">{t(`orders.disputeStatuses.${d.status}`)} · {formatDate(d.created_at)}</p>
          {d.details && <p className="text-lg">“{d.details}”</p>}
          {d.seller_response && <p className="text-lg"><strong>{t("orders.sellerSaid")}</strong> {d.seller_response}</p>}
          {d.decision_note && <p className="text-lg"><strong>{t("orders.decision")}</strong> {d.decision_note}</p>}
          {o.role === "seller" && (d.status === "open" || d.status === "responded") && d.reason !== "chargeback" && (
            <div className="space-y-2 print:hidden">
              <TextArea id="dr" label={t("orders.respond")} value={reply} onChange={setReply} rows={3} max={2000} />
              <Button className="w-full" disabled={reply.trim().length < 5} onClick={() => act(`/market/disputes/${d.id}/respond`, { response: reply })}>{t("orders.sendResponse")}</Button>
            </div>
          )}
        </Card>
      ))}

      {o.role === "buyer" && held && !openDispute && (
        showDispute ? (
          <Card className="space-y-3 print:hidden">
            <h2 className="text-xl font-bold">{t("orders.reportProblem")}</h2>
            <p className="text-base">{t("orders.reportProblemHint")}</p>
            <Label htmlFor="dreason">{t("orders.whatHappened")}</Label>
            <Select id="dreason" value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => <option key={r} value={r}>{t(`orders.reasons.${r}`)}</option>)}
            </Select>
            <TextArea id="ddetails" label={t("orders.details")} value={details} onChange={setDetails} rows={4} max={2000} />
            <Button variant="danger" className="w-full" disabled={details.trim().length < 10}
              onClick={() => act(`/market/orders/${o.id}/dispute`, { reason, details })}>{t("orders.sendProblem")}</Button>
          </Card>
        ) : (
          <Button variant="danger" className="w-full print:hidden" onClick={() => setShowDispute(true)}>{t("orders.reportProblem")}</Button>
        )
      )}
      <Button variant="secondary" className="w-full print:hidden" onClick={() => window.print()}>🖨 {t("orders.print")}</Button>
    </div>
  );
}
