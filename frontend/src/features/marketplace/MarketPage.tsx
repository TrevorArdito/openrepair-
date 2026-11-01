import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Select, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { useDocumentTitle } from "../../lib/title";
import type { GarageItem, Vehicle } from "../../lib/types";
import { CONDITIONS, price, type ListingSummary } from "./types";

export function ListingCard({ l }: { l: ListingSummary }) {
  const { t } = useTranslation();
  return (
    <Link to={`/market/listings/${l.id}`} className="flex gap-3 rounded-2xl border-2 border-slate-200 p-3 hover:border-amber-400 dark:border-slate-800">
      {l.photo_url ? (
        <img src={l.photo_url} alt="" loading="lazy" className="size-24 shrink-0 rounded-xl object-cover" />
      ) : (
        <div aria-hidden="true" className="flex size-24 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-3xl dark:bg-slate-900">🔧</div>
      )}
      <div className="min-w-0">
        <p className="text-xl font-extrabold">{l.price_cents === 0 ? t("market.free") : price(l.price_cents, l.currency)}</p>
        <h3 className="line-clamp-2 text-lg font-bold">{l.title}</h3>
        <p className="text-base">
          {t(`market.conditions.${l.condition}`)} · {l.city}, {l.state}
          {l.seller_verified && <> · <span className="font-semibold text-emerald-700 dark:text-emerald-400">✓ {t("market.verified")}</span></>}
        </p>
        {l.status !== "active" && <p className="font-bold uppercase text-amber-700 dark:text-amber-400">{t(`market.statuses.${l.status}`)}</p>}
      </div>
    </Link>
  );
}

export default function MarketPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  useDocumentTitle(t("market.title"));
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [cats, setCats] = useState<string[]>([]);
  const [garage, setGarage] = useState<Vehicle[]>([]);
  const [linked, setLinked] = useState<Vehicle | null>(null);
  const [data, setData] = useState<{ total: number; items: ListingSummary[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const vehicleId = params.get("vehicle_id") ?? "";

  useEffect(() => {
    api<{ slug: string }[]>("/market/categories").then((c) => setCats(c.map((x) => x.slug))).catch(() => undefined);
  }, []);
  useEffect(() => {
    if (!user) return;
    api<GarageItem[]>("/garage").then((g) => setGarage(g.map((x) => x.vehicle))).catch(() => undefined);
  }, [user]);
  useEffect(() => {
    if (!vehicleId || garage.some((v) => String(v.id) === vehicleId)) return setLinked(null);
    api<Vehicle>(`/vehicles/${vehicleId}`).then(setLinked).catch(() => setLinked(null));
  }, [vehicleId, garage]);
  useEffect(() => {
    setData(null);
    setError(null);
    const qs = new URLSearchParams([...params].filter(([, v]) => v));
    api<{ total: number; items: ListingSummary[] }>(`/market/listings?${qs}`)
      .then(setData)
      .catch((e) => setError(errorMessage(t, e)));
  }, [params, t]);

  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };
  const vehicles = linked ? [linked, ...garage] : garage;

  return (
    <div className="space-y-5">
      <PageTitle>{t("market.title")}</PageTitle>
      <p className="text-lg">{t("market.intro")}</p>
      <div className="grid grid-cols-2 gap-3">
        <LinkButton to="/market/sell">{t("market.sell")}</LinkButton>
        <LinkButton to="/market/selling" variant="secondary">{t("market.mySelling")}</LinkButton>
        <LinkButton to="/market/messages" variant="secondary">{t("market.messages")}</LinkButton>
        {user && (user.role === "moderator" || user.role === "admin") && (
          <LinkButton to="/market/mod" variant="secondary">{t("market.mod.title")}</LinkButton>
        )}
      </div>

      <Card className="space-y-3">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); set("q", q.trim()); }}>
          <label htmlFor="mq" className="sr-only">{t("market.searchLabel")}</label>
          <Input id="mq" type="search" value={q} placeholder={t("market.searchPlaceholder")} onChange={(e) => setQ(e.target.value)} />
          <Button type="submit">{t("market.searchButton")}</Button>
        </form>
        <div>
          <Label htmlFor="mv">{t("market.fitsVehicle")}</Label>
          <Select id="mv" value={vehicleId} onChange={(e) => set("vehicle_id", e.target.value)}>
            <option value="">{t("market.anyVehicle")}</option>
            {vehicles.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="mc">{t("market.category")}</Label>
            <Select id="mc" value={params.get("category") ?? ""} onChange={(e) => set("category", e.target.value)}>
              <option value="">{t("market.all")}</option>
              {cats.map((c) => <option key={c} value={c}>{t(`market.categories.${c}`)}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="mcond">{t("market.condition")}</Label>
            <Select id="mcond" value={params.get("condition") ?? ""} onChange={(e) => set("condition", e.target.value)}>
              <option value="">{t("market.all")}</option>
              {CONDITIONS.map((c) => <option key={c} value={c}>{t(`market.conditions.${c}`)}</option>)}
            </Select>
          </div>
        </div>
        <div>
          <Label htmlFor="ms">{t("market.sort")}</Label>
          <Select id="ms" value={params.get("sort") ?? "newest"} onChange={(e) => set("sort", e.target.value)}>
            {["newest", "price_low", "price_high"].map((s) => <option key={s} value={s}>{t(`market.sorts.${s}`)}</option>)}
          </Select>
        </div>
      </Card>

      {error && <Alert>{error}</Alert>}
      {!data && !error && <Spinner label={t("app.loading")} />}
      {data && (
        <>
          <p className="font-semibold">{t("market.count", { count: data.total })}</p>
          {data.items.length === 0 && <p className="text-lg">{t("market.none")}</p>}
          <div className="space-y-3">{data.items.map((l) => <ListingCard key={l.id} l={l} />)}</div>
        </>
      )}
      <Alert kind="info">{t("market.safetyTips")}</Alert>
    </div>
  );
}
