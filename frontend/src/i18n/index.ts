// All user-facing text lives in locales/<lang>/common.json. To add Spanish later:
// create locales/es/common.json with the same keys and register it below.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/common.json";

export const resources = { en: { common: en } } as const;

void i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
