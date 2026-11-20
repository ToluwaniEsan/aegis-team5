// frontend/src/contracts/ui.ts : FROZEN CONTRACT (see docs/02-contracts.md)

export type Severity = "CRITICAL" | "WARNING" | "CAUTION";
export type Health = "OK" | "WARN" | "FAULT" | "UNKNOWN";
export type LinkState = "CONNECTED" | "DEGRADED" | "LOST";
export type OverallHealth = "NOMINAL" | "DEGRADED" | "FAULT";
export type PayloadState =
  | "EMPTY" | "LOADED" | "SECURED" | "TRAVELLING" | "AT_DESTINATION"
  | "RELEASED" | "DELIVERED" | "RETURNING" | "HELD";
export type MissionStatus = "QUEUED" | "ASSIGNED" | "ACTIVE" | "COMPLETE" | "ABORTED";
export type Priority = "ROUTINE" | "PRIORITY" | "URGENT";
export type CommandName =
  | "assign_mission" | "start_queued_mission" | "remove_queued_mission"
  | "abort" | "return_to_origin" | "change_destination"
  | "update_payload" | "release" | "ack_fault" | "estop";
export type CommandState = "SENT" | "RECEIVED" | "COMPLETED" | "FAILED";

export interface LatLon { lat: number; lon: number }
export interface Place extends LatLon { id: string; name: string }
export interface Dims { length: number; width: number; height: number }

/** Every status group carries its own age so the screen can mark OUT OF DATE (OI-008, OI-017). */
export interface Freshness {
  updated_at: string | null;   // the sent_at of the last message for this group, null if none yet
  age_s: number | null;        // seconds since updated_at, computed by the server
  stale: boolean;              // age_s > limits.stale_after_s, or no data yet
}

export interface LinkView extends Freshness {
  state: LinkState;
  latency_ms: number | null;
  loss_pct: number | null;
}

export interface Subsystem extends Freshness {
  key: "power" | "mobility" | "navigation" | "comms" | "payload_sensors";
  label: string;               // "Power & Battery"
  team: 2 | 3 | 4 | 5;
  status: Health;
  detail: string;              // short, ready to show: "82 % · 41 km"
}

export interface PayloadView extends Freshness {
  state: PayloadState;
  held_from: PayloadState | null;
  payload_id: string | null;
  secured: boolean;            // lock closed, sensors OK, mass in range, shift within limit
  locked: boolean;             // the lock itself
  mass_kg: number | null;
  shift_cm: number | null;
  release_energy_wh: number | null;
  sensor_health: Health;       // worst of load_cell, lock, shift
  sensors: { load_cell: Health; lock: Health; shift: Health };
  prerelease_authorized: boolean;
  departure_permitted: boolean;
  departure_reason: string | null;  // why departure is blocked, null when permitted
}

export interface NavView extends Freshness {
  origin: Place | null;
  destination: Place | null;
  position: LatLon | null;
  route: LatLon[];
  progress_pct: number | null;
  moving: boolean;
  speed_mps: number | null;
  eta_s: number | null;
  blocked: null | { reason: string; at: LatLon; old_route: LatLon[]; new_eta_s: number | null; since: string };
}

export interface Mission {
  mission_id: string;
  payload_id: string;
  status: MissionStatus;
  origin: Place;
  destination: Place;
  priority: Priority;
  declared_mass_kg: number;
  dims_cm: Dims;
  prerelease_authorized: boolean;
  created_at: string;
}

export interface CommandView {
  command_id: string;          // envelope msg_id
  command: CommandName;
  label: string;               // "Release payload"
  state: CommandState;
  reason: string | null;       // set when FAILED
  sent_at: string;
  updated_at: string;
}

export interface Permission {
  allowed: boolean;
  reason: string | null;       // why not, in plain words (OI-004)
  needs_confirmation: boolean; // OI-003
}

export interface AlertView {
  alert_id: string;            // fault_id
  code: string;
  severity: Severity;
  title: string;               // "Payload shifted 3.1 cm"
  source: string;              // "Payload" | "Team 2 Navigation" | ...
  recommended_action: string;
  raised_at: string;
  acknowledged: boolean;
  active: boolean;             // condition still present
}

export interface DeliverySummary {
  mission_id: string;
  payload_id: string;
  destination: Place;
  released_at: string;
  confirmed_at: string;
  confirm_latency_s: number;   // AEG-508 evidence
  mass_kg: number;
  energy_used_wh: number;
}

export interface Snapshot {
  kind: "snapshot";
  seq: number;                 // increases by 1 per snapshot
  server_time: string;
  test_mode: boolean;
  link: LinkView;
  vehicle_health: { overall: OverallHealth; subsystems: Subsystem[] };
  payload: PayloadView;
  nav: NavView;
  mission: {
    active: Mission | null;
    queue: Mission[];
    next_ids: { mission_id: string; payload_id: string }; // pre-filled on the form (AEG-510)
  };
  commands: CommandView[];     // newest first, at most 8
  allowed: Record<CommandName, Permission>;
  alerts: AlertView[];         // active or unacknowledged; CRITICAL first, then newest
  estop_active: boolean;
  delivery: DeliverySummary | null;  // last completed delivery (OI-016)
  places: Place[];
  limits: {
    mass_min_kg: number; mass_max_kg: number; dims_max_cm: Dims; stale_after_s: number;
    unsecured_shift_cm: number; release_energy_wh_max: number;
  };
}

export interface UiCommand {
  kind: "command";
  client_req_id: string;       // uuid from the browser
  command: CommandName;
  args: Record<string, unknown>;  // see the table below
  confirmed: boolean;          // true only after the confirmation dialog (OI-003)
}

export interface CommandResult {
  kind: "command_result";
  client_req_id: string;
  accepted: boolean;           // false = refused locally, nothing was sent
  command_id: string | null;
  reason: string | null;
}

export type ServerMessage = Snapshot | CommandResult;
