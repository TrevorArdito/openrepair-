import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function ExpandableText({ text, limit = 260 }: { text: string | null; limit?: number }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  if (!text) return null;
  if (text.length <= limit) return <p className="whitespace-pre-line">{text}</p>;
  return (
    <div>
      <p className="whitespace-pre-line">{open ? text : `${text.slice(0, limit).trimEnd()}…`}</p>
      <button type="button" onClick={() => setOpen(!open)} className="min-h-12 font-bold underline">
        {open ? t("safety.showLess") : t("safety.readMore")}
      </button>
    </div>
  );
}
