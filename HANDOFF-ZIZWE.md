# Handoff: Zizwe, vehicle software and message plumbing

You build:
- The Payload Controller and its safety interlocks.
- The Payload Simulator, the link watch and the Event Buffer.
- The message bus and the Team 3 link stand-in.
- The Team 2 and Team 4 stand-ins.
- Ground-side command permissions and the Fault Injector.

This is the safety-critical half. An accidental release is a mission failure, so the property test (A8) is your main evidence at review.

Emmanuel builds the other half: the ground application and the Operator Screen (`HANDOFF-EMMANUEL.md`).

## Start your agent

Paste this into your coding agent for the first session:

```
You work for Zizwe. Read AGENTS.md and HANDOFF-ZIZWE.md.
Follow rule zero first: open docs/decisions.md and ask me, in one message,
every unanswered question owned by Zizwe or Both that blocks "start",
each with the options and your recommended answer. Do not write code until
I answer. Record my answers in docs/decisions.md, then tell me the first
task from my handoff and wait for my go.
```

Then give it one task at a time:

```
Do task A4 from HANDOFF-ZIZWE.md. Read the task in docs/03-workstream-A-vehicle.md
(or docs/04-... for B tasks) and the changes listed for it in my handoff.
Stop when its Done-when list is met and report as AGENTS.md describes.
```

Review every pull request before you merge it. Check that the tests the report names exist and actually assert the requirement.

## Questions your agent asks first

From `docs/decisions.md`:
- **Before any code:** D-01 (RETURNING), D-02 (Team 2 interlock), D-03 (shared clock A-17), D-04 (10 s pre-release wait).
- **Before Phase 1:** D-16, the contract freeze with Emmanuel.
- **Non-blocking:** D-05 to D-08 and D-17. Your agent mentions them and keeps working.

## You own

- **Common:** `backend/aegis/common/models.py`, `envelope.py`, `clock.py`, `config.py`. Emmanuel owns `ui_models.py` in the same folder.
- **Bus:** `backend/aegis/bus/` (all of it).
- **Vehicle:** `backend/aegis/vehicle/` (all of it).
- **Stand-ins:** `backend/aegis/standins/link.py`, `nav.py`, `power.py`.
- **Ground:** `backend/aegis/ground/permissions.py` and `heartbeat.py`.
- **Ground entry point:** `backend/aegis/ground/main.py`, shared. You create it; Emmanuel adds his components.
- **Testing:** `backend/aegis/testing/fault_injector.py`.
- **Run everything:** `backend/aegis/run_all.py`.
- **Adapters:** `backend/aegis/adapters/team2.py`, `team3.py`, `team4.py`.
- **Schema export:** `backend/scripts/export_schemas.py`, the message half.
- **Your tests in `backend/tests/`:** `fakes.py`, `test_safety_properties.py`, and tests for every module above.

Don't touch `frontend/`, the rest of `backend/aegis/ground/`, `standins/team1.py`, `testing/scenario_runner.py`, CI or `CODEOWNERS`. Ask Emmanuel instead.

## Tasks in order

Tick each box when its pull request is merged. Days are working days from day 1.

### Phase 0: foundations (days 1 to 2)

- [x] **A0. Settings loader** (doc 03). Emmanuel's B0 creates `pyproject.toml` in the first hour of day 1. Until it merges, use a local venv with `pip install pydantic pyyaml pytest`. Don't write your own `pyproject.toml`.
- [x] **A1. Clock** (doc 03).
- [x] **A2. Models and envelope** (doc 03). This covers the messages in contracts sections 2 to 4, 7 and 10 only.
  - The screen protocol (section 9) is Emmanuel's `ui_models.py`.
  - The `make()` registry takes `dst`, `iface` and `priority` from the routing table in contracts section 2.
  - `hb.ground` now goes to `vehicle.link_watch`. That was a contract bug, now fixed.
  - Push a draft on day 1 so Emmanuel can build against it.
- [x] **B1. Bus and link port** (doc 04), **plus `tests/fakes.py`** with `FakeBus` and `FakeLog` matching the B1 and B2 interfaces exactly.
  - Emmanuel's B2 Mission Log lands on day 1. Until then, use `FakeLog`.
- [x] **B3. Link stand-in, Team 3** (doc 04).
- [ ] **B4. Run everything** (doc 04). Also create:
  - **`aegis/ground/heartbeat.py`:** publishes `hb.ground` with `seq` at `timing.heartbeat_rate_hz`, `src = ground.command_manager`, `dst = [vehicle.link_watch]`.
  - **`aegis/ground/main.py`:** loads settings, starts the Mission Log, the bus, the LinkPort and the heartbeat. Leave clearly marked places where Emmanuel adds the Command Manager, Status Monitor, Alert Manager, Team 1 stand-in and UI server.
- [ ] **Contract freeze with Emmanuel** by the end of day 2. Answer D-16.

**Phase 0 exit:** `run_all` starts three processes, heartbeats cross the link, and they appear in all three logs.

### Phase 1: walking skeleton (days 3 to 7)

- [ ] **A4 stub first (day 3).** The Payload Controller accepts `cmd.assign_mission` and emits `payload.status` at 1 Hz. Hand it to Emmanuel. Then:
- [ ] **A3. Payload Simulator** (doc 03).
- [ ] **A4. Payload Controller core state machine** (doc 03). `departure_permitted` uses the one definition in contracts section 4: SECURED, `secured` true and a mission open.
- [ ] **B5. Team 2 stand-in** (doc 04). Due day 4, because Emmanuel's Status Monitor needs `nav.state`.
- [ ] **B6. Team 4 stand-in** (doc 04). Done when mass reports are logged and `power.status` reaches `ground.status_monitor`. The `POWER_LOW` alert test is Emmanuel's (B11).
- [ ] **B8. Permissions** (doc 04). Due day 4.
  - Signature: `permissions(payload, nav, link, alerts, active, queue, cfg)`, using only Emmanuel's `ui_models` types (`PayloadView`, `NavView`, `LinkView`, `AlertView`, `Mission`).
  - Use the same release guard order and reason texts as `rules.py`.
- [ ] **A5. Link loss on the vehicle** (doc 03).
- [ ] **Day 7, with Emmanuel:** a happy-path mission works from the real screen.

### Phase 2: off-nominal (days 8 to 13)

- [ ] **A6. Faults on the vehicle** (doc 03).
- [ ] **A7. Event Buffer** (doc 03).
- [ ] **A9. Vehicle entry point and `vehicle.test_agent`** (doc 03).
- [ ] **B14. Fault Injector** (doc 04), as a plain class:
  - `FaultInjector(bus, clock, cfg, log).inject(target, action, params)` raises `ValueError` with a reason on bad params.
  - Test every row of contracts section 10 by calling `inject()` directly.
  - Emmanuel's UI server mounts it at `POST /api/test/inject`.
- [ ] **Day 10 hand-off:** A6, A7, A9 and B14 merged, so Emmanuel's scenario runner can drive every fault.
- [ ] **A8. Safety property test** (doc 03). It needs 2,000 examples passing in CI. Any failure hypothesis finds becomes a named regression test.

### Phase 3: real teams (day 14 onward)

- [ ] **B16. Adapters** for Team 2, then Team 4, then Team 3 (doc 06 section 1, swap procedure). Run `iron_hawk.yaml` after each swap.

## What you give Emmanuel, and when

| Day | What |
|---|---|
| 1 | Draft `models.py`, `envelope.py`, `tests/fakes.py` |
| 2 | Frozen `models.py` and `config.py` |
| 3 | Bus, LinkPort, link stand-in, heartbeat, `run_all`, `ground/main.py`; a controller stub that emits `payload.status` |
| 4 | `permissions.py`; `nav.state` and `power.status` from the stand-ins |
| 7 | Full happy path with real acks |
| 10 | All vehicle faults, the Event Buffer, `FaultInjector`, `vehicle.test_agent` |

## What you get from Emmanuel

| Day | What | Until then |
|---|---|---|
| 1 | `pyproject.toml`, CI, `MissionLog` | local venv, `FakeLog` |
| 2 | Frozen `ui_models.py` (needed for B8) | write B8 tests against the contract text in section 9 |
| 12 | `iron_hawk.yaml` passing in CI | your own unit and property tests |

## Review questions you must be able to answer with a test

- "Show me that release is impossible while moving." Point to the `test_AEG_506_*` tests and A8.
- "What happens if the link drops at the destination?" Point to the `test_AEG_514_*` and `test_AEG_507_*` tests.
- "What happens if your software crashes?" Point to the `test_GEN_004_*` tests.
- "How do you stop an old command from running late?" Point to `test_stale_command_rejected`.
