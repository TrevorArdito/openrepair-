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
