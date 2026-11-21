import { useRef, useState } from "react";
import type { AlertView } from "./contracts/ui";
import { sendCommand } from "./net/socket";
import { SeverityShape } from "./SeverityShape";
import { useScreenStore } from "./state/store";

export function AlertsFeed() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const connected = useScreenStore(
    (state) => state.connection === "connected" && !state.screenDisconnected,
  );
  const [expanded, setExpanded] = useState(false);
  const [pending, setPending] = useState<string[]>([]);
  const pendingIds = useRef(new Set<string>());
  const [feedback, setFeedback] = useState<string | null>(null);
  const alerts = [...(snapshot?.alerts ?? [])]
    .filter((alert) => alert.active || !alert.acknowledged)
    .sort(
      (a, b) =>
        ({ CRITICAL: 0, WARNING: 1, CAUTION: 2 })[a.severity] -
          { CRITICAL: 0, WARNING: 1, CAUTION: 2 }[b.severity] ||
        b.raised_at.localeCompare(a.raised_at),
    );
  async function acknowledge(alert: AlertView) {
    const state = useScreenStore.getState();
    const current = state.snapshot?.alerts.find(
      (item) => item.alert_id === alert.alert_id,
    );
    if (
      !current ||
      current.acknowledged ||
      state.connection !== "connected" ||
      state.screenDisconnected ||
      !state.snapshot?.allowed.ack_fault.allowed ||
      state.snapshot.allowed.ack_fault.needs_confirmation ||
      pendingIds.current.has(alert.alert_id)
    )
      return;
    pendingIds.current.add(alert.alert_id);
    setPending((ids) => [...ids, alert.alert_id]);
    setFeedback(null);
    try {
      const result = await sendCommand(
        "ack_fault",
        { alert_id: alert.alert_id },
        false,
      );
      if (!result.accepted)
        setFeedback(result.reason ?? "Acknowledgement refused");
    } catch {
      setFeedback(
        "Acknowledgement result unavailable. Check the command tracker.",
      );
    } finally {
      pendingIds.current.delete(alert.alert_id);
      setPending((ids) => ids.filter((id) => id !== alert.alert_id));
    }
  }
  const permission = snapshot?.allowed.ack_fault;
  const unavailable = !snapshot
    ? "Awaiting ground station data"
    : !connected
      ? "Screen disconnected from ground station"
      : !permission?.allowed
        ? (permission?.reason ?? "Acknowledgement unavailable")
        : permission.needs_confirmation
          ? "Acknowledgement requires confirmation"
          : null;
  return (
    <div className="alert-feed">
      <div className="alert-heading">
        <strong>
          ALERTS &amp; RECOMMENDED ACTIONS · {alerts.length}
          {!connected && snapshot ? " · OUT OF DATE" : ""}
        </strong>
        <span>critical first, then newest</span>
      </div>
      <div
        className={expanded ? "alert-expanded" : undefined}
        aria-label={expanded ? "All alerts" : "Recent alerts"}
      >
        {expanded && (
          <button type="button" onClick={() => setExpanded(false)}>
            Close alerts
          </button>
        )}
        {(expanded ? alerts : alerts.slice(0, 3)).map((alert) => {
          const age = snapshot
            ? (Date.parse(snapshot.server_time) - Date.parse(alert.raised_at)) /
              1000
            : NaN;
          return (
            <div
              key={alert.alert_id}
              className={`alert-row alert-${alert.severity.toLowerCase()}${alert.severity === "CRITICAL" && !alert.acknowledged ? " alert-pulse" : ""}`}
            >
              <span className="alert-severity">
                <SeverityShape severity={alert.severity} />
                {alert.severity}
              </span>
              <span className="alert-text">
                <strong>
                  {alert.title} · {alert.source}
                </strong>
                <span>{alert.recommended_action}</span>
              </span>
              <span className="alert-time">
                {alert.raised_at.slice(11, 19)}Z ·{" "}
                {Number.isFinite(age) && age >= 0
                  ? `${Math.floor(age)} s`
                  : "age unavailable"}
              </span>
              {alert.acknowledged ? (
                <span>Acknowledged</span>
              ) : (
                <div>
                  <button
                    type="button"
                    disabled={
                      Boolean(unavailable) || pending.includes(alert.alert_id)
                    }
                    onClick={() => void acknowledge(alert)}
                  >
                    Acknowledge
                  </button>
                  {unavailable && (
                    <span className="alert-unavailable">{unavailable}</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {!expanded && alerts.length > 3 && (
        <button
          type="button"
          className="alerts-more"
          onClick={() => setExpanded(true)}
        >
          +{alerts.length - 3} more
        </button>
      )}
      {feedback && (
        <div role="alert" className="alert-feedback">
          {feedback}
        </div>
      )}
    </div>
  );
}
