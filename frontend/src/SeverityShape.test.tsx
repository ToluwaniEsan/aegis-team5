import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SeverityShape } from "./SeverityShape";

afterEach(cleanup);

it.each([
  ["CRITICAL", "path", "d", "M6 0 12 12H0Z"],
  ["WARNING", "path", "d", "M6 0 12 6 6 12 0 6Z"],
  ["CAUTION", "circle", "r", "5"],
] as const)(
  "test_OI_018_%s_uses_the_expected_shape",
  (severity, element, attribute, value) => {
    const { container } = render(<SeverityShape severity={severity} />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("data-severity")).toBe(severity);
    expect(svg?.children).toHaveLength(1);
    expect(svg?.querySelector(element)?.getAttribute(attribute)).toBe(value);
  },
);
