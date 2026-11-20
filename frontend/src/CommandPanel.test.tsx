import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CommandPanel } from "./CommandPanel";
import type { Snapshot } from "./contracts/ui";
import { idle, travelling } from "./mock/fixtures.generated";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));
beforeEach(() => {
  useScreenStore.setState({
    snapshot: null,
    connection: "connected",
    screenDisconnected: false,
  });
  vi.mocked(sendCommand).mockReset();
});
afterEach(cleanup);
function show(snapshot: Snapshot) {
  useScreenStore.setState({ snapshot });
  return render(<CommandPanel />);
}

it("test_OI_004_disabled_reasons_and_permission_updates", () => {
  show(travelling);
  expect(screen.getByText("Only before departure")).toBeTruthy();
  expect(screen.getByText("Vehicle is moving")).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Abort" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(
    screen.getAllByText("Confirmation dialog unavailable").length,
  ).toBeGreaterThan(0);
  const next = {
    ...travelling,
    allowed: {
      ...travelling.allowed,
      abort: {
        allowed: false,
        reason: "Payload is held",
        needs_confirmation: true,
      },
    },
  };
  act(() => useScreenStore.setState({ snapshot: next }));
  expect(screen.getByText("Payload is held")).toBeTruthy();
});

it("test_OI_004_every_command_displays_its_backend_refusal", () => {
  const names = [
    "abort",
    "return_to_origin",
    "change_destination",
    "update_payload",
    "release",
  ] as const;
  const allowed = { ...travelling.allowed };
  names.forEach((name) => {
    allowed[name] = {
      ...allowed[name],
      allowed: false,
      reason: `Refused ${name}`,
    };
  });
  show({ ...travelling, allowed });
  names.forEach((name) =>
    expect(screen.getByText(`Refused ${name}`)).toBeTruthy(),
  );
});

it("test_OI_004_no_snapshot_or_connection_never_enables_commands", () => {
  render(<CommandPanel />);
  expect(
    (screen.getByRole("button", { name: "New mission" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(
    screen.getAllByText("Awaiting ground station data").length,
  ).toBeGreaterThan(0);
  act(() =>
    useScreenStore.setState({ snapshot: travelling, screenDisconnected: true }),
  );
  expect(
    (
      screen.getByRole("button", {
        name: "Change destination",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});

it("test_OI_003_forms_and_confirmations_do_not_send_without_integrations", () => {
  show(travelling);
  expect(screen.getByText("Mission form unavailable")).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Queue mission" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Abort" }));
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_OI_003_destination_picker_excludes_current_and_requires_confirmation", () => {
  show(travelling);
  fireEvent.click(screen.getByRole("button", { name: "Change destination" }));
  const select = screen.getByLabelText("Destination");
  expect(
    within(select).queryByRole("option", { name: "Outpost Bravo" }),
  ).toBeNull();
  fireEvent.change(select, { target: { value: "OP_CHARLIE" } });
  expect(
    (
      screen.getByRole("button", {
        name: "Apply destination",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_OI_003_confirmation_and_drawer_callbacks_receive_intent_only", () => {
  useScreenStore.setState({ snapshot: travelling });
  const confirmation = vi.fn();
  const drawer = vi.fn();
  render(
    <CommandPanel
      onRequestConfirmation={confirmation}
      onOpenMissionDrawer={drawer}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Abort" }));
  expect(confirmation).toHaveBeenCalledWith({ command: "abort", args: {} });
  fireEvent.click(screen.getByRole("button", { name: "Queue mission" }));
  expect(drawer).toHaveBeenCalledWith("queue");
  fireEvent.click(screen.getByRole("button", { name: "Change destination" }));
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "OP_CHARLIE" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply destination" }));
  expect(confirmation).toHaveBeenCalledWith({
    command: "change_destination",
    args: { destination_id: "OP_CHARLIE" },
  });
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_OI_006_lifecycle_comes_from_snapshots_and_failed_reason_is_visible", async () => {
  const mission = {
    ...travelling.mission.active!,
    mission_id: "MSN-Q1",
    status: "QUEUED" as const,
  };
  const snapshot = {
    ...travelling,
    mission: { ...travelling.mission, queue: [mission] },
    allowed: {
      ...travelling.allowed,
      remove_queued_mission: {
        allowed: true,
        needs_confirmation: false,
        reason: null,
      },
    },
  };
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: true,
    command_id: "1",
    reason: null,
  });
  show(snapshot);
  fireEvent.click(screen.getByRole("button", { name: "Remove MSN-Q1" }));
  expect(sendCommand).toHaveBeenCalledWith(
    "remove_queued_mission",
    { mission_id: "MSN-Q1" },
    false,
  );
  expect(screen.queryByText("SENT")).toBeNull();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        commands: [
          {
            command_id: "c",
            command: "abort",
            label: "Abort mission",
            state: "FAILED",
            reason: "No confirmation in 5 s. Not resent.",
            sent_at: snapshot.server_time,
            updated_at: snapshot.server_time,
          },
        ],
      },
    }),
  );
  expect(screen.getByText("FAILED")).toBeTruthy();
  expect(screen.getByText("No confirmation in 5 s. Not resent.")).toBeTruthy();
  expect(screen.getByText("15:04:05Z")).toBeTruthy();
});

it("test_OI_015_queue_order_and_disconnection", () => {
  const mission = { ...travelling.mission.active!, status: "QUEUED" as const };
  const snapshot = {
    ...idle,
    mission: {
      ...idle.mission,
      active: null,
      queue: [
        { ...mission, mission_id: "Q1" },
        { ...mission, mission_id: "Q2" },
      ],
    },
    allowed: {
      ...idle.allowed,
      start_queued_mission: {
        allowed: true,
        reason: null,
        needs_confirmation: true,
      },
      remove_queued_mission: {
        allowed: true,
        reason: null,
        needs_confirmation: false,
      },
    },
  };
  const confirm = vi.fn();
  useScreenStore.setState({ snapshot });
  render(<CommandPanel onRequestConfirmation={confirm} />);
  fireEvent.click(screen.getByRole("button", { name: "Start Q1" }));
  expect(confirm).toHaveBeenCalledWith({
    command: "start_queued_mission",
    args: { mission_id: "Q1" },
  });
  expect(
    (screen.getByRole("button", { name: "Start Q2" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(screen.getByText("Start the first queued mission")).toBeTruthy();
  act(() => useScreenStore.setState({ connection: "disconnected" }));
  expect(
    (screen.getByRole("button", { name: "Remove Q1" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(
    screen.getAllByText("Screen disconnected from ground station").length,
  ).toBeGreaterThan(0);
});

it("test_OI_006_and_OI_015_limit_snapshot_tracker_and_queue", () => {
  const mission = { ...travelling.mission.active!, status: "QUEUED" as const };
  const queue = [1, 2, 3, 4].map((n) => ({ ...mission, mission_id: `Q${n}` }));
  const commands = [1, 2, 3, 4, 5].map((n) => ({
    command_id: `${n}`,
    command: "abort" as const,
    label: `Action ${n}`,
    state: "SENT" as const,
    reason: null,
    sent_at: travelling.server_time,
    updated_at: travelling.server_time,
  }));
  show({ ...travelling, mission: { ...travelling.mission, queue }, commands });
  expect(screen.getByText("MISSION QUEUE · 4")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Remove Q4" })).toBeNull();
  expect(screen.getByText("Action 4")).toBeTruthy();
  expect(screen.queryByText("Action 5")).toBeNull();
});

it.each(["Refused by ground", "No answer; command may have been sent"])(
  "test_OI_009_shows_command_result_without_resend_%s",
  async (reason) => {
    const mission = {
      ...travelling.mission.active!,
      mission_id: "Q1",
      status: "QUEUED" as const,
    };
    const snapshot = {
      ...travelling,
      mission: { ...travelling.mission, queue: [mission] },
      allowed: {
        ...travelling.allowed,
        remove_queued_mission: {
          allowed: true,
          reason: null,
          needs_confirmation: false,
        },
      },
    };
    vi.mocked(sendCommand).mockResolvedValue({
      kind: "command_result",
      client_req_id: "1",
      accepted: false,
      command_id: null,
      reason,
    });
    show(snapshot);
    fireEvent.click(screen.getByRole("button", { name: "Remove Q1" }));
    expect((await screen.findByRole("alert")).textContent).toContain(reason);
    expect(sendCommand).toHaveBeenCalledTimes(1);
  },
);
