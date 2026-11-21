# ENV-001 laptop demonstration

Run date: 2026-11-21. Human sign-off is pending.

| Item | Observed |
|---|---|
| Laptop | MacBook Pro, Apple M1, 16 GB RAM |
| Operating system | macOS 26.5 (25F71) |
| Runtimes | Python 3.12.16 and Node.js 22.13.1 |
| Browser | Playwright Chromium, 1366 × 768 viewport |
| Repository revision | `16f814b` |
| Launcher | `python -m aegis.run_all --run-id env-001-browser-final` |
| Mission | `MSN-2026-023`, FOB Alpha to Outpost Bravo, 500 kg, 50 × 30 × 30 cm |

Codex drove the README workflow through the production build of the Operator Screen and the test panel. The simulated vehicle, link, and ground application ran as separate local processes with the team stand-ins. The assignment drawer was closed after the mission reached SECURED.

The mission progressed through LOADED, SECURED, TRAVELLING, AT_DESTINATION, RELEASED, and DELIVERED. The Operator Screen displayed DELIVERED · CONFIRMED after release. See the [delivery screenshot](ENV-001-delivered.png) and [mission log excerpt](ENV-001-mission-excerpt.jsonl). The excerpt contains the first ground entry for each state and the delivery confirmation.
