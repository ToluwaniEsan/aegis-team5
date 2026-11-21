import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { LinkBadge } from "./LinkBadge";
import { travelling } from "./test-fixtures/fixtures";

afterEach(cleanup);

it.each([
  ["CONNECTED", null],
  ["DEGRADED", "WARNING"],
  ["LOST", "CRITICAL"],
] as const)("test_OI_007_link_badge_%s", (state, severity) => {
  const snapshot = { ...travelling, link: { ...travelling.link, state } };
  const { container } = render(
    <LinkBadge snapshot={snapshot} disconnected={false} />,
  );
  expect(screen.getByText(new RegExp(`LINK ${state}`))).toBeTruthy();
  expect(
    container.querySelector("svg")?.getAttribute("data-severity") ?? null,
  ).toBe(severity);
});

it("test_OI_008_link_missing_or_stale_is_labelled", () => {
  const { rerender } = render(
    <LinkBadge snapshot={null} disconnected={false} />,
  );
  expect(screen.getByText("LINK UNKNOWN")).toBeTruthy();
  rerender(<LinkBadge snapshot={travelling} disconnected />);
  expect(screen.getByText("LINK CONNECTED · 80 ms · OUT OF DATE")).toBeTruthy();
});

it("test_OI_007_does_not_use_status_age_as_lost_duration", () => {
  const snapshot = {
    ...travelling,
    link: {
      ...travelling.link,
      state: "LOST" as const,
      age_s: 42,
      stale: true,
    },
  };
  render(<LinkBadge snapshot={snapshot} disconnected />);
  expect(
    screen.getByText("LINK LOST · duration unavailable · OUT OF DATE"),
  ).toBeTruthy();
  expect(screen.queryByText(/42/)).toBeNull();
});
