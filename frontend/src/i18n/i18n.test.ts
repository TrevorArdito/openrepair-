import { describe, expect, it } from "vitest";
import en from "./locales/en/common.json";

// Every error code the backend can send should have a friendly message.
const BACKEND_ERROR_CODES = [
  "vin_wrong_length", "vin_invalid_letters", "vin_invalid_characters", "vin_not_decodable",
  "upstream_unavailable", "invalid_credentials", "email_taken", "terms_not_accepted",
  "registration_rejected", "rate_limited", "account_disabled", "auth_required", "csrf_failed",
  "validation_error", "garage_full", "vehicle_not_found", "not_found", "dtc_invalid",
];

describe("translations", () => {
  it("has a message for every backend error code", () => {
    for (const code of BACKEND_ERROR_CODES) {
      expect(en.errors, code).toHaveProperty(code);
    }
  });
});
