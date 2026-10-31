import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, LinkButton, PageTitle, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { errorMessage } from "../../lib/errors";
import { usePrefs, type Theme } from "../../lib/prefs";
import type { Me } from "../../lib/types";
import type { UnitSystem } from "../../lib/units";

function Choice<T extends string>({ legend, value, options, onChange }: { legend: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <fieldset>
      <legend className="mb-2 font-bold">{legend}</legend>
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            aria-pressed={value === o.value}
            onClick={() => onChange(o.value)}
            className={`min-h-14 rounded-xl border-2 px-2 font-bold ${
              value === o.value ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-400 dark:border-slate-600"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function AccountPage() {
  const { t } = useTranslation();
  const { user, loading, logout, setUser } = useAuth();
  const { units, theme, setUnits, setTheme } = usePrefs();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  async function syncPref(body: Partial<Me>) {
    if (!user) return;
    try {
      setUser(await api<Me>("/me", { method: "PATCH", body }));
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  async function exportData() {
    const data = await api<unknown>("/me/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "chrystalclear-my-data.json" });
    a.click();
    URL.revokeObjectURL(url);
  }

  async function deleteAccount() {
    if (!window.confirm(t("account.confirmDelete"))) return;
    try {
      await api("/me", { method: "DELETE" });
      setUser(null);
      navigate("/");
    } catch (e) {
      setError(errorMessage(t, e));
    }
  }

  if (loading) return <Spinner label={t("app.loading")} />;

  return (
    <div className="space-y-5">
      <PageTitle>{t("account.title")}</PageTitle>
      {user ? (
        <Card>
          <p className="text-lg">{t("account.signedInAs", { name: user.display_name })}</p>
          <p className="text-base text-slate-600 dark:text-slate-400">
            {user.email} · {t(`account.role.${user.role}`)}
          </p>
          {["moderator", "admin"].includes(user.role) && (
            <LinkButton to="/mod" className="mt-3 w-full">
              {t("nav.moderation")}
            </LinkButton>
          )}
          <Button variant="secondary" className="mt-3 w-full" onClick={() => logout().then(() => navigate("/"))}>
            {t("auth.logout")}
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <LinkButton to="/login">{t("auth.login")}</LinkButton>
          <LinkButton to="/register" variant="secondary">
            {t("auth.register")}
          </LinkButton>
        </div>
      )}

      <Card className="space-y-5">
        <h2 className="text-xl font-bold">{t("account.settings")}</h2>
        <Choice<UnitSystem>
          legend={t("account.units")}
          value={units}
          options={[
            { value: "imperial", label: t("account.imperial") },
            { value: "metric", label: t("account.metric") },
          ]}
          onChange={(u) => {
            setUnits(u);
            void syncPref({ unit_pref: u });
          }}
        />
        <Choice<Theme>
          legend={t("account.theme")}
          value={theme}
          options={[
            { value: "system", label: t("account.themeSystem") },
            { value: "light", label: t("account.themeLight") },
            { value: "dark", label: t("account.themeDark") },
          ]}
          onChange={(th) => {
            setTheme(th);
            void syncPref({ theme: th });
          }}
        />
      </Card>

      {user && (
        <Card className="space-y-3">
          <h2 className="text-xl font-bold">{t("account.yourData")}</h2>
          <Button variant="secondary" className="w-full" onClick={exportData}>
            {t("account.export")}
          </Button>
          <Button variant="danger" className="w-full" onClick={deleteAccount}>
            {t("account.delete")}
          </Button>
        </Card>
      )}
      {error && <Alert>{error}</Alert>}
    </div>
  );
}
