import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { fault_shift, idle, travelling } from "./test-fixtures/fixtures";
import { RouteNavigation } from "./RouteNavigation";
import {
  projectPoints,
  routeHeading,
  ROUTE_HEIGHT,
  ROUTE_MARGIN,
  ROUTE_WIDTH,
  travelledPoints,
} from "./routeGeometry";
import { useScreenStore } from "./state/store";

afterEach(() => {
  cleanup();
  useScreenStore.setState({ snapshot: null, screenDisconnected: false });
});

it("test_OI_012_idle_and_travelling_snapshots", () => {
  useScreenStore.setState({ snapshot: idle });
  const { rerender, container } = render(<RouteNavigation />);
  expect(screen.getByText("No active mission")).toBeTruthy();
  act(() => useScreenStore.setState({ snapshot: travelling }));
  rerender(<RouteNavigation />);
  expect(screen.getByText("FOB Alpha")).toBeTruthy();
  expect(screen.getByText("Outpost Bravo")).toBeTruthy();
  expect(screen.getByText("46 %")).toBeTruthy();
  expect(screen.getByText("07:40")).toBeTruthy();
  expect(screen.getByText("Moving")).toBeTruthy();
  expect(screen.getByText("8.0 m/s")).toBeTruthy();
  expect(container.querySelector(".route-travelled")).toBeTruthy();
  expect(container.querySelector(".route-vehicle")).toBeTruthy();
});

it("test_OI_012_blocked_notice_draws_old_route_cross_and_caution", () => {
  const blocked = {
    reason: "Bridge out",
    at: travelling.nav.route[0],
    old_route: travelling.nav.route,
    new_eta_s: 500,
    since: travelling.server_time,
  };
  useScreenStore.setState({
    snapshot: { ...fault_shift, nav: { ...fault_shift.nav, blocked } },
  });
  const { container } = render(<RouteNavigation />);
  expect(screen.getByText("CAUTION · ROUTE BLOCKED")).toBeTruthy();
  expect(screen.getByText("Bridge out · new ETA 08:20")).toBeTruthy();
  expect(container.querySelector(".route-old")).toBeTruthy();
  expect(container.querySelector(".route-cross")).toBeTruthy();
  expect(container.querySelector('[data-severity="CAUTION"]')).toBeTruthy();
  act(() => useScreenStore.setState({ snapshot: travelling }));
  expect(screen.queryByText(/ROUTE BLOCKED/)).toBeNull();
  expect(screen.queryByText(/route clear/i)).toBeNull();
});

it("test_OI_008_stale_disconnected_and_unobserved_navigation", () => {
  useScreenStore.setState({
    snapshot: {
      ...travelling,
      nav: { ...travelling.nav, stale: true, age_s: 12 },
    },
  });
  const { container } = render(<RouteNavigation />);
  expect(screen.getByText("OUT OF DATE · 12 s")).toBeTruthy();
  expect(screen.getByText("07:40")).toBeTruthy();
  expect(container.querySelector(".navigation-stale")).toBeTruthy();
  act(() =>
    useScreenStore.setState({ snapshot: travelling, screenDisconnected: true }),
  );
  expect(screen.getByText("OUT OF DATE · 0 s")).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        nav: {
          ...travelling.nav,
          updated_at: null,
          age_s: null,
          moving: false,
        },
      },
      screenDisconnected: false,
    }),
  );
  expect(screen.getByText("Awaiting navigation status")).toBeTruthy();
  expect(screen.queryByText("Stopped")).toBeNull();
});

it("test_OI_012_missing_route_position_and_measurements_are_unavailable", () => {
  useScreenStore.setState({
    snapshot: {
      ...travelling,
      nav: {
        ...travelling.nav,
        route: [],
        origin: null,
        destination: null,
        position: null,
        eta_s: null,
        speed_mps: null,
        progress_pct: null,
        moving: false,
      },
    },
  });
  const { container } = render(<RouteNavigation />);
  expect(screen.getByText("Route unavailable")).toBeTruthy();
  expect(screen.getByText("Stopped")).toBeTruthy();
  expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  expect(screen.getByText("Speed unavailable")).toBeTruthy();
  expect(container.querySelector(".route-vehicle")).toBeNull();
});

it("test_OI_012_projection_edge_cases_are_finite_and_equal_scale", () => {
  expect(projectPoints([])).toEqual([]);
  const same = projectPoints([
    { lat: 1, lon: 2 },
    { lat: 1, lon: 2 },
  ]);
  expect(same).toEqual([
    { x: 250, y: 165 },
    { x: 250, y: 165 },
  ]);
  expect(routeHeading(same, same[0])).toBeNull();
  expect(travelledPoints(same, 50)).toEqual([same[0]]);
  const points = projectPoints([
    { lat: 0, lon: 0 },
    { lat: 1, lon: 1 },
    { lat: 2, lon: 4 },
  ]);
  for (const point of points) {
    expect(Number.isFinite(point.x) && Number.isFinite(point.y)).toBe(true);
    expect(point.x).toBeGreaterThanOrEqual(ROUTE_MARGIN);
    expect(point.x).toBeLessThanOrEqual(ROUTE_WIDTH - ROUTE_MARGIN);
    expect(point.y).toBeGreaterThanOrEqual(ROUTE_MARGIN);
    expect(point.y).toBeLessThanOrEqual(ROUTE_HEIGHT - ROUTE_MARGIN);
  }
  expect(points[1].x - points[0].x).toBeCloseTo(points[0].y - points[1].y);
  expect(travelledPoints([points[0]], 50)).toEqual([]);
  expect(routeHeading(points, points[0])).not.toBeNull();
});

it("test_OI_012_single_and_repeated_route_points_never_generate_invalid_svg", () => {
  const point = { lat: 34, lon: -86 };
  useScreenStore.setState({
    snapshot: {
      ...travelling,
      nav: {
        ...travelling.nav,
        route: [point],
        origin: null,
        destination: null,
        position: point,
      },
    },
  });
  const { container } = render(<RouteNavigation />);
  expect(container.querySelector(".route-map")).toBeTruthy();
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        nav: { ...travelling.nav, route: [point, point], position: point },
      },
    }),
  );
  expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
});
