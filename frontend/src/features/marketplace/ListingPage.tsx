import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, Label, LinkButton, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { TextArea } from "../entries/fields";
import { price, type Conversation, type Listing } from "./types";

const REPORT_REASONS = ["stolen", "prohibited", "scam", "counterfeit", "wrong_fitment", "other"];

function fitLabel(f: Listing["fitment"][number]): string {
  const years = f.year_from === f.year_to ? `${f.year_from}` : `${f.year_from}–${f.year_to}`;
  return [years, f.make, f.model, f.engine ?? (f.displacement_l ? `${f.displacement_l}L` : null)].filter(Boolean).join(" ");
}

function ContactSeller({ l }: { l: Listing }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const nav = useNavigate();
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  if (!user)
    return <LinkButton to="/login" className="w-full">{t("market.loginToMessage")}</LinkButton>;
  return (
    <form
      className="space-y-2"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          const c = await api<Conversation>(`/market/listings/${l.id}/messages`, { method: "POST", body: { body } });
          nav(`/market/messages/${c.id}`);
        } catch (err) {
          setError(errorMessage(t, err));
        }
      }}
    >
      <TextArea id="msg" label={t("market.messageSeller")} value={body} onChange={setBody} rows={3} max={2000} hint={t("market.messageHint")} />
      {error && <Alert>{error}</Alert>}
      <Button type="submit" className="w-full" disabled={!body.trim()}>{t("market.send")}</Button>
    </form>
  );
}

function SaveButton({ l, onChange }: { l: Listing; onChange: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  if (!user || l.is_owner) return null;
  const toggle = () =>
    api(`/market/listings/${l.id}/save`, { method: l.saved ? "DELETE" : "POST" })
      .then(() => onChange(!l.saved))
      .catch(() => undefined);
  return (
    <Button variant="secondary" className="w-full" aria-pressed={l.saved} onClick={toggle}>
      {l.saved ? `★ ${t("market.savedButton")}` : `☆ ${t("market.save")}`}
    </Button>
  );
}

function VehicleChecks({ l }: { l: Listing }) {
  const { t } = useTranslation();
  const v = l.vehicle!;
  const ext = "inline-flex min-h-12 items-center font-semibold underline";
  return (
    <Card className="space-y-2">
      <h2 className="text-xl font-bold">{t("market.beforeYouBuy")}</h2>
      <ul className="space-y-1 text-lg">
        {v.vehicle_id && <li><Link className={ext} to={`/vehicle/${v.vehicle_id}`}>🔧 {t("market.repairInfo")}</Link></li>}
        {v.vin && <li><a className={ext} href="https://www.nhtsa.gov/recalls" target="_blank" rel="noopener noreferrer">⚠️ {t("market.nhtsaRecalls")} ↗</a></li>}
        <li><a className={ext} href="https://www.nicb.org/vincheck" target="_blank" rel="noopener noreferrer">🔎 {t("market.nicbCheck")} ↗</a></li>
      </ul>
      <p className="text-base">{t("market.vehicleTips")}</p>
    </Card>
  );
}

function ReportForm({ id }: { id: number }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("stolen");
  const [details, setDetails] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!user) return null;
  if (done) return <Alert kind="info">{t("market.reportThanks")}</Alert>;
  if (!open) return <Button variant="secondary" className="w-full" onClick={() => setOpen(true)}>{t("market.report")}</Button>;
  return (
    <Card className="space-y-3">
      <Label htmlFor="rr">{t("market.reportReason")}</Label>
      <Select id="rr" value={reason} onChange={(e) => setReason(e.target.value)}>
        {REPORT_REASONS.map((r) => <option key={r} value={r}>{t(`market.reportReasons.${r}`)}</option>)}
      </Select>
      <TextArea id="rd" label={t("market.reportDetails")} value={details} onChange={setDetails} rows={3} max={2000} />
      {error && <Alert>{error}</Alert>}
      <Button
        className="w-full"
        onClick={() =>
          api(`/market/listings/${id}/report`, { method: "POST", body: { reason, details: details || null } })
            .then(() => setDone(true))
            .catch((e) => setError(errorMessage(t, e)))
        }
      >
        {t("market.sendReport")}
      </Button>
    </Card>
  );
}

function OwnerControls({ l, onChange }: { l: Listing; onChange: (l: Listing) => void }) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const status = (s: string) =>
    api<Listing>(`/market/listings/${l.id}/status`, { method: "POST", body: { status: s } })
      .then(onChange)
      .catch((e) => setError(errorMessage(t, e)));
  return (
    <Card className="space-y-3">
      <h2 className="text-xl font-bold">{t("market.yourListing")}</h2>
      <p className="text-lg">{t("market.statusIs", { status: t(`market.statuses.${l.status}`) })}</p>
      {l.status === "pending" && <Alert kind="info">{t("market.pendingNote")}</Alert>}
      {l.status === "removed" && <Alert kind="warning">{t("market.removedNote", { reason: l.status_reason ?? "—" })}</Alert>}
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-2 gap-2">
        {l.status !== "removed" && <LinkButton to={`/market/listings/${l.id}/edit`} variant="secondary">{t("market.edit")}</LinkButton>}
        {l.status === "active" && <Button onClick={() => status("sold")}>{t("market.markSold")}</Button>}
        {l.status === "active" && <Button variant="secondary" onClick={() => status("withdrawn")}>{t("market.withdraw")}</Button>}
        {(l.status === "sold" || l.status === "withdrawn") && <Button onClick={() => status("active")}>{t("market.relist")}</Button>}
      </div>
    </Card>
  );
}

export default function ListingPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [l, setL] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState(0);
  useDocumentTitle(l?.title);
  const load = useCallback(() => {
    api<Listing>(`/market/listings/${id}`).then(setL).catch((e) => setError(errorMessage(t, e)));
  }, [id, t]);
  useEffect(load, [load]);

  if (error) return <Alert>{error}</Alert>;
  if (!l) return <Spinner label={t("app.loading")} />;
  const v = l.vehicle;
  const vehicleRows: [string, string | null][] = v ? [
    [t("market.yearMakeModel"), [v.year, v.make, v.model, v.trim].filter(Boolean).join(" ")],
    [t("market.odometer"), v.odometer != null ? `${v.odometer.toLocaleString()} ${v.odometer_unit}` : null],
    [t("market.titleStatus"), t(`market.titleStatuses.${v.title_status}`) + (v.has_lien ? ` · ${t("market.lien")}` : "")],
    [t("market.running"), t(`market.runnings.${v.running}`)],
    [t("market.vin"), v.vin ?? null],
    [t("market.drive"), v.drive ?? null],
    [t("market.transmission"), v.transmission ?? null],
    [t("market.color"), v.exterior_color ?? null],
  ] : [];
  const rows: [string, string | null][] = v ? [
    ...vehicleRows,
    [t("market.shipping"), t(`market.shippings.${l.shipping}`) + (l.shipping_note ? ` — ${l.shipping_note}` : "")],
    [t("market.listed"), formatDate(l.created_at)],
  ] : [
    [t("market.condition"), t(`market.conditions.${l.condition}`)],
    [t("market.category"), t(`market.categories.${l.category}`)],
    [t("market.brand"), l.brand],
    [t("market.partNumber"), l.part_number],
    [t("market.quantity"), String(l.quantity)],
    [t("market.shipping"), t(`market.shippings.${l.shipping}`) + (l.shipping_note ? ` — ${l.shipping_note}` : "")],
    [t("market.mileage"), l.mileage != null ? l.mileage.toLocaleString() : null],
    [t("market.sourceVin"), l.source_vin],
    [t("market.compliance"), l.emissions_compliance ? t(`market.compliances.${l.emissions_compliance}`) + (l.carb_eo_number ? ` (EO ${l.carb_eo_number})` : "") : null],
    [t("market.listed"), formatDate(l.created_at)],
  ];

  return (
    <div className="space-y-5">
      <Link to="/market" className="inline-flex min-h-12 items-center font-semibold underline">← {t("market.title")}</Link>
      {l.photos.length > 0 && (
        <div className="space-y-2">
          <img src={l.photos[photo]?.url} alt="" className="max-h-96 w-full rounded-2xl object-contain bg-slate-100 dark:bg-slate-900" />
          {l.photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto">
              {l.photos.map((p, i) => (
                <button key={p.id} type="button" onClick={() => setPhoto(i)} aria-label={t("market.photoN", { n: i + 1 })}
                  className={`shrink-0 rounded-xl border-4 ${i === photo ? "border-amber-400" : "border-transparent"}`}>
                  <img src={p.url} alt="" className="size-16 rounded-lg object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div>
        <p className="text-3xl font-extrabold">{l.price_cents === 0 ? t("market.free") : price(l.price_cents, l.currency)}</p>
        <PageTitle>{l.title}</PageTitle>
        {l.status !== "active" && <p className="text-lg font-bold uppercase text-amber-700 dark:text-amber-400">{t(`market.statuses.${l.status}`)}</p>}
      </div>

      {l.is_owner && <OwnerControls l={l} onChange={setL} />}
      <SaveButton l={l} onChange={(saved) => setL({ ...l, saved })} />

      {v ? <VehicleChecks l={l} /> : <Card className="space-y-2">
        <h2 className="text-xl font-bold">{t("market.fits")}</h2>
        {l.fits_all ? <p className="text-lg">{t("market.fitsAll")}</p> : (
          <ul className="list-disc space-y-1 pl-6 text-lg">{l.fitment.map((f, i) => <li key={i}>{fitLabel(f)}</li>)}</ul>
        )}
        <p className="text-base">{t("market.fitmentWarning")}</p>
      </Card>}

      <Card>
        <p className="whitespace-pre-line text-lg">{l.description}</p>
        <dl className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
          {rows.filter(([, v]) => v).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-2 text-lg">
              <dt className="font-semibold">{k}</dt>
              <dd className="text-right">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-xl font-bold">{t("market.seller")}</h2>
        <Link to={`/market/sellers/${l.seller_id}`} className="text-lg font-bold underline">{l.seller_name}</Link>
        <p className="text-lg">
          {l.city}, {l.state}
          {l.seller_verified && <> · <span className="font-semibold text-emerald-700 dark:text-emerald-400">✓ {t("market.verifiedBusiness")}</span></>}
        </p>
        {!l.is_owner && l.status === "active" && <ContactSeller l={l} />}
      </Card>

      <Alert kind="info">{t("market.safetyTips")}</Alert>
      {!l.is_owner && <ReportForm id={l.id} />}
    </div>
  );
}
