export type NamedRef = { id: number; name: string };

export type Engine = {
  displacement_l: number | null;
  cylinders: number | null;
  layout: string | null;
  fuel_type: string | null;
  engine_code: string | null;
  aspiration?: string | null;
  label: string | null;
  family?: NamedRef | null;
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
  email_verified: boolean;
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
  /** maker = counted; other_engine = maker recall naming a different engine; aftermarket = another company's. */
  group: "maker" | "other_engine" | "aftermarket";
};
/** total counts only the vehicle maker's own recalls for this engine. */
export type RecallList = Freshness & { total: number; other_engine: number; aftermarket: number; items: Recall[] };

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

export type DtcSummary = { code: string; title: string; severity: "low" | "medium" | "high" };
export type Dtc = {
  code: string;
  known: boolean;
  structure: { system: string; generic: boolean; subsystem: string | null };
  title: string | null;
  description: string | null;
  symptoms: string[];
  causes: string[];
  diagnostic_steps: string[];
  severity: "low" | "medium" | "high" | null;
  systems: string[];
  source: string | null;
  source_license: string | null;
  related_entries: { id: number; title: string; kind: string }[];
};

export type Kind = "procedure" | "torque_spec" | "fluid_capacity" | "spec" | "part_note" | "labor_time" | "dtc_guide";
export const KINDS: Kind[] = ["procedure", "torque_spec", "fluid_capacity", "spec", "part_note", "labor_time"];
export type Person = { id: number | null; display_name: string; role?: string | null };
export type Source = { type: string; citation?: string };
export type AppliesTo = { make_id: number; model_id?: number | null; year_from: number; year_to: number; displacement_l?: number | null; engine_family_id?: number | null };
export type EntryTags = { applies_to: AppliesTo[]; systems: string[]; dtcs: string[] };
export type Revision = {
  id: number;
  number: number;
  title: string;
  data: Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  tags: EntryTags;
  edit_summary: string | null;
  status: "approved" | "pending" | "rejected";
  author: Person;
  created_at: string;
  fact_check?: { written_by: string; reviewed_by: string; reviewed_at: string; notes?: string } | null;
  unverified?: number;
};
export type LaborCell = { reports: number; median?: number; min?: number; max?: number };
export type Entry = {
  id: number;
  kind: Kind;
  status: "published" | "pending" | "hidden";
  title: string;
  score: number;
  my_vote: number;
  safety_critical: boolean;
  verification: { state: "verified" | "verified_older" | "none"; by?: Person | null; at?: string | null; revision_number?: number | null };
  open_reports: number;
  under_review?: boolean;
  pending_revisions: number;
  revision: Revision | null;
  tags_display: { applies_to: (AppliesTo & { make: string; model: string | null })[]; systems: string[]; dtcs: string[] };
  labor: Record<string, Record<string, LaborCell>> | null;
  created_at: string;
  updated_at: string;
};
export type EntrySummary = {
  id: number;
  kind: Kind;
  title: string;
  score: number;
  verified: boolean;
  safety_critical: boolean;
  generic: boolean;
  summary: string | null;
  data?: Record<string, any> | null; // eslint-disable-line @typescript-eslint/no-explicit-any
  updated_at: string;
};

export type EngineFamily = {
  id: number;
  slug: string;
  name: string;
  manufacturer: string;
  displacement_l: number | null;
  cylinders: number | null;
  layout: string | null;
  fuel_type: string | null;
  aspiration: string | null;
  codes: string | null;
  year_from: number | null;
  year_to: number | null;
  applications: string[];
  notes: string | null;
  vehicle_count: number | null;
};
export type EngineDetail = EngineFamily & {
  used_in: { make: string; model: string; model_id: number; year_from: number; year_to: number; vehicles: number }[];
};
