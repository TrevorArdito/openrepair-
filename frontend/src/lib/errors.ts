import type { TFunction } from "i18next";
import { ApiError } from "./api";

export function errorMessage(t: TFunction, e: unknown): string {
  if (e instanceof ApiError) {
    const key = `errors.${e.code}`;
    return t(key, { ...e.details, defaultValue: t("errors.unknown_error") });
  }
  return t("errors.unknown_error");
}
