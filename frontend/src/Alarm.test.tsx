import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { OperatorScreen } from "./OperatorScreen";
import { travelling } from "./mock/fixtures.generated";
import { useScreenStore } from "./state/store";
import { ALARM_INTERVAL_MS } from "./config";

const starts = vi.fn();
const oscillators: Array<{ frequency: { value: number } }> = [];
class FakeAudioContext {
  state = "running";
  currentTime = 0;
  destination = {};
  resume = vi.fn(async () => {});
  close = vi.fn(async () => {});
  createOscillator() {
    const oscillator = {
      frequency: { value: 0 },
      connect: vi.fn(),
      disconnect: vi.fn(),
      start: starts,
      stop: vi.fn(),
      onended: null,
    };
    oscillators.push(oscillator);
    return oscillator;
  }
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("AudioContext", FakeAudioContext);
  starts.mockClear();
  oscillators.length = 0;
  useScreenStore.setState({
    snapshot: travelling,
    connection: "connected",
    screenDisconnected: false,
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("test_OI_011_alarm_only_sounds_for_unacknowledged_critical", async () => {
  render(<OperatorScreen />);
  await act(async () =>
    fireEvent.click(
      screen.getByRole("button", { name: "Start operator console" }),
    ),
  );
  expect(starts).not.toHaveBeenCalled();
  const critical = {
    alert_id: "1",
    code: "ESTOP_ACTIVE",
    severity: "CRITICAL" as const,
    title: "Stopped",
    source: "Payload",
    recommended_action: "Inspect",
    raised_at: travelling.server_time,
    acknowledged: false,
    active: true,
  };
  act(() =>
    useScreenStore.setState({
      snapshot: { ...travelling, alerts: [critical] },
    }),
  );
  expect(starts).toHaveBeenCalledTimes(2);
  expect(oscillators.map((oscillator) => oscillator.frequency.value)).toEqual([
    880, 660,
  ]);
  act(() => vi.advanceTimersByTime(ALARM_INTERVAL_MS));
  expect(starts).toHaveBeenCalledTimes(4);
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        alerts: [{ ...critical, acknowledged: true }],
      },
    }),
  );
  act(() => vi.advanceTimersByTime(ALARM_INTERVAL_MS * 2));
  expect(starts).toHaveBeenCalledTimes(4);
});

it("test_OI_011_blocked_audio_is_visible_and_can_be_retried", async () => {
  class BlockedAudio extends FakeAudioContext {
    resume = vi.fn(async () => {
      throw new Error("blocked");
    });
  }
  vi.stubGlobal("AudioContext", BlockedAudio);
  render(<OperatorScreen />);
  await act(async () =>
    fireEvent.click(
      screen.getByRole("button", { name: "Start operator console" }),
    ),
  );
  expect(
    screen.getByRole("button", { name: /Alarm sound is off/ }),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: /E-STOP/ })).toBeTruthy();
});
