import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { AppliesTo, NamedRef } from "../../lib/types";
import { PhotoField, TextArea, TextField } from "../entries/fields";
import { RangeRow } from "../entries/TagsForm";
import { SellerForm } from "./SellingPage";
import { CONDITIONS, type Listing, type Seller } from "./types";

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
  source_vin: string;
  mileage: string;
  emissions_compliance: string;
  carb_eo_number: string;
  fitment: AppliesTo[];
  photo_ids: number[];
  accept_rules: boolean;
};

const EMPTY: Form = {
  title: "", description: "", category: "", condition: "used", brand: "", part_number: "", price: "",
  quantity: 1, shipping: "pickup_or_ships", shipping_note: "", source_vin: "", mileage: "",
  emissions_compliance: "", carb_eo_number: "", fitment: [], photo_ids: [], accept_rules: false,
};

function fromListing(l: Listing): Form {
  return {
    title: l.title, description: l.description, category: l.category, condition: l.condition,
    brand: l.brand ?? "", part_number: l.part_number ?? "", price: (l.price_cents / 100).toFixed(2),
    quantity: l.quantity, shipping: l.shipping, shipping_note: l.shipping_note ?? "",
    source_vin: l.source_vin ?? "", mileage: l.mileage != null ? String(l.mileage) : "",
    emissions_compliance: l.emissions_compliance ?? "", carb_eo_number: l.carb_eo_number ?? "",
    fitment: l.fitment.map(({ make_id, model_id, year_from, year_to, displacement_l, engine_family_id }) =>
      ({ make_id, model_id, year_from, year_to, displacement_l, engine_family_id })),
    photo_ids: l.photos.map((p) => p.id), accept_rules: false,
  };
}

const MAX_PHOTOS = 12;

export default function ListingEditPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const nav = useNavigate();
  const { user, loading } = useAuth();
  useDocumentTitle(t(id ? "market.editTitle" : "market.sell"));
  const [seller, setSeller] = useState<Seller | null | undefined>(undefined);
  const [f, setF] = useState<Form | null>(id ? null : EMPTY);
  const [cats, setCats] = useState<string[]>([]);
  const [makes, setMakes] = useState<NamedRef[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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

  const set = (patch: Partial<Form>) => setF({ ...f, ...patch });
  const year = new Date().getFullYear();
  const isCat = f.category === "catalytic_converter";
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
      source_vin: f.source_vin || null, mileage: f.mileage ? parseInt(f.mileage, 10) : null,
      emissions_compliance: f.emissions_compliance || null, carb_eo_number: f.carb_eo_number || null,
      fitment: f.fitment, photo_ids: f.photo_ids, accept_rules: f.accept_rules,
    };
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
      <PageTitle>{t(id ? "market.editTitle" : "market.sell")}</PageTitle>
      <Card className="space-y-4">
        <TextField id="lt" label={t("market.listingTitle")} hint={t("market.listingTitleHint")} value={f.title} max={120} required onChange={(v) => set({ title: v })} />
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="lc">{t("market.category")}</Label>
            <Select id="lc" required value={f.category} onChange={(e) => set({ category: e.target.value })}>
              <option value="" />
              {cats.map((c) => <option key={c} value={c}>{t(`market.categories.${c}`)}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="lcond">{t("market.condition")}</Label>
            <Select id="lcond" value={f.condition} onChange={(e) => set({ condition: e.target.value })}>
              {CONDITIONS.map((c) => <option key={c} value={c}>{t(`market.conditions.${c}`)}</option>)}
            </Select>
          </div>
        </div>
        {f.category === "airbag_srs" && <Alert kind="warning">{t("market.rules.srs")}</Alert>}
        {isCat && <Alert kind="warning">{t("market.rules.cat")}</Alert>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="lp">{t("market.price")}</Label>
            <Input id="lp" required inputMode="decimal" type="number" min="0" step="0.01" value={f.price} onChange={(e) => set({ price: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="lq">{t("market.quantity")}</Label>
            <Input id="lq" type="number" min="1" max="999" step="1" value={f.quantity} onChange={(e) => set({ quantity: Math.max(1, parseInt(e.target.value || "1", 10)) })} />
          </div>
        </div>
        <TextArea id="ld" label={t("market.description")} hint={t("market.descriptionHint")} value={f.description} max={5000} rows={5} onChange={(v) => set({ description: v })} />
        <div className="grid grid-cols-2 gap-3">
          <TextField id="lb" label={t("market.brand")} value={f.brand} max={60} onChange={(v) => set({ brand: v })} />
          <TextField id="lpn" label={t("market.partNumber")} value={f.part_number} max={60} onChange={(v) => set({ part_number: v })} />
        </div>
        {used && (
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
        <TextField id="lsn" label={t("market.shippingNote")} value={f.shipping_note} max={300} onChange={(v) => set({ shipping_note: v })} />
      </Card>

      <Card className="space-y-4">
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
      </Card>

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
          {["legal", "noDefeat", "noSrs", "cats", "recall", "honest"].map((k) => <li key={k}>{t(`market.rules.${k}`)}</li>)}
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
