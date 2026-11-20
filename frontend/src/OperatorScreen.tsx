import { useScreenStore } from "./state/store";
import { TopBar } from "./TopBar";
import { PayloadStatus } from "./PayloadStatus";
import { VehicleHealth } from "./VehicleHealth";
import { RouteNavigation } from "./RouteNavigation";
import { CommandPanel } from "./CommandPanel";

export function OperatorScreen() {
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const serverTime = useScreenStore((state) => state.snapshot?.server_time);
  return (
    <>
      <main
        id="app"
        aria-label="Operator Screen"
        className={disconnected ? "screen-disconnected" : undefined}
      >
        <TopBar />
        {disconnected && (
          <div className="disconnect-bar" role="alert">
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
              <path d="M5 0 L10 10 L0 10 Z" fill="currentColor" />
            </svg>
            SCREEN DISCONNECTED FROM GROUND STATION ·{" "}
            {serverTime
              ? `data frozen at ${serverTime.slice(11, 19)}Z`
              : "data unavailable"}
          </div>
        )}
        <section
          className="panel panel-left"
          aria-label="Payload and vehicle health"
        >
          <PayloadStatus />
          <VehicleHealth />
        </section>
        <section
          className="panel panel-route"
          aria-label="Route and navigation"
        >
          <RouteNavigation />
        </section>
        <section className="panel panel-right" aria-label="Mission controls">
          <CommandPanel />
        </section>
        <footer className="bottom" aria-label="Alerts and delivery" />
      </main>
      <p className="window-warning">
        Increase the window size to at least 1366 × 768.
      </p>
    </>
  );
}
