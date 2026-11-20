import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { travelling } from "./mock/fixtures.generated";
import { useScreenStore } from "./state/store";
import { TopBar } from "./TopBar";

afterEach(() => {
  cleanup();
  useScreenStore.setState({ snapshot: null, screenDisconnected: false });
});

it("test_AEG_510_displays_mission_payload_and_ground_clock", () => {
  useScreenStore.setState({ snapshot: travelling, screenDisconnected: false });
  render(<TopBar />);
  expect(
    screen.getByText("MSN-2026-001 · FOB Alpha → Outpost Bravo"),
  ).toBeTruthy();
  expect(screen.getByText("PAYLOAD PAY-2026-001")).toBeTruthy();
  expect(screen.getByText("15:04:05 Z")).toBeTruthy();
});

it("test_OI_008_unobserved_payload_is_awaiting_status", () => {
  useScreenStore.setState({
    snapshot: {
      ...travelling,
      payload: {
        ...travelling.payload,
        updated_at: null,
        age_s: null,
        stale: true,
        state: "EMPTY",
        payload_id: null,
      },
    },
  });
  render(<TopBar />);
  expect(screen.getByText("PAYLOAD AWAITING STATUS")).toBeTruthy();
  expect(screen.queryByText(/EMPTY/)).toBeNull();
});

it("test_OI_019_snapshot_false_is_not_shown_as_confirmed_inactive", () => {
  useScreenStore.setState({
    snapshot: { ...travelling, estop_active: false },
    screenDisconnected: true,
  });
  const { rerender } = render(<TopBar />);
  expect(screen.getByText("E-STOP status unavailable")).toBeTruthy();
  expect(screen.getByText("15:04:05 Z · OUT OF DATE")).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: { ...travelling, estop_active: true },
    }),
  );
  rerender(<TopBar />);
  expect(screen.getByText("E-STOP ACTIVE")).toBeTruthy();
});
