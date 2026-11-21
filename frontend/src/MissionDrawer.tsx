import { useEffect, useRef, useState } from "react";
import type { CommandName, Priority, Snapshot } from "./contracts/ui";
import { useScreenStore } from "./state/store";

export type DrawerMode = "assign" | "queue" | "update";
export type DrawerIntent = {
  command: CommandName;
  args: Record<string, unknown>;
};
type Fields = {
  origin: string;
  destination: string;
  priority: Priority;
  mass: string;
  length: string;
  width: string;
  height: string;
  authorized: boolean;
};

function validate(
  fields: Fields,
  mode: DrawerMode,
  snapshot: Snapshot | null,
  connected: boolean,
  missionId: string | null,
  payloadId: string | null,
  confirmationAvailable: boolean,
): string[] {
  if (!snapshot) return ["Awaiting ground station data"];
  if (!connected) return ["Screen disconnected from ground station"];
  const command = mode === "update" ? "update_payload" : "assign_mission";
  const permission = snapshot.allowed[command];
  const reasons: string[] = [];
  if (!permission.allowed)
    reasons.push(permission.reason ?? "Command not permitted");
  if (permission.needs_confirmation && !confirmationAvailable)
    reasons.push("Confirmation dialog unavailable");
  if ((snapshot.mission.active?.mission_id ?? null) !== missionId)
    reasons.push("Active mission changed; close and reopen the form");
  if (mode !== "update" && snapshot.mission.next_ids.payload_id !== payloadId)
    reasons.push("Payload ID changed; close and reopen the form");
  if (mode === "update" && !missionId)
    reasons.push("No active mission to update");
  if (mode !== "update") {
    if (!snapshot.places.some((place) => place.id === fields.origin))
      reasons.push("Select an available origin");
    if (!snapshot.places.some((place) => place.id === fields.destination))
      reasons.push("Select an available destination");
    if (fields.origin && fields.origin === fields.destination)
      reasons.push("Origin and destination must differ");
  }
  const num = (value: string) => (value.trim() === "" ? NaN : Number(value));
  const mass = num(fields.mass);
  if (
    !Number.isFinite(mass) ||
    mass < snapshot.limits.mass_min_kg ||
    mass > snapshot.limits.mass_max_kg
  )
    reasons.push(
      `Weight must be ${snapshot.limits.mass_min_kg} to ${snapshot.limits.mass_max_kg} kg`,
    );
  for (const key of ["length", "width", "height"] as const) {
    const value = num(fields[key]);
    const maximum = snapshot.limits.dims_max_cm[key];
    if (!Number.isFinite(value) || value <= 0 || value > maximum)
      reasons.push(
        `${key[0].toUpperCase() + key.slice(1)} must be greater than 0 and at most ${maximum} cm`,
      );
  }
  return reasons;
}

export function MissionDrawer({
  mode,
  onClose,
  pending,
  feedback,
  onSubmit,
  confirmationAvailable,
}: {
  mode: DrawerMode;
  onClose: () => void;
  pending: boolean;
  feedback: string | null;
  onSubmit: (intent: DrawerIntent, requiresConfirmation: boolean) => void;
  confirmationAvailable: boolean;
}) {
  const snapshot = useScreenStore((state) => state.snapshot);
  const connected = useScreenStore(
    (state) => state.connection === "connected" && !state.screenDisconnected,
  );
  const initial = useRef(snapshot);
  const missionId = initial.current?.mission.active?.mission_id ?? null;
  const payloadId = initial.current?.mission.next_ids.payload_id ?? null;
  const mission = initial.current?.mission.active;
  const [fields, setFields] = useState<Fields>({
    origin: "",
    destination: "",
    priority: "ROUTINE",
    mass: mode === "update" && mission ? String(mission.declared_mass_kg) : "",
    length: mode === "update" && mission ? String(mission.dims_cm.length) : "",
    width: mode === "update" && mission ? String(mission.dims_cm.width) : "",
    height: mode === "update" && mission ? String(mission.dims_cm.height) : "",
    authorized: false,
  });
  const first = useRef<HTMLSelectElement | HTMLInputElement>(null);
  useEffect(() => {
    first.current?.focus();
  }, []);
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);
  const reasons = validate(
    fields,
    mode,
    snapshot,
    connected,
    missionId,
    payloadId,
    confirmationAvailable,
  );
  const command = mode === "update" ? "update_payload" : "assign_mission";
  const update = (name: keyof Fields, value: string | boolean) =>
    setFields((previous) => ({ ...previous, [name]: value }));
  const submit = () => {
    const state = useScreenStore.getState();
    const latest = state.snapshot;
    if (
      pending ||
      validate(
        fields,
        mode,
        latest,
        state.connection === "connected" && !state.screenDisconnected,
        missionId,
        payloadId,
        confirmationAvailable,
      ).length ||
      !latest
    )
      return;
    const load = {
      declared_mass_kg: Number(fields.mass),
      dims_cm: {
        length: Number(fields.length),
        width: Number(fields.width),
        height: Number(fields.height),
      },
    };
    const args =
      mode === "update"
        ? load
        : {
            origin_id: fields.origin,
            destination_id: fields.destination,
            priority: fields.priority,
            ...load,
            prerelease_authorized: fields.authorized,
          };
    onSubmit({ command, args }, latest.allowed[command].needs_confirmation);
  };
  return (
    <div className="drawer-backdrop">
      <section
        className="mission-drawer"
        role="dialog"
        aria-label={mode === "update" ? "Update payload" : "Mission form"}
      >
        <h2>
          {mode === "update"
            ? "Update payload"
            : mode === "queue"
              ? "Queue mission"
              : "New mission"}
        </h2>
        <form
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          {mode !== "update" && (
            <>
              <label>
                Origin
                <select
                  ref={first as React.RefObject<HTMLSelectElement>}
                  value={fields.origin}
                  onChange={(e) => update("origin", e.target.value)}
                >
                  <option value="">Select origin</option>
                  {snapshot?.places.map((place) => (
                    <option key={place.id} value={place.id}>
                      {place.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Destination
                <select
                  value={fields.destination}
                  onChange={(e) => update("destination", e.target.value)}
                >
                  <option value="">Select destination</option>
                  {snapshot?.places.map((place) => (
                    <option key={place.id} value={place.id}>
                      {place.name}
                    </option>
                  ))}
                </select>
              </label>
              <fieldset>
                <legend>Priority</legend>
                {(["ROUTINE", "PRIORITY", "URGENT"] as const).map(
                  (priority) => (
                    <label key={priority}>
                      <input
                        type="radio"
                        name="priority"
                        checked={fields.priority === priority}
                        onChange={() => update("priority", priority)}
                      />
                      {priority}
                    </label>
                  ),
                )}
              </fieldset>
            </>
          )}
          <label>
            Declared weight (kg)
            <input
              ref={
                mode === "update"
                  ? (first as React.RefObject<HTMLInputElement>)
                  : undefined
              }
              type="number"
              value={fields.mass}
              onChange={(e) => update("mass", e.target.value)}
            />
          </label>
          <fieldset className="drawer-dims">
            <legend>Dimensions (cm)</legend>
            {(["length", "width", "height"] as const).map((key) => (
              <label key={key}>
                {key[0].toUpperCase() + key.slice(1)}
                <input
                  type="number"
                  value={fields[key]}
                  onChange={(e) => update(key, e.target.value)}
                />
              </label>
            ))}
          </fieldset>
          {mode !== "update" && (
            <>
              <label className="drawer-check">
                <input
                  type="checkbox"
                  checked={fields.authorized}
                  onChange={(e) => update("authorized", e.target.checked)}
                />
                Pre-authorize release if the link is lost at the destination
              </label>
              <label>
                Payload ID
                <input value={payloadId ?? "Unavailable"} readOnly />
              </label>
            </>
          )}
          {reasons.length > 0 && (
            <ul className="drawer-reasons">
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          {feedback && (
            <p className="drawer-feedback" role="status">
              {feedback}
            </p>
          )}
          <div className="drawer-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={pending || reasons.length > 0}>
              {pending
                ? "Sending…"
                : mode === "update"
                  ? "Update payload"
                  : mode === "queue"
                    ? "Add to queue"
                    : "Assign mission"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
