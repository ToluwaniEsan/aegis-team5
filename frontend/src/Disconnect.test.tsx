import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { OperatorScreen } from "./OperatorScreen";
import { SCREEN_DISCONNECTED_AFTER_MS } from "./config";
import { idle } from "./mock/fixtures.generated";
import { useScreenStore } from "./state/store";
import { SocketClient } from "./net/socket";

class FakeSocket {
  static OPEN = 1;
  static current: FakeSocket;
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() {
    FakeSocket.current = this;
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeSocket);
  useScreenStore.setState({
    snapshot: null,
    connection: "connecting",
    screenDisconnected: false,
    pendingRequests: [],
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("test_OI_008_disconnect_bar_shows_frozen_ground_time_and_stale_panels", () => {
  const client = new SocketClient();
  render(<OperatorScreen />);
  act(() => {
    client.start();
    FakeSocket.current.open();
    FakeSocket.current.onmessage?.({ data: JSON.stringify(idle) });
    FakeSocket.current.close();
  });
  act(() => vi.advanceTimersByTime(SCREEN_DISCONNECTED_AFTER_MS - 1));
  expect(screen.queryByRole("alert")).toBeNull();
  act(() => vi.advanceTimersByTime(1));
  expect(screen.getByRole("alert").textContent).toContain(
    `data frozen at ${idle.server_time.slice(11, 19)}Z`,
  );
  expect(
    screen.getByRole("main").classList.contains("screen-disconnected"),
  ).toBe(true);
  act(() => {
    FakeSocket.current.open();
  });
  expect(screen.queryByRole("alert")).toBeNull();
  act(() => client.stop());
});
