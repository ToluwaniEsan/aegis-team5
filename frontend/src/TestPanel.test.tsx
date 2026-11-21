import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TestPanel } from "./TestPanel";
import { idle } from "./test-fixtures/fixtures";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));
const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({
    ok: true,
    json: async () => ({ msg_id: "injection-1" }),
  });
  vi.stubGlobal("fetch", fetchMock);
  useScreenStore.setState({
    snapshot: idle,
    connection: "connected",
    screenDisconnected: false,
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("test_GEN_001_all_contract_injections_use_the_real_endpoint", async () => {
  render(<TestPanel />);
  const cases = [
    ["Inject shift", "payload", "shift", { cm: 1 }],
    ["Set sensor", "payload", "sensor", { sensor: "load_cell", health: "OK" }],
    ["Override mass", "payload", "mass_override", { kg: 1 }],
    ["Set release jam", "payload", "release_jam", { on: false }],
    ["Stop controller", "payload", "controller_crash", {}],
    ["Unload payload", "payload", "unload", {}],
    ["Set link", "link", "set", { latency_ms: 1, loss_pct: 1 }],
    ["Start outage", "link", "outage", { seconds: 1 }],
    ["Depart", "nav", "depart", {}],
    ["Arrive", "nav", "arrive", {}],
    ["Stop navigation", "nav", "stop", {}],
    ["Block route", "nav", "block_route", { reason: "test" }],
    ["Set navigation health", "nav", "health", { health: "OK" }],
    ["Set battery", "power", "battery", { pct: 1 }],
    ["Set drivetrain", "power", "drivetrain", { health: "OK" }],
    ["Set Team 1 mode", "team1", "mode", { mode: "test" }],
  ] as const;
  for (const [label, target, action, params] of cases) {
    const button = screen.getByRole("button", { name: label });
    const form = button.closest("form")!;
    for (const input of form.querySelectorAll("input"))
      fireEvent.change(input, {
        target: { value: input.type === "number" ? "1" : "test" },
      });
    fireEvent.click(button);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledTimes(
        cases.findIndex((entry) => entry[0] === label) + 1,
      ),
    );
    const [url, request] = fetchMock.mock.calls.at(-1)!;
    expect(url).toBe("/api/test/inject");
    expect(JSON.parse(request.body)).toEqual({ target, action, params });
  }
  expect(
    within(screen.getByRole("list")).getAllByRole("listitem"),
  ).toHaveLength(10);
});

it("test_GEN_001_disabled_mode_and_disconnection_do_not_inject", () => {
  useScreenStore.setState({ snapshot: { ...idle, test_mode: false } });
  render(<TestPanel />);
  expect(screen.getByText("Test mode is unavailable")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Inject shift" })).toBeNull();
  act(() =>
    useScreenStore.setState({ snapshot: idle, connection: "disconnected" }),
  );
  expect(
    (screen.getByRole("button", { name: "Depart" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(fetchMock).not.toHaveBeenCalled();
});

it("test_GEN_001_invalid_injection_reason_and_estop", async () => {
  fetchMock.mockResolvedValue({
    ok: false,
    status: 400,
    json: async () => ({ detail: "Invalid battery" }),
  });
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: true,
    command_id: "c",
    reason: null,
  });
  render(<TestPanel />);
  fireEvent.change(screen.getByLabelText("Battery (%)"), {
    target: { value: "500" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Set battery" }));
  expect(await screen.findByText("Set battery: Invalid battery")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /E-STOP/ }));
  expect(sendCommand).toHaveBeenCalledWith("estop", {}, false);
});
