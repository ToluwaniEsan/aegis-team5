import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { Health, Snapshot } from "./contracts/ui";
import { travelling } from "./mock/fixtures.generated";
import { useScreenStore } from "./state/store";
import { VehicleHealth } from "./VehicleHealth";

function show(snapshot: Snapshot | null, screenDisconnected = false) {
  useScreenStore.setState({ snapshot, screenDisconnected });
  return render(<VehicleHealth />);
}

afterEach(() => {
  cleanup();
  useScreenStore.setState({ snapshot: null, screenDisconnected: false });
});

it.each([
  ["OK", null],
  ["WARN", "WARNING"],
  ["FAULT", "CRITICAL"],
  ["UNKNOWN", null],
] as [Health, string | null][])(
  "test_OI_018_health_%s_has_text_and_correct_shape",
  (status, shape) => {
    const power = { ...travelling.vehicle_health.subsystems[0], status };
    show({
      ...travelling,
      vehicle_health: {
        ...travelling.vehicle_health,
        subsystems: [power, ...travelling.vehicle_health.subsystems.slice(1)],
      },
    });
    const row = screen.getByLabelText("Power & Battery");
    expect(within(row).getByText(status)).toBeTruthy();
    expect(
      row.querySelector("svg")?.getAttribute("data-severity") ?? null,
    ).toBe(shape);
  },
);

it("test_OI_005_shows_all_subsystems_details_teams_and_ages", () => {
  show(travelling);
  for (const item of travelling.vehicle_health.subsystems) {
    const row = screen.getByLabelText(item.label);
    expect(row.querySelector(".health-detail")?.textContent).toBe(item.detail);
    expect(within(row).getByText(`Team ${item.team}`)).toBeTruthy();
    expect(within(row).getByText("0 s")).toBeTruthy();
  }
  expect(screen.getByText("NOMINAL")).toBeTruthy();
});

it("test_OI_010_displays_overall_fault_and_degraded_shape", () => {
  const { rerender } = show({
    ...travelling,
    vehicle_health: { ...travelling.vehicle_health, overall: "FAULT" },
  });
  expect(
    screen.getByText("FAULT").querySelector('[data-severity="CRITICAL"]'),
  ).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        vehicle_health: { ...travelling.vehicle_health, overall: "DEGRADED" },
      },
    }),
  );
  rerender(<VehicleHealth />);
  expect(
    screen.getByText("DEGRADED").querySelector('[data-severity="WARNING"]'),
  ).toBeTruthy();
});

it("test_OI_008_stale_and_disconnected_rows_retain_values_and_age", () => {
  const power = {
    ...travelling.vehicle_health.subsystems[0],
    stale: true,
    age_s: 12,
  };
  const snapshot = {
    ...travelling,
    vehicle_health: {
      ...travelling.vehicle_health,
      subsystems: [power, ...travelling.vehicle_health.subsystems.slice(1)],
    },
  };
  const { rerender } = show(snapshot);
  const row = screen.getByLabelText("Power & Battery");
  expect(row.classList.contains("health-stale")).toBe(true);
  expect(within(row).getByText("12 s")).toBeTruthy();
  expect(within(row).getByText(power.detail)).toBeTruthy();
  expect(screen.getByText(/Hatched rows are OUT OF DATE/)).toBeTruthy();
  act(() =>
    useScreenStore.setState({ snapshot: travelling, screenDisconnected: true }),
  );
  rerender(<VehicleHealth />);
  expect(document.querySelectorAll(".health-row.health-stale")).toHaveLength(5);
  expect(
    within(screen.getByLabelText("Comms Link")).getByText("80 ms"),
  ).toBeTruthy();
});

it("test_OI_005_missing_observations_and_ages_do_not_imply_healthy", () => {
  const { rerender } = show(null);
  expect(screen.getAllByText("UNKNOWN")).toHaveLength(6);
  expect(screen.getAllByText("Team unavailable")).toHaveLength(5);
  const power = {
    ...travelling.vehicle_health.subsystems[0],
    updated_at: null,
    age_s: null,
    status: "OK" as const,
    detail: "92 %",
  };
  const mobility = { ...travelling.vehicle_health.subsystems[1], age_s: null };
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        vehicle_health: {
          ...travelling.vehicle_health,
          subsystems: [power, mobility],
        },
      },
    }),
  );
  rerender(<VehicleHealth />);
  expect(screen.getByText(/NOMINAL · DATA INCOMPLETE/)).toBeTruthy();
  const powerRow = screen.getByLabelText("Power & Battery");
  expect(within(powerRow).getByText("UNKNOWN")).toBeTruthy();
  expect(within(powerRow).queryByText("92 %")).toBeNull();
  expect(within(powerRow).getByText("—")).toBeTruthy();
  expect(
    within(screen.getByLabelText("Mobility & Drivetrain")).getByText("—"),
  ).toBeTruthy();
});
