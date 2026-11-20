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
import { idle, travelling } from "./mock/fixtures.generated";
import { sendCommand } from "./net/socket";
import { useScreenStore } from "./state/store";

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));
beforeEach(() => {
  vi.mocked(sendCommand).mockReset();
  useScreenStore.setState({
    snapshot: idle,
    connection: "connected",
    screenDisconnected: false,
  });
});
afterEach(cleanup);
function accept() {
  vi.mocked(sendCommand).mockResolvedValue({
    kind: "command_result",
    client_req_id: "1",
    accepted: true,
    command_id: "c",
    reason: null,
  });
}
function fill() {
  fireEvent.change(screen.getByLabelText("Origin"), {
    target: { value: "FOB_ALPHA" },
  });
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "OP_BRAVO" },
  });
  fireEvent.change(screen.getByLabelText("Declared weight (kg)"), {
    target: { value: "500" },
  });
  for (const [field, value] of [
    ["Length", "50"],
    ["Width", "30"],
    ["Height", "20"],
  ])
    fireEvent.change(screen.getByLabelText(field), { target: { value } });
}

it.each([
  ["assign", idle, "New mission", "Assign mission"],
  ["queue", travelling, "Queue mission", "Add to queue"],
] as const)(
  "test_AEG_501_%s_sends_complete_args",
  async (_mode, snapshot, open, submit) => {
    useScreenStore.setState({ snapshot });
    accept();
    render(<CommandPanel />);
    fireEvent.click(screen.getByRole("button", { name: open }));
    expect(
      (screen.getByLabelText(/Pre-authorize release/) as HTMLInputElement)
        .checked,
    ).toBe(false);
    expect(
      (screen.getByLabelText("Payload ID") as HTMLInputElement).value,
    ).toBe(snapshot.mission.next_ids.payload_id);
    fill();
    fireEvent.click(screen.getByRole("button", { name: submit }));
    expect(sendCommand).toHaveBeenCalledWith(
      "assign_mission",
      {
        origin_id: "FOB_ALPHA",
        destination_id: "OP_BRAVO",
        priority: "ROUTINE",
        declared_mass_kg: 500,
        dims_cm: { length: 50, width: 30, height: 20 },
        prerelease_authorized: false,
      },
      false,
    );
    expect(
      await screen.findByText(
        "Request accepted. Check the command tracker for progress.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("COMPLETED")).toBeNull();
  },
);

it("test_AEG_507_update_prefills_and_blocks_changed_mission", async () => {
  const snapshot = {
    ...travelling,
    allowed: {
      ...travelling.allowed,
      update_payload: {
        allowed: true,
        reason: null,
        needs_confirmation: false,
      },
    },
  };
  useScreenStore.setState({ snapshot });
  accept();
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "Update payload" }));
  const dialog = screen.getByRole("dialog", { name: "Update payload" });
  expect(within(dialog).queryByLabelText("Origin")).toBeNull();
  expect(
    (within(dialog).getByLabelText("Declared weight (kg)") as HTMLInputElement)
      .value,
  ).toBe("742");
  expect(
    (within(dialog).getByLabelText("Length") as HTMLInputElement).value,
  ).toBe("58");
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...snapshot,
        mission: {
          ...snapshot.mission,
          active: { ...snapshot.mission.active!, mission_id: "different" },
        },
      },
    }),
  );
  expect(
    screen.getByText("Active mission changed; close and reopen the form"),
  ).toBeTruthy();
  expect(
    (
      within(dialog).getByRole("button", {
        name: "Update payload",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  act(() => useScreenStore.setState({ snapshot }));
  fireEvent.click(
    within(dialog).getByRole("button", { name: "Update payload" }),
  );
  expect(sendCommand).toHaveBeenCalledWith(
    "update_payload",
    { declared_mass_kg: 742, dims_cm: { length: 58, width: 38, height: 36 } },
    false,
  );
});

it("test_AEG_501_limits_blank_same_place_and_nonfinite_values", () => {
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "New mission" }));
  const submit = screen.getByRole("button", { name: "Assign mission" });
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  fill();
  const mass = screen.getByLabelText("Declared weight (kg)");
  fireEvent.change(mass, {
    target: { value: String(idle.limits.mass_min_kg) },
  });
  fireEvent.change(screen.getByLabelText("Length"), {
    target: { value: String(idle.limits.dims_max_cm.length) },
  });
  expect((submit as HTMLButtonElement).disabled).toBe(false);
  fireEvent.change(mass, {
    target: { value: String(idle.limits.mass_max_kg) },
  });
  expect((submit as HTMLButtonElement).disabled).toBe(false);
  fireEvent.change(mass, {
    target: { value: String(idle.limits.mass_max_kg + 1) },
  });
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(mass, { target: { value: "500" } });
  fireEvent.change(screen.getByLabelText("Length"), { target: { value: "0" } });
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Length"), {
    target: { value: "1e999" },
  });
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Length"), {
    target: { value: "50" },
  });
  fireEvent.change(screen.getByLabelText("Destination"), {
    target: { value: "FOB_ALPHA" },
  });
  expect(screen.getByText("Origin and destination must differ")).toBeTruthy();
});

it("test_AEG_501_rechecks_selected_places_and_reserved_id", () => {
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "New mission" }));
  fill();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...idle,
        places: idle.places.filter((place) => place.id !== "OP_BRAVO"),
      },
    }),
  );
  expect(
    within(screen.getByRole("dialog")).getByText(
      "Select an available destination",
    ),
  ).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...idle,
        mission: {
          ...idle.mission,
          next_ids: { ...idle.mission.next_ids, payload_id: "changed" },
        },
      },
    }),
  );
  expect(
    screen.getByText("Payload ID changed; close and reopen the form"),
  ).toBeTruthy();
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_OI_003_confirmation_integration_receives_valid_intent_without_sending", () => {
  const snapshot = {
    ...idle,
    allowed: {
      ...idle.allowed,
      assign_mission: { allowed: true, reason: null, needs_confirmation: true },
    },
  };
  useScreenStore.setState({ snapshot });
  const confirm = vi.fn();
  render(<CommandPanel onRequestConfirmation={confirm} />);
  fireEvent.click(screen.getByRole("button", { name: "New mission" }));
  fill();
  fireEvent.click(screen.getByRole("button", { name: "Assign mission" }));
  expect(confirm).toHaveBeenCalledWith(
    expect.objectContaining({
      command: "assign_mission",
      args: expect.objectContaining({
        origin_id: "FOB_ALPHA",
        destination_id: "OP_BRAVO",
      }),
    }),
  );
  expect(sendCommand).not.toHaveBeenCalled();
});

it("test_OI_004_preserves_edits_and_rechecks_snapshots_permissions_and_connection", () => {
  render(<CommandPanel />);
  fireEvent.click(screen.getByRole("button", { name: "New mission" }));
  fill();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...idle,
        seq: idle.seq + 1,
        limits: { ...idle.limits, mass_max_kg: 400 },
      },
    }),
  );
  expect(
    (screen.getByLabelText("Declared weight (kg)") as HTMLInputElement).value,
  ).toBe("500");
  expect(screen.getByText(/Weight must be .* to 400 kg/)).toBeTruthy();
  act(() =>
    useScreenStore.setState({
      snapshot: {
        ...idle,
        allowed: {
          ...idle.allowed,
          assign_mission: {
            allowed: false,
            reason: "Payload held",
            needs_confirmation: false,
          },
        },
      },
    }),
  );
  expect(
    within(screen.getByRole("dialog")).getByText("Payload held"),
  ).toBeTruthy();
  act(() => useScreenStore.setState({ connection: "disconnected" }));
  expect(
    within(screen.getByRole("dialog")).getByText(
      "Screen disconnected from ground station",
    ),
  ).toBeTruthy();
});

it("test_OI_003_confirmation_boundary_and_escape_focus", () => {
  const snapshot = {
    ...idle,
    allowed: {
      ...idle.allowed,
      assign_mission: { allowed: true, reason: null, needs_confirmation: true },
    },
  };
  useScreenStore.setState({ snapshot });
  render(<CommandPanel />);
  const opener = screen.getByRole("button", { name: "New mission" });
  opener.focus();
  fireEvent.click(opener);
  fill();
  expect(screen.getByText("Confirmation dialog unavailable")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Assign mission" }));
  expect(sendCommand).not.toHaveBeenCalled();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(opener);
});

it.each(["Command may have been sent", "Refused by ground"])(
  "test_OI_009_prevents_duplicates_and_shows_result_%s",
  async (reason) => {
    let finish!: (value: {
      kind: "command_result";
      client_req_id: string;
      accepted: boolean;
      command_id: null;
      reason: string;
    }) => void;
    vi.mocked(sendCommand).mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    render(<CommandPanel />);
    fireEvent.click(screen.getByRole("button", { name: "New mission" }));
    fill();
    const submit = screen.getByRole("button", { name: "Assign mission" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(sendCommand).toHaveBeenCalledTimes(1);
    await act(async () =>
      finish({
        kind: "command_result",
        client_req_id: "1",
        accepted: false,
        command_id: null,
        reason,
      }),
    );
    expect(screen.getAllByText(reason).length).toBeGreaterThan(0);
    expect(sendCommand).toHaveBeenCalledTimes(1);
  },
);
