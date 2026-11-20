import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { AlertView } from "./contracts/ui";
import { AlertsFeed } from "./AlertsFeed";
import { travelling } from "./test-fixtures/fixtures";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));
const makeAlert = (
  id: string,
  severity: AlertView["severity"],
  raised_at: string,
): AlertView => ({
  alert_id: id,
  code: id,
  severity,
  title: `Alert ${id}`,
  source: "Payload",
  recommended_action: "Inspect payload",
  raised_at,
  acknowledged: false,
  active: true,
});
beforeEach(() => {
  vi.mocked(sendCommand).mockReset();
  useScreenStore.setState({
    connection: "connected",
    screenDisconnected: false,
  });
});
afterEach(cleanup);

it("test_OI_010_critical_order_overflow_and_acknowledgement", async () => {
  const time = travelling.server_time;
  const alerts = [
    makeAlert("caution", "CAUTION", time),
    makeAlert("old", "CRITICAL", "2026-11-19T15:04:00.000Z"),
    makeAlert("warning", "WARNING", time),
    makeAlert("new", "CRITICAL", time),
  ];
  useScreenStore.setState({
    snapshot: {
      ...travelling,
      alerts,
      allowed: {
        ...travelling.allowed,
        ack_fault: { allowed: true, reason: null, needs_confirmation: false },
      },
    },
  });
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: true,
    command_id: "c",
    reason: null,
  });
  render(<AlertsFeed />);
  const recent = screen.getByLabelText("Recent alerts");
  expect(
    Array.from(
      recent.querySelectorAll(".alert-text strong"),
      (node) => node.textContent,
    ),
  ).toEqual([
    "Alert new · Payload",
    "Alert old · Payload",
    "Alert warning · Payload",
  ]);
  expect(screen.queryByText("Alert caution · Payload")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "+1 more" }));
  const full = screen.getByLabelText("All alerts");
  expect(within(full).getByText("Alert caution · Payload")).toBeTruthy();
  fireEvent.click(
    within(full).getAllByRole("button", { name: "Acknowledge" })[0],
  );
  expect(sendCommand).toHaveBeenCalledWith(
    "ack_fault",
    { alert_id: "new" },
    false,
  );
  expect(
    within(full).getAllByRole("button", { name: "Acknowledge" }),
  ).toHaveLength(4);
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...useScreenStore.getState().snapshot!,
        alerts: alerts.map((a) =>
          a.alert_id === "new" ? { ...a, acknowledged: true } : a,
        ),
      },
    }),
  );
  expect(within(full).getByText("Acknowledged")).toBeTruthy();
});

it("test_OI_011_disconnected_and_refused_acknowledgement", async () => {
  const alert = makeAlert("one", "CRITICAL", travelling.server_time);
  const snapshot = {
    ...travelling,
    alerts: [alert],
    allowed: {
      ...travelling.allowed,
      ack_fault: { allowed: true, reason: null, needs_confirmation: false },
    },
  };
  useScreenStore.setState({ snapshot });
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: false,
    command_id: null,
    reason: "Command may have been sent",
  });
  render(<AlertsFeed />);
  fireEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Command may have been sent",
  );
  act(() => useScreenStore.setState({ connection: "disconnected" }));
  expect(
    (screen.getByRole("button", { name: "Acknowledge" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(sendCommand).toHaveBeenCalledTimes(1);
});
