import { useRef, useState } from "react";
import type { CommandName, Snapshot } from "./contracts/ui";
import { sendCommand } from "./net/socket";
import { SeverityShape } from "./SeverityShape";
import { useScreenStore } from "./state/store";
import { MissionDrawer } from "./MissionDrawer";
import type { DrawerIntent, DrawerMode } from "./MissionDrawer";

type Intent = { command: CommandName; args: Record<string, unknown> };
export type CommandPanelProps = {
  onOpenMissionDrawer?: (mode: "assign" | "queue" | "update") => void;
  onRequestConfirmation?: (intent: Intent) => void;
};

const controls = [
  { command: "abort", label: "Abort" },
  { command: "return_to_origin", label: "Return to origin" },
  { command: "change_destination", label: "Change destination" },
  { command: "update_payload", label: "Update payload" },
  { command: "release", label: "Release payload" },
] as const;

function unavailable(
  snapshot: Snapshot | null,
  connected: boolean,
  command: CommandName,
): string | null {
  if (!snapshot) return "Awaiting ground station data";
  if (!connected) return "Screen disconnected from ground station";
  const permission = snapshot.allowed[command];
  return permission.allowed
    ? null
    : (permission.reason ?? "Command not permitted");
}

function CommandButton({
  label,
  reason,
  onClick,
}: {
  label: string;
  reason: string | null;
  onClick: () => void;
}) {
  return (
    <div className="command-control">
      <button type="button" disabled={reason !== null} onClick={onClick}>
        {label}
      </button>
      {reason && <div className="command-reason">{reason}</div>}
    </div>
  );
}

export function CommandPanel({
  onOpenMissionDrawer,
  onRequestConfirmation,
}: CommandPanelProps) {
  const snapshot = useScreenStore((state) => state.snapshot);
  const connection = useScreenStore((state) => state.connection);
  const disconnected = useScreenStore((state) => state.screenDisconnected);
  const connected = connection === "connected" && !disconnected;
  const [pickerOpen, setPickerOpen] = useState(false);
  const [destination, setDestination] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerMode | null>(null);
  const [drawerPending, setDrawerPending] = useState(false);
  const sending = useRef(false);
  const opener = useRef<HTMLElement | null>(null);

  function openDrawer(mode: DrawerMode) {
    if (onOpenMissionDrawer) {
      onOpenMissionDrawer(mode);
      return;
    }
    opener.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setFeedback(null);
    setDrawer(mode);
  }
  function closeDrawer() {
    setDrawer(null);
    opener.current?.focus();
  }
  async function submitDrawer(
    intent: DrawerIntent,
    needsConfirmation: boolean,
  ) {
    if (sending.current) return;
    if (needsConfirmation) {
      onRequestConfirmation?.(intent);
      return;
    }
    sending.current = true;
    setDrawerPending(true);
    setFeedback(null);
    try {
      const result = await sendCommand(intent.command, intent.args, false);
      setFeedback(
        result.accepted
          ? "Request accepted. Check the command tracker for progress."
          : (result.reason ?? "Command refused"),
      );
    } catch {
      setFeedback("Command result unavailable. Check the command tracker.");
    } finally {
      sending.current = false;
      setDrawerPending(false);
    }
  }

  async function execute(intent: Intent) {
    const state = useScreenStore.getState();
    const current = state.snapshot;
    const reason = unavailable(
      current,
      state.connection === "connected" && !state.screenDisconnected,
      intent.command,
    );
    if (reason || !current) {
      setFeedback(reason);
      return;
    }
    if (intent.command === "start_queued_mission" && current.mission.active) {
      setFeedback("Finish or abort the active mission first");
      return;
    }
    if (
      intent.command === "start_queued_mission" &&
      current.mission.queue[0]?.mission_id !== intent.args.mission_id
    ) {
      setFeedback("Start the first queued mission");
      return;
    }
    if (
      intent.command === "remove_queued_mission" &&
      !current.mission.queue.some(
        (mission) => mission.mission_id === intent.args.mission_id,
      )
    ) {
      setFeedback("Mission is not in the queue");
      return;
    }
    if (
      intent.command === "change_destination" &&
      !current.places.some(
        (place) =>
          place.id === intent.args.destination_id &&
          place.id !==
            (current.nav.destination?.id ??
              current.mission.active?.destination.id),
      )
    ) {
      setFeedback("Select an available destination");
      return;
    }
    if (current.allowed[intent.command].needs_confirmation) {
      if (onRequestConfirmation) onRequestConfirmation(intent);
      else setFeedback("Confirmation dialog unavailable");
      return;
    }
    setFeedback(null);
    try {
      const result = await sendCommand(intent.command, intent.args, false);
      if (!result.accepted) setFeedback(result.reason ?? "Command refused");
    } catch {
      setFeedback("Command result unavailable. Check the command tracker.");
    }
  }

  const formReason = unavailable(snapshot, connected, "assign_mission");
  const options =
    snapshot?.places.filter(
      (place) =>
        place.id !==
        (snapshot.nav.destination?.id ??
          snapshot.mission.active?.destination.id),
    ) ?? [];
  return (
    <div className="commands-panel">
      <CommandButton
        label={snapshot?.mission.active ? "Queue mission" : "New mission"}
        reason={formReason}
        onClick={() =>
          openDrawer(snapshot?.mission.active ? "queue" : "assign")
        }
      />
      <h2>MISSION CONTROLS</h2>
      <div className="command-grid">
        {controls.map(({ command, label }) => {
          let reason = unavailable(snapshot, connected, command);
          if (
            !reason &&
            command !== "change_destination" &&
            command !== "update_payload" &&
            snapshot?.allowed[command].needs_confirmation &&
            !onRequestConfirmation
          )
            reason = "Confirmation dialog unavailable";
          return (
            <CommandButton
              key={command}
              label={label}
              reason={reason}
              onClick={() => {
                if (command === "change_destination") {
                  setDestination("");
                  setPickerOpen(true);
                } else if (command === "update_payload") openDrawer("update");
                else void execute({ command, args: {} });
              }}
            />
          );
        })}
      </div>
      {pickerOpen && (
        <div className="destination-picker">
          <label htmlFor="destination">Destination</label>
          <select
            id="destination"
            value={destination}
            disabled={Boolean(
              unavailable(snapshot, connected, "change_destination"),
            )}
            onChange={(event) => setDestination(event.target.value)}
          >
            <option value="">Select destination</option>
            {options.map((place) => (
              <option key={place.id} value={place.id}>
                {place.name}
              </option>
            ))}
          </select>
          <CommandButton
            label="Apply destination"
            reason={
              unavailable(snapshot, connected, "change_destination") ??
              (!destination ||
              !options.some((place) => place.id === destination)
                ? "Select an available destination"
                : snapshot?.allowed.change_destination.needs_confirmation &&
                    !onRequestConfirmation
                  ? "Confirmation dialog unavailable"
                  : null)
            }
            onClick={() =>
              void execute({
                command: "change_destination",
                args: { destination_id: destination },
              })
            }
          />
          <button type="button" onClick={() => setPickerOpen(false)}>
            Cancel
          </button>
        </div>
      )}
      {feedback && !drawer && (
        <div className="command-feedback" role="alert">
          <SeverityShape severity="WARNING" />
          {feedback}
        </div>
      )}
      <h2>COMMAND TRACKER</h2>
      <div className="command-tracker">
        {snapshot?.commands.slice(0, 4).map((command) => (
          <div className="command-tracker-row" key={command.command_id}>
            <div className="command-track-line">
              <span>{command.label}</span>
              <span
                className={
                  command.state === "FAILED" ? "command-failed" : undefined
                }
              >
                {command.state === "FAILED" && (
                  <SeverityShape severity="CRITICAL" />
                )}
                {command.state}
              </span>
              <time dateTime={command.updated_at}>
                {command.updated_at.slice(11, 19)}Z
              </time>
            </div>
            {command.state === "FAILED" && command.reason && (
              <div className="command-failed">{command.reason}</div>
            )}
          </div>
        ))}
      </div>
      <h2>MISSION QUEUE · {snapshot?.mission.queue.length ?? "—"}</h2>
      <div className="mission-queue">
        {snapshot?.mission.queue.slice(0, 3).map((mission, index) => {
          const startReason =
            unavailable(snapshot, connected, "start_queued_mission") ??
            (snapshot.mission.active
              ? "Finish or abort the active mission first"
              : index !== 0
                ? "Start the first queued mission"
                : snapshot.allowed.start_queued_mission.needs_confirmation &&
                    !onRequestConfirmation
                  ? "Confirmation dialog unavailable"
                  : null);
          const removeReason =
            unavailable(snapshot, connected, "remove_queued_mission") ??
            (snapshot.allowed.remove_queued_mission.needs_confirmation &&
            !onRequestConfirmation
              ? "Confirmation dialog unavailable"
              : null);
          return (
            <div className="queued-mission" key={mission.mission_id}>
              <div>
                <strong>{mission.mission_id}</strong> · {mission.origin.name} →{" "}
                {mission.destination.name} · {mission.declared_mass_kg} kg
              </div>
              <div className="queue-buttons">
                <CommandButton
                  label={`Start ${mission.mission_id}`}
                  reason={startReason}
                  onClick={() =>
                    void execute({
                      command: "start_queued_mission",
                      args: { mission_id: mission.mission_id },
                    })
                  }
                />
                <CommandButton
                  label={`Remove ${mission.mission_id}`}
                  reason={removeReason}
                  onClick={() =>
                    void execute({
                      command: "remove_queued_mission",
                      args: { mission_id: mission.mission_id },
                    })
                  }
                />
              </div>
            </div>
          );
        })}
      </div>
      {drawer && (
        <MissionDrawer
          mode={drawer}
          onClose={closeDrawer}
          pending={drawerPending}
          feedback={feedback}
          onSubmit={submitDrawer}
          confirmationAvailable={Boolean(onRequestConfirmation)}
        />
      )}
    </div>
  );
}
