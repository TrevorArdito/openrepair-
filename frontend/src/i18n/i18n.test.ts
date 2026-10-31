import { describe, expect, it } from "vitest";
import en from "./locales/en/common.json";

// Every error code the backend can send should have a friendly message.
const BACKEND_ERROR_CODES = [
  "vin_wrong_length", "vin_invalid_letters", "vin_invalid_characters", "vin_not_decodable",
  "upstream_unavailable", "invalid_credentials", "email_taken", "terms_not_accepted",
  "registration_rejected", "rate_limited", "account_disabled", "auth_required", "csrf_failed",
  "validation_error", "garage_full", "vehicle_not_found", "not_found", "dtc_invalid", "entry_invalid", "entry_not_found",
  "edit_conflict", "unknown_system", "photo_not_found", "photo_too_large", "photo_bad_type", "cannot_vote_own",
  "already_reported", "forbidden", "make_not_found", "model_not_found", "revision_not_found",
  "revision_not_pending", "entry_not_published", "not_labor_entry", "report_not_found", "search_empty",
  "token_invalid", "already_pro", "pro_request_pending", "pro_request_not_found", "user_not_found",
  "cannot_moderate_self", "email_not_verified", "engine_not_found",
];

describe("translations", () => {
  it("has a message for every backend error code", () => {
    for (const code of BACKEND_ERROR_CODES) {
      expect(en.errors, code).toHaveProperty(code);
    }
  });
});
