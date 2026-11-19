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
| D-01 | start | Keep the `RETURNING` payload state? It is in Figure 2 but not the PRD state list. It stops a payload heading home from ever being released. | Keep / Drop | **Keep**, as in contracts section 4 | | |
| D-02 | start | Keep the proposed `payload.interlock` message to Team 2 (`departure_permitted`, 1 Hz)? Without it, AEG-511 can only detect a bad departure after it happens. | Keep and ask Team 2 to honor it / Drop | **Keep.** Our Team 2 stand-in honors it. | | |
| D-03 | start | Accept assumption A-17: all nodes share UTC within 0.5 s? The stale-command and future-timestamp checks depend on it. | Accept / Change the tolerance | **Accept.** The demo runs on one laptop; Team 1's environment uses NTP. | | |
| D-04 | start | With pre-authorized release and the link LOST at the destination, how long does the vehicle wait before releasing on its own? | 10 s / another value | **10 s** (`link.prerelease_wait_s`) | | |
| D-05 | no | Simulated mechanism times: load 2 s, lock 3 s, release 4 s, re-weigh 1 s. OK? | Accept / Change in config | **Accept** | | |
| D-06 | no | After an emergency stop is acknowledged, the Team 2 stand-in stays stopped until it gets a new command. OK until Team 2 defines restart? | Accept / Other | **Accept**, and ask Team 2 | | |
| D-07 | no | For GEN-004 we show that a crashed Payload Controller leaves the payload locked. Restarting the controller is out of scope. OK? | Accept / Add restart | **Accept**, and say so at review | | |
| D-08 | no | Who sends the interface sheets (doc 06 section 1) to Teams 2, 3 and 4, and by when? | Zizwe / someone else | **Zizwe, by day 2.** He owns those adapters. | | |

## Emmanuel (ground application and Operator Screen)

| ID | Blocks | Question | Options | Recommended | Answer | Date |
|---|---|---|---|---|---|---|
| D-09 | start | GitHub usernames for both builders, for `CODEOWNERS` and branch protection? | (type them) | n/a | | |
| D-10 | start | Assumption A-16: the payload can change only before departure. IRON HAWK makes the change before departure; a change mid-route is refused with a reason. Keep it? | Keep / Allow mid-route changes (contract change) | **Keep**, and be ready to defend it at the demo | | |
| D-11 | start | Mission priorities `ROUTINE`, `PRIORITY`, `URGENT`. OK? | Accept / Change | **Accept** | | |
| D-12 | start | Screen look: match `design/operator-screen-reference.png` exactly, one light theme, the ISA-101 palette in doc 05, no dark theme. OK? | Accept / Change before C0 | **Accept** | | |
| D-13 | no | The four named places in `config.yaml` (FOB Alpha, Outpost Bravo, Outpost Charlie, Landing Zone Delta). Use them until Team 2 sends real waypoints? | Accept / Edit | **Accept** | | |
| D-14 | no | The recommended-action texts in the fault catalog (contracts section 7). Review them now or at CDR? | Now / At CDR | **At CDR.** The texts are data and easy to change. | | |
| D-15 | no | Who sends the interface sheet to Team 1, and by when? Team 1's answer shapes everything else. | Emmanuel / someone else | **Emmanuel, by day 1** | | |

## Both builders

| ID | Blocks | Question | Options | Recommended | Answer | Date |
|---|---|---|---|---|---|---|
| D-16 | Phase 1 | Have Zizwe and Emmanuel read `docs/02-contracts.md` together and agreed to freeze it, along with `models.py`, `ui_models.py`, `ui.ts` and `config.yaml`? | Yes, frozen on (date) / Not yet | Do it by the end of day 2 (about 45 minutes) | | |
| D-17 | no | Payload mass versus box size: 1,000 kg in a 60 × 40 × 40 cm box is about 10,400 kg/m³, which is denser than steel. Reviewers will ask about it. | Keep and explain / Bigger box / Lower max mass | **Keep the config values for now.** The team (Solomon) decides before CDR; it is a config change only. | | |

## Added during the build

| ID | Asked by | Question | Answer | Date |
|---|---|---|---|---|
| | | | | |
