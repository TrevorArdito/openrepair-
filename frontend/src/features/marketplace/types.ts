import type { AppliesTo } from "../../lib/types";

export type Condition = "new" | "used" | "reman" | "for_parts";
export type ListingStatus = "pending" | "active" | "sold" | "withdrawn" | "removed";
export type Shipping = "pickup" | "ships" | "pickup_or_ships";

export type VehicleFacts = {
  year: number;
  make: string;
  model: string | null;
  trim: string | null;
  odometer: number | null;
  odometer_unit: "mi" | "km";
  title_status: "clean" | "rebuilt" | "salvage" | "non_repairable";
  has_lien: boolean;
  running: "runs_drives" | "runs_not_drives" | "not_running";
  vehicle_id: number | null;
  vin?: string | null;
  make_id?: number;
  model_id?: number | null;
  drive?: string | null;
  transmission?: string | null;
  exterior_color?: string | null;
};

export type ListingSummary = {
  id: number;
  kind: "part" | "vehicle";
  title: string;
  category: string;
  condition: Condition;
  price_cents: number;
  currency: string;
  status: ListingStatus;
  city: string;
  state: string;
  seller_id: number;
  seller_name: string;
  seller_verified: boolean;
  photo_url: string | null;
  fits_all: boolean;
  vehicle: VehicleFacts | null;
  saved: boolean;
  distance_mi: number | null;
  buy_now: boolean;
  created_at: string;
};

export type FitmentRow = AppliesTo & { make: string; model: string | null; engine: string | null };

export type Listing = ListingSummary & {
  description: string;
  brand: string | null;
  part_number: string | null;
  quantity: number;
  shipping: Shipping;
  shipping_note: string | null;
  shipping_cents: number | null;
  buy_now_reason: string | null;
  source_vin: string | null;
  mileage: number | null;
  emissions_compliance: "epa" | "carb" | null;
  carb_eo_number: string | null;
  status_reason: string | null;
  fitment: FitmentRow[];
  photos: { id: number; url: string }[];
  is_owner: boolean;
  updated_at: string;
};

export type Seller = {
  id: number;
  seller_type: "individual" | "shop" | "recycler" | "retailer";
  display_name: string;
  city: string;
  state: string;
  postal_code: string | null;
  about: string | null;
  status: string;
  verified: string[];
  member_since: string;
  active_listings: number;
  rating: number | null;
  rating_count: number;
};

export type Review = { id: number; rating: number; comment: string | null; reviewer_name: string; listing_title: string; created_at: string };

export function stars(n: number): string {
  const full = Math.round(n);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

export type Verification = {
  id: number;
  kind: "business_license" | "dismantler_license" | "dealer_license";
  license_number: string;
  issuing_state: string;
  business_name: string;
  status: "pending" | "approved" | "rejected";
  note: string | null;
  created_at: string;
};

export type Message = { id: number; mine: boolean; body: string; created_at: string };

export type Conversation = {
  id: number;
  listing_id: number;
  listing_title: string;
  other_name: string;
  role: "buyer" | "seller";
  unread: number;
  last_message: string | null;
  updated_at: string;
  messages: Message[] | null;
};

export const CONDITIONS: Condition[] = ["new", "used", "reman", "for_parts"];
export const US_STATES =
  "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split(" ");

export function price(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}

export const TITLE_STATUSES = ["clean", "rebuilt", "salvage", "non_repairable"] as const;
export const RUNNING = ["runs_drives", "runs_not_drives", "not_running"] as const;

export type PaymentsConfig = {
  enabled: boolean;
  fee_percent: number;
  stripe_fee_percent: number;
  stripe_fee_fixed_cents: number;
  tax_enabled: boolean;
  contact_only_categories: string[];
  release_days_after_delivery: number;
  agreement_version: string;
};

export type PaymentsStatus = {
  has_account: boolean;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  details_submitted: boolean;
  agreement_version: string | null;
  agreement_current: boolean;
  phone: string | null;
  inform: { high_volume: boolean; sales_12m: number; revenue_12m_cents: number; missing: string[]; ok: boolean };
};

export type OrderDispute = {
  id: number; reason: string; details: string | null; seller_response: string | null;
  status: "open" | "responded" | "refunded" | "released"; decision_note: string | null; created_at: string;
};

export type Order = {
  id: number;
  role: "buyer" | "seller" | null;
  listing_id: number | null;
  listing_title: string;
  seller_id: number | null;
  seller_name: string;
  status: "pending_payment" | "paid" | "shipped" | "delivered" | "completed" | "disputed" | "refunded" | "canceled";
  quantity: number;
  item_cents: number;
  shipping_cents: number;
  tax_cents: number;
  total_cents: number;
  currency: string;
  created_at: string;
  paid_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  released_at: string | null;
  refunded_at: string | null;
  release_due_at: string | null;
  carrier: string | null;
  tracking_number: string | null;
  note: string | null;
  ship_name?: string | null;
  ship_address?: string | null;
  fee_cents?: number;
  fee_percent?: number;
  disputes?: OrderDispute[];
};

/** Same math as the backend (app/modules/marketplace/payments.py) — shown before listing. */
export function feeBreakdown(cfg: PaymentsConfig, priceCents: number, shippingCents: number) {
  const gross = priceCents + shippingCents;
  const fee = Math.max(0, Math.round((gross * cfg.fee_percent) / 100));
  const stripe = gross ? Math.round((gross * cfg.stripe_fee_percent) / 100) + cfg.stripe_fee_fixed_cents : 0;
  return { gross, fee, stripe, net: gross - fee - stripe };
}
