import { useRef, useState } from "react";
import { sendCommand } from "./net/socket";
import { SeverityShape } from "./SeverityShape";

export function EStopButton({ active }: { active: boolean }) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const lastRequest = useRef(0);

  async function stop() {
    const request = ++lastRequest.current;
    setFeedback(null);
    try {
      const result = await sendCommand("estop", {}, false);
      if (request === lastRequest.current && !result.accepted) {
        setFeedback(result.reason ?? "E-STOP command was refused.");
      }
    } catch {
      if (request === lastRequest.current) {
        setFeedback("E-STOP result unavailable. Check the command tracker.");
      }
    }
  }

  return (
    <div className="estop-control">
      <button type="button" className="estop" onClick={stop}>
        <strong>{active ? "E-STOP ACTIVE" : "E-STOP"}</strong>
        <span>Stops vehicle · holds payload</span>
        <span>
          {active ? "acknowledge in alerts" : "E-STOP status unavailable"}
        </span>
      </button>
      {feedback && (
        <div className="estop-feedback" role="alert">
          <SeverityShape severity="CRITICAL" />
          <span>{feedback}</span>
        </div>
      )}
    </div>
  );
}
