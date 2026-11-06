import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Label, Select } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { rememberVehicle } from "../../lib/recent";
import MakeOptions from "../../components/MakeOptions";
import type { Make, NamedRef, Vehicle } from "../../lib/types";

const UNKNOWN = "unknown";

export default function YmmPicker() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [years, setYears] = useState<number[]>([]);
  const [makes, setMakes] = useState<Make[]>([]);
  const [models, setModels] = useState<NamedRef[] | null>(null);
  const [engines, setEngines] = useState<Vehicle[]>([]);
  const [year, setYear] = useState("");
  const [makeId, setMakeId] = useState("");
  const [modelId, setModelId] = useState("");
  const [engine, setEngine] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api<number[]>("/vehicles/years"), api<Make[]>("/vehicles/makes")])
      .then(([y, m]) => {
        setYears(y);
        setMakes(m);
      })
      .catch((e) => setError(errorMessage(t, e)));
  }, [t]);

  useEffect(() => {
    setModels(null);
    setModelId("");
    setError(null);
    if (!year || !makeId) return;
    const ctrl = new AbortController();
    api<NamedRef[]>(`/vehicles/models?year=${year}&make_id=${makeId}`, { signal: ctrl.signal })
      .then(setModels)
      .catch((e) => e.name !== "AbortError" && setError(errorMessage(t, e)));
    return () => ctrl.abort();
  }, [year, makeId, t]);

  useEffect(() => {
    setEngines([]);
    setEngine("");
    if (!year || !modelId) return;
    api<Vehicle[]>(`/vehicles/engines?year=${year}&model_id=${modelId}`)
      .then((list) => {
        const withEngine = list.filter((v) => v.engine.label);
        setEngines(withEngine);
        setEngine(withEngine.length === 1 ? String(withEngine[0].id) : withEngine.length ? "" : UNKNOWN);
      })
      .catch((e) => setError(errorMessage(t, e)));
  }, [year, modelId, t]);

  async function go() {
    setError(null);
    setBusy(true);
    try {
      const vehicle =
        engine && engine !== UNKNOWN
          ? engines.find((v) => String(v.id) === engine)!
          : await api<Vehicle>("/vehicles", { method: "POST", body: { year: Number(year), model_id: Number(modelId) } });
      rememberVehicle(vehicle);
      navigate(`/vehicle/${vehicle.id}`);
    } catch (e) {
      setError(errorMessage(t, e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="ymm-year">{t("picker.year")}</Label>
        <Select id="ymm-year" value={year} onChange={(e) => setYear(e.target.value)}>
          <option value="">{t("picker.choose")}</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor="ymm-make">{t("picker.make")}</Label>
        <Select id="ymm-make" value={makeId} onChange={(e) => setMakeId(e.target.value)} disabled={!year}>
          <option value="">{t("picker.choose")}</option>
          <MakeOptions makes={makes} />
        </Select>
      </div>
      <div>
        <Label htmlFor="ymm-model">{t("picker.model")}</Label>
        <Select id="ymm-model" value={modelId} onChange={(e) => setModelId(e.target.value)} disabled={!models?.length}>
          <option value="">{models === null && year && makeId ? t("app.loading") : t("picker.choose")}</option>
          {models?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </Select>
        {models?.length === 0 && <p className="mt-1 text-base">{t("picker.noModels")}</p>}
      </div>
      <div>
        <Label htmlFor="ymm-engine">{t("picker.engine")}</Label>
        <Select id="ymm-engine" value={engine} onChange={(e) => setEngine(e.target.value)} disabled={!modelId}>
          <option value="">{t("picker.choose")}</option>
          {engines.map((v) => (
            <option key={v.id} value={v.id}>
              {v.engine.label}
              {v.engine.family ? ` — ${v.engine.family.name}` : v.engine.engine_code ? ` (${v.engine.engine_code})` : ""}
            </option>
          ))}
          <option value={UNKNOWN}>{t("picker.engineUnknown")}</option>
        </Select>
      </div>
      {error && <Alert>{error}</Alert>}
      <Button className="w-full" disabled={!modelId || !engine || busy} onClick={go}>
        {t("picker.go")}
      </Button>
    </div>
  );
}
