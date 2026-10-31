export type NamedRef = { id: number; name: string };

export type Engine = {
  displacement_l: number | null;
  cylinders: number | null;
  layout: string | null;
  fuel_type: string | null;
  engine_code: string | null;
  label: string | null;
};

export type Vehicle = {
  id: number;
  year: number;
  make: NamedRef;
  model: NamedRef;
  engine: Engine;
  label: string;
};

export type VehicleProfile = Vehicle & { counts: Record<string, number> };

export type VinDecode = {
  vin: string;
  check_digit_valid: boolean;
  vehicle: Vehicle;
  details: Record<string, string>;
  warnings: string[];
  source: string;
};

export type Me = {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "pro" | "moderator" | "admin";
  status: string;
  unit_pref: "metric" | "imperial";
  locale: string;
  theme: "system" | "light" | "dark";
};

export type GarageItem = {
  id: number;
  vehicle: Vehicle;
  vin: string | null;
  nickname: string | null;
  notes: string | null;
};

type Freshness = { source: string; source_url: string; fetched_at: string | null; stale: boolean };

export type Recall = {
  campaign_number: string;
  manufacturer: string | null;
  component: string | null;
  summary: string | null;
  consequence: string | null;
  remedy: string | null;
  notes: string | null;
  report_date: string | null;
  park_it: boolean;
  park_outside: boolean;
  over_the_air: boolean;
};
export type RecallList = Freshness & { total: number; items: Recall[] };

export type Complaint = {
  odi_number: string;
  components: string | null;
  summary: string | null;
  crash: boolean;
  fire: boolean;
  injuries: number;
  deaths: number;
  incident_date: string | null;
  filed_date: string | null;
};
export type ComplaintList = Freshness & { total: number; items: Complaint[]; components: Record<string, number> };

export type Tsb = {
  nhtsa_id: number;
  bulletin_number: string | null;
  bulletin_date: string | null;
  comm_type: string | null;
  components: string | null;
  summary: string | null;
};
export type TsbList = Freshness & { total: number; items: Tsb[]; last_import: string | null };
