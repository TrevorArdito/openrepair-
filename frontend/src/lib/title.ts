import { useEffect } from "react";
import i18n from "../i18n";

/** Set the browser tab / history title for the current page. */
export function useDocumentTitle(title: string | null | undefined) {
  useEffect(() => {
    const app = i18n.t("app.name");
    document.title = title ? `${title} | ${app}` : app;
  }, [title]);
}
