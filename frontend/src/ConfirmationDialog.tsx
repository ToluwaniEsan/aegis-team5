import { useEffect, useRef, useState } from "react";
import type { CommandName, Snapshot } from "./contracts/ui";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

export type ConfirmationIntent = {
  command: CommandName;
  args: Record<string, unknown>;
};
export type Review = {
  intent: ConfirmationIntent;
  context: string;
  title: string;
  consequence: string;
  details: string[];
  verb: string;
};

function context(intent: ConfirmationIntent, snapshot: Snapshot): string {
  const { command, args } = intent;
  const active = snapshot.mission.active;
  const permission = snapshot.allowed[command];
  const activeTarget = active && {
    mission_id: active.mission_id,
    payload_id: active.payload_id,
    destination: active.destination,
    origin: active.origin,
  };
  const places = (ids: unknown[]) =>
    ids.map((id) => snapshot.places.find((place) => place.id === id) ?? null);
  const base = {
    active: activeTarget,
    payload: snapshot.payload.payload_id,
    destination: snapshot.nav.destination,
    permission,
  };
  if (command === "assign_mission")
    return JSON.stringify({
      active: activeTarget,
      payload: snapshot.payload.payload_id,
      permission,
      next: snapshot.mission.next_ids,
      places: places([args.origin_id, args.destination_id]),
      limits: snapshot.limits,
    });
  if (command === "update_payload")
    return JSON.stringify({
      ...base,
      load: active && { mass: active.declared_mass_kg, dims: active.dims_cm },
      limits: snapshot.limits,
    });
  if (command === "start_queued_mission" || command === "remove_queued_mission")
    return JSON.stringify({
      active: activeTarget,
      first: snapshot.mission.queue[0]?.mission_id,
      permission,
      target:
        snapshot.mission.queue.find(
          (item) => item.mission_id === args.mission_id,
        ) ?? null,
      payload: snapshot.payload.payload_id,
    });
  if (command === "change_destination")
    return JSON.stringify({ ...base, place: places([args.destination_id]) });
  return JSON.stringify(base);
}

function validForm(intent: ConfirmationIntent, snapshot: Snapshot): boolean {
  if (
    intent.command !== "assign_mission" &&
    intent.command !== "update_payload"
  )
    return true;
  const { args } = intent;
  const mass = args.declared_mass_kg;
  const dims = args.dims_cm;
  if (
    typeof mass !== "number" ||
    !Number.isFinite(mass) ||
    mass < snapshot.limits.mass_min_kg ||
    mass > snapshot.limits.mass_max_kg ||
    !dims ||
    typeof dims !== "object"
  )
    return false;
  const values = dims as Record<string, unknown>;
  for (const key of ["length", "width", "height"] as const) {
    const value = values[key];
    if (
      typeof value !== "number" ||
      !Number.isFinite(value) ||
      value <= 0 ||
      value > snapshot.limits.dims_max_cm[key]
    )
      return false;
  }
  if (intent.command === "assign_mission")
    return (
      typeof args.origin_id === "string" &&
      typeof args.destination_id === "string" &&
      args.origin_id !== args.destination_id &&
      snapshot.places.some((place) => place.id === args.origin_id) &&
      snapshot.places.some((place) => place.id === args.destination_id) &&
      ["ROUTINE", "PRIORITY", "URGENT"].includes(String(args.priority)) &&
      typeof args.prerelease_authorized === "boolean"
    );
  return true;
}

export function createReview(
  intent: ConfirmationIntent,
  snapshot: Snapshot,
): Review {
  const active = snapshot.mission.active;
  const payload =
    active?.payload_id ?? snapshot.payload.payload_id ?? "unavailable";
  const mission = active?.mission_id ?? "unavailable";
  const destination =
    snapshot.nav.destination?.name ?? active?.destination.name ?? "unavailable";
  const origin = active?.origin.name ?? "unavailable";
  const verbs: Partial<Record<CommandName, string>> = {
    abort: "Abort mission",
    return_to_origin: "Return to origin",
    release: "Release payload",
    change_destination: "Change destination",
    start_queued_mission: "Start queued mission",
    remove_queued_mission: "Remove queued mission",
    assign_mission: active ? "Add to queue" : "Assign mission",
    update_payload: "Update payload",
  };
  const verb = verbs[intent.command] ?? intent.command;
  const target =
    intent.command === "start_queued_mission" ||
    intent.command === "remove_queued_mission"
      ? String(intent.args.mission_id)
      : intent.command === "assign_mission"
        ? snapshot.mission.next_ids.payload_id
        : `${mission} · ${payload} · ${intent.command === "return_to_origin" ? origin : destination}`;
  const consequences: Partial<Record<CommandName, string>> = {
    abort: "The active mission will be aborted.",
    return_to_origin: "The vehicle will be instructed to return to its origin.",
    release: "The payload will be released; this cannot be undone.",
    change_destination:
      "The vehicle will be instructed to use the selected destination.",
    start_queued_mission: "The first queued mission will start.",
    remove_queued_mission:
      "The selected mission will be removed from the queue.",
    assign_mission: active
      ? "The mission will be added to the queue."
      : "The mission will be assigned to the vehicle.",
    update_payload: "The active mission's declared payload values will change.",
  };
  const details = Object.entries(intent.args).map(([key, value]) => {
    const place =
      key === "origin_id" || key === "destination_id"
        ? snapshot.places.find((item) => item.id === value)
        : undefined;
    const labels: Record<string, string> = {
      origin_id: "Origin",
      destination_id: "Destination",
      mission_id: "Mission",
      priority: "Priority",
      declared_mass_kg: "Declared weight",
      dims_cm: "Dimensions",
      prerelease_authorized: "Pre-authorized release",
      alert_id: "Alert",
    };
    const label = labels[key] ?? key.replaceAll("_", " ");
    if (key === "dims_cm" && value && typeof value === "object") {
      const dims = value as Record<string, unknown>;
      return `${label}: ${dims.length} × ${dims.width} × ${dims.height} cm`;
    }
    const text = place
      ? `${place.name} (${place.id})`
      : typeof value === "boolean"
        ? value
          ? "Yes"
          : "No"
        : typeof value === "object"
          ? "Unavailable"
          : String(value);
    return `${label}: ${text}${key === "declared_mass_kg" ? " kg" : ""}`;
  });
  return {
    intent: structuredClone(intent),
    context: context(intent, snapshot),
    title: `${verb}: ${target}?`,
    consequence:
      consequences[intent.command] ?? "The selected command will be sent.",
    details,
    verb,
  };
}

export function ConfirmationDialog({
  review,
  onClose,
}: {
  review: Review;
  onClose: () => void;
}) {
  const cancel = useRef<HTMLButtonElement>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLElement>(null);
  const sending = useRef(false);
  // Set once the command is sent. The command itself changes the snapshot
  // (a release moves the payload to RELEASED), so after sending we stop
  // treating snapshot changes as "the context changed under the operator".
  const sent = useRef(false);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [invalidated, setInvalidated] = useState(false);
  useEffect(() => {
    cancel.current?.focus();
  }, []);
  useEffect(
    () =>
      useScreenStore.subscribe((state) => {
        if (sent.current) return;
        if (
          !state.snapshot ||
          context(review.intent, state.snapshot) !== review.context
        ) {
          setInvalidated(true);
          setError(
            state.snapshot?.allowed[review.intent.command].allowed === false
              ? `${state.snapshot.allowed[review.intent.command].reason ?? "Command not permitted"}. Cancel and review again.`
              : "Command context changed. Cancel and review the action again.",
          );
        }
      }),
    [review],
  );
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (
        event.key === "Tab" &&
        !pending &&
        !dialog.current?.contains(document.activeElement)
      ) {
        event.preventDefault();
        cancel.current?.focus();
      }
      if (event.key === "Escape" && !pending) {
        event.preventDefault();
        event.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", handle, true);
    return () => document.removeEventListener("keydown", handle, true);
  }, [onClose, pending]);
  const confirm = async () => {
    if (sending.current || result || invalidated) return;
    const state = useScreenStore.getState();
    const snapshot = state.snapshot;
    if (
      !snapshot ||
      state.connection !== "connected" ||
      state.screenDisconnected
    ) {
      setError(
        "Screen disconnected from ground station. Review again when connected.",
      );
      return;
    }
    const permission = snapshot.allowed[review.intent.command];
    if (!permission.allowed) {
      setError(permission.reason ?? "Command not permitted");
      return;
    }
    if (
      context(review.intent, snapshot) !== review.context ||
      !validForm(review.intent, snapshot)
    ) {
      setError("Command context changed. Cancel and review the action again.");
      return;
    }
    if (
      review.intent.command === "start_queued_mission" &&
      (snapshot.mission.active ||
        snapshot.mission.queue[0]?.mission_id !== review.intent.args.mission_id)
    ) {
      setError("Queue changed. Cancel and review again.");
      return;
    }
    if (
      review.intent.command === "remove_queued_mission" &&
      !snapshot.mission.queue.some(
        (item) => item.mission_id === review.intent.args.mission_id,
      )
    ) {
      setError("Mission is no longer queued. Cancel and review again.");
      return;
    }
    if (
      review.intent.command === "change_destination" &&
      !snapshot.places.some(
        (place) =>
          place.id === review.intent.args.destination_id &&
          place.id !==
            (snapshot.nav.destination?.id ??
              snapshot.mission.active?.destination.id),
      )
    ) {
      setError("Destination changed. Cancel and review again.");
      return;
    }
    sending.current = true;
    sent.current = true;
    setPending(true);
    setError(null);
    try {
      const reply = await sendCommand(
        review.intent.command,
        review.intent.args,
        true,
      );
      setResult(
        reply.accepted
          ? "Request accepted. Check the command tracker for progress."
          : (reply.reason ?? "Command refused"),
      );
    } catch {
      setResult("Command result unavailable. Check the command tracker.");
    } finally {
      sending.current = false;
      setPending(false);
    }
  };
  return (
    <div className="confirmation-backdrop">
      <section
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label="Confirm command"
        className="confirmation-dialog"
        onKeyDown={(event) => {
          if (event.key === "Enter") event.preventDefault();
          if (event.key === "Tab" && !pending) {
            if (
              event.shiftKey &&
              document.activeElement === cancel.current &&
              !confirmButton.current?.disabled
            ) {
              event.preventDefault();
              confirmButton.current?.focus();
            } else if (
              !event.shiftKey &&
              (document.activeElement === confirmButton.current ||
                (document.activeElement === cancel.current &&
                  confirmButton.current?.disabled))
            ) {
              event.preventDefault();
              cancel.current?.focus();
            }
          }
          if (event.key === "Escape" && !pending) {
            event.preventDefault();
            event.stopPropagation();
            onClose();
          }
        }}
      >
        <h2>{review.title}</h2>
        <p>{review.consequence}</p>
        {review.details.length > 0 && (
          <ul>
            {review.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        )}
        {error && <p role="alert">{error}</p>}
        {result && <p role="status">{result}</p>}
        <div className="confirmation-actions">
          <button
            ref={cancel}
            type="button"
            disabled={pending}
            onClick={onClose}
          >
            {result ? "Close" : "Cancel"}
          </button>
          <button
            ref={confirmButton}
            type="button"
            disabled={pending || result !== null || invalidated}
            onClick={() => void confirm()}
          >
            {pending ? "Sending…" : review.verb}
          </button>
        </div>
      </section>
    </div>
  );
}
