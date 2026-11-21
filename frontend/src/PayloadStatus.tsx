import type { Health, PayloadState, Snapshot } from "./contracts/ui";
import { SeverityShape } from "./SeverityShape";
import { useScreenStore } from "./state/store";

const steps: { state: PayloadState; label: string }[] = [
  { state: "EMPTY", label: "EMPTY" },
  { state: "LOADED", label: "LOADED" },
  { state: "SECURED", label: "SECURED" },
  { state: "TRAVELLING", label: "TRAVEL" },
  { state: "AT_DESTINATION", label: "AT DEST" },
  { state: "RELEASED", label: "RELEASED" },
  { state: "DELIVERED", label: "DELIVERED" },
];

function Sensor({ label, health }: { label: string; health: Health }) {
  const severity =
    health === "FAULT" ? "CRITICAL" : health === "WARN" ? "WARNING" : null;
  return (
    <span
      className={severity ? `payload-${severity.toLowerCase()}` : undefined}
    >
      {severity && <SeverityShape severity={severity} />}
      {label} {health}
    </span>
  );
}

function PayloadBody({ snapshot }: { snapshot: Snapshot }) {
  const { payload, limits } = snapshot;
  const current = steps.findIndex((step) => step.state === payload.state);
  const badMass =
    payload.mass_kg !== null &&
    (payload.mass_kg < limits.mass_min_kg ||
      payload.mass_kg > limits.mass_max_kg);
  const badShift =
    payload.shift_cm !== null && payload.shift_cm > limits.unsecured_shift_cm;
  return (
    <>
      <div className="payload-state">{payload.state}</div>
      {payload.state === "HELD" ? (
        <div className="payload-held">
          <SeverityShape severity="CRITICAL" /> HELD
          {payload.held_from && ` (was ${payload.held_from})`} · release blocked
        </div>
      ) : payload.state === "RETURNING" ? (
        <div className="payload-returning">Returning to origin</div>
      ) : (
        <div className="payload-stepper" aria-label="Payload progress">
          {steps.map((step, index) => (
            <span
              key={step.state}
              className={`payload-step${current === index ? " current" : ""}`}
              aria-current={current === index ? "step" : undefined}
            >
              {step.label}
            </span>
          ))}
        </div>
      )}
      <dl className="payload-rows">
        <div>
          <dt>Lock</dt>
          <dd className={payload.locked ? undefined : "payload-critical"}>
            {!payload.locked && <SeverityShape severity="CRITICAL" />}
            {payload.locked ? "Closed" : "OPEN"}
          </dd>
        </div>
        <div>
          <dt>Weight</dt>
          <dd className={badMass ? "payload-warning" : undefined}>
            {badMass && <SeverityShape severity="WARNING" />}
            {payload.mass_kg === null
              ? "Unavailable"
              : `${payload.mass_kg.toFixed(1)} kg`}
          </dd>
        </div>
        <div>
          <dt>Shift</dt>
          <dd className={badShift ? "payload-warning" : undefined}>
            {badShift && <SeverityShape severity="WARNING" />}
            {payload.shift_cm === null
              ? "Unavailable"
              : `${payload.shift_cm.toFixed(1)} cm`}
            {badShift && ` (limit ${limits.unsecured_shift_cm.toFixed(1)})`}
          </dd>
        </div>
        <div>
          <dt>Release energy</dt>
          <dd>
            {payload.release_energy_wh === null
              ? "Unavailable"
              : `${payload.release_energy_wh.toFixed(1)} Wh / ${limits.release_energy_wh_max.toFixed(1)} max`}
          </dd>
        </div>
        <div>
          <dt>Sensors</dt>
          <dd className="payload-sensors">
            <Sensor label="load" health={payload.sensors.load_cell} /> ·{" "}
            <Sensor label="lock" health={payload.sensors.lock} /> ·{" "}
            <Sensor label="shift" health={payload.sensors.shift} />
          </dd>
        </div>
        <div>
          <dt>Pre-authorized release</dt>
          <dd>{payload.prerelease_authorized ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Departure</dt>
          <dd
            className={
              payload.departure_permitted ? undefined : "payload-warning"
            }
          >
            {payload.departure_permitted
              ? "Permitted"
              : `Blocked: ${payload.departure_reason ?? "Reason unavailable"}`}
          </dd>
        </div>
      </dl>
    </>
  );
}

export function PayloadStatus() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const payload = snapshot?.payload;
  const observed = Boolean(payload?.updated_at);
  const stale = !observed || Boolean(payload?.stale) || disconnected;
  const age = payload?.age_s == null ? null : `${payload.age_s.toFixed(0)} s`;
  return (
    <section className="payload-card" aria-label="Payload status">
      <header className="payload-header">
        <h2>PAYLOAD</h2>
        <span>
          {stale
            ? `OUT OF DATE${age ? ` · ${age}` : ""}`
            : age
              ? `updated ${age} ago`
              : "age unavailable"}
        </span>
      </header>
      <div className={`payload-body${stale ? " payload-stale" : ""}`}>
        {observed && snapshot ? (
          <PayloadBody snapshot={snapshot} />
        ) : (
          <div className="payload-awaiting">Awaiting payload status</div>
        )}
      </div>
    </section>
  );
}
