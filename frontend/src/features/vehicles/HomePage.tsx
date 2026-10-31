import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Card } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import { recentEntries, recentVehicles } from "../../lib/recent";
import { useDocumentTitle } from "../../lib/title";
import VinForm from "./VinForm";
import YmmPicker from "./YmmPicker";

export default function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const recent = recentVehicles();
  const recentGuides = recentEntries();
  useDocumentTitle(null);

  return (
    <div className="space-y-6">
      <p className="text-lg text-slate-700 dark:text-slate-300">{t("app.tagline")}</p>
      <Card>
        <h2 className="mb-3 text-2xl font-bold">{t("home.vinTitle")}</h2>
        <VinForm />
      </Card>
      <Card>
        <h2 className="mb-3 text-2xl font-bold">{t("home.orPick")}</h2>
        <YmmPicker />
      </Card>
      <Card>
        <h2 className="mb-3 text-2xl font-bold">{t("home.recent")}</h2>
        {recent.length === 0 ? (
          <p>{t("home.noRecent")}</p>
        ) : (
          <ul className="divide-y-2 divide-slate-200 dark:divide-slate-800">
            {recent.map((v) => (
              <li key={v.id}>
                <Link to={`/vehicle/${v.id}`} className="flex min-h-14 items-center text-lg font-semibold underline-offset-4 hover:underline">
                  {v.label}
                </Link>
              </li>
            ))}
          </ul>
        )}
        {recentGuides.length > 0 && (
          <>
            <h3 className="mt-4 mb-1 text-lg font-bold">{t("home.recentGuides")}</h3>
            <ul className="divide-y-2 divide-slate-200 dark:divide-slate-800">
              {recentGuides.map((e) => (
                <li key={e.id}>
                  <Link to={`/entries/${e.id}`} className="flex min-h-14 flex-col justify-center py-1">
                    <span className="text-sm font-semibold uppercase text-amber-700 dark:text-amber-400">{t(`kinds.${e.kind}`)}</span>
                    <span className="text-lg font-semibold">{e.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
        {user && (
          <Link to="/garage" className="mt-2 flex min-h-12 items-center font-bold text-amber-700 underline dark:text-amber-400">
            {t("home.openGarage")}
          </Link>
        )}
      </Card>
    </div>
  );
}
