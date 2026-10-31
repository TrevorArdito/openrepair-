import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Input, Label } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { rememberVehicle } from "../../lib/recent";
import type { VinDecode } from "../../lib/types";
import { normalizeVin, vinProblem } from "../../lib/vin";

export default function VinForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [vin, setVin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const clean = normalizeVin(vin);
  const liveProblem = clean.length > 0 ? vinProblem(clean) : null;
  const showLive = liveProblem && liveProblem !== "vin_wrong_length";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const problem = vinProblem(clean);
    if (problem) {
      setError(t(`errors.${problem}`));
      return;
    }
    setBusy(true);
    try {
      const result = await api<VinDecode>(`/vehicles/decode/${clean}`);
      rememberVehicle(result.vehicle);
      navigate(`/vehicle/${result.vehicle.id}`, { state: { decode: result } });
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <Label htmlFor="vin">{t("home.vinLabel")}</Label>
      <Input
        id="vin"
        value={vin}
        onChange={(e) => setVin(e.target.value)}
        placeholder={t("home.vinPlaceholder")}
        autoCapitalize="characters"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        inputMode="text"
        maxLength={24}
        className="font-mono text-xl tracking-wider uppercase placeholder:normal-case placeholder:tracking-normal"
        aria-describedby="vin-help vin-count"
        aria-invalid={!!(error || showLive)}
      />
      <div className="flex justify-between gap-3 text-base text-slate-600 dark:text-slate-300">
        <p id="vin-help">{t("home.vinHelp")}</p>
        <p id="vin-count" className={`shrink-0 font-mono ${clean.length === 17 && !liveProblem ? "font-bold text-green-700 dark:text-green-400" : ""}`}>
          {t("home.vinCount", { count: clean.length })}
        </p>
      </div>
      {showLive && <Alert kind="warning">{t(`errors.${liveProblem}`)}</Alert>}
      {error && <Alert>{error}</Alert>}
      <Button type="submit" disabled={busy} className="w-full">
        {busy ? t("home.decoding") : t("home.decode")}
      </Button>
    </form>
  );
}
