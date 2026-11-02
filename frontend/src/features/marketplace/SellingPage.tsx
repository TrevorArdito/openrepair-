import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { useModule } from "../../lib/modules";
import { TextArea, TextField } from "../entries/fields";
import PaymentsSetup from "./PaymentsSetup";
import { ListingCard } from "./MarketPage";
import { US_STATES, type ListingSummary, type Seller, type Verification } from "./types";

const TYPES = ["individual", "shop", "recycler", "retailer"] as const;

export function SellerForm({ seller, onSaved }: { seller: Seller | null; onSaved: (s: Seller) => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({
    seller_type: seller?.seller_type ?? "individual",
    display_name: seller?.display_name ?? "",
    city: seller?.city ?? "",
    state: seller?.state ?? "",
    postal_code: seller?.postal_code ?? "",
    about: seller?.about ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  return (
    <form
      className="space-y-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          const s = await api<Seller>("/market/seller/me", {
            method: "PUT",
            body: { ...f, postal_code: f.postal_code || null, about: f.about || null },
          });
          setSaved(true);
          onSaved(s);
        } catch (err) {
          setError(errorMessage(t, err));
        }
      }}
    >
      <div>
        <Label htmlFor="st">{t("market.sellerType")}</Label>
        <Select id="st" value={f.seller_type} onChange={(e) => setF({ ...f, seller_type: e.target.value as Seller["seller_type"] })}>
          {TYPES.map((x) => <option key={x} value={x}>{t(`market.sellerTypes.${x}`)}</option>)}
        </Select>
      </div>
      <TextField id="sn" label={t("market.sellerName")} value={f.display_name} max={60} required onChange={(v) => setF({ ...f, display_name: v })} />
      <div className="grid grid-cols-2 gap-3">
        <TextField id="sc" label={t("market.city")} value={f.city} max={60} required onChange={(v) => setF({ ...f, city: v })} />
        <div>
          <Label htmlFor="ss">{t("market.state")}</Label>
          <Select id="ss" required value={f.state} onChange={(e) => setF({ ...f, state: e.target.value })}>
            <option value="" />
            {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </div>
      </div>
      <div>
        <Label htmlFor="sz">{t("market.zip")}</Label>
        <Input id="sz" inputMode="numeric" pattern="\d{5}" maxLength={5} value={f.postal_code} onChange={(e) => setF({ ...f, postal_code: e.target.value })} />
        <p className="mt-1 text-base">{t("market.zipHint")}</p>
      </div>
      <TextArea id="sa" label={t("market.about")} value={f.about} max={2000} rows={3} onChange={(v) => setF({ ...f, about: v })} />
      {error && <Alert>{error}</Alert>}
      {saved && <Alert kind="info">{t("market.saved")}</Alert>}
      <Button type="submit" className="w-full">{t("market.saveProfile")}</Button>
    </form>
  );
}

function Verifications() {
  const { t } = useTranslation();
  const [list, setList] = useState<Verification[]>([]);
  const [f, setF] = useState({ kind: "dismantler_license", license_number: "", issuing_state: "", business_name: "" });
  const [error, setError] = useState<string | null>(null);
  useEffect(() => void api<Verification[]>("/market/seller/me/verifications").then(setList).catch(() => undefined), []);
  return (
    <Card className="space-y-4">
      <h2 className="text-xl font-bold">{t("market.verifyTitle")}</h2>
      <p className="text-lg">{t("market.verifyIntro")}</p>
      {list.map((v) => (
        <p key={v.id} className="text-lg">
          <strong>{t(`market.verifyKinds.${v.kind}`)}</strong> {v.license_number} ({v.issuing_state}) — {t(`market.verifyStatuses.${v.status}`)}
          {v.note && <> · {v.note}</>} · {formatDate(v.created_at)}
        </p>
      ))}
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            const v = await api<Verification>("/market/seller/me/verifications", { method: "POST", body: f });
            setList([v, ...list]);
            setF({ ...f, license_number: "" });
          } catch (err) {
            setError(errorMessage(t, err));
          }
        }}
      >
        <Label htmlFor="vk">{t("market.verifyKind")}</Label>
        <Select id="vk" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
          {["dismantler_license", "dealer_license", "business_license"].map((k) => <option key={k} value={k}>{t(`market.verifyKinds.${k}`)}</option>)}
        </Select>
        <TextField id="vb" label={t("market.businessName")} value={f.business_name} max={120} required onChange={(v) => setF({ ...f, business_name: v })} />
        <div className="grid grid-cols-2 gap-3">
          <TextField id="vn" label={t("market.licenseNumber")} value={f.license_number} max={60} required onChange={(v) => setF({ ...f, license_number: v })} />
          <div>
            <Label htmlFor="vs">{t("market.issuingState")}</Label>
            <Select id="vs" required value={f.issuing_state} onChange={(e) => setF({ ...f, issuing_state: e.target.value })}>
              <option value="" />
              {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </div>
        </div>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" variant="secondary" className="w-full">{t("market.verifySubmit")}</Button>
      </form>
    </Card>
  );
}

export default function SellingPage() {
  const { t } = useTranslation();
  const paymentsOn = useModule("market_payments");
  const { user, loading } = useAuth();
  useDocumentTitle(t("market.mySelling"));
  const [seller, setSeller] = useState<Seller | null | undefined>(undefined);
  const [items, setItems] = useState<ListingSummary[]>([]);
  useEffect(() => {
    if (!user) return;
    api<Seller | null>("/market/seller/me").then(setSeller).catch(() => setSeller(null));
    api<ListingSummary[]>("/market/my/listings").then(setItems).catch(() => undefined);
  }, [user]);

  if (loading) return <Spinner label={t("app.loading")} />;
  if (!user) return <Navigate to="/login" replace />;
  if (seller === undefined) return <Spinner label={t("app.loading")} />;
  return (
    <div className="space-y-5">
      <PageTitle>{t("market.mySelling")}</PageTitle>
      {seller && <LinkButton to="/market/sell" className="w-full">{t("market.sell")}</LinkButton>}
      {seller && (
        <section className="space-y-3">
          <h2 className="text-2xl font-bold">{t("market.myListings")} ({items.length})</h2>
          {items.length === 0 && <p className="text-lg">{t("market.noListingsYet")}</p>}
          {items.map((l) => <ListingCard key={l.id} l={l} />)}
        </section>
      )}
      <Card className="space-y-3">
        <h2 className="text-xl font-bold">{seller ? t("market.sellerProfile") : t("market.becomeSeller")}</h2>
        {!seller && <p className="text-lg">{t("market.becomeSellerIntro")}</p>}
        <SellerForm seller={seller} onSaved={setSeller} />
      </Card>
      {seller && paymentsOn && <PaymentsSetup />}
      {seller && <Verifications />}
    </div>
  );
}
