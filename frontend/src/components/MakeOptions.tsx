import { useTranslation } from "react-i18next";
import type { Make } from "../lib/types";

/** <option>s for a make <select>: the most common makes first, then every make A–Z. */
export default function MakeOptions({ makes }: { makes: Make[] }) {
  const { t } = useTranslation();
  const common = makes.filter((m) => m.common).sort((a, b) => a.common! - b.common!);
  const all = makes.map((m) => (
    <option key={m.id} value={m.id}>
      {m.name}
    </option>
  ));
  if (common.length === 0) return <>{all}</>;
  return (
    <>
      <optgroup label={t("picker.commonMakes")}>
        {common.map((m) => (
          <option key={`c${m.id}`} value={m.id}>
            {m.name}
          </option>
        ))}
      </optgroup>
      <optgroup label={t("picker.allMakes")}>{all}</optgroup>
    </>
  );
}
