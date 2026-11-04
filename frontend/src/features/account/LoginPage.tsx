import { useState, type FormEvent } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Alert, Button, Card, Input, Label, PageTitle } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageTitle>{t("auth.login")}</PageTitle>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" disabled={busy} className="w-full">
            {t("auth.login")}
          </Button>
          <Link to="/forgot-password" className="flex min-h-12 items-center justify-center font-semibold underline">
            {t("auth.forgot")}
          </Link>
        </form>
      </Card>
      <p>
        {t("auth.noAccount")}{" "}
        <Link to="/register" state={{ from }} className="font-bold underline">
          {t("auth.register")}
        </Link>
      </p>
    </div>
  );
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [form, setForm] = useState({ email: "", password: "", display_name: "", accept_terms: false, website: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register({ ...form, website: form.website || undefined });
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  return (
    <div className="space-y-4">
      <PageTitle>{t("auth.register")}</PageTitle>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label htmlFor="r-email">{t("auth.email")}</Label>
            <Input id="r-email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
          </div>
          <div>
            <Label htmlFor="r-name">{t("auth.displayName")}</Label>
            <Input id="r-name" autoComplete="nickname" required minLength={2} maxLength={40} value={form.display_name} onChange={set("display_name")} aria-describedby="r-name-help" />
            <p id="r-name-help" className="mt-1 text-base text-slate-600 dark:text-slate-400">{t("auth.displayNameHelp")}</p>
          </div>
          <div>
            <Label htmlFor="r-password">{t("auth.password")}</Label>
            <Input id="r-password" type="password" autoComplete="new-password" required minLength={10} value={form.password} onChange={set("password")} aria-describedby="r-pw-help" />
            <p id="r-pw-help" className="mt-1 text-base text-slate-600 dark:text-slate-400">{t("auth.passwordHelp")}</p>
          </div>
          {/* Honeypot for bots: hidden from people and screen readers. */}
          <div aria-hidden="true" className="absolute -left-[9999px]">
            <label htmlFor="r-website">Website</label>
            <input id="r-website" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} />
          </div>
          <label className="flex min-h-12 items-start gap-3 text-lg">
            <input type="checkbox" className="mt-1 size-7 shrink-0 accent-amber-400" checked={form.accept_terms} onChange={set("accept_terms")} required />
            <span>
              <Trans i18nKey="auth.acceptTerms" components={{ terms: <Link to="/about" className="font-bold underline" /> }} />
            </span>
          </label>
          <p className="text-base text-slate-600 dark:text-slate-400">{t("auth.privacyNote")}</p>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" disabled={busy} className="w-full">
            {t("auth.register")}
          </Button>
        </form>
      </Card>
      <p>
        {t("auth.haveAccount")}{" "}
        <Link to="/login" state={{ from }} className="font-bold underline">
          {t("auth.login")}
        </Link>
      </p>
    </div>
  );
}
