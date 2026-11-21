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
import { travelling } from "./test-fixtures/fixtures";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

it("test_OI_003_changed_then_restored_target_still_requires_new_review", () => {
  const { dialog } = open();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        payload: { ...travelling.payload, payload_id: "OTHER" },
      },
    }),
  );
  act(() => useScreenStore.setState({ snapshot: travelling }));
  expect(within(dialog).getByRole("alert").textContent).toContain("review");
  expect(
    (
      within(dialog).getByRole("button", {
        name: "Abort mission",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(sendCommand).not.toHaveBeenCalled();
});

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));
beforeEach(() => {
  vi.mocked(sendCommand).mockReset();
  useScreenStore.setState({
    snapshot: travelling,
    connection: "connected",
    screenDisconnected: false,
  });
});
afterEach(cleanup);
function open() {
  render(<CommandPanel />);
  const button = screen.getByRole("button", { name: "Abort" });
  button.focus();
  fireEvent.click(button);
  return {
    button,
    dialog: screen.getByRole("dialog", { name: "Confirm command" }),
  };
}

it("test_OI_003_focus_enter_escape_and_restore", () => {
  const { button, dialog } = open();
  const cancel = within(dialog).getByRole("button", { name: "Cancel" });
  expect(document.activeElement).toBe(cancel);
  expect(within(dialog).getByText(/MSN-2026-001.*PAY-2026-001/)).toBeTruthy();
  expect(
    within(dialog).getByText("The active mission will be aborted."),
  ).toBeTruthy();
  fireEvent.keyDown(
    within(dialog).getByRole("button", { name: "Abort mission" }),
    { key: "Enter" },
  );
  expect(sendCommand).not.toHaveBeenCalled();
  fireEvent.keyDown(dialog, { key: "Escape" });
  expect(screen.queryByRole("dialog", { name: "Confirm command" })).toBeNull();
  expect(document.activeElement).toBe(button);
});

it("test_OI_003_explicit_confirmation_sends_once_without_inventing_lifecycle", async () => {
  let finish!: (result: {
    kind: "command_result";
    client_req_id: string;
    accepted: boolean;
    command_id: string;
    reason: null;
  }) => void;
  vi.mocked(sendCommand).mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const { dialog } = open();
  const confirm = within(dialog).getByRole("button", { name: "Abort mission" });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(sendCommand).toHaveBeenCalledOnce();
  expect(sendCommand).toHaveBeenCalledWith("abort", {}, true);
  await act(async () =>
    finish({
      kind: "command_result",
      client_req_id: "1",
      accepted: true,
      command_id: "c",
      reason: null,
    }),
  );
  expect(
    within(dialog).getByText(
      "Request accepted. Check the command tracker for progress.",
    ),
  ).toBeTruthy();
  expect(screen.queryByText("SENT")).toBeNull();
});

it("test_OI_003_accepted_command_that_changes_the_snapshot_shows_no_stale_error", async () => {
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: true,
    command_id: "c",
    reason: null,
  });
  const { dialog } = open();
  await act(async () => {
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Abort mission" }),
    );
  });
  // The command itself changes the snapshot and makes it no longer allowed.
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...travelling,
        payload: { ...travelling.payload, state: "RETURNING" },
        allowed: {
          ...travelling.allowed,
          abort: {
            ...travelling.allowed.abort,
            allowed: false,
            reason: "Payload is RETURNING",
          },
        },
      },
    }),
  );
  expect(within(dialog).queryByRole("alert")).toBeNull();
  expect(within(dialog).getByRole("status").textContent).toBe(
    "Request accepted. Check the command tracker for progress.",
  );
  expect(within(dialog).getByRole("button", { name: "Close" })).toBeTruthy();
});

it.each(["permission", "mission", "payload", "destination", "disconnect"])(
  "test_OI_004_%s_change_prevents_confirmation",
  (change) => {
    const { dialog } = open();
    const active = travelling.mission.active!;
    if (change === "permission")
      act(() =>
        useScreenStore.setState({
          snapshot: {
            ...travelling,
            allowed: {
              ...travelling.allowed,
              abort: {
                allowed: false,
                reason: "No longer allowed",
                needs_confirmation: true,
              },
            },
          },
        }),
      );
    if (change === "mission")
      act(() =>
        useScreenStore.setState({
          snapshot: {
            ...travelling,
            mission: {
              ...travelling.mission,
              active: { ...active, mission_id: "OTHER" },
            },
          },
        }),
      );
    if (change === "payload")
      act(() =>
        useScreenStore.setState({
          snapshot: {
            ...travelling,
            payload: { ...travelling.payload, payload_id: "OTHER" },
          },
        }),
      );
    if (change === "destination")
      act(() =>
        useScreenStore.setState({
          snapshot: {
            ...travelling,
            nav: { ...travelling.nav, destination: travelling.places[2] },
          },
        }),
      );
    if (change === "disconnect")
      act(() => useScreenStore.setState({ connection: "disconnected" }));
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Abort mission" }),
    );
    expect(within(dialog).getByRole("alert")).toBeTruthy();
    expect(sendCommand).not.toHaveBeenCalled();
  },
);

it.each(["Refused by ground", "No answer; the command may have been sent"])(
  "test_OI_009_shows_result_and_does_not_resend_%s",
  async (reason) => {
    vi.mocked(sendCommand).mockResolvedValue({
      kind: "command_result",
      client_req_id: "1",
      accepted: false,
      command_id: null,
      reason,
    });
    const { dialog } = open();
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Abort mission" }),
    );
    expect((await within(dialog).findByRole("status")).textContent).toBe(
      reason,
    );
    expect(sendCommand).toHaveBeenCalledOnce();
  },
);

it("test_OI_015_changed_queue_item_is_not_started", () => {
  const item = {
    ...travelling.mission.active!,
    mission_id: "Q1",
    status: "QUEUED" as const,
  };
  const snapshot = {
    ...travelling,
    mission: { ...travelling.mission, active: null, queue: [item] },
    allowed: {
      ...travelling.allowed,
      start_queued_mission: {
        allowed: true,
        reason: null,
        needs_confirmation: true,
      },
    },
  };
  useScreenStore.setState({ snapshot });
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "Start Q1" }));
  const dialog = screen.getByRole("dialog", { name: "Confirm command" });
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        mission: {
          ...snapshot.mission,
          queue: [{ ...item, mission_id: "Q2" }, item],
        },
      },
    }),
  );
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Start queued mission" }),
  );
  expect(within(dialog).getByRole("alert")).toBeTruthy();
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_AEG_501_changed_form_limits_require_review_again", () => {
  const snapshot = {
    ...travelling,
    allowed: {
      ...travelling.allowed,
      assign_mission: { allowed: true, reason: null, needs_confirmation: true },
    },
  };
  useScreenStore.setState({ snapshot });
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "Queue mission" }));
  fireEvent.change(screen.getByLabelText("Origin"), {
    target: { value: "FOB_ALPHA" },
  });
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "OP_BRAVO" },
  });
  fireEvent.change(screen.getByLabelText("Declared weight (kg)"), {
    target: { value: "500" },
  });
  for (const field of ["Length", "Width", "Height"])
    fireEvent.change(screen.getByLabelText(field), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: "Add to queue" }));
  const dialog = screen.getByRole("dialog", { name: "Confirm command" });
  expect(within(dialog).getByText(/FOB Alpha/)).toBeTruthy();
  expect(within(dialog).getByText("Declared weight: 500 kg")).toBeTruthy();
  expect(within(dialog).getByText("Dimensions: 10 × 10 × 10 cm")).toBeTruthy();
  expect(within(dialog).getByText("Pre-authorized release: No")).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        limits: { ...snapshot.limits, mass_max_kg: 400 },
      },
    }),
  );
  fireEvent.click(within(dialog).getByRole("button", { name: "Add to queue" }));
  expect(within(dialog).getByRole("alert")).toBeTruthy();
  expect(sendCommand).not.toHaveBeenCalled();
});
