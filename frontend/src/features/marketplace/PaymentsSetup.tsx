import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import { price, type PaymentsConfig, type PaymentsStatus } from "./types";

/** Seller's "Get paid in the app" card: agreement → Stripe sign-up → status → INFORM check. */
export default function PaymentsSetup() {
  const { t } = useTranslation();
  const [search, setSearch] = useSearchParams();
  const [cfg, setCfg] = useState<PaymentsConfig | null>(null);
  const [st, setSt] = useState<PaymentsStatus | null>(null);
  const [agree, setAgree] = useState(false);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setCfg(await api<PaymentsConfig>("/market/payments/config"));
      // Coming back from Stripe's sign-up: pull the latest status from Stripe.
      const fresh = search.get("stripe")
        ? await api<PaymentsStatus>("/market/payments/refresh", { method: "POST" })
        : await api<PaymentsStatus | null>("/market/payments/me");
      setSt(fresh);
      if (fresh?.phone) setPhone(fresh.phone);
      if (search.get("stripe")) setSearch({}, { replace: true });
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }, [search, setSearch, t]);
  useEffect(() => void load(), [load]);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(errorMessage(t, e));
    } finally {
      setBusy(false);
    }
  };
  const go = (path: string) => run(async () => {
    window.location.href = (await api<{ url: string }>(path, { method: "POST" })).url;
  });

  if (!cfg || !st) return error ? <Alert>{error}</Alert> : null;
  const ready = st.charges_enabled && st.agreement_current;

  return (
    <Card className="space-y-4">
      <h2 className="text-xl font-bold">{t("pay.title")}</h2>
      <p className="text-lg">{t("pay.intro", { percent: cfg.fee_percent })}</p>
      {ready ? (
        <Alert kind="info">✓ {t(st.payouts_enabled ? "pay.ready" : "pay.readyNoPayouts")}</Alert>
      ) : st.has_account && st.details_submitted ? (
        <Alert kind="warning">{t("pay.pendingStripe")}</Alert>
      ) : null}

      {!st.agreement_current && (
        <div className="space-y-2">
          <p className="text-lg">
            {t("pay.agreementIntro")} <Link className="font-semibold underline" to="/legal/seller-agreement">{t("legal.seller-agreement")}</Link>
          </p>
          <label className="flex min-h-14 items-center gap-3 text-lg font-semibold">
            <input type="checkbox" className="size-7" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
            {t("pay.agree")}
          </label>
          <Button className="w-full" disabled={!agree || busy}
            onClick={() => run(async () => setSt(await api<PaymentsStatus>("/market/payments/agreement", { method: "POST", body: { accept: true, version: cfg.agreement_version } })))}>
            {t("pay.acceptAgreement")}
          </Button>
        </div>
      )}

      {st.agreement_current && !st.charges_enabled && (
        <Button className="w-full" disabled={busy} onClick={() => go("/market/payments/onboard")}>
          {t(st.has_account ? "pay.continueStripe" : "pay.setUpStripe")}
        </Button>
      )}
      {st.details_submitted && (
        <Button variant="secondary" className="w-full" disabled={busy} onClick={() => go("/market/payments/dashboard")}>
          {t("pay.openStripe")}
        </Button>
      )}
      <p className="text-base">{t("pay.stripeNote")}</p>

      {st.inform.high_volume && (
        <div className="space-y-3 rounded-xl border-2 border-amber-500 p-3">
          <h3 className="text-lg font-bold">{t("pay.informTitle")}</h3>
          <p className="text-base">{t("pay.informIntro", { sales: st.inform.sales_12m, revenue: price(st.inform.revenue_12m_cents) })}</p>
          {st.inform.ok ? (
            <p className="font-semibold text-emerald-700 dark:text-emerald-400">✓ {t("pay.informOk")}</p>
          ) : (
            <ul className="list-disc pl-6 text-lg">{st.inform.missing.map((m) => <li key={m}>{t(`pay.informMissing.${m}`)}</li>)}</ul>
          )}
          <div>
            <Label htmlFor="pphone">{t("pay.phone")}</Label>
            <div className="flex gap-2">
              <Input id="pphone" type="tel" autoComplete="tel" value={phone} maxLength={20} onChange={(e) => setPhone(e.target.value)} />
              <Button type="button" variant="secondary" disabled={busy || phone.trim().length < 7}
                onClick={() => run(async () => setSt(await api<PaymentsStatus>("/market/payments/contact", { method: "PUT", body: { phone } })))}>
                {t("pay.save")}
              </Button>
            </div>
          </div>
          <Button className="w-full" disabled={busy || !st.phone}
            onClick={() => run(async () => setSt(await api<PaymentsStatus>("/market/payments/inform-certify", { method: "POST" })))}>
            {t("pay.informCertify")}
          </Button>
        </div>
      )}
      {error && <Alert>{error}</Alert>}
    </Card>
  );
}
