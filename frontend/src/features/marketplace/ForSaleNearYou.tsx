import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, LinkButton } from "../../components/ui";
import { api } from "../../lib/api";
import type { Vehicle } from "../../lib/types";
import { ListingCard, readZip } from "./MarketPage";
import type { ListingSummary } from "./types";

type Page = { total: number; items: ListingSummary[] };

/** Vehicle page: parts that fit this vehicle and whole vehicles of the same model, nearest first. */
export default function ForSaleNearYou({ vehicle }: { vehicle: Vehicle }) {
  const { t } = useTranslation();
  const [parts, setParts] = useState<Page | null>(null);
  const [cars, setCars] = useState<Page | null>(null);
  useEffect(() => {
    const zip = readZip();
    const near = zip ? `&near_zip=${zip}&radius_mi=100&sort=nearest` : "";
    api<Page>(`/market/listings?kind=part&vehicle_id=${vehicle.id}&limit=3${near}`).then(setParts).catch(() => setParts(null));
    api<Page>(`/market/listings?kind=vehicle&make_id=${vehicle.make.id}&model_id=${vehicle.model.id}&limit=3${near}`)
      .then(setCars)
      .catch(() => setCars(null));
  }, [vehicle.id, vehicle.make.id, vehicle.model.id]);

  if (!parts?.total && !cars?.total) return null; // nothing for sale: don't show an empty box
  const model = `${vehicle.make.name} ${vehicle.model.name}`;
  return (
    <Card className="space-y-3">
      <h2 className="text-xl font-bold">🛒 {t("market.forSaleNear")}</h2>
      {!!parts?.total && (
        <section className="space-y-2">
          <h3 className="text-lg font-bold">{t("market.partsThatFit", { count: parts.total })}</h3>
          {parts.items.map((l) => <ListingCard key={l.id} l={l} />)}
          <LinkButton to={`/market?vehicle_id=${vehicle.id}`} variant="secondary" className="w-full">{t("market.seeAllParts")}</LinkButton>
        </section>
      )}
      {!!cars?.total && (
        <section className="space-y-2">
          <h3 className="text-lg font-bold">{t("market.sameModelForSale", { count: cars.total, model })}</h3>
          {cars.items.map((l) => <ListingCard key={l.id} l={l} />)}
          <LinkButton to={`/market?kind=vehicle&make_id=${vehicle.make.id}&model_id=${vehicle.model.id}`} variant="secondary" className="w-full">
            {t("market.seeAllVehicles", { model })}
          </LinkButton>
        </section>
      )}
    </Card>
  );
}
