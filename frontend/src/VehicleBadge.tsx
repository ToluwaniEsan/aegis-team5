import type { Snapshot } from "./contracts/ui";
import { SeverityShape } from "./SeverityShape";

export function VehicleBadge({
  snapshot,
  disconnected,
}: {
  snapshot: Snapshot | null;
  disconnected: boolean;
}) {
  const subsystems = snapshot?.vehicle_health.subsystems ?? [];
  const missing =
    !snapshot ||
    subsystems.length === 0 ||
    subsystems.every((s) => !s.updated_at);
  const stale =
    disconnected ||
    subsystems.some((s) => s.stale || !s.updated_at || s.status === "UNKNOWN");
  const status = missing ? "UNKNOWN" : snapshot.vehicle_health.overall;
  const severity =
    status === "FAULT" ? "CRITICAL" : status === "DEGRADED" ? "WARNING" : null;

  return (
    <div
      className={`status-badge ${severity?.toLowerCase() ?? ""} ${stale ? "out-of-date" : ""}`}
    >
      {severity && <SeverityShape severity={severity} />}
      <span>
        VEHICLE {status}
        {!missing && stale ? " · OUT OF DATE" : ""}
      </span>
    </div>
  );
}
