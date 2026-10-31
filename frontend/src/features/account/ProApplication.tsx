import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Alert, Button, Card } from "../../components/ui";
import { api } from "../../lib/api";
import { errorMessage } from "../../lib/errors";
import type { Me } from "../../lib/types";
import { TextArea } from "../entries/fields";

type Req = { id: number; status: "pending" | "approved" | "rejected"; note: string | null } | null;

export default function ProApplication({ user }: { user: Me }) {
  const { t } = useTranslation();
  const [req, setReq] = useState<Req | undefined>(undefined);
  const [statement, setStatement] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Req>("/pro-requests/mine").then(setReq).catch(() => setReq(null));
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/pro-requests", { method: "POST", body: { statement } });
      setReq({ id: 0, status: "pending", note: null });
    } catch (err) {
      setError(errorMessage(t, err));
    }
  }
  const isPro = ["pro", "moderator", "admin"].includes(user.role);
  return (
    <Card className="space-y-3">
      <h2 className="text-xl font-bold">{t("account.proTitle")}</h2>
      {isPro ? (
        <p className="text-lg font-semibold text-green-700 dark:text-green-400">✓ {t("account.proApproved")}</p>
      ) : req?.status === "pending" ? (
        <Alert kind="info">{t("account.proPending")}</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          {req?.status === "rejected" && (
            <Alert kind="warning">
              {t("account.proRejected")} {req.note ? t("account.proNote", { note: req.note }) : ""}
            </Alert>
          )}
          <p>{t("account.proIntro")}</p>
          <TextArea id="pro-statement" label={t("account.proStatement")} value={statement} max={2000} onChange={setStatement} />
          {error && <Alert>{error}</Alert>}
          <Button type="submit" className="w-full" disabled={statement.trim().length < 20}>{t("account.proApply")}</Button>
        </form>
      )}
    </Card>
  );
}
