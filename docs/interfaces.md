# Interfaces (Sprint 3 baseline, I1–I9)

Every message: **JSON · metric units · UTC timestamp · `payload_id`**.

| ID | Between | Key messages | Timing |
|---|---|---|---|
| I1 | Operator ↔ Operator Screen | Views, commands, two-step confirms, one-click E-Stop | ≥ 1 update / s |
| I2 | Command Manager → Payload Controller | Assign, update payload, release, acknowledge fault | Confirmed in 5 s or FAILED |
| I3 | Payload Controller → Status Monitor | State, lock, weight, shift, sensors, delivery | 1 / s; delivery ≤ 10 s |
| I4 | Command Manager → Team 2 | Mission, abort, return to origin, change destination | Confirmed in 5 s or FAILED |
| I5 | Command Manager → Payload Controller, Team 2, Team 4 | Emergency stop, priority 0 | Sent ahead of all traffic |
| I6 | Team 2 → Payload Controller, Status Monitor | Position, route, moving/arrived, blocked route, nav sensor health | ≥ 1 / s; works with link down |
| I7 | Payload Controller ↔ Team 4 | Payload mass and release energy ↔ battery %, drivetrain health | On change / 1 per s |
| I8 | Team 3 → Status Monitor | Link health: CONNECTED, DEGRADED, LOST | 1 / s |
| I9 | Ground station / vehicle → Team 1 | Mission and system mode, faults, delivery confirmation | Faults ≤ 2 s; delivery ≤ 10 s |

## Change control

When another team changes its design (handbook §12), record: what changed, why, affected requirements, affected subsystems and interfaces, technical and schedule impact, new risks, and work to reprioritize. Because limits live in a config file rather than code, most value changes need no code changes.
