import { useEffect, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Select, Spinner } from "../../components/ui";
import MakeOptions from "../../components/MakeOptions";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useModule } from "../../lib/modules";
import { useDocumentTitle } from "../../lib/title";
import type { GarageItem, Make, Vehicle } from "../../lib/types";
import { CONDITIONS, RUNNING, TITLE_STATUSES, US_STATES, price, type ListingSummary, type VehicleFacts } from "./types";

export function vehicleLine(t: TFunction, v: VehicleFacts): string {
  return [
    v.odometer != null ? `${v.odometer.toLocaleString()} ${v.odometer_unit}` : null,
    t(`market.titleStatuses.${v.title_status}`),
    t(`market.runnings.${v.running}`),
    v.has_keys == null ? null : v.has_keys ? t("market.keysYes") : t("market.keysNo"),
    v.damage ? t("market.damageShort", { damage: v.damage }) : null,
  ].filter(Boolean).join(" · ");
}

/** Yard line for a vehicle card: row / stock number and when it arrived on the lot. */
export function yardLine(t: TFunction, v: VehicleFacts): string {
  return [v.stock_number, v.arrived_on ? t("market.arrived", { date: formatDate(v.arrived_on) }) : null]
    .filter(Boolean).join(" · ");
}

// Per-device convenience: remember the buyer's ZIP for distance search (never sent anywhere else).
export function readZip(): string {
  try {
    return localStorage.getItem("cc_market_zip") ?? "";
  } catch {
    return "";
  }
}
function rememberZip(z: string) {
  try {
    if (z) localStorage.setItem("cc_market_zip", z);
    else localStorage.removeItem("cc_market_zip");
  } catch {
    /* storage blocked: fine */
  }
}

export function ListingCard({ l }: { l: ListingSummary }) {
  const { t } = useTranslation();
  return (
    <Link to={`/market/listings/${l.id}`} className="flex gap-3 rounded-2xl border-2 border-slate-200 p-3 hover:border-amber-400 dark:border-slate-800">
      {l.photo_url ? (
        <img src={l.photo_url} alt="" loading="lazy" className="size-24 shrink-0 rounded-xl object-cover" />
      ) : (
        <div aria-hidden="true" className="flex size-24 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-3xl dark:bg-slate-900">
          {l.kind === "vehicle" ? "🚗" : "🔧"}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xl font-extrabold">
          {l.price_cents === 0 ? t("market.free") : price(l.price_cents, l.currency)}
          {l.saved && <span className="ml-2 text-amber-600" aria-label={t("market.saved")}>★</span>}
        </p>
        <h3 className="line-clamp-2 text-lg font-bold">{l.title}</h3>
        {l.vehicle ? (
          <>
            {l.vehicle.lien_sale_after && (
              <p className="my-1 inline-block rounded-md bg-amber-400 px-2 py-0.5 text-base font-bold text-slate-950">
                {t("market.lienSaleAfter", { date: formatDate(l.vehicle.lien_sale_after) })}
              </p>
            )}
            <p className="text-base">{vehicleLine(t, l.vehicle)}</p>
            {yardLine(t, l.vehicle) && <p className="text-base font-semibold">{yardLine(t, l.vehicle)}</p>}
          </>
        ) : (
          <p className="text-base">{t(`market.conditions.${l.condition}`)}</p>
        )}
        <p className="text-base">
          {l.city}, {l.state}
          {l.distance_mi != null && <> · {t("market.milesAway", { count: l.distance_mi })}</>}
          {l.seller_verified && <> · <span className="font-semibold text-emerald-700 dark:text-emerald-400">✓ {t("market.verified")}</span></>}
        </p>
        {l.status !== "active" && <p className="font-bold uppercase text-amber-700 dark:text-amber-400">{t(`market.statuses.${l.status}`)}</p>}
      </div>
    </Link>
  );
}

function FilterSelect({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: [string, string][]; onChange: (v: string) => void }) {
  const { t } = useTranslation();
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t("market.all")}</option>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </Select>
    </div>
  );
}

export default function MarketPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const paymentsOn = useModule("market_payments");
  const [params, setParams] = useSearchParams();
  const kind = params.get("kind") === "vehicle" ? "vehicle" : "part";
  useDocumentTitle(t(kind === "vehicle" ? "market.vehiclesTitle" : "market.title"));
  const [q, setQ] = useState(params.get("q") ?? "");
  const [cats, setCats] = useState<string[]>([]);
  const [makes, setMakes] = useState<Make[]>([]);
  const [garage, setGarage] = useState<Vehicle[]>([]);
  const [linked, setLinked] = useState<Vehicle | null>(null);
  const [data, setData] = useState<{ total: number; items: ListingSummary[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const vehicleId = params.get("vehicle_id") ?? "";
  const activeFilters = [...params.keys()].filter((k) => !["q", "kind", "sort", "radius_mi"].includes(k) && params.get(k)).length;
  const [showFilters, setShowFilters] = useState(false);
  const [zip, setZip] = useState(params.get("near_zip") ?? readZip());

  useEffect(() => {
    api<{ slug: string }[]>("/market/categories").then((c) => setCats(c.map((x) => x.slug).filter((x) => x !== "vehicle"))).catch(() => undefined);
    api<Make[]>("/vehicles/makes").then(setMakes).catch(() => undefined);
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
    qs.set("kind", kind);
    if (kind === "vehicle") qs.delete("vehicle_id");
    api<{ total: number; items: ListingSummary[] }>(`/market/listings?${qs}`)
      .then(setData)
      .catch((e) => setError(errorMessage(t, e)));
  }, [params, kind, t]);

  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };
  const applyZip = () => {
    const z = zip.trim();
    if (z && !/^\d{5}$/.test(z)) return;
    if (z === (params.get("near_zip") ?? "")) return;
    rememberZip(z);
    set("near_zip", z);
  };
  const switchKind = (k: string) => {
    const next = new URLSearchParams();
    if (k === "vehicle") next.set("kind", "vehicle");
    for (const keep of ["near_zip", "radius_mi"]) {
      const v = params.get(keep);
      if (v) next.set(keep, v);
    }
    setParams(next, { replace: true });
  };
  const vehicles = linked ? [linked, ...garage] : garage;
  const years = Array.from({ length: new Date().getFullYear() + 2 - 1950 }, (_, i) => String(new Date().getFullYear() + 1 - i));

  return (
    <div className="space-y-5">
      <PageTitle>{t("market.title")}</PageTitle>
      <div role="tablist" className="grid grid-cols-2 gap-2">
        {(["part", "vehicle"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={kind === k} onClick={() => switchKind(k)}
            className={`min-h-14 rounded-xl border-2 text-lg font-bold ${kind === k ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-400"}`}>
            {t(k === "vehicle" ? "market.tabVehicles" : "market.tabParts")}
          </button>
        ))}
      </div>
      <LinkButton to={kind === "vehicle" ? "/market/sell?kind=vehicle" : "/market/sell"} className="w-full">
        {t(kind === "vehicle" ? "market.sellVehicle" : "market.sell")}
      </LinkButton>

      <Card className="space-y-3">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); set("q", q.trim()); }}>
          <label htmlFor="mq" className="sr-only">{t("market.searchLabel")}</label>
          <Input id="mq" type="search" value={q} placeholder={t(kind === "vehicle" ? "market.searchVehiclesPlaceholder" : "market.searchPlaceholder")} onChange={(e) => setQ(e.target.value)} />
          <Button type="submit">{t("market.searchButton")}</Button>
        </form>
        <Button type="button" variant="secondary" className="w-full" aria-expanded={showFilters} aria-controls="market-filters"
          onClick={() => setShowFilters(!showFilters)}>
          {showFilters ? "▲" : "▼"} {activeFilters ? t("market.filtersActive", { count: activeFilters }) : t("market.filters")}
        </Button>
        {showFilters && <div id="market-filters" className="space-y-3">
        {kind === "part" ? (
          <>
            <div>
              <Label htmlFor="mv">{t("market.fitsVehicle")}</Label>
              <Select id="mv" value={vehicleId} onChange={(e) => set("vehicle_id", e.target.value)}>
                <option value="">{t("market.anyVehicle")}</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FilterSelect id="mc" label={t("market.category")} value={params.get("category") ?? ""} onChange={(v) => set("category", v)}
                options={cats.map((c) => [c, t(`market.categories.${c}`)])} />
              <FilterSelect id="mcond" label={t("market.condition")} value={params.get("condition") ?? ""} onChange={(v) => set("condition", v)}
                options={CONDITIONS.map((c) => [c, t(`market.conditions.${c}`)])} />
            </div>
          </>
        ) : (
          <>
            <div>
              <Label htmlFor="vmk">{t("market.make")}</Label>
              <Select id="vmk" value={params.get("make_id") ?? ""} onChange={(e) => set("make_id", e.target.value)}>
                <option value="">{t("market.all")}</option>
                <MakeOptions makes={makes} />
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FilterSelect id="vy1" label={t("market.yearMin")} value={params.get("year_min") ?? ""} onChange={(v) => set("year_min", v)} options={years.map((y) => [y, y])} />
              <FilterSelect id="vy2" label={t("market.yearMax")} value={params.get("year_max") ?? ""} onChange={(v) => set("year_max", v)} options={years.map((y) => [y, y])} />
              <FilterSelect id="vts" label={t("market.titleStatus")} value={params.get("title_status") ?? ""} onChange={(v) => set("title_status", v)}
                options={TITLE_STATUSES.map((s) => [s, t(`market.titleStatuses.${s}`)])} />
              <FilterSelect id="vrn" label={t("market.running")} value={params.get("running") ?? ""} onChange={(v) => set("running", v)}
                options={RUNNING.map((s) => [s, t(`market.runnings.${s}`)])} />
            </div>
          </>
        )}
        <form className="grid grid-cols-2 gap-3" onSubmit={(e) => { e.preventDefault(); applyZip(); }}>
          <div>
            <Label htmlFor="mzip">{t("market.nearZip")}</Label>
            <Input id="mzip" inputMode="numeric" pattern="\d{5}" maxLength={5} value={zip} onChange={(e) => setZip(e.target.value)} onBlur={applyZip} />
          </div>
          <div>
            <Label htmlFor="mrad">{t("market.within")}</Label>
            <Select id="mrad" value={params.get("radius_mi") ?? "50"} onChange={(e) => set("radius_mi", e.target.value)} disabled={!params.get("near_zip")}>
              {["10", "25", "50", "100", "250", "500"].map((r) => <option key={r} value={r}>{t("market.miles", { count: Number(r) })}</option>)}
            </Select>
          </div>
        </form>
        <div className="grid grid-cols-2 gap-3">
          <FilterSelect id="mst" label={t("market.state")} value={params.get("state") ?? ""} onChange={(v) => set("state", v)}
            options={US_STATES.map((s) => [s, s])} />
          <div>
            <Label htmlFor="ms">{t("market.sort")}</Label>
            <Select id="ms" value={params.get("sort") ?? "newest"} onChange={(e) => set("sort", e.target.value)}>
              {["newest", "price_low", "price_high", ...(params.get("near_zip") ? ["nearest"] : [])].map((s) => <option key={s} value={s}>{t(`market.sorts.${s}`)}</option>)}
            </Select>
          </div>
        </div>
        {activeFilters > 0 && (
          <Button type="button" variant="secondary" className="w-full" onClick={() => setParams(kind === "vehicle" ? { kind: "vehicle" } : {}, { replace: true })}>
            {t("market.clearFilters")}
          </Button>
        )}
        </div>}
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
      <div className="grid grid-cols-2 gap-3">
        <LinkButton to="/market/selling" variant="secondary">{t("market.mySelling")}</LinkButton>
        <LinkButton to="/market/messages" variant="secondary">{t("market.messages")}</LinkButton>
        <LinkButton to="/market/saved" variant="secondary">★ {t("market.savedTitle")}</LinkButton>
        {paymentsOn && <LinkButton to="/market/orders" variant="secondary" className="col-span-2">{t("orders.title")}</LinkButton>}
        {user && (user.role === "moderator" || user.role === "admin") && (
          <LinkButton to="/market/mod" variant="secondary" className="col-span-2">{t("market.mod.title")}</LinkButton>
        )}
      </div>
      <p className="text-lg">{t("market.intro")}</p>
      <Alert kind="info">{t(kind === "vehicle" ? "market.vehicleTips" : "market.safetyTips")}</Alert>
      <p className="text-base">
        <Link className="underline" to="/legal/terms">{t("legal.terms")}</Link> · <Link className="underline" to="/legal/prohibited-items">{t("legal.prohibited-items")}</Link>
      </p>
    </div>
  );
}
