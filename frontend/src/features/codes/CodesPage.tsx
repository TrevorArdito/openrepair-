import { useTranslation } from "react-i18next";
import { PageTitle } from "../../components/ui";
import CodeSearch from "./CodeSearch";

export default function CodesPage() {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <PageTitle>{t("codes.title")}</PageTitle>
      <p className="text-lg">{t("codes.intro")}</p>
      <CodeSearch />
    </div>
  );
}
