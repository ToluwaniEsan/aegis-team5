# OI-018 grayscale inspection

Human sign-off is pending. The [grayscale evidence](OI-018-grayscale/) contains 12 full-screen Playwright captures at 1366 × 768 and six supplementary `-expanded.png` captures. The expanded views show the alert rows hidden by the collapsed feed in the full-screen captures.

Codex visually inspected the captures on 2026-11-21. Every alert row shown retained both a severity label and a distinct shape. CRITICAL used a triangle, WARNING used a diamond, and CAUTION used a circle. Fixtures with no active alerts showed an empty feed.

For sign-off, review the full-screen and expanded captures, then record the reviewer, date, and result in `tools/manual_evidence.csv`.
