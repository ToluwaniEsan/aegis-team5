import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useScreenStore } from "../state/store";
import { DataSource } from "./DataSource";
import { socketClient } from "./socket";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("test_OI_005_mock_and_socket_are_exclusive_and_cleanup_when_switched", () => {
  vi.useFakeTimers();
  const start = vi.spyOn(socketClient, "start").mockImplementation(() => {});
  const stop = vi.spyOn(socketClient, "stop").mockImplementation(() => {});
  const view = render(
    <DataSource mock>
      <span>child</span>
    </DataSource>,
  );
  expect(start).not.toHaveBeenCalled();
  expect(useScreenStore.getState().snapshot?.payload.state).toBe("EMPTY");
  view.rerender(
    <DataSource mock={false}>
      <span>child</span>
    </DataSource>,
  );
  expect(start).toHaveBeenCalledTimes(1);
  expect(vi.getTimerCount()).toBe(0);
  view.unmount();
  expect(stop).toHaveBeenCalledTimes(1);
});
