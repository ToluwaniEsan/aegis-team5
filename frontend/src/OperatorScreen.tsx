import { useEffect, useRef, useState } from "react";
import { useScreenStore } from "./state/store";
import { TopBar } from "./TopBar";
import { PayloadStatus } from "./PayloadStatus";
import { VehicleHealth } from "./VehicleHealth";
import { RouteNavigation } from "./RouteNavigation";
import { CommandPanel } from "./CommandPanel";
import { AlertsFeed } from "./AlertsFeed";
import { DeliverySummary } from "./DeliverySummary";
import { Alarm } from "./audio/alarm";
import { ALARM_INTERVAL_MS } from "./config";

export function OperatorScreen() {
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const serverTime = useScreenStore((state) => state.snapshot?.server_time);
  const critical = useScreenStore(
    (state) =>
      state.snapshot?.alerts.some(
        (alert) => alert.severity === "CRITICAL" && !alert.acknowledged,
      ) ?? false,
  );
  const alarm = useRef<Alarm | null>(null);
  const [started, setStarted] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
  const [audioBlocked, setAudioBlocked] = useState(false);
  async function enableAlarm() {
    alarm.current ??= new Alarm();
    try {
      await alarm.current.unlock();
      setAudioReady(true);
      setAudioBlocked(false);
    } catch {
      setAudioReady(false);
      setAudioBlocked(true);
    }
    setStarted(true);
  }
  useEffect(() => {
    if (!audioReady || !critical) return;
    const sound = () => {
      try {
        alarm.current?.play();
      } catch {
        setAudioReady(false);
        setAudioBlocked(true);
      }
    };
    sound();
    const timer = setInterval(sound, ALARM_INTERVAL_MS);
    return () => {
      clearInterval(timer);
      alarm.current?.stop();
    };
  }, [audioReady, critical]);
  useEffect(
    () => () => {
      void alarm.current?.close();
    },
    [],
  );
  return (
    <>
      <main
        id="app"
        aria-label="Operator Screen"
        className={disconnected ? "screen-disconnected" : undefined}
      >
        <TopBar
          alarmBlocked={audioBlocked}
          enableAlarm={() => void enableAlarm()}
        />
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
        <footer className="bottom" aria-label="Alerts and delivery">
          <AlertsFeed />
          <DeliverySummary />
        </footer>
        {!started && (
          <div className="console-start">
            <button type="button" onClick={() => void enableAlarm()}>
              Start operator console
            </button>
          </div>
        )}
      </main>
      <p className="window-warning">
        Increase the window size to at least 1366 × 768.
      </p>
    </>
  );
}
