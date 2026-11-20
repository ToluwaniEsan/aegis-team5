import type { Severity } from "./contracts/ui";

/** Shape supplements the label and color used to describe a severity. */
export function SeverityShape({ severity }: { severity: Severity }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      aria-hidden="true"
      data-severity={severity}
    >
      {severity === "CAUTION" ? (
        <circle cx="6" cy="6" r="5" fill="currentColor" />
      ) : (
        <path
          d={severity === "CRITICAL" ? "M6 0 12 12H0Z" : "M6 0 12 6 6 12 0 6Z"}
          fill="currentColor"
        />
      )}
    </svg>
  );
}
