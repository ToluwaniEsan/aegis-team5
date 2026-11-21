import {
  COMMAND_RESULT_TIMEOUT_MS,
  RECONNECT_INITIAL_MS,
  RECONNECT_MAX_MS,
  SCREEN_DISCONNECTED_AFTER_MS,
} from "../config";
import type {
  CommandName,
  CommandResult,
  Snapshot,
  UiCommand,
} from "../contracts/ui";
import { useScreenStore } from "../state/store";

const UNCERTAIN_REASON =
  "No answer from the ground station. The command may have been sent: check the command tracker.";

type Pending = {
  resolve: (result: CommandResult) => void;
  timer: ReturnType<typeof setTimeout>;
};

function isFullSnapshot(value: object): value is Snapshot {
  const has = (object: unknown, keys: string[]) =>
    object !== null &&
    typeof object === "object" &&
    keys.every((key) => Object.hasOwn(object, key));
  if (
    !has(value, [
      "seq",
      "server_time",
      "test_mode",
      "link",
      "vehicle_health",
      "payload",
      "nav",
      "mission",
      "commands",
      "allowed",
      "alerts",
      "estop_active",
      "delivery",
      "places",
      "limits",
    ])
  )
    return false;
  const snapshot = value as Snapshot;
  return (
    typeof snapshot.seq === "number" &&
    typeof snapshot.server_time === "string" &&
    has(snapshot.link, [
      "updated_at",
      "age_s",
      "stale",
      "state",
      "latency_ms",
      "loss_pct",
    ]) &&
    has(snapshot.payload, [
      "updated_at",
      "age_s",
      "stale",
      "state",
      "held_from",
      "payload_id",
      "secured",
      "locked",
      "mass_kg",
      "shift_cm",
      "release_energy_wh",
      "sensor_health",
      "sensors",
      "prerelease_authorized",
      "departure_permitted",
      "departure_reason",
    ]) &&
    has(snapshot.payload.sensors, ["load_cell", "lock", "shift"]) &&
    has(snapshot.nav, [
      "updated_at",
      "age_s",
      "stale",
      "origin",
      "destination",
      "position",
      "route",
      "progress_pct",
      "moving",
      "speed_mps",
      "eta_s",
      "blocked",
    ]) &&
    has(snapshot.vehicle_health, ["overall", "subsystems"]) &&
    Array.isArray(snapshot.vehicle_health.subsystems) &&
    has(snapshot.mission, ["active", "queue", "next_ids"]) &&
    Array.isArray(snapshot.mission.queue) &&
    has(snapshot.mission.next_ids, ["mission_id", "payload_id"]) &&
    has(snapshot.allowed, [
      "assign_mission",
      "start_queued_mission",
      "remove_queued_mission",
      "abort",
      "return_to_origin",
      "change_destination",
      "update_payload",
      "release",
      "ack_fault",
      "estop",
    ]) &&
    has(snapshot.limits, [
      "mass_min_kg",
      "mass_max_kg",
      "dims_max_cm",
      "stale_after_s",
      "unsecured_shift_cm",
      "release_energy_wh_max",
    ]) &&
    Array.isArray(snapshot.nav.route) &&
    Array.isArray(snapshot.commands) &&
    Array.isArray(snapshot.alerts) &&
    Array.isArray(snapshot.places)
  );
}

export class SocketClient {
  private socket: WebSocket | null = null;
  private retry: ReturnType<typeof setTimeout> | null = null;
  private disconnectedTimer: ReturnType<typeof setTimeout> | null = null;
  private nextDelay = RECONNECT_INITIAL_MS;
  private stopped = true;
  private pending = new Map<string, Pending>();

  constructor(private readonly url: string = SocketClient.defaultUrl()) {}

  static defaultUrl(): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws`;
  }

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    // Starting a new source must not present an old mock snapshot as live data.
    useScreenStore.setState({ snapshot: null });
    useScreenStore.getState().setConnection("connecting");
    this.connect();
  }

  private connect(): void {
    if (this.stopped) return;
    let socket: WebSocket;
    try {
      socket = new WebSocket(this.url);
    } catch {
      this.closed();
      return;
    }
    this.socket = socket;
    socket.onopen = () => {
      if (this.stopped || this.socket !== socket) return;
      this.nextDelay = RECONNECT_INITIAL_MS;
      if (this.disconnectedTimer !== null) clearTimeout(this.disconnectedTimer);
      this.disconnectedTimer = null;
      useScreenStore.getState().setScreenDisconnected(false);
      useScreenStore.getState().setConnection("connected");
    };
    socket.onmessage = (event: MessageEvent) => {
      if (
        this.stopped ||
        this.socket !== socket ||
        typeof event.data !== "string"
      )
        return;
      let message: unknown;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!message || typeof message !== "object" || !("kind" in message))
        return;
      if (message.kind === "snapshot" && isFullSnapshot(message)) {
        useScreenStore.getState().setSnapshot(message);
      } else if (
        message.kind === "command_result" &&
        "client_req_id" in message &&
        typeof message.client_req_id === "string" &&
        "accepted" in message &&
        typeof message.accepted === "boolean" &&
        "command_id" in message &&
        (message.command_id === null ||
          typeof message.command_id === "string") &&
        "reason" in message &&
        (message.reason === null || typeof message.reason === "string")
      ) {
        this.finish(message as CommandResult);
      }
    };
    socket.onerror = () => socket.close();
    socket.onclose = () => {
      if (this.socket !== socket || this.stopped) return;
      this.socket = null;
      this.closed();
    };
  }

  private closed(): void {
    useScreenStore.getState().setConnection("disconnected");
    if (
      this.disconnectedTimer === null &&
      !useScreenStore.getState().screenDisconnected
    ) {
      this.disconnectedTimer = setTimeout(() => {
        this.disconnectedTimer = null;
        if (
          !this.stopped &&
          useScreenStore.getState().connection !== "connected"
        ) {
          useScreenStore.getState().setScreenDisconnected(true);
        }
      }, SCREEN_DISCONNECTED_AFTER_MS);
    }
    if (this.retry === null) {
      const delay = this.nextDelay;
      this.nextDelay = Math.min(this.nextDelay * 2, RECONNECT_MAX_MS);
      this.retry = setTimeout(() => {
        this.retry = null;
        this.connect();
      }, delay);
    }
  }

  sendCommand(
    command: CommandName,
    args: Record<string, unknown>,
    confirmed: boolean,
  ): Promise<CommandResult> {
    const id = crypto.randomUUID();
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return Promise.resolve({
        kind: "command_result",
        client_req_id: id,
        accepted: false,
        command_id: null,
        reason: "Screen disconnected from ground station. Command not sent.",
      });
    }
    const request: UiCommand = {
      kind: "command",
      client_req_id: id,
      command,
      args,
      confirmed,
    };
    return new Promise((resolve) => {
      const timer = setTimeout(
        () =>
          this.finish({
            kind: "command_result",
            client_req_id: id,
            accepted: false,
            command_id: null,
            reason: UNCERTAIN_REASON,
          }),
        COMMAND_RESULT_TIMEOUT_MS,
      );
      this.pending.set(id, { resolve, timer });
      useScreenStore.getState().addPending(id);
      try {
        this.socket!.send(JSON.stringify(request));
      } catch {
        this.finish({
          kind: "command_result",
          client_req_id: id,
          accepted: false,
          command_id: null,
          reason: UNCERTAIN_REASON,
        });
      }
    });
  }

  private finish(result: CommandResult): void {
    const pending = this.pending.get(result.client_req_id);
    if (!pending) return;
    clearTimeout(pending.timer);
    this.pending.delete(result.client_req_id);
    useScreenStore.getState().removePending(result.client_req_id);
    pending.resolve(result);
  }

  stop(): void {
    if (this.stopped) return;
    this.stopped = true;
    if (this.retry !== null) clearTimeout(this.retry);
    if (this.disconnectedTimer !== null) clearTimeout(this.disconnectedTimer);
    this.retry = this.disconnectedTimer = null;
    const socket = this.socket;
    this.socket = null;
    socket?.close();
    for (const id of [...this.pending.keys()])
      this.finish({
        kind: "command_result",
        client_req_id: id,
        accepted: false,
        command_id: null,
        reason: UNCERTAIN_REASON,
      });
    useScreenStore.getState().setConnection("disconnected");
    useScreenStore.getState().setScreenDisconnected(false);
  }
}

export const socketClient = new SocketClient();
export const sendCommand = (
  command: CommandName,
  args: Record<string, unknown>,
  confirmed: boolean,
) => socketClient.sendCommand(command, args, confirmed);
