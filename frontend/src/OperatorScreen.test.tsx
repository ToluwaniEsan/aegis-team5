import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OperatorScreen } from "./OperatorScreen";

describe("C0 scaffold", () => {
  it("renders five named screen regions", () => {
    render(<OperatorScreen />);
    const app = screen.getByRole("main", { name: "Operator Screen" });
    expect(app.children).toHaveLength(5);
    expect(
      Array.from(app.children).map((node) => node.getAttribute("aria-label")),
    ).toEqual([
      "Top bar",
      "Payload and vehicle health",
      "Route and navigation",
      "Mission controls",
      "Alerts and delivery",
    ]);
    expect(
      Array.from(app.children)
        .slice(4)
        .every((node) => node.textContent === ""),
    ).toBe(true);
  });
});
