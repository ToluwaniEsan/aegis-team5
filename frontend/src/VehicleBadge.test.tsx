import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { travelling } from "./mock/fixtures.generated";
import { VehicleBadge } from "./VehicleBadge";

afterEach(cleanup);

it.each([
  ["NOMINAL", null],
  ["DEGRADED", "WARNING"],
  ["FAULT", "CRITICAL"],
] as const)("test_GEN_002_vehicle_badge_%s", (overall, severity) => {
  const snapshot = {
    ...travelling,
    vehicle_health: { ...travelling.vehicle_health, overall },
  };
  const { container } = render(
    <VehicleBadge snapshot={snapshot} disconnected={false} />,
  );
  expect(screen.getByText(`VEHICLE ${overall}`)).toBeTruthy();
  expect(
    container.querySelector("svg")?.getAttribute("data-severity") ?? null,
  ).toBe(severity);
});

it("test_OI_008_missing_and_stale_vehicle_data_is_not_presented_as_current", () => {
  const { rerender } = render(
    <VehicleBadge snapshot={null} disconnected={false} />,
  );
  expect(screen.getByText("VEHICLE UNKNOWN")).toBeTruthy();
  rerender(<VehicleBadge snapshot={travelling} disconnected />);
  expect(screen.getByText("VEHICLE NOMINAL · OUT OF DATE")).toBeTruthy();
});
