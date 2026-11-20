import type { Snapshot } from "./contracts/ui";
import { SeverityShape } from "./SeverityShape";

export function LinkBadge({
  snapshot,
  disconnected,
}: {
  snapshot: Snapshot | null;
  disconnected: boolean;
}) {
  const link = snapshot?.link;
  const missing = !link?.updated_at;
  const stale = Boolean(link?.stale || disconnected);
  const state = missing ? "UNKNOWN" : link.state;
  const severity =
    state === "LOST" ? "CRITICAL" : state === "DEGRADED" ? "WARNING" : null;
  return (
    <div
      className={`status-badge ${severity?.toLowerCase() ?? ""} ${stale ? "out-of-date" : ""}`}
    >
      {severity && <SeverityShape severity={severity} />}
      <span>
        LINK {state}
        {state === "LOST" && " · duration unavailable"}
        {state === "CONNECTED" &&
          ` · ${link?.latency_ms == null ? "latency unavailable" : `${link.latency_ms} ms`}`}
        {!missing && stale && " · OUT OF DATE"}
      </span>
    </div>
  );
}
