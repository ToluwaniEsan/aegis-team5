import type { Severity } from "./contracts/ui";

/** Shape supplements the label and color used to describe a severity. */
export function SeverityShape({ severity }: { severity: Severity }) {
  const path = {
    CRITICAL: "M6 0 12 12H0Z",
    WARNING: "M6 0 12 6 6 12 0 6Z",
    CAUTION: "M1 1H11V11H1Z",
  }[severity];

  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      aria-hidden="true"
      data-severity={severity}
    >
      <path d={path} fill="currentColor" />
    </svg>
  );
}
