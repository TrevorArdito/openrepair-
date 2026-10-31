import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Alert, Button, Card, Input, Label, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import type { Me } from "../../lib/types";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email } });
      setSent(true);
    } catch (err) {
      setError(errorMessage(t, err));
    }
  }
  return (
    <div className="space-y-4">
      <PageTitle>{t("auth.forgotTitle")}</PageTitle>
      {sent ? (
        <Alert kind="info">{t("auth.linkSent")}</Alert>
      ) : (
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <p className="text-lg">{t("auth.forgotHelp")}</p>
            <div>
              <Label htmlFor="fp-email">{t("auth.email")}</Label>
              <Input id="fp-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            {error && <Alert>{error}</Alert>}
            <Button type="submit" className="w-full">{t("auth.sendLink")}</Button>
          </form>
        </Card>
      )}
    </div>
  );
}

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/auth/reset-password", { method: "POST", body: { token, password } });
      setDone(true);
    } catch (err) {
      setError(errorMessage(t, err));
    }
  }
  if (!token) return <Alert>{t("auth.missingToken")}</Alert>;
  return (
    <div className="space-y-4">
      <PageTitle>{t("auth.resetTitle")}</PageTitle>
      {done ? (
        <>
          <Alert kind="info">{t("auth.resetDone")}</Alert>
          <LinkButton to="/login" className="w-full">{t("auth.login")}</LinkButton>
        </>
      ) : (
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="rp-pw">{t("auth.newPassword")}</Label>
              <Input id="rp-pw" type="password" autoComplete="new-password" minLength={10} required value={password} onChange={(e) => setPassword(e.target.value)} />
              <p className="mt-1 text-base text-slate-600 dark:text-slate-400">{t("auth.passwordHelp")}</p>
            </div>
            {error && <Alert>{error}</Alert>}
            <Button type="submit" className="w-full">{t("auth.savePassword")}</Button>
          </form>
        </Card>
      )}
    </div>
  );
}

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token");
  const { user, setUser } = useAuth();
  const [state, setState] = useState<"working" | "done" | "error">("working");
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  useEffect(() => {
    if (!token || started.current) return;
    started.current = true; // links are one-time: don't send twice (React dev mode runs effects twice)
    api<Me>("/auth/verify-email", { method: "POST", body: { token } })
      .then((me) => {
        if (user && user.id === me.id) setUser({ ...user, email_verified: true });
        setState("done");
      })
      .catch((e) => {
        setError(errorMessage(t, e));
        setState("error");
      });
  }, [token, t, user, setUser]);
  if (!token) return <Alert>{t("auth.missingToken")}</Alert>;
  return (
    <div className="space-y-4">
      <PageTitle>{t("auth.verifyTitle")}</PageTitle>
      {state === "working" && <Spinner label={t("app.loading")} />}
      {state === "done" && (
        <>
          <Alert kind="info">{t("auth.verifyDone")}</Alert>
          <LinkButton to="/" className="w-full">{t("notFound.home")}</LinkButton>
        </>
      )}
      {state === "error" && <Alert>{error}</Alert>}
    </div>
  );
}
