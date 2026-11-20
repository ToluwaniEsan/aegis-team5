import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EStopButton } from "./EStopButton";
import { sendCommand } from "./net/socket";

vi.mock("./net/socket", () => ({ sendCommand: vi.fn() }));

describe("E-STOP", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.mocked(sendCommand).mockReset();
  });

  it("test_OI_019_sends_immediately_even_when_active_and_clicked_again", () => {
    vi.mocked(sendCommand).mockResolvedValue({
      kind: "command_result",
      client_req_id: "1",
      accepted: true,
      command_id: "command-1",
      reason: null,
    });
    render(<EStopButton active />);
    const button = screen.getByRole("button", {
      name: /E-STOP ACTIVE.*acknowledge in alerts/i,
    });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(sendCommand).toHaveBeenCalledTimes(2);
    expect(sendCommand).toHaveBeenCalledWith("estop", {}, false);
  });

  it("test_OI_019_false_estop_state_is_unavailable_and_still_clickable", () => {
    vi.mocked(sendCommand).mockResolvedValue({
      kind: "command_result",
      client_req_id: "1",
      accepted: true,
      command_id: "command-1",
      reason: null,
    });
    render(<EStopButton active={false} />);
    const button = screen.getByRole("button", {
      name: /E-STOP status unavailable/i,
    });
    fireEvent.click(button);
    expect(sendCommand).toHaveBeenCalledWith("estop", {}, false);
    expect(screen.queryByText(/inactive/i)).toBeNull();
  });

  it.each([
    "Refused by ground station",
    "No answer from the ground station. The command may have been sent: check the command tracker.",
  ])("test_OI_007_shows_a_refused_or_uncertain_result: %s", async (reason) => {
    vi.mocked(sendCommand).mockResolvedValue({
      kind: "command_result",
      client_req_id: "1",
      accepted: false,
      command_id: null,
      reason,
    });
    render(<EStopButton active={false} />);
    fireEvent.click(screen.getByRole("button", { name: /E-STOP/i }));
    expect((await screen.findByRole("alert")).textContent).toContain(reason);
    expect(sendCommand).toHaveBeenCalledTimes(1);
  });
});
