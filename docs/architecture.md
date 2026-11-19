# Architecture

> **Sprint 3 background.** The build now follows `docs/01-system-overview.md`. Its repository layout replaces the "Suggested folder layout" below.

Source: Team 5 design document (Traceability section and Sprint 3 decisions).

The **Ground Station** runs in Python and serves a browser-based **Operator Screen** over a local WebSocket. The **Payload Controller** runs on the vehicle so safety checks hold even when the link is down.

## Parts and what they own

| Part | Runs on | Job | Requirements |
|---|---|---|---|
| Operator Screen | Ground (browser) | Mission entry, status display, commands, alerts | OI-001, OI-014, OI-016, ENV-002 |
| Command Manager | Ground | Validates, confirms, sends and tracks commands; 5 s timeout, never resends; E-Stop at priority 0 | OI-002, OI-003, OI-004, OI-006, OI-009, OI-015, OI-019, AEG-512 |
| Status Monitor | Ground | Merges vehicle and Team 2/3/4 data, tracks the age of every value, marks OUT OF DATE | OI-005, OI-007, OI-008, OI-012, OI-017 |
| Alert Manager | Ground | Faults with severity (Critical, Warning, Caution), recommended action, acknowledgement; never color alone | OI-010, OI-011, OI-018, AEG-513 |
| Mission Log | Ground | Records every command, status change and alert with UTC time and payload_id | OI-013, AEG-510 |
| Payload Controller | Vehicle | Release safety checks, departure check, delivery confirmation, hold on link loss | AEG-501, 503, 506, 507, 508, 510, 511, 512, 513, 514, GEN-004, OI-019 |
| Payload Simulator | Vehicle (simulated) | Interactive simulator for weight, lock, shift, sensors and release energy | AEG-502, 504, 505, 509, GEN-005 |
| Fault Injector | Test tool | Triggers link loss, payload shift, sensor and drivetrain faults | GEN-001 |

## Other teams

| Team | We send | We receive |
|---|---|---|
| Team 1: Mission & Systems Integration | Mission and system mode, faults (≤ 2 s), delivery confirmation (≤ 10 s) | Integration environment |
| Team 2: Navigation & Autonomy | Mission, abort, return to origin, change destination, E-Stop | Position, route, ETA, blocked route, moving/arrived, nav sensor health |
| Team 3: Communications | Commands and status over the link | Link health: CONNECTED, DEGRADED, LOST (1 / s) |
| Team 4: Power & Mobility | Payload mass, release energy, E-Stop | Battery %, drivetrain health |

## Suggested folder layout (a starting point, not created yet)

```
config/          limits and timing values (config.yaml)
common/          shared message format, config loader, mission log
vehicle/         payload controller, payload simulator
ground_station/  command manager, status monitor, alert manager, screen backend
web/             operator screen (HTML/CSS/JS)
stubs/           fault injector and stand-ins for Teams 2, 3 and 4
tests/           one or more tests per requirement where possible
```
