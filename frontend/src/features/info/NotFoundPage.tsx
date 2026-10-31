import { useTranslation } from "react-i18next";
import { LinkButton, PageTitle } from "../../components/ui";

export default function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div>
      <PageTitle>{t("notFound.title")}</PageTitle>
      <LinkButton to="/">{t("notFound.home")}</LinkButton>
    </div>
  );
}
