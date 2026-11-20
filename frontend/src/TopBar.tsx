import { EStopButton } from "./EStopButton";
import { LinkBadge } from "./LinkBadge";
import { useScreenStore } from "./state/store";
import { VehicleBadge } from "./VehicleBadge";

export function TopBar() {
  const snapshot = useScreenStore((state) => state.snapshot);
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const mission = snapshot?.mission.active;
  const payload = snapshot?.payload;

  return (
    <header className="top" aria-label="Top bar">
      <div className="top-mission">
        <div className="mission-name">
          {mission
            ? `${mission.mission_id} · ${mission.origin.name} → ${mission.destination.name}`
            : snapshot
              ? "NO ACTIVE MISSION"
              : "MISSION DATA UNAVAILABLE"}
        </div>
        <div className="mission-payload">
          {payload?.updated_at
            ? `PAYLOAD ${payload.payload_id ?? "ID UNAVAILABLE"}${payload.stale || disconnected ? " · OUT OF DATE" : ""}`
            : "PAYLOAD AWAITING STATUS"}
        </div>
      </div>
      <div className="top-center">
        <time className="top-clock" dateTime={snapshot?.server_time}>
          {snapshot ? `${snapshot.server_time.slice(11, 19)} Z` : "--:--:-- Z"}
          {disconnected && " · OUT OF DATE"}
        </time>
        <LinkBadge snapshot={snapshot} disconnected={disconnected} />
        <VehicleBadge snapshot={snapshot} disconnected={disconnected} />
      </div>
      <EStopButton active={snapshot?.estop_active === true} />
    </header>
  );
}
