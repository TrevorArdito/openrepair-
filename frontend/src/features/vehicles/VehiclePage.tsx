import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router-dom";
import { Alert, Button, Card, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useModule } from "../../lib/modules";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { rememberVehicle } from "../../lib/recent";
import { useDocumentTitle } from "../../lib/title";
import CodeSearch from "../codes/CodeSearch";
import EntryList from "../entries/EntryList";
import QuickSpecs from "../entries/QuickSpecs";
import ForSaleNearYou from "../marketplace/ForSaleNearYou";
import { ComplaintsTab, RecallsTab, TsbsTab } from "../safety/SafetyTabs";
import type { RecallList, Vehicle, VehicleProfile, VinDecode } from "../../lib/types";

const TABS = ["overview", "recalls", "tsbs", "complaints", "codes", "guides", "specs"] as const;
type Tab = (typeof TABS)[number];

export default function VehiclePage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const location = useLocation();
  const decode = (location.state as { decode?: VinDecode } | null)?.decode;
  const { user } = useAuth();
  const market = useModule("marketplace");
  const [vehicle, setVehicle] = useState<VehicleProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [recallCount, setRecallCount] = useState<number | null>(null);
  const [engines, setEngines] = useState<Vehicle[]>([]);
  useDocumentTitle(vehicle?.label);

  useEffect(() => {
    // No engine chosen yet? Offer the engines we know for this year + model.
    setEngines([]);
    if (!vehicle || vehicle.engine.label) return;
    api<Vehicle[]>(`/vehicles/engines?year=${vehicle.year}&model_id=${vehicle.model.id}`)
      .then((list) => setEngines(list.filter((v) => v.engine.label)))
      .catch(() => setEngines([]));
  }, [vehicle]);

  useEffect(() => {
    // Recalls matter most: check them as soon as the vehicle opens.
    setRecallCount(null);
    api<RecallList>(`/vehicles/${id}/recalls`)
      .then((r) => setRecallCount(r.total))
      .catch(() => setRecallCount(null));
  }, [id]);

  useEffect(() => {
    setVehicle(null);
    setError(null);
    api<VehicleProfile>(`/vehicles/${id}`)
      .then((v) => {
        setVehicle(v);
        rememberVehicle(v);
      })
      .catch((e) => setError(errorMessage(t, e)));
  }, [id, t]);

  async function addToGarage() {
    setSaveError(null);
    try {
      await api("/garage", {
        method: "POST",
        body: { vehicle_id: Number(id), vin: decode?.vin ?? null },
      });
      setSaved(true);
    } catch (e) {
      setSaveError(errorMessage(t, e));
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!vehicle) return <Spinner label={t("app.loading")} />;

  return (
    <div className="space-y-5">
      <div>
        <p className="text-lg font-semibold text-slate-600 dark:text-slate-300">
          {vehicle.year} · {vehicle.make.name}
        </p>
        <PageTitle>
          {vehicle.model.name}
          <span className="block text-xl font-bold text-slate-700 dark:text-slate-300">
            {vehicle.engine.label ?? t("vehicle.engineNotSpecified")}
          </span>
        </PageTitle>
        {vehicle.engine.family && (
          <Link to={`/engines/${vehicle.engine.family.id}`} className="flex min-h-12 items-center text-lg font-semibold text-amber-700 underline dark:text-amber-400">
            {t("engines.familyLink", { name: vehicle.engine.family.name })}
          </Link>
        )}
        {decode && <p className="font-mono text-base">{t("vehicle.fromVin", { vin: decode.vin })}</p>}
      </div>

      {engines.length > 0 && (
        <Card>
          <p className="mb-2 text-lg font-bold">{t("vehicle.chooseEngine")}</p>
          <div className="flex flex-wrap gap-2">
            {engines.map((e) => (
              <Link key={e.id} to={`/vehicle/${e.id}`} className="inline-flex min-h-12 items-center rounded-lg border-2 border-amber-400 px-4 font-bold">
                {e.engine.label}
                {e.engine.family ? ` · ${e.engine.family.name}` : e.engine.engine_code ? ` · ${e.engine.engine_code}` : ""}
              </Link>
            ))}
          </div>
        </Card>
      )}
      {decode && !decode.check_digit_valid && <Alert kind="warning">{t("vehicle.checkDigitWarning")}</Alert>}
      {!!recallCount && (
        <button type="button" onClick={() => setTab("recalls")} className="block w-full text-left">
          <Alert kind="error">
            <span className="text-lg font-bold">{t("safety.recallAlert", { count: recallCount })}</span>
          </Alert>
        </button>
      )}

      {user ? (
        <Button variant={saved ? "secondary" : "primary"} disabled={saved} onClick={addToGarage} className="w-full">
          {saved ? `✓ ${t("vehicle.inGarage")}` : t("vehicle.addToGarage")}
        </Button>
      ) : (
        <Link to="/login" state={{ from: location.pathname }} className="flex min-h-12 items-center font-bold underline">
          {t("vehicle.loginToSave")}
        </Link>
      )}
      {saveError && <Alert>{saveError}</Alert>}
      <LinkButton to={`/search?vehicle_id=${vehicle.id}`} variant="secondary" className="w-full">
        🔍 {t("search.searchVehicle")}
      </LinkButton>
      {market && (
        <LinkButton to={`/market?vehicle_id=${vehicle.id}`} variant="secondary" className="w-full">
          🛒 {t("market.partsForVehicle")}
        </LinkButton>
      )}

      <div role="tablist" aria-label={vehicle.label} className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {TABS.map((key) => {
          const count = key === "recalls" && recallCount !== null ? recallCount : vehicle.counts[key];
          return (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`min-h-12 shrink-0 rounded-full border-2 px-4 font-bold ${
                tab === key
                  ? "border-amber-400 bg-amber-400 text-slate-950"
                  : "border-slate-300 dark:border-slate-700"
              }`}
            >
              {t(`vehicle.tabs.${key}`)}
              {count ? ` (${count})` : ""}
            </button>
          );
        })}
      </div>

      <div role="tabpanel">
        {tab === "overview" ? (
          <div className="space-y-4">
            <QuickSpecs vehicleId={id!} onShowAll={() => setTab("specs")} />
            {market && <ForSaleNearYou vehicle={vehicle} />}
            <Card>
            <h2 className="mb-2 text-xl font-bold">{t("vehicle.details")}</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-lg">
              <dt className="font-semibold">{t("picker.engine")}</dt>
              <dd>
                {vehicle.engine.label ?? t("vehicle.engineNotSpecified")}
                {vehicle.engine.engine_code ? ` · ${vehicle.engine.engine_code}` : ""}
              </dd>
              {vehicle.engine.fuel_type && (
                <>
                  <dt className="font-semibold">{t("vehicle.fuel")}</dt>
                  <dd>{t(`fuel.${vehicle.engine.fuel_type}`)}</dd>
                </>
              )}
              {decode &&
                Object.entries(decode.details)
                  .filter(([k]) => k !== "engine_model")
                  .map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="font-semibold">{t(`vehicle.fields.${k}`, { defaultValue: k })}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
            </dl>
            {decode && decode.warnings.length > 0 && (
              <details className="mt-3">
                <summary className="min-h-12 cursor-pointer font-semibold">{t("vehicle.nhtsaNotes")}</summary>
                <ul className="list-disc pl-6 text-base">
                  {decode.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </details>
            )}
            {decode && <p className="mt-3 text-base text-slate-600 dark:text-slate-400">{t("vehicle.source", { source: decode.source })}</p>}
          </Card>
          </div>
        ) : tab === "recalls" ? (
          <RecallsTab vehicleId={id!} />
        ) : tab === "tsbs" ? (
          <TsbsTab vehicleId={id!} />
        ) : tab === "complaints" ? (
          <ComplaintsTab vehicleId={id!} />
        ) : tab === "guides" ? (
          <EntryList vehicleId={id!} kinds={["dtc_guide", "procedure"]} addKind="procedure" />
        ) : tab === "specs" ? (
          <EntryList vehicleId={id!} kinds={["fluid_capacity", "torque_spec", "spec", "part_note", "labor_time"]} addKind={null} />
        ) : tab === "codes" ? (
          <div className="space-y-2">
            <p className="text-lg">{t("codes.vehicleTabHint")}</p>
            <CodeSearch />
          </div>
        ) : (
          <Card>
            <p className="text-lg">{t("vehicle.tabComingSoon")}</p>
          </Card>
        )}
      </div>
    </div>
  );
}
