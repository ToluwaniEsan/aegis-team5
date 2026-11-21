import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { PayloadState, Snapshot } from "./contracts/ui";
import { fault_shift, travelling } from "./mock/fixtures.generated";
import { PayloadStatus } from "./PayloadStatus";
import { useScreenStore } from "./state/store";

function show(snapshot: Snapshot | null, disconnected = false) {
  useScreenStore.setState({ snapshot, screenDisconnected: disconnected });
  return render(<PayloadStatus />);
}

afterEach(() => {
  cleanup();
  useScreenStore.setState({ snapshot: null, screenDisconnected: false });
});

it.each([
  ["EMPTY", "EMPTY"],
  ["LOADED", "LOADED"],
  ["SECURED", "SECURED"],
  ["TRAVELLING", "TRAVEL"],
  ["AT_DESTINATION", "AT DEST"],
  ["RELEASED", "RELEASED"],
  ["DELIVERED", "DELIVERED"],
] as [PayloadState, string][])(
  "test_AEG_510_observed_%s_highlights_%s",
  (state, label) => {
    show({ ...travelling, payload: { ...travelling.payload, state } });
    expect(
      screen
        .getByLabelText("Payload progress")
        .querySelector('[aria-current="step"]')?.textContent,
    ).toBe(label);
  },
);

it("test_AEG_509_held_and_returning_have_special_treatments", () => {
  const snapshot = {
    ...fault_shift,
    payload: {
      ...fault_shift.payload,
      state: "HELD" as const,
      held_from: "TRAVELLING" as const,
    },
  };
  const { rerender } = show(snapshot);
  expect(
    screen.getByText(/HELD.*was TRAVELLING.*release blocked/),
  ).toBeTruthy();
  expect(screen.queryByLabelText("Payload progress")).toBeNull();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        payload: { ...snapshot.payload, state: "RETURNING" },
      },
    }),
  );
  rerender(<PayloadStatus />);
  expect(screen.getByText("Returning to origin")).toBeTruthy();
  expect(screen.queryByLabelText("Payload progress")).toBeNull();
});

it("test_OI_017_stale_and_disconnected_keep_values_and_mark_age", () => {
  const snapshot = {
    ...travelling,
    payload: { ...travelling.payload, stale: true, age_s: 12 },
  };
  const { container, rerender } = show(snapshot);
  expect(screen.getByText("OUT OF DATE · 12 s")).toBeTruthy();
  expect(screen.getByText("742.0 kg")).toBeTruthy();
  expect(container.querySelector(".payload-body.payload-stale")).toBeTruthy();
  act(() =>
    useScreenStore.setState({ snapshot: travelling, screenDisconnected: true }),
  );
  rerender(<PayloadStatus />);
  expect(screen.getByText("OUT OF DATE · 0 s")).toBeTruthy();
  expect(screen.getByText("742.0 kg")).toBeTruthy();
  expect(container.querySelector(".payload-body.payload-stale")).toBeTruthy();
});

it("test_OI_008_startup_placeholder_never_displays_unobserved_values", () => {
  const snapshot = {
    ...travelling,
    payload: {
      ...travelling.payload,
      updated_at: null,
      age_s: null,
      stale: true,
      state: "EMPTY" as const,
      locked: false,
      departure_permitted: false,
    },
  };
  const { container } = show(snapshot);
  expect(screen.getByText("Awaiting payload status")).toBeTruthy();
  expect(screen.queryByText("EMPTY")).toBeNull();
  expect(screen.queryByText("OPEN")).toBeNull();
  expect(container.querySelector('[aria-current="step"]')).toBeNull();
  act(() => useScreenStore.setState({ snapshot: travelling }));
  expect(screen.queryByText("Awaiting payload status")).toBeNull();
  expect(screen.getByText("742.0 kg")).toBeTruthy();
});

it("test_AEG_502_nullable_measurements_and_sensor_states", () => {
  const snapshot = {
    ...travelling,
    payload: {
      ...travelling.payload,
      mass_kg: null,
      shift_cm: null,
      release_energy_wh: null,
      locked: false,
      sensors: {
        load_cell: "UNKNOWN" as const,
        lock: "FAULT" as const,
        shift: "WARN" as const,
      },
    },
  };
  show(snapshot);
  expect(screen.getAllByText("Unavailable")).toHaveLength(3);
  expect(screen.getByText("OPEN")).toBeTruthy();
  for (const text of ["load UNKNOWN", "lock FAULT", "shift WARN"])
    expect(screen.getByText(text)).toBeTruthy();
});

it("test_AEG_510_shows_departure_reason_and_authorization", () => {
  const { rerender } = show(fault_shift);
  expect(screen.getByText("Blocked: Shift over limit")).toBeTruthy();
  expect(screen.getByText("No")).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        payload: {
          ...travelling.payload,
          departure_permitted: true,
          departure_reason: null,
          prerelease_authorized: true,
        },
      },
    }),
  );
  rerender(<PayloadStatus />);
  expect(screen.getByText("Permitted")).toBeTruthy();
  expect(screen.getByText("Yes")).toBeTruthy();
});

it("test_AEG_504_and_AEG_505_thresholds_use_snapshot_limits_inclusively", () => {
  const snapshot = {
    ...travelling,
    limits: {
      ...travelling.limits,
      mass_min_kg: 10,
      mass_max_kg: 20,
      unsecured_shift_cm: 7,
      release_energy_wh_max: 13,
    },
    payload: {
      ...travelling.payload,
      mass_kg: 10,
      shift_cm: 7,
      release_energy_wh: 12,
    },
  };
  const { container, rerender } = show(snapshot);
  expect(screen.getByText("10.0 kg").querySelector("svg")).toBeNull();
  expect(screen.getByText("7.0 cm").querySelector("svg")).toBeNull();
  expect(screen.getByText("12.0 Wh / 13.0 max")).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        payload: { ...snapshot.payload, mass_kg: 20, shift_cm: 7 },
      },
    }),
  );
  rerender(<PayloadStatus />);
  expect(screen.getByText("20.0 kg").querySelector("svg")).toBeNull();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        payload: { ...snapshot.payload, mass_kg: 20.1, shift_cm: 7.1 },
      },
    }),
  );
  rerender(<PayloadStatus />);
  expect(
    within(container.querySelector(".payload-rows")!)
      .getByText("20.1 kg")
      .querySelector('[data-severity="WARNING"]'),
  ).toBeTruthy();
  expect(
    screen
      .getByText(/7.1 cm.*limit 7.0/)
      .querySelector('[data-severity="WARNING"]'),
  ).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: { ...snapshot, payload: { ...snapshot.payload, mass_kg: 9.9 } },
    }),
  );
  rerender(<PayloadStatus />);
  expect(
    screen.getByText("9.9 kg").querySelector('[data-severity="WARNING"]'),
  ).toBeTruthy();
});
