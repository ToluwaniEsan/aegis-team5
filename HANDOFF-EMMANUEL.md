# Handoff: Emmanuel, ground application and Operator Screen

You build:
- The ground station's Command Manager, Status Monitor, Alert Manager and Mission Log.
- The UI server and the snapshot builder.
- The Team 1 stand-in.
- The scenario runner and the IRON HAWK scenario files.
- The whole Operator Screen in `frontend/`.
- Repo setup and CI.

You own the screen data format (contracts section 9) from end to end: the pydantic models, the TypeScript types, the snapshot the server builds and the screen that reads it.

Zizwe builds the other half: vehicle software and message plumbing (`HANDOFF-ZIZWE.md`).

## Start your agent

Paste this into your coding agent for the first session:

```
You work for Emmanuel. Read AGENTS.md and HANDOFF-EMMANUEL.md.
Follow rule zero first: open docs/decisions.md and ask me, in one message,
every unanswered question owned by Emmanuel or Both that blocks "start",
each with the options and your recommended answer. Do not write code until
I answer. Record my answers in docs/decisions.md, then tell me the first
task from my handoff and wait for my go.
```

Then give it one task at a time:

```
Do task C4 from HANDOFF-EMMANUEL.md. Read the task in docs/05-workstream-C-operator-screen.md
(or docs/04-... for B tasks) and the changes listed for it in my handoff.
For screen work, look at design/operator-screen-reference.png first and use only the
tokens in frontend/src/styles/tokens.css. Stop when its Done-when list is met and
report as AGENTS.md describes.
```

Review every pull request before you merge it. Check that the tests the report names exist and actually assert the requirement.

## Questions your agent asks first

From `docs/decisions.md`:
- **Before any code:** D-09 (GitHub usernames), D-10 (payload change only before departure), D-11 (mission priorities), D-12 (screen look).
- **Before Phase 1:** D-16, the contract freeze with Zizwe.
- **Non-blocking:** D-13 to D-15 and D-17. Your agent mentions them and keeps working.

## The screen must look professional

Tell your agent this for every C task. It is also in AGENTS.md rule 10.

- **Use the palette in doc 05 exactly** (`tokens.css`). It is an ISA-101 high-performance HMI palette, the style used in industrial control rooms, with contrast measured at 4.5:1 or better.
  - Calm gray and dark blue when everything is normal.
  - Red, amber and yellow only for abnormal states.
  - Green only for "delivered".
  - No invented colors, no "accent" or "brand" colors, no purple or violet.
  - No Tailwind, Material, Bootstrap or other default palettes, and no generic AI-dashboard look.
- **No blur.**
  - No `backdrop-filter`, no `filter: blur()`.
  - No frosted glass or glassmorphism, no glow, no shadows, no gradients. The only exception is the `--stale-pattern` hatch.
  - Flat panels with 1 px borders and 4 px corners.
- **No filler text.**
  - No lorem ipsum, marketing blurbs, taglines, welcome text or decorative descriptions.
  - Every word is a real label, value, reason or action from the contracts or the snapshot.
- **Match `design/operator-screen-reference.png`.** Open `design/operator-screen-reference.html` for the exact tokens and spacing. If a component looks different from the reference, the reference is right.
- **Fonts:** IBM Plex Sans and Mono, bundled. The `.woff2` files are in `design/fonts/`, or use the `@fontsource` packages. Never load fonts from the internet; the screen must work offline.
- **Severity:** always shape, then word, then color: ▲ CRITICAL, ◆ WARNING, ● CAUTION. Draw the shapes as SVG. The screen must still make sense in grayscale.

## You own

- **Common:** `backend/aegis/common/ui_models.py`, the pydantic models for contracts section 9.
- **Ground:** `backend/aegis/ground/` except `permissions.py` and `heartbeat.py`, which are Zizwe's. That includes `mission_log.py`, `command_manager.py`, `status_monitor.py`, `alert_manager.py`, `ui_server.py` and `snapshot.py`.
- **Ground entry point:** `backend/aegis/ground/main.py`, shared. Zizwe creates it on day 2; you add your components where it marks.
- **Stand-ins:** `backend/aegis/standins/team1.py`.
- **Testing:** `backend/aegis/testing/scenario_runner.py`.
- **Scenarios:** `backend/scenarios/`. The IRON HAWK draft is already there; Zizwe reviews.
- **Adapters:** `backend/aegis/adapters/team1.py`.
- **Schema export:** the UI half of `backend/scripts/export_schemas.py`.
- **Repo setup:** `backend/pyproject.toml`, `.github/workflows/ci.yml`, `CODEOWNERS`.
- **Frontend:** `frontend/` (all of it).
- **Tools:** `tools/` (`dump_snapshot_fixtures.py`, `verification_report.py`).
- **Your tests in `backend/tests/`.**

Don't touch `backend/aegis/vehicle/`, `bus/`, the other stand-ins, `fault_injector.py`, `permissions.py`, `models.py` or `envelope.py`. Ask Zizwe instead.

## Tasks in order

Tick each box when its pull request is merged. Days are working days from day 1.

### Phase 0: foundations (days 1 to 2)

- [x] **B0. Repo, CI and CODEOWNERS** (doc 04). Do this first, in the first hour, because Zizwe needs `pyproject.toml`.
  - Zizwe writes `tests/fakes.py`, so skip that part of B0.
  - `CODEOWNERS` follows the "You own" lists in both handoffs, using the usernames from D-09.
  - Add the frontend CI job now, even before `frontend/` exists, and let it skip if the folder is missing.
- [x] **B2. Mission Log** (doc 04). Deliver the `MissionLog` class on day 1; Zizwe's code calls it. The Done-when test needs a full mission, so finish it in Phase 2.
- [x] **`ui_models.py`:** pydantic v2 models that produce exactly the `Snapshot`, `UiCommand` and `CommandResult` shapes in contracts section 9. Add the UI half of `export_schemas.py` (writes `contracts/ui.schema.json`).
- [x] **C0. Scaffold** (doc 05). Copy `ui.ts` from contracts section 9 unchanged. Copy the tokens from doc 05 into `tokens.css` unchanged.
- [x] **C1. Mock feed** (doc 05). Hand-write the three placeholder fixtures.
- [ ] **Contract freeze with Zizwe** by the end of day 2. Answer D-16.

**Phase 0 exit:** the screen renders a mock snapshot at exactly 1366 × 768, matching the reference grid.

### Phase 1: walking skeleton (days 3 to 7)

- [x] **B10. Status Monitor** (doc 04). Builds against Zizwe's day-3 `payload.status` and day-4 `nav.state` and `power.status`.
- [x] **B9. Command Manager** (doc 04).
  - Until Zizwe's `permissions.py` lands on day 4, use a stub that allows everything.
  - Don't send `hb.ground`; Zizwe's `heartbeat.py` does that.
- [x] **B12. UI server and snapshot builder** (doc 04). Put the snapshot builder in `aegis/ground/snapshot.py`; the scenario runner reads it directly.
  - Mount Zizwe's `FaultInjector` at `POST /api/test/inject` (404 when `test_mode` is false, 400 with the reason on `ValueError`).
  - Add a test of the HTTP route.
  - Until B14 lands, mount a stub that only logs `test.inject`.
- [x] **B7. Team 1 stand-in** (doc 04).
- [x] **C2. WebSocket client and store** (doc 05).
- [x] **C3. Top bar and E-STOP** (doc 05).
- [x] **C4. Payload Status card** (doc 05).
- [x] **C5. Vehicle Health card** (doc 05).
- [x] **C6. Route and Navigation panel** (doc 05).
- [x] **C7. Command panel** (doc 05).
- [x] **C8. Mission form drawer** (doc 05).
- [x] **C9. Confirmation dialog** (doc 05).
- [x] **Day 7, with Zizwe:** a happy-path mission works from the real screen. Commands show SENT, RECEIVED, COMPLETED.

### Phase 2: off-nominal and evidence (days 8 to 13)

- [x] **B11. Alert Manager** (doc 04). Also add `test_POWER_LOW_raised_below_threshold`, which was moved here from B6.
- [x] **C10. Alerts feed and alarm** (doc 05).
- [x] **B15. Scenario runner** (doc 04 and doc 06 section 2).
  - Start the runner and `iron_hawk_short.yaml` early.
  - The full `iron_hawk.yaml` needs Zizwe's day-10 hand-off (all vehicle faults, Event Buffer, Fault Injector).
  - Make the CI smoke job required once it passes.
- [x] **B13. Contract test and fixtures** (doc 04). Do the schema comparison by day 5 and the 12 real fixtures once B15 runs.
- [x] **C11. Test panel `/test`** (doc 05).
- [x] **C12. Layout and accessibility checks** (doc 05).
- [x] **The other scenario files** from doc 06 section 2: link loss at destination, E-STOP, faults, abort/return, repeatability.
- [x] **Day 12:** `iron_hawk.yaml` passes in `--fast` mode in CI.
- [x] **Day 13:** the screen is ready for Mercy's usability test (OI-014), with the grayscale screenshots.

### Phase 3: real teams and evidence (day 14 onward)

- [ ] **B16. Team 1 adapter.** Run our three processes in Team 1's environment first (doc 06 section 1).
- [x] **`tools/verification_report.py`** (doc 06 section 3).

## What you give Zizwe, and when

| Day | What |
|---|---|
| 1 | `pyproject.toml`, CI, `CODEOWNERS`, the `MissionLog` class |
| 2 | Frozen `ui_models.py` and `ui.ts` |
| 5 | `/ws` with real snapshots and the schema comparison test |
| 12 | `iron_hawk.yaml` passing in CI, so Zizwe's changes are checked end to end |

## What you get from Zizwe

| Day | What | Until then |
|---|---|---|
| 1 | Draft `models.py`, `envelope.py`, `tests/fakes.py` | build against the contract text |
| 3 | Bus, link stand-in, heartbeat, `run_all`, `ground/main.py`, a controller emitting `payload.status` | `FakeBus` and the mock feed |
| 4 | `permissions.py`, `nav.state` and `power.status` | an allow-everything stub |
| 10 | All vehicle faults, the Event Buffer, `FaultInjector`, `vehicle.test_agent` | the stub inject route, short scenarios |

## Review questions you must be able to answer with a test

- "How does the operator know a value is out of date?" Point to the `test_OI_017_*` and `test_OI_008_*` tests and the stale fixtures.
- "What if a command never arrives?" Point to `test_OI_009_command_fails_after_timeout_and_is_not_resent`.
- "How fast does a fault reach the screen?" Point to `test_OI_010_*` and the scenario report times.
- "Can a new operator use it?" Point to the usability results in `reports/usability.csv`.
