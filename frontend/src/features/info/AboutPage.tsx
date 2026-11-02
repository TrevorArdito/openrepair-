import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Alert, Card, PageTitle } from "../../components/ui";
import { api } from "../../lib/api";

export default function AboutPage() {
  const { t } = useTranslation();
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);

  useEffect(() => {
    api<{ source_code_url: string }>("/meta")
      .then((m) => setSourceUrl(m.source_code_url))
      .catch(() => setSourceUrl(null));
  }, []);

  return (
    <div className="space-y-5">
      <PageTitle>{t("about.title")}</PageTitle>
      <p className="text-lg">{t("about.mission")}</p>
      <p className="text-lg font-semibold">{t("about.free")}</p>
      <Alert kind="warning">
        <h2 className="mb-1 text-xl font-bold">{t("about.disclaimerTitle")}</h2>
        <p>{t("about.disclaimer")}</p>
      </Alert>
      <Card>
        <h2 className="mb-1 text-xl font-bold">{t("about.privacyTitle")}</h2>
        <p>{t("about.privacy")}</p>
      </Card>
      <Card>
        <h2 className="mb-1 text-xl font-bold">{t("about.licenseTitle")}</h2>
        <p>{t("about.license")}</p>
        {/* AGPL §13: users of the network service must be offered the source code. */}
        <a
          href={sourceUrl ?? "https://github.com/TrevorArdito/openrepair-"}
          className="mt-2 flex min-h-12 items-center font-bold underline"
          rel="noopener noreferrer"
          target="_blank"
        >
          {t("about.source")}
        </a>
      </Card>
      <Card>
        <h2 className="mb-1 text-xl font-bold">{t("legal.title")}</h2>
        {["terms", "seller-agreement", "prohibited-items"].map((n) => (
          <Link key={n} to={`/legal/${n}`} className="flex min-h-12 items-center font-bold underline">{t(`legal.${n}`)}</Link>
        ))}
      </Card>
      <p className="text-base text-slate-600 dark:text-slate-400">{t("about.notAffiliated")}</p>
    </div>
  );
}
