import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Alert, Button, Card, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useDocumentTitle } from "../../lib/title";
import { ListingCard } from "./MarketPage";
import { stars, type ListingSummary, type Review, type Seller } from "./types";

export default function SellerPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [s, setS] = useState<Seller | null>(null);
  const [items, setItems] = useState<ListingSummary[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [show, setShow] = useState<"all" | "vehicle" | "part">("all");
  const [make, setMake] = useState("");
  const [shared, setShared] = useState(false);
  const [manual, setManual] = useState(false); // sharing and copying both blocked: show the link
  useDocumentTitle(s?.display_name);
  useEffect(() => {
    api<Seller>(`/market/sellers/${id}`).then(setS).catch((e) => setError(errorMessage(t, e)));
    api<Review[]>(`/market/sellers/${id}/reviews`).then(setReviews).catch(() => undefined);
    api<{ items: ListingSummary[] }>(`/market/listings?seller_id=${id}&limit=50`).then((r) => setItems(r.items)).catch(() => undefined);
  }, [id, t]);

  if (error) return <Alert>{error}</Alert>;
  if (!s) return <Spinner label={t("app.loading")} />;
  const vehicles = items.filter((l) => l.kind === "vehicle");
  const makeCounts = Object.entries(
    vehicles.reduce<Record<string, number>>((acc, l) => ({ ...acc, [l.vehicle!.make]: (acc[l.vehicle!.make] ?? 0) + 1 }), {}),
  ).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const shown = items.filter((l) => (show === "all" || l.kind === show) && (!make || l.vehicle?.make === make));
  const chip = (active: boolean) =>
    `min-h-12 rounded-full border-2 px-4 font-bold ${active ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-300 dark:border-slate-700"}`;
  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title: s!.display_name, url });
      else await navigator.clipboard.writeText(url);
      setShared(true);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setManual(true); // AbortError = closed the share sheet
    }
  }
  return (
    <div className="space-y-5">
      <PageTitle>{s.display_name}</PageTitle>
      <Card className="space-y-1 text-lg">
        <p>{t(`market.sellerTypes.${s.seller_type}`)} · {s.city}, {s.state}</p>
        {s.verified.map((v) => (
          <p key={v} className="font-semibold text-emerald-700 dark:text-emerald-400">✓ {t(`market.verifyKinds.${v}`)} {t("market.checked")}</p>
        ))}
        <p>{t("market.memberSince", { date: formatDate(s.member_since) })}</p>
        <p className="font-semibold">
          {s.rating != null ? <><span className="text-amber-500" aria-hidden="true">{stars(s.rating)}</span> {t("market.ratingOf", { rating: s.rating, count: s.rating_count })}</> : t("market.noReviews")}
        </p>
        {s.about && <p className="whitespace-pre-line pt-2">{s.about}</p>}
      </Card>
      {reviews.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-2xl font-bold">{t("market.reviews")}</h2>
          {reviews.map((r) => (
            <Card key={r.id} className="space-y-1 text-lg">
              <p><span className="text-amber-500" aria-label={t("market.starsN", { count: r.rating })}>{stars(r.rating)}</span> · {r.reviewer_name} · {formatDate(r.created_at)}</p>
              <p className="text-base">{r.listing_title}</p>
              {r.comment && <p>{r.comment}</p>}
            </Card>
          ))}
        </section>
      )}
      <h2 className="text-2xl font-bold">{t("market.listingsBy", { count: s.active_listings })}</h2>
      {items.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {(["all", "vehicle", "part"] as const).map((k) => (
              <button key={k} type="button" className={chip(show === k)} aria-pressed={show === k}
                onClick={() => { setShow(k); if (k === "part") setMake(""); }}>
                {t(`market.inventory.${k}`, { count: k === "all" ? items.length : items.filter((l) => l.kind === k).length })}
              </button>
            ))}
          </div>
          {makeCounts.length > 1 && show !== "part" && (
            <div className="flex flex-wrap gap-2" aria-label={t("market.make")}>
              {makeCounts.map(([name, n]) => (
                <button key={name} type="button" className={chip(make === name)} aria-pressed={make === name}
                  onClick={() => setMake(make === name ? "" : name)}>
                  {name} ({n})
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="space-y-3">{shown.map((l) => <ListingCard key={l.id} l={l} />)}</div>
      <Card className="space-y-2">
        <p className="text-lg font-semibold">{t("market.inventory.shareHint")}</p>
        <Button variant="secondary" className="w-full" onClick={share}>
          {shared ? `✓ ${t("market.inventory.shared")}` : t("market.inventory.share")}
        </Button>
        {manual && (
          <p className="break-all rounded-lg bg-slate-100 p-3 font-mono text-base select-all dark:bg-slate-900">{window.location.href}</p>
        )}
      </Card>
    </div>
  );
}
