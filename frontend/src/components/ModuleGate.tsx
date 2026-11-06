import { useTranslation } from "react-i18next";
import { Outlet } from "react-router-dom";
import { useModuleState } from "../lib/modules";
import { Card, LinkButton, PageTitle, Spinner } from "./ui";

/** Pages of an optional module: shown when it's switched on, a friendly "coming soon" when not. */
export default function ModuleGate({ name }: { name: string }) {
  const { t } = useTranslation();
  const state = useModuleState(name);
  if (state === "loading") return <Spinner label={t("app.loading")} />;
  if (state === "on") return <Outlet />;
  return (
    <div className="space-y-5">
      <PageTitle>{t(`comingSoon.${name}.title`, { defaultValue: t("comingSoon.title") })}</PageTitle>
      <Card className="space-y-3 text-lg">
        <p>{t(`comingSoon.${name}.body`, { defaultValue: t("comingSoon.body") })}</p>
        <LinkButton to="/" className="w-full">{t("comingSoon.home")}</LinkButton>
      </Card>
    </div>
  );
}
