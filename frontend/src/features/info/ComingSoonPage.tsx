import { useTranslation } from "react-i18next";
import { Card, PageTitle } from "../../components/ui";

export default function ComingSoonPage({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <div>
      <PageTitle>{t(titleKey)}</PageTitle>
      <Card>
        <p className="text-lg">{t("vehicle.tabComingSoon")}</p>
      </Card>
    </div>
  );
}
