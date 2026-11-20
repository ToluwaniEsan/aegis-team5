# 06. Connecting the teams, the IRON HAWK scenario, and evidence

Workstream B leads this file. Everyone uses it.

## 1. What "connecting the teams" means

Every other team appears in our system as one endpoint name:
- `team1.integration`
- `team2.nav`
- `team3.link`
- `team4.power`

Today each one is a stand-in. Connecting a team means replacing its stand-in with an adapter in `backend/aegis/adapters/` that talks to that team's real software, under the same endpoint name. Nothing else in our code changes. That is the whole integration strategy.

The handbook says the other subsystems are not ours to design. So for each team we do three things:
1. Send them our side of the interface in writing.
2. Get their answer in writing.
3. Record it in the Open Questions tab's Resolution column.

Until a team answers, we build on our assumption and the stand-in.

### The interface sheet to send each team

One page per team:
- the message names
- a JSON example of each message, copied from `02-contracts.md`
- the rate
- who sends what
- three questions at the bottom: "Is this right? What do you send instead? When can we test together?"

Ask for an answer within two working days. Record no answer as a risk (handbook rule in the Open Questions tab).

### Offer Team 1 our envelope

Team 1 owns cross-team interfaces but has only answered "Python". Offer them our message envelope (contracts section 2) and the `aegis.bus` code as the program-wide format. It is about 200 lines with no dependencies. If they adopt it, every team integrates faster and our adapters become trivial. If they choose something else, only `adapters/` and `bus/tcp.py` change.

### Per team

**Team 1 (Integration).** Ask first, because their answer shapes everything else.
- **Questions:**
  - Where does each team's software run: one machine, containers or several laptops?
  - How are messages exchanged?
  - Do they accept our envelope?
  - What does `t1.system_mode` contain?
  - Do they want our mission, fault and delivery reports in our format?
- **Swap:** first run our three processes inside their environment with all stand-ins still in place. That is GEN-003 and ENV-001 evidence on its own.

**Team 4 (Power & Mobility).** Simplest, so swap second.
- **Questions:**
  - Do you accept 226.8 kg (500 lb) to 1000 kg and 3.2 Wh nominal / 5.0 Wh max per release?
  - Is `power.status` with `battery_pct`, `est_range_km` and `drivetrain_health` at 1 Hz right?
  - Do you carry out the emergency stop when Team 2 commands it (A-07)?
  - Do you have a terrain or vibration profile?

**Team 2 (Navigation & Autonomy).** The most important interface for safety.
- **Questions:**
  - Do you send `nav.state` (moving, at_destination, at_origin, position, ETA, route, health) at 1 Hz, on the vehicle, so it reaches the Payload Controller without Team 3's link?
  - Will you refuse to depart while our `payload.interlock` says `departure_permitted: false`? AEG-511 depends on this; without it, we can only detect a bad departure after it happens.
  - Do you accept `nav.assign`, `cmd.abort`, `cmd.return_to_origin`, `cmd.change_destination` and `cmd.estop`, and ack each one?
  - After an emergency stop is cleared, who restarts the vehicle and how? Nothing defines this yet. Our stand-in stays stopped until a new command.
  - Position as lat/lon and ETA in seconds (A-assumption in Open Questions)?

**Team 3 (Communications).** Swap last, because a link change affects every test.
- **Questions:**
  - What are your degraded and lost limits?
  - Typical latency?
  - Do you honor our `priority` field so the emergency stop goes first?
  - Will you send `link.health` at 1 Hz?
  - Do you provide a relay we connect to on each side, the way our stand-in does?

### Swap procedure, one team at a time

1. The interface is agreed in writing (Open Questions Resolution column filled).
2. Get real sample messages from the team, recorded from their software. Save them in `tests/samples/teamN/`.
3. Write the adapter. Its unit tests run the samples through it in both directions.
4. Run with that team's real software and stand-ins for the rest, in Team 1's environment.
5. Run `iron_hawk.yaml` in `--live` mode and keep the report.
6. Log the result in the doc. Any problem becomes a defect issue (section 5).

If a team is never ready, demo with its stand-in and say so plainly. The agreed contract plus a passing adapter test is still evidence of integration readiness.

## 2. Scenario files

Scenarios are both our test procedures (needed for TRR) and our demo script.

### Format

```yaml
name: iron_hawk
description: Operation IRON HAWK, handbook section 13, with our CONOPS steps
steps:
  - id: S01                      # unique within the file
    title: Start-up shows link status
    reqs: [OI-007]               # requirement IDs this step proves
    expect:                      # wait until true, fail after within_s
      within_s: 3
      snapshot: {link.state: CONNECTED}

  - id: S02
    title: Operator assigns a mission
    reqs: [OI-001, AEG-510]
    ui:                          # send a UiCommand exactly as the screen would
      command: assign_mission
      confirmed: false
      args: {origin_id: FOB_ALPHA, destination_id: OP_BRAVO, priority: PRIORITY,
             declared_mass_kg: 742, dims_cm: {length: 58, width: 38, height: 36},
             prerelease_authorized: false}
    expect:
      within_s: 2
      result: {accepted: true}

  - id: S07
    inject: {target: link, action: outage, params: {seconds: 12}}
```

**Step keys** (a step has an `id`, a `title`, `reqs`, and one or more of these):

| key | meaning |
|---|---|
| `ui` | Send a `UiCommand`. `confirmed` is given explicitly. |
| `inject` | `POST /api/test/inject` with `target`, `action`, `params` (contracts section 10). |
| `wait_s` | Let time pass. |
| `repeat` | Run the step this many times and record every result. Use it for the "10 out of 10" and "20 out of 20" checks. |
| `expect` | Conditions to wait for, with `within_s`. |

**What `expect` can check:**
- **`result`:** fields of the last `CommandResult`.
- **`snapshot`:** dotted paths into the latest snapshot. A number in the path indexes a list (`commands.0.state`). A plain value means equals, and `null` means the value is null. Operators are `{lt: }`, `{gt: }`, `{in: [...]}`, `{not: }`, `{contains: }`, `{len: }`.
- **`alert`:** `{code: PAYLOAD_SHIFT, severity: WARNING, acknowledged: false}` must be present.
- **`no_alert`:** must be absent.
- **`log`:** `{kind: msg.sent, env.type: cmd.change_destination, count: 1}`, counted over the whole run so far.
  - `count` must match exactly. Use it to prove "never resent".
  - `min_count` sets a lower bound.

**Variables in `ui.args`:** `"$alert.<CODE>"` is replaced with the `alert_id` of the newest alert with that code.

The runner records, for every `expect`, how long it took to become true. Those times are the evidence for "within 2 s" requirements.

### Scenario files to write (B15)

| File | Purpose |
|---|---|
| `iron_hawk.yaml` | The full scenario below. Run before every review and the demo. |
| `iron_hawk_short.yaml` | Assign, secure, travel, arrive, release, delivered. The CI smoke test. |
| `link_loss_at_destination.yaml` | AEG-514 without pre-authorization, AEG-507 with it. |
| `estop.yaml` | Emergency stop from each payload state; HELD; acknowledge; recovery. |
| `faults.yaml` | Every fault code in contracts section 7 raised, shown within 2 s with its action, acknowledged and cleared. Uses `repeat: 10` for AEG-502 and AEG-505. |
| `abort_return.yaml` | Abort before departure (payload unloaded), abort while travelling (RETURNING, back to SECURED at origin, departure blocked, unload), return to origin after delivery (OI-002, AEG-511). |
| `repeatability.yaml` | `repeat: 10` for AEG-506, AEG-508 and AEG-511, and `repeat: 20` for OI-006, matching the "10 out of 10" and "20 out of 20" checks in the requirements. |

### The IRON HAWK scenario

`scenarios/iron_hawk.yaml` in this pack is the full draft. Its steps follow the CONOPS and the handbook's IRON HAWK list:

| Steps | What happens | Requirements proved |
|---|---|---|
| S01 | Start-up, link CONNECTED | OI-007 |
| S02 to S04 | Assign mission, payload ID generated, payload loaded, weighed and secured, interlock opens | OI-001, AEG-510, AEG-503, AEG-504, AEG-505, AEG-511 |
| S05 to S06 | Payload change within bounds, before departure. A second change over the limit is refused with a reason | AEG-512, AEG-501, OI-004 |
| S07 to S08 | Departure; release refused while moving; status updating every second | AEG-506, OI-004, OI-005 |
| S09 to S10 | Communications degrade; link DEGRADED alert | OI-007, OI-017 |
| S11 to S14 | Link outage. Values go OUT OF DATE with last-known values shown. A command sent during the outage fails at 5 s and is never resent. Link restores. | OI-008, OI-017, OI-009, OI-006 |
| S15 | Route blocked, new route and ETA shown | OI-012 |
| S16 to S17 | New mission during the active one goes to the queue and does not start | OI-015 |
| S18 to S20b | Simulated payload fault (3.1 cm shift): payload shown unsecured within 2 s, alert with recommended action, reported to Team 1, acknowledged, cleared | AEG-502, AEG-505, OI-010, AEG-513 |
| S21 to S23 | Arrival, confirmed release, delivery confirmed within 10 s to the operator and Team 1 | AEG-507, AEG-508, OI-016, OI-003 |
| S24 | Queued mission still waiting for the operator | OI-015 |

**A decision the team must make before the demo.** The handbook's IRON HAWK says "the payload requirement changes within allowable bounds" during the mission. Our assumption A-16 only allows payload changes before departure. The scenario puts the change before departure. If the Program Director makes the change mid-route, the system will refuse it with a reason. Decide whether that refusal is the intended behaviour and be ready to defend it, or change A-16.

## 3. Verification evidence (handbook: "evidence, not opinions")

**`tools/verification_report.py`** produces the table the Traceability tab is missing: the result for every requirement.

1. **Inputs:**
   - pytest results (`pytest --junitxml reports/pytest.xml`)
   - every `reports/scenario-*.json`
   - the Playwright results
   - `tools/requirements.csv`: ID, short text and method (Test, Demo, Analysis, Inspection), copied from the Traceability tab
   - `tools/manual_evidence.csv`: requirement, evidence file, checked by, date, result. One row per piece of evidence that is not an automated test (the table below).
2. **Matching evidence to requirements:**
   - A test counts for a requirement when its name contains the ID (`test_AEG_506_...` counts for AEG-506).
   - A scenario step counts for every ID in its `reqs`.
3. **Output:** `reports/verification.md` and `.csv`, with these columns:
   - Requirement, Method
   - Evidence (test names, scenario step IDs, files)
   - Result (PASS, FAIL, or NO EVIDENCE)
   - Measured value, for example "fault on screen in 0.9 s" or "delivery confirmed in 3.4 s"
   - Log file
4. **A requirement with NO EVIDENCE is a defect.** Fix it before TRR.

**Evidence that is not an automated test** (each is a row in `manual_evidence.csv`):

| Requirement | Evidence |
|---|---|
| AEG-509 (Analysis) | `docs/analysis/AEG-509.md`: the release energy calculation behind 3.2 Wh nominal and 5.0 Wh max, and the simulator log showing the value reported to Team 4 |
| OI-018 (Inspection) | Grayscale screenshots from C12, checked by a person, with that person's name and date in the report |
| ENV-002 (Inspection) | Playwright no-scroll check at 1366 × 768 (C12) |
| GEN-002 (Inspection) | `test_GEN_002_log_units_and_utc` scans a full run's logs. Every time ends in `Z`; every numeric field name carries a unit suffix. |
| OI-014 (Test) | The usability test, run by the Test Lead with at least 3 people from outside the team, 30 minutes of training each. Record each person's time to assign a mission in `reports/usability.csv`. Pass is at least 90 % finishing in under 2 minutes. |
| GEN-003, ENV-001 (Demo) | `iron_hawk.yaml --live` run inside Team 1's environment (GEN-003) and on a standard laptop (ENV-001). Keep each run's report and note the machine. |

Paste the report's Result and Evidence columns into the Traceability tab at each review.

## 4. Review checklists

**CDR (end of Sprint 4): "Is the design mature enough to build and integrate?"**
- [ ] Contracts frozen; `models.py`, `ui.ts` and `config.yaml` in the repo
- [ ] Walking skeleton demo: one mission from the real screen with stand-ins
- [ ] Interface sheets sent to all four teams; status of each answer shown
- [ ] Risk register updated with owners, triggers and status
- [ ] The payload mass versus box size question settled

**TRR (end of Sprint 5): "Are we ready to conduct meaningful testing?"**
- [ ] Every requirement has at least one named test or scenario step (no NO EVIDENCE rows)
- [ ] `iron_hawk.yaml` and the four other scenarios pass in `--fast` mode in CI
- [ ] Our software runs in Team 1's environment (GEN-003)
- [ ] Integration status per team: agreed, adapter tested, run together, or still a stand-in
- [ ] Open defects listed with owners
- [ ] Usability test scheduled with named participants

**Final demonstration (Sprint 6)**
- [ ] Laptop 1: `run_all` and the Operator Screen
- [ ] Second monitor: `/test` panel for live fault injection
- [ ] `iron_hawk.yaml --live` rehearsed twice end to end, with timing
- [ ] Verification report, usability results and logs from the rehearsal ready to show
- [ ] Fallback if Team 1's environment fails on the day: `run_all --single-process` on one laptop with stand-ins, stated openly

## 5. Defects

Track defects as GitHub issues labelled `defect`. Each one records:
- the requirement ID
- the scenario step or test that found it
- the log file
- the severity
- the owner

The handbook asks for defect records at TRR. The issue list is that record.
