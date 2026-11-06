// Yards: paste a VIN list (one per line, optional price and row/stock #) to list many vehicles at once.
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Button, Card, Label, Select } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { RUNNING, TITLE_STATUSES } from "./types";

type Result = { vin: string; listing_id: number | null; title: string | null; published: boolean; error: string | null };
const MAX_LINES = 25;

/** "1FTFW1EF6CF000000, 3400, Row 4" → { vin, price_cents, stock_number } */
export function parseVinLines(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [vin, ...rest] = line.split(/[\s,;\t]+/);
      const priceIdx = rest.findIndex((x) => /^\$?\d[\d,]*(\.\d{1,2})?$/.test(x));
      const price = priceIdx >= 0 ? parseFloat(rest[priceIdx].replace(/[$,]/g, "")) : null;
      const stock = rest.filter((_, i) => i !== priceIdx).join(" ").slice(0, 30);
      return {
        vin: vin.toUpperCase(),
        price_cents: price != null && !Number.isNaN(price) ? Math.round(price * 100) : null,
        stock_number: stock || null,
      };
    });
}

export default function BulkVins({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [titleStatus, setTitleStatus] = useState("salvage");
  const [running, setRunning] = useState("not_running");
  const [accept, setAccept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Result[] | null>(null);
  const lines = parseVinLines(text);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const r = await api<Result[]>("/market/listings/bulk-vins", {
        method: "POST",
        body: { lines, title_status: titleStatus, running, accept_rules: accept },
      });
      setResults(r);
      if (r.some((x) => x.listing_id)) setText("");
      onDone();
    } catch (e) {
      setError(errorMessage(t, e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-xl font-bold">{t("market.bulk.title")}</h2>
      <p className="text-lg">{t("market.bulk.intro")}</p>
      <div>
        <Label htmlFor="bulk-vins">{t("market.bulk.label")}</Label>
        <textarea id="bulk-vins" rows={6} value={text} onChange={(e) => setText(e.target.value)}
          placeholder={"1FTFW1EF6CF000000, 3400, Row 4\n4T1BE46K68U000000"} spellCheck={false}
          className="w-full rounded-xl border-2 border-slate-300 bg-white p-3 font-mono text-lg dark:border-slate-700 dark:bg-slate-900" />
        <p className="text-base text-slate-600 dark:text-slate-400">{t("market.bulk.count", { count: lines.length, max: MAX_LINES })}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="bulk-ts">{t("market.titleStatus")}</Label>
          <Select id="bulk-ts" value={titleStatus} onChange={(e) => setTitleStatus(e.target.value)}>
            {TITLE_STATUSES.map((s) => <option key={s} value={s}>{t(`market.titleStatuses.${s}`)}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="bulk-rn">{t("market.running")}</Label>
          <Select id="bulk-rn" value={running} onChange={(e) => setRunning(e.target.value)}>
            {RUNNING.map((s) => <option key={s} value={s}>{t(`market.runnings.${s}`)}</option>)}
          </Select>
        </div>
      </div>
      <label className="flex min-h-14 items-center gap-3 text-lg font-semibold">
        <input type="checkbox" className="size-7" checked={accept} onChange={(e) => setAccept(e.target.checked)} />
        {t("market.bulk.accept")}
      </label>
      {error && <Alert>{error}</Alert>}
      <Button className="w-full" disabled={busy || !accept || lines.length === 0 || lines.length > MAX_LINES} onClick={submit}>
        {busy ? t("market.bulk.working") : t("market.bulk.submit", { count: lines.length })}
      </Button>
      {results && (
        <ul className="space-y-2 text-lg" aria-live="polite">
          {results.map((r) => (
            <li key={r.vin} className="break-words">
              <span className="font-mono">{r.vin}</span>{" — "}
              {r.listing_id ? (
                <Link to={`/market/listings/${r.listing_id}/edit`} className="font-semibold underline">
                  {r.title} · {r.published ? t("market.bulk.published") : t("market.bulk.hidden")}
                </Link>
              ) : (
                <span className="font-semibold text-red-700 dark:text-red-400">{t(`errors.${r.error}`, { defaultValue: t("errors.unknown_error") })}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
