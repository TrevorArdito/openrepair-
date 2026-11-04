import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { AppliesTo, NamedRef, VinDecode } from "../../lib/types";
import { PhotoField, TextArea, TextField } from "../entries/fields";
import { RangeRow } from "../entries/TagsForm";
import { SellerForm } from "./SellingPage";
import { useModule } from "../../lib/modules";
import { CONDITIONS, RUNNING, TITLE_STATUSES, feeBreakdown, price as fmtPrice, type Listing, type PaymentsConfig, type Seller } from "./types";

/** "What you take home" — shown before listing (owner requirement). */
function FeeBreakdown({ cfg, priceCents, shippingCents, ships }: { cfg: PaymentsConfig; priceCents: number; shippingCents: number; ships: boolean }) {
  const { t } = useTranslation();
  if (!ships) return <Alert kind="info">{t("pay.pickupFree")}</Alert>;
  const b = feeBreakdown(cfg, priceCents, shippingCents);
  const rows: [string, string][] = [
    [t("pay.salePrice"), fmtPrice(priceCents)],
    [t("pay.shippingCharged"), fmtPrice(shippingCents)],
    [t("pay.ourFee", { percent: cfg.fee_percent }), `− ${fmtPrice(b.fee)}`],
    [t("pay.stripeFee", { percent: cfg.stripe_fee_percent, fixed: fmtPrice(cfg.stripe_fee_fixed_cents) }), `− ${fmtPrice(b.stripe)}`],
  ];
  return (
    <div className="rounded-xl border-2 border-slate-300 p-3 dark:border-slate-700">
      <h3 className="text-lg font-bold">{t("pay.breakdownTitle")}</h3>
      <dl className="divide-y divide-slate-200 dark:divide-slate-800">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 py-1 text-lg"><dt>{k}</dt><dd>{v}</dd></div>
        ))}
        <div className="flex justify-between gap-3 py-1 text-xl font-extrabold"><dt>{t("pay.takeHome")}</dt><dd>{fmtPrice(b.net)}</dd></div>
      </dl>
      <p className="mt-1 text-base">{t("pay.breakdownNote")}</p>
    </div>
  );
}

type VForm = {
  vin: string; year: string; make_id: number | null; model_id: number | null; odometer: string;
  odometer_unit: "mi" | "km"; title_status: string; has_lien: boolean; running: string;
  trim: string; drive: string; transmission: string; exterior_color: string;
};
const EMPTY_V: VForm = {
  vin: "", year: "", make_id: null, model_id: null, odometer: "", odometer_unit: "mi", title_status: "clean",
  has_lien: false, running: "runs_drives", trim: "", drive: "", transmission: "", exterior_color: "",
};

function VehicleFields({ v, set, makes, onDecoded }: { v: VForm; set: (p: Partial<VForm>) => void; makes: NamedRef[]; onDecoded: (label: string) => void }) {
  const { t } = useTranslation();
  const [models, setModels] = useState<NamedRef[]>([]);
  const [msg, setMsg] = useState<{ kind: "info" | "error"; text: string } | null>(null);
  useEffect(() => {
    if (!v.make_id || !v.year) return setModels([]);
    api<NamedRef[]>(`/vehicles/models?year=${v.year}&make_id=${v.make_id}`).then(setModels).catch(() => setModels([]));
  }, [v.make_id, v.year]);
  async function lookUp() {
    setMsg(null);
    try {
      const d = await api<VinDecode>(`/vehicles/decode/${encodeURIComponent(v.vin)}`);
      set({
        year: String(d.vehicle.year), make_id: d.vehicle.make.id, model_id: d.vehicle.model.id,
        trim: v.trim || d.details.trim || "", drive: v.drive || d.details.drive_type || "",
        transmission: v.transmission || d.details.transmission || "",
      });
      onDecoded(d.vehicle.label);
      setMsg({ kind: "info", text: t("market.vinFound", { label: d.vehicle.label }) });
    } catch (e) {
      setMsg({ kind: "error", text: errorMessage(t, e) });
    }
  }
  const field = (id: string, key: keyof VForm, label: string, max = 40) => (
    <TextField id={id} label={label} value={String(v[key] ?? "")} max={max} onChange={(x) => set({ [key]: x } as Partial<VForm>)} />
  );
  return (
    <Card className="space-y-4">
      <h2 className="text-xl font-bold">{t("market.vehicleDetails")}</h2>
      <div>
        <Label htmlFor="vvin">{t("market.vin")}</Label>
        <div className="flex gap-2">
          <Input id="vvin" value={v.vin} maxLength={17} autoCapitalize="characters" onChange={(e) => set({ vin: e.target.value.toUpperCase().replace(/\s/g, "") })} />
          <Button type="button" variant="secondary" disabled={v.vin.length !== 17} onClick={lookUp}>{t("market.lookUp")}</Button>
        </div>
        <p className="mt-1 text-base">{t("market.vinHint")}</p>
      </div>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="vyr">{t("market.year")}</Label>
          <Input id="vyr" required type="number" inputMode="numeric" min="1900" max={new Date().getFullYear() + 1} value={v.year} onChange={(e) => set({ year: e.target.value, model_id: null })} />
        </div>
        <div>
          <Label htmlFor="vmk">{t("market.make")}</Label>
          <Select id="vmk" required value={v.make_id ?? ""} onChange={(e) => set({ make_id: e.target.value ? Number(e.target.value) : null, model_id: null })}>
            <option value="" />
            {makes.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>
      </div>
      <div>
        <Label htmlFor="vmd">{t("market.model")}</Label>
        <Select id="vmd" value={v.model_id ?? ""} onChange={(e) => set({ model_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">—</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </Select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="vts">{t("market.titleStatus")}</Label>
          <Select id="vts" value={v.title_status} onChange={(e) => set({ title_status: e.target.value })}>
            {TITLE_STATUSES.map((x) => <option key={x} value={x}>{t(`market.titleStatuses.${x}`)}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="vrn">{t("market.running")}</Label>
          <Select id="vrn" value={v.running} onChange={(e) => set({ running: e.target.value })}>
            {RUNNING.map((x) => <option key={x} value={x}>{t(`market.runnings.${x}`)}</option>)}
          </Select>
        </div>
      </div>
      <label className="flex min-h-14 items-center gap-3 text-lg font-semibold">
        <input type="checkbox" className="size-7" checked={v.has_lien} onChange={(e) => set({ has_lien: e.target.checked })} />
        {t("market.hasLien")}
      </label>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="vod">{t("market.odometer")}</Label>
          <Input id="vod" type="number" inputMode="numeric" min="0" value={v.odometer} onChange={(e) => set({ odometer: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="vou">{t("market.odometerUnit")}</Label>
          <Select id="vou" value={v.odometer_unit} onChange={(e) => set({ odometer_unit: e.target.value as "mi" | "km" })}>
            <option value="mi">mi</option>
            <option value="km">km</option>
          </Select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {field("vtr", "trim", t("market.trim"), 60)}
        {field("vcl", "exterior_color", t("market.color"))}
        {field("vdr", "drive", t("market.drive"))}
        {field("vtx", "transmission", t("market.transmission"))}
      </div>
    </Card>
  );
}

type Form = {
  title: string;
  description: string;
  category: string;
  condition: string;
  brand: string;
  part_number: string;
  price: string; // dollars, as typed
  quantity: number;
  shipping: string;
  shipping_note: string;
  shipping_price: string; // dollars, as typed
  source_vin: string;
  mileage: string;
  emissions_compliance: string;
  carb_eo_number: string;
  fitment: AppliesTo[];
  photo_ids: number[];
  vehicle: VForm;
  accept_rules: boolean;
};

const EMPTY: Form = {
  title: "", description: "", category: "", condition: "used", brand: "", part_number: "", price: "",
  quantity: 1, shipping: "pickup_or_ships", shipping_note: "", shipping_price: "", source_vin: "", mileage: "",
  emissions_compliance: "", carb_eo_number: "", fitment: [], photo_ids: [], vehicle: EMPTY_V, accept_rules: false,
};

function fromListing(l: Listing): Form {
  return {
    title: l.title, description: l.description, category: l.category, condition: l.condition,
    brand: l.brand ?? "", part_number: l.part_number ?? "", price: (l.price_cents / 100).toFixed(2),
    quantity: l.quantity, shipping: l.shipping, shipping_note: l.shipping_note ?? "",
    shipping_price: l.shipping_cents != null ? (l.shipping_cents / 100).toFixed(2) : "",
    source_vin: l.source_vin ?? "", mileage: l.mileage != null ? String(l.mileage) : "",
    emissions_compliance: l.emissions_compliance ?? "", carb_eo_number: l.carb_eo_number ?? "",
    fitment: l.fitment.map(({ make_id, model_id, year_from, year_to, displacement_l, engine_family_id }) =>
      ({ make_id, model_id, year_from, year_to, displacement_l, engine_family_id })),
    photo_ids: l.photos.map((p) => p.id), accept_rules: false,
    vehicle: l.vehicle ? {
      vin: l.vehicle.vin ?? "", year: String(l.vehicle.year), make_id: l.vehicle.make_id ?? null,
      model_id: l.vehicle.model_id ?? null, odometer: l.vehicle.odometer != null ? String(l.vehicle.odometer) : "",
      odometer_unit: l.vehicle.odometer_unit, title_status: l.vehicle.title_status, has_lien: l.vehicle.has_lien,
      running: l.vehicle.running, trim: l.vehicle.trim ?? "", drive: l.vehicle.drive ?? "",
      transmission: l.vehicle.transmission ?? "", exterior_color: l.vehicle.exterior_color ?? "",
    } : EMPTY_V,
  };
}

const MAX_PHOTOS = 20;

export default function ListingEditPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const nav = useNavigate();
  const { user, loading } = useAuth();
  const [search] = useSearchParams();
  const startAsVehicle = !id && search.get("kind") === "vehicle";
  useDocumentTitle(t(id ? "market.editTitle" : startAsVehicle ? "market.sellVehicle" : "market.sell"));
  const [seller, setSeller] = useState<Seller | null | undefined>(undefined);
  const [f, setF] = useState<Form | null>(
    id ? null : startAsVehicle ? { ...EMPTY, category: "vehicle", shipping: "pickup" } : EMPTY,
  );
  const [cats, setCats] = useState<string[]>([]);
  const [makes, setMakes] = useState<NamedRef[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const paymentsOn = useModule("market_payments");
  const [payCfg, setPayCfg] = useState<PaymentsConfig | null>(null);
  useEffect(() => {
    if (paymentsOn) api<PaymentsConfig>("/market/payments/config").then(setPayCfg).catch(() => undefined);
  }, [paymentsOn]);

  useEffect(() => {
    if (!user) return;
    api<Seller | null>("/market/seller/me").then(setSeller).catch(() => setSeller(null));
    api<{ slug: string }[]>("/market/categories").then((c) => setCats(c.map((x) => x.slug))).catch(() => undefined);
    api<NamedRef[]>("/vehicles/makes").then(setMakes).catch(() => undefined);
    if (id) api<Listing>(`/market/listings/${id}`).then((l) => setF(fromListing(l))).catch((e) => setError(errorMessage(t, e)));
  }, [user, id, t]);

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  if (error && !f) return <Alert>{error}</Alert>;
  if (seller === undefined || !f) return <Spinner label={t("app.loading")} />;
  if (!seller)
    return (
      <div className="space-y-5">
        <PageTitle>{t("market.becomeSeller")}</PageTitle>
        <p className="text-lg">{t("market.becomeSellerIntro")}</p>
        <SellerForm seller={null} onSaved={setSeller} />
      </div>
    );

  const set = (patch: Partial<Form>) => setF((cur) => cur && { ...cur, ...patch });
  const setVehicle = (patch: Partial<VForm>) => setF((cur) => cur && { ...cur, vehicle: { ...cur.vehicle, ...patch } });
  const year = new Date().getFullYear();
  const isCat = f.category === "catalytic_converter";
  const isVehicle = f.category === "vehicle";
  const vf = f.vehicle;
  const used = f.condition !== "new";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!f) return;
    setBusy(true);
    setError(null);
    const body = {
      title: f.title, description: f.description, category: f.category, condition: f.condition,
      brand: f.brand || null, part_number: f.part_number || null,
      price_cents: Math.round(parseFloat(f.price || "0") * 100), quantity: f.quantity,
      shipping: f.shipping, shipping_note: f.shipping_note || null,
      shipping_cents: f.shipping !== "pickup" && f.shipping_price !== "" && !isVehicle ? Math.round(parseFloat(f.shipping_price) * 100) : null,
      source_vin: f.source_vin || null, mileage: f.mileage ? parseInt(f.mileage, 10) : null,
      emissions_compliance: f.emissions_compliance || null, carb_eo_number: f.carb_eo_number || null,
      fitment: isVehicle ? [] : f.fitment, photo_ids: f.photo_ids, accept_rules: f.accept_rules,
      vehicle: isVehicle ? {
        vin: vf.vin || null, year: parseInt(vf.year, 10), make_id: vf.make_id, model_id: vf.model_id,
        odometer: vf.odometer ? parseInt(vf.odometer, 10) : null, odometer_unit: vf.odometer_unit,
        title_status: vf.title_status, has_lien: vf.has_lien, running: vf.running, trim: vf.trim || null,
        drive: vf.drive || null, transmission: vf.transmission || null, exterior_color: vf.exterior_color || null,
      } : null,
    };
    if (isVehicle) Object.assign(body, { quantity: 1, part_number: null, brand: null, source_vin: null, mileage: null, emissions_compliance: null, carb_eo_number: null });
    try {
      const l = await api<Listing>(id ? `/market/listings/${id}` : "/market/listings", { method: id ? "PUT" : "POST", body });
      nav(`/market/listings/${l.id}`);
    } catch (err) {
      setError(errorMessage(t, err));
      setBusy(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={submit}>
      <PageTitle>{t(id ? "market.editTitle" : isVehicle ? "market.sellVehicle" : "market.sell")}</PageTitle>
      {!id && (
        <div role="tablist" className="grid grid-cols-2 gap-2">
          {[false, true].map((veh) => (
            <button key={String(veh)} type="button" role="tab" aria-selected={isVehicle === veh}
              onClick={() => set(veh ? { category: "vehicle", shipping: "pickup", condition: "used" } : { category: "" })}
              className={`min-h-14 rounded-xl border-2 text-lg font-bold ${isVehicle === veh ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-400"}`}>
              {t(veh ? "market.aVehicle" : "market.aPart")}
            </button>
          ))}
        </div>
      )}
      {isVehicle && <VehicleFields v={vf} set={setVehicle} makes={makes}
        onDecoded={(label) => setF((cur) => cur && (cur.title ? cur : { ...cur, title: label }))} />}
      <Card className="space-y-4">
        <TextField id="lt" label={t("market.listingTitle")} hint={t(isVehicle ? "market.vehicleTitleHint" : "market.listingTitleHint")} value={f.title} max={120} required onChange={(v) => set({ title: v })} />
        {!isVehicle && <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="lc">{t("market.category")}</Label>
            <Select id="lc" required value={f.category} onChange={(e) => set({ category: e.target.value })}>
              <option value="" />
              {cats.filter((c) => c !== "vehicle").map((c) => <option key={c} value={c}>{t(`market.categories.${c}`)}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="lcond">{t("market.condition")}</Label>
            <Select id="lcond" value={f.condition} onChange={(e) => set({ condition: e.target.value })}>
              {CONDITIONS.map((c) => <option key={c} value={c}>{t(`market.conditions.${c}`)}</option>)}
            </Select>
          </div>
        </div>}
        {f.category === "airbag_srs" && <Alert kind="warning">{t("market.rules.srs")}</Alert>}
        {isCat && <Alert kind="warning">{t("market.rules.cat")}</Alert>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="lp">{t("market.price")}</Label>
            <Input id="lp" required inputMode="decimal" type="number" min="0" step="0.01" value={f.price} onChange={(e) => set({ price: e.target.value })} />
          </div>
          {!isVehicle && <div>
            <Label htmlFor="lq">{t("market.quantity")}</Label>
            <Input id="lq" type="number" min="1" max="999" step="1" value={f.quantity} onChange={(e) => set({ quantity: Math.max(1, parseInt(e.target.value || "1", 10)) })} />
          </div>}
        </div>
        <TextArea id="ld" label={t("market.description")} hint={t(isVehicle ? "market.vehicleDescriptionHint" : "market.descriptionHint")} value={f.description} max={5000} rows={5} onChange={(v) => set({ description: v })} />
        {!isVehicle && <div className="grid grid-cols-2 gap-3">
          <TextField id="lb" label={t("market.brand")} value={f.brand} max={60} onChange={(v) => set({ brand: v })} />
          <TextField id="lpn" label={t("market.partNumber")} value={f.part_number} max={60} onChange={(v) => set({ part_number: v })} />
        </div>}
        {used && !isVehicle && (
          <div className="grid grid-cols-2 gap-3">
            <TextField id="lv" label={t("market.sourceVin")} hint={t("market.sourceVinHint")} value={f.source_vin} max={17} onChange={(v) => set({ source_vin: v.toUpperCase() })} />
            <div>
              <Label htmlFor="lm">{t("market.mileage")}</Label>
              <Input id="lm" type="number" min="0" step="1" inputMode="numeric" value={f.mileage} onChange={(e) => set({ mileage: e.target.value })} />
            </div>
          </div>
        )}
        {(isCat || f.category === "emissions") && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="lec">{t("market.compliance")}</Label>
              <Select id="lec" value={f.emissions_compliance} onChange={(e) => set({ emissions_compliance: e.target.value })}>
                <option value="">—</option>
                <option value="epa">{t("market.compliances.epa")}</option>
                <option value="carb">{t("market.compliances.carb")}</option>
              </Select>
            </div>
            {f.emissions_compliance === "carb" && (
              <TextField id="leo" label={t("market.carbEo")} value={f.carb_eo_number} max={30} onChange={(v) => set({ carb_eo_number: v })} />
            )}
          </div>
        )}
        <div>
          <Label htmlFor="ls">{t("market.shipping")}</Label>
          <Select id="ls" value={f.shipping} onChange={(e) => set({ shipping: e.target.value })}>
            {["pickup", "ships", "pickup_or_ships"].map((s) => <option key={s} value={s}>{t(`market.shippings.${s}`)}</option>)}
          </Select>
        </div>
        {f.shipping !== "pickup" && !isVehicle && (
          <div>
            <Label htmlFor="lsp">{t("pay.shippingPrice")}</Label>
            <Input id="lsp" type="number" inputMode="decimal" min="0" step="0.01" value={f.shipping_price} onChange={(e) => set({ shipping_price: e.target.value })} />
            <p className="mt-1 text-base">{t("pay.shippingPriceHint")}</p>
          </div>
        )}
        <TextField id="lsn" label={t("market.shippingNote")} value={f.shipping_note} max={300} onChange={(v) => set({ shipping_note: v })} />
        {payCfg?.enabled && !isVehicle && !payCfg.contact_only_categories.includes(f.category) && (
          <FeeBreakdown cfg={payCfg} priceCents={Math.round(parseFloat(f.price || "0") * 100) || 0}
            shippingCents={Math.round(parseFloat(f.shipping_price || "0") * 100) || 0}
            ships={f.shipping !== "pickup" && f.shipping_price !== ""} />
        )}
      </Card>

      {!isVehicle && <Card className="space-y-4">
        <h2 className="text-xl font-bold">{t("market.fits")}</h2>
        <p className="text-lg">{f.fitment.length === 0 ? t("market.fitsAllHint") : t("market.fitsHint")}</p>
        {f.fitment.map((r, i) => (
          <RangeRow key={i} idx={i} r={r} makes={makes}
            onChange={(nr) => set({ fitment: f.fitment.map((x, j) => (j === i ? nr : x)) })}
            onRemove={() => set({ fitment: f.fitment.filter((_, j) => j !== i) })} />
        ))}
        <Button type="button" variant="secondary" className="w-full" disabled={!makes.length || f.fitment.length >= 30}
          onClick={() => set({ fitment: [...f.fitment, { make_id: makes[0].id, model_id: null, year_from: year - 5, year_to: year }] })}>
          + {t("editor.addVehicleRange")}
        </Button>
      </Card>}

      <Card className="space-y-3">
        <h2 className="text-xl font-bold">{t("market.photos")} ({f.photo_ids.length}/{MAX_PHOTOS})</h2>
        <div className="grid grid-cols-2 gap-3">
          {f.photo_ids.map((pid) => (
            <PhotoField key={pid} photoId={pid} onChange={() => set({ photo_ids: f.photo_ids.filter((x) => x !== pid) })} />
          ))}
        </div>
        {f.photo_ids.length < MAX_PHOTOS && <PhotoField photoId={null} onChange={(pid) => pid && set({ photo_ids: [...f.photo_ids, pid] })} />}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-xl font-bold">{t("market.rules.title")}</h2>
        <ul className="list-disc space-y-1 pl-6 text-lg">
          {(isVehicle ? ["vehLegal", "vehTitle", "vehDealer", "vehOdometer", "honest"] : ["legal", "noDefeat", "noSrs", "cats", "recall", "honest"])
            .map((k) => <li key={k}>{t(`market.rules.${k}`)}</li>)}
        </ul>
        <label className="flex min-h-14 items-center gap-3 text-lg font-semibold">
          <input type="checkbox" className="size-7" checked={f.accept_rules} onChange={(e) => set({ accept_rules: e.target.checked })} />
          {t("market.rules.accept")}
        </label>
      </Card>

      {error && <Alert>{error}</Alert>}
      <Button type="submit" className="w-full" disabled={busy || !f.accept_rules}>
        {busy ? t("app.loading") : t(id ? "market.saveListing" : "market.publish")}
      </Button>
    </form>
  );
}
