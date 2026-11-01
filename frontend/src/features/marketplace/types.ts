import type { AppliesTo } from "../../lib/types";

export type Condition = "new" | "used" | "reman" | "for_parts";
export type ListingStatus = "pending" | "active" | "sold" | "withdrawn" | "removed";
export type Shipping = "pickup" | "ships" | "pickup_or_ships";

export type ListingSummary = {
  id: number;
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
};

export type Verification = {
  id: number;
  kind: "business_license" | "dismantler_license";
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
