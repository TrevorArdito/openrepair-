import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Alert, Card, PageTitle, Spinner } from "../../components/ui";
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
  useDocumentTitle(s?.display_name);
  useEffect(() => {
    api<Seller>(`/market/sellers/${id}`).then(setS).catch((e) => setError(errorMessage(t, e)));
    api<Review[]>(`/market/sellers/${id}/reviews`).then(setReviews).catch(() => undefined);
    api<{ items: ListingSummary[] }>(`/market/listings?seller_id=${id}&limit=50`).then((r) => setItems(r.items)).catch(() => undefined);
  }, [id, t]);

  if (error) return <Alert>{error}</Alert>;
  if (!s) return <Spinner label={t("app.loading")} />;
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
      <div className="space-y-3">{items.map((l) => <ListingCard key={l.id} l={l} />)}</div>
    </div>
  );
}
