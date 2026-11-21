import { useScreenStore } from "./state/store";

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
        <header className="top" aria-label="Top bar" />
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
        <section className="panel" aria-label="Payload and vehicle health" />
        <section className="panel" aria-label="Route and navigation" />
        <section className="panel panel-right" aria-label="Mission controls" />
        <footer className="bottom" aria-label="Alerts and delivery" />
      </main>
      <p className="window-warning">
        Increase the window size to at least 1366 × 768.
      </p>
    </>
  );
}
