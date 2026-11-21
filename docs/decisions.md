# Start-up decisions and questions

Coding agents read this file at the start of every session (AGENTS.md, rule zero).

- **Blocks** says when a question must be answered:
  - `start`: before any code at all.
  - `Phase 1`: before the first Phase 1 task.
  - `no`: the agent mentions it but keeps working.
- **What the agent does:** it asks its builder every unanswered question it owns that blocks now, all in one message, with the recommended answer. Then it waits. It records the answer here word for word, with the date.
- **Answers that change a contract** (`docs/02-contracts.md`, `models.py`, `ui_models.py`, `ui.ts`, `config.yaml` keys) need a `CONTRACT CHANGE` pull request approved by both builders. A changed value in `config.yaml` needs both builders to agree.

Questions found during work go at the bottom, under "Added during the build".

## Zizwe (vehicle software and message plumbing)

| ID | Blocks | Question | Options | Recommended | Answer | Date |
|---|---|---|---|---|---|---|
| D-01 | start | Keep the `RETURNING` payload state? It is in Figure 2 but not the PRD state list. It stops a payload heading home from ever being released. | Keep / Drop | **Keep**, as in contracts section 4 | Keep | 2026-11-19 |
| D-02 | start | Keep the proposed `payload.interlock` message to Team 2 (`departure_permitted`, 1 Hz)? Without it, AEG-511 can only detect a bad departure after it happens. | Keep and ask Team 2 to honor it / Drop | **Keep.** Our Team 2 stand-in honors it. | Keep | 2026-11-19 |
| D-03 | start | Accept assumption A-17: all nodes share UTC within 0.5 s? The stale-command and future-timestamp checks depend on it. | Accept / Change the tolerance | **Accept.** The demo runs on one laptop; Team 1's environment uses NTP. | Accept | 2026-11-19 |
| D-04 | start | With pre-authorized release and the link LOST at the destination, how long does the vehicle wait before releasing on its own? | 10 s / another value | **10 s** (`link.prerelease_wait_s`) | 10 s | 2026-11-19 |
| D-05 | no | Simulated mechanism times: load 2 s, lock 3 s, release 4 s, re-weigh 1 s. OK? | Accept / Change in config | **Accept** | Accept | 2026-11-20 |
| D-06 | no | After an emergency stop is acknowledged, the Team 2 stand-in stays stopped until it gets a new command. OK until Team 2 defines restart? | Accept / Other | **Accept**, and ask Team 2 | Accept | 2026-11-20 |
| D-07 | no | For GEN-004 we show that a crashed Payload Controller leaves the payload locked. Restarting the controller is out of scope. OK? | Accept / Add restart | **Accept**, and say so at review | Accept | 2026-11-20 |
| D-08 | no | Who sends the interface sheets (doc 06 section 1) to Teams 2, 3 and 4, and by when? | Zizwe / someone else | **Zizwe, by day 2.** He owns those adapters. | | |

## Emmanuel (ground application and Operator Screen)

| ID | Blocks | Question | Options | Recommended | Answer | Date |
|---|---|---|---|---|---|---|
| D-09 | start | GitHub usernames for both builders, for `CODEOWNERS` and branch protection? | (type them) | n/a | Emmanuel: Aina316; Zizwe: Zizwe27 | 2026-11-19 |
| D-10 | start | Assumption A-16: the payload can change only before departure. IRON HAWK makes the change before departure; a change mid-route is refused with a reason. Keep it? | Keep / Allow mid-route changes (contract change) | **Keep**, and be ready to defend it at the demo | Keep | 2026-11-19 |
| D-11 | start | Mission priorities `ROUTINE`, `PRIORITY`, `URGENT`. OK? | Accept / Change | **Accept** | Accept | 2026-11-19 |
| D-12 | start | Screen look: match `design/operator-screen-reference.png` exactly, one light theme, the ISA-101 palette in doc 05, no dark theme. OK? | Accept / Change before C0 | **Accept** | Accept | 2026-11-19 |
| D-13 | no | The four named places in `config.yaml` (FOB Alpha, Outpost Bravo, Outpost Charlie, Landing Zone Delta). Use them until Team 2 sends real waypoints? | Accept / Edit | **Accept** | Accept | 2026-11-19 |
| D-14 | no | The recommended-action texts in the fault catalog (contracts section 7). Review them now or at CDR? | Now / At CDR | **At CDR.** The texts are data and easy to change. | At CDR | 2026-11-19 |
| D-15 | no | Who sends the interface sheet to Team 1, and by when? Team 1's answer shapes everything else. | Emmanuel / someone else | **Emmanuel, by day 1** | Emmanuel, by day 1 | 2026-11-19 |

## Both builders

| ID | Blocks | Question | Options | Recommended | Answer | Date |
|---|---|---|---|---|---|---|
| D-16 | Phase 1 | Have Zizwe and Emmanuel read `docs/02-contracts.md` together and agreed to freeze it, along with `models.py`, `ui_models.py`, `ui.ts` and `config.yaml`? | Yes, frozen on (date) / Not yet | Do it by the end of day 2 (about 45 minutes) | Not yet, build anyway | 2026-11-20 |
| D-17 | no | Payload mass versus box size: 1,000 kg in a 60 × 40 × 40 cm box is about 10,400 kg/m³, which is denser than steel. Reviewers will ask about it. | Keep and explain / Bigger box / Lower max mass | **Keep the config values for now.** The team (Solomon) decides before CDR; it is a config change only. | Emmanuel and Zizwe agree to keep the config values for now. The team (Solomon) decides before CDR; it is a config change only. | 2026-11-20 |

## Added during the build

| ID | Asked by | Question | Answer | Date |
|---|---|---|---|---|
| D-18 | Toluwani (Scrum Master) | Payload minimum mass: `config.yaml` had 500 kg, the requirements doc said "up to 500 lb". Which is right? | Minimum 500 lb (226.8 kg). `mass_min_kg` changed from 500 to 226.8; `mass_max_kg` stays 1000 (D-17 still open). | 2026-11-20 |
| D-19 | Emmanuel | B10 says to clear a route-blocked notice once the vehicle passes the detour point, but `nav.route_blocked` defines no detour point or passing rule. How should B10 determine that? | Interim: use the configured timeout to expire the notice. Expiry does not confirm the route is clear or change command permissions. Detour-passed clearing remains outstanding until Team 2 supplies an agreed signal and both builders approve a CONTRACT CHANGE. | 2026-11-20 |
| D-20 | Emmanuel | `payload.delivered` has a position but no destination `Place`, while `DeliverySummary.destination` is required. How should B10 obtain it when the Command Manager is not yet available? | Inject a mission destination lookup (Recommended) | 2026-11-20 |
| D-21 | Emmanuel | Before the first payload status arrives, Snapshot requires a payload state but the contract has no UNKNOWN state. What should B12 send on WebSocket connection? | Use the stale EMPTY placeholder only for snapshot serialization:<br>- updated_at=null, age_s=null, stale=true<br>- Sensors UNKNOWN and nullable measurements null<br>- secured=false, locked=false, departure_permitted=false<br>- Reason: "Awaiting payload status"<br><br>Do not insert this placeholder into the Status Monitor or treat EMPTY as an observed vehicle state. Enforce refusal of non-E-STOP commands in the backend too, not just in snapshot.allowed.<br><br>Replace it immediately when actual payload status arrives. Record this interim decision and test startup, command refusal, E-STOP availability, and transition to real status.<br><br>The screen must clearly identify this as awaiting data, rather than presenting EMPTY or unlocked as confirmed observations. | 2026-11-20 |
| D-22 | Emmanuel | B11 is absent and Snapshot requires the non-null boolean `estop_active`; B10 does not expose an acknowledged E-STOP alert state. How should B12 represent it until B11 exists? | Derive estop_active from the injected alert source when available. Until B11 is connected, serialize false only as a documented placeholder—not evidence that E-STOP is inactive.<br><br>Do not use this fallback to authorize commands or clear an E-STOP state. Preserve the existing missing-alert-source command restrictions, and keep the E-STOP command available.<br><br>Do not infer E-STOP from HELD alone; other faults also cause HELD.<br><br>Record the limitation and test both missing-source behavior and ESTOP_ACTIVE handling with an injected source. Track real B11 integration as required before the end-to-end mission demonstration. | 2026-11-20 |
