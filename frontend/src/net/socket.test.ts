import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  COMMAND_RESULT_TIMEOUT_MS,
  RECONNECT_INITIAL_MS,
  RECONNECT_MAX_MS,
  SCREEN_DISCONNECTED_AFTER_MS,
} from "../config";
import { idle, travelling } from "../test-fixtures/fixtures";
import { useScreenStore } from "../state/store";
import { SocketClient } from "./socket";

class FakeSocket {
  static OPEN = 1;
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  send(value: string) {
    this.sent.push(value);
  }
  message(value: unknown) {
    this.onmessage?.({ data: JSON.stringify(value) });
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
  vi.spyOn(crypto, "randomUUID").mockReturnValue(
    "12345678-1234-4234-9234-123456789abc",
  );
  useScreenStore.setState({
    snapshot: null,
    connection: "connecting",
    screenDisconnected: false,
    pendingRequests: [],
  });
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("C2 WebSocket", () => {
  it("test_OI_005_replaces_whole_snapshots", () => {
    const client = new SocketClient("ws://localhost/ws");
    client.start();
    const ws = FakeSocket.instances[0];
    expect(ws.url).toBe("ws://localhost/ws");
    ws.open();
    ws.message(idle);
    expect(useScreenStore.getState().snapshot).toEqual(idle);
    ws.message({ kind: "snapshot", seq: 99, server_time: idle.server_time });
    expect(useScreenStore.getState().snapshot).toEqual(idle);
    ws.message(travelling);
    expect(useScreenStore.getState().snapshot).toEqual(travelling);
    client.stop();
  });
  it("test_OI_017_keeps_startup_placeholder_and_estop_value_unchanged", () => {
    const client = new SocketClient();
    client.start();
    const ws = FakeSocket.instances[0];
    ws.open();
    const placeholder = {
      ...idle,
      estop_active: false,
      payload: {
        ...idle.payload,
        updated_at: null,
        age_s: null,
        stale: true,
        departure_reason: "Awaiting payload status",
      },
    };
    ws.message(placeholder);
    expect(useScreenStore.getState().snapshot).toEqual(placeholder);
    expect(useScreenStore.getState().snapshot?.payload.updated_at).toBeNull();
    client.stop();
  });
  it("test_OI_006_sends_protocol_and_resolves_only_matching_result", async () => {
    const client = new SocketClient();
    client.start();
    const ws = FakeSocket.instances[0];
    ws.open();
    const promise = client.sendCommand("release", {}, true);
    const wire = JSON.parse(ws.sent[0]);
    expect(wire).toEqual({
      kind: "command",
      client_req_id: "12345678-1234-4234-9234-123456789abc",
      command: "release",
      args: {},
      confirmed: true,
    });
    expect(useScreenStore.getState().pendingRequests).toEqual([
      wire.client_req_id,
    ]);
    ws.message({
      kind: "command_result",
      client_req_id: "other",
      accepted: false,
      command_id: null,
      reason: "No",
    });
    expect(useScreenStore.getState().pendingRequests).toHaveLength(1);
    const result = {
      kind: "command_result",
      client_req_id: wire.client_req_id,
      accepted: true,
      command_id: "command-id",
      reason: null,
    };
    ws.message(result);
    expect(await promise).toEqual(result);
    expect(useScreenStore.getState().pendingRequests).toEqual([]);
    client.stop();
  });
  it("test_OI_006_timeout_is_uncertain_and_does_not_resend", async () => {
    const client = new SocketClient();
    client.start();
    const first = FakeSocket.instances[0];
    first.open();
    const pending = client.sendCommand("release", {}, true);
    first.close();
    vi.advanceTimersByTime(RECONNECT_INITIAL_MS);
    const second = FakeSocket.instances[1];
    second.open();
    vi.advanceTimersByTime(COMMAND_RESULT_TIMEOUT_MS - RECONNECT_INITIAL_MS);
    const result = await pending;
    expect(result.accepted).toBe(false);
    expect(result.reason).toBe(
      "No answer from the ground station. The command may have been sent: check the command tracker.",
    );
    expect(first.sent).toHaveLength(1);
    expect(second.sent).toHaveLength(0);
    expect(useScreenStore.getState().pendingRequests).toEqual([]);
    client.stop();
  });
  it("test_OI_008_reconnects_with_capped_backoff_and_retains_snapshot", () => {
    const client = new SocketClient();
    client.start();
    FakeSocket.instances[0].open();
    FakeSocket.instances[0].message(idle);
    FakeSocket.instances[0].close();
    for (const delay of [
      RECONNECT_INITIAL_MS,
      RECONNECT_INITIAL_MS * 2,
      RECONNECT_INITIAL_MS * 4,
      RECONNECT_INITIAL_MS * 8,
      RECONNECT_MAX_MS,
      RECONNECT_MAX_MS,
    ]) {
      const count = FakeSocket.instances.length;
      vi.advanceTimersByTime(delay - 1);
      expect(FakeSocket.instances).toHaveLength(count);
      vi.advanceTimersByTime(1);
      expect(FakeSocket.instances).toHaveLength(count + 1);
      FakeSocket.instances.at(-1)!.close();
    }
    expect(useScreenStore.getState().snapshot).toEqual(idle);
    expect(useScreenStore.getState().screenDisconnected).toBe(true);
    vi.advanceTimersByTime(RECONNECT_MAX_MS);
    FakeSocket.instances.at(-1)!.open();
    expect(useScreenStore.getState().screenDisconnected).toBe(false);
    expect(useScreenStore.getState().connection).toBe("connected");
    FakeSocket.instances.at(-1)!.close();
    vi.advanceTimersByTime(RECONNECT_INITIAL_MS);
    expect(FakeSocket.instances.at(-1)!.readyState).toBe(0);
    client.stop();
  });
  it("test_OI_008_cleanup_cancels_timers_and_settles_inflight_commands", async () => {
    const client = new SocketClient();
    client.start();
    const ws = FakeSocket.instances[0];
    ws.open();
    const result = client.sendCommand("estop", {}, false);
    client.stop();
    expect((await result).reason).toContain("may have been sent");
    expect(vi.getTimerCount()).toBe(0);
    vi.advanceTimersByTime(SCREEN_DISCONNECTED_AFTER_MS + RECONNECT_MAX_MS);
    expect(FakeSocket.instances).toHaveLength(1);
  });
  it("test_OI_006_offline_commands_are_refused_without_queueing", async () => {
    const client = new SocketClient();
    client.start();
    const result = await client.sendCommand("release", {}, true);
    expect(result.accepted).toBe(false);
    expect(result.reason).toContain("Command not sent");
    FakeSocket.instances[0].open();
    expect(FakeSocket.instances[0].sent).toEqual([]);
    client.stop();
  });
});
