import type { Health, Subsystem } from "./contracts/ui";
import { SeverityShape } from "./SeverityShape";
import { useScreenStore } from "./state/store";

const subsystems: { key: Subsystem["key"]; label: string }[] = [
  { key: "power", label: "Power & Battery" },
  { key: "mobility", label: "Mobility & Drivetrain" },
  { key: "navigation", label: "Navigation Sensors" },
  { key: "comms", label: "Comms Link" },
  { key: "payload_sensors", label: "Payload Bay Sensors" },
];

function HealthStatus({ status }: { status: Health }) {
  const severity =
    status === "WARN" ? "WARNING" : status === "FAULT" ? "CRITICAL" : null;
  return (
    <span className={`health-status health-${status.toLowerCase()}`}>
      {severity && <SeverityShape severity={severity} />}
      {status}
    </span>
  );
}

export function VehicleHealth() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const rows = subsystems.map(({ key, label }) => ({
    key,
    label,
    data: snapshot?.vehicle_health.subsystems.find((item) => item.key === key),
  }));
  const observed = rows.some(({ data }) => Boolean(data?.updated_at));
  const incomplete = rows.some(
    ({ data }) => !data?.updated_at || data.status === "UNKNOWN",
  );
  const stale = rows.some(
    ({ data }) => data?.updated_at && (data.stale || disconnected),
  );
  const overall = observed ? snapshot!.vehicle_health.overall : "UNKNOWN";
  const severity =
    overall === "FAULT"
      ? "CRITICAL"
      : overall === "DEGRADED"
        ? "WARNING"
        : null;

  return (
    <section className="health-card" aria-label="Vehicle health">
      <header className="health-header">
        <h2>VEHICLE HEALTH</h2>
        <span className={`health-overall health-${overall.toLowerCase()}`}>
          {severity && <SeverityShape severity={severity} />}
          {overall}
          {incomplete && observed && " · DATA INCOMPLETE"}
          {stale && " · OUT OF DATE"}
        </span>
      </header>
      {rows.map(({ key, label, data }) => {
        const hasObservation = Boolean(data?.updated_at);
        const isStale =
          hasObservation && (Boolean(data?.stale) || disconnected);
        return (
          <div
            className={`health-row${isStale ? " health-stale" : ""}`}
            key={key}
            aria-label={label}
          >
            <span className="health-name">
              {label}{" "}
              <span className="health-team">
                {data ? `Team ${data.team}` : "Team unavailable"}
              </span>
            </span>
            <HealthStatus status={hasObservation ? data!.status : "UNKNOWN"} />
            <span className="health-detail">
              {hasObservation ? data!.detail : "Unavailable"}
            </span>
            <span className="health-age">
              {hasObservation && data?.age_s != null
                ? `${data.age_s.toFixed(0)} s`
                : "—"}
            </span>
          </div>
        );
      })}
      {stale && (
        <p className="health-stale-note">
          Hatched rows are OUT OF DATE · last known values shown.
        </p>
      )}
    </section>
  );
}
