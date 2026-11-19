# 01. System overview and build plan

## What we are building

This is not mostly frontend. Team 5 builds three things of roughly equal size:

1. **Vehicle software (Workstream A).** The Payload Controller with every safety interlock, the Payload Simulator that stands in for hardware, and the Event Buffer. This is the highest-risk part: an accidental release is a mission failure.
2. **Ground station backend and team connections (Workstream B).** The Command Manager, Status Monitor, Alert Manager and Mission Log, the Fault Injector and scenario runner, stand-ins for Teams 1 to 4, and later the adapters that connect the real team software.
3. **Operator Screen (Workstream C).** The web screen the operator uses, on a fixed 1366 × 768 layout.

"Connecting all the teams" is real work, but most of it cannot happen until the other teams answer. Eight of the ten open questions are still unanswered. So we build against stand-ins with the same message contracts, and swap each stand-in for the real team's software when it is ready. Each swap should touch one adapter file.

## Decisions this plan uses

Where a later tab in the team doc changed an earlier one, the later tab wins.

| Decision | Source in the doc |
|---|---|
| Python backend, browser screen connected over a local WebSocket | Sprint 3 Trade Studies, Design Decisions |
| Interactive payload simulator; faults triggered without code changes | Trade Studies |
| Vehicle Health summary card on the dashboard | Trade Studies |
| Safety checks run on the vehicle | Design Decisions |
| Two-sided 5 s command timeout, never resent | Design Decisions |
| Emergency stop: one click, no confirmation, payload HELD | Design Decisions |
| Each value shows its age; OUT OF DATE after 5 s | Design Decisions |
| Payload ID generated automatically, `PAY-YYYY-NNN` | Design Decisions, CONOPS |
| New missions are queued and start only when the operator confirms | Design Decisions, OI-015 |
| Vehicle Event Buffer replays events after an outage | Design Decisions |
| All limits in `config.yaml` | Design Decisions |
| 500 to 1000 kg, 60 × 40 × 40 cm, 2.0 cm shift, ±0.5 kg, 3.2 Wh nominal / 5.0 Wh max, 1 Hz, 5 s, 5 s | Finalized TBR Settings |
| Interfaces I1 to I9 and the screen grid (64 / 544 / 160 px rows, 420 / 526 / 420 px columns) | PRD tab |
| Link limits: degraded above 1 s or 10 % loss, lost after 5 s | Assumption A-15 (Team 3 has not answered) |

**Added by this plan. The team should confirm or change these.**
- **`RETURNING` payload state.** It is in Figure 2 but missing from the PRD state list.
- **`payload.interlock` message to Team 2.** AEG-511 cannot be met without it.
- **Assumption A-17:** all nodes share UTC within 0.5 s. The two-sided timeout depends on it.
- **Smaller values and behaviour:**
  - Mission priorities `ROUTINE`, `PRIORITY`, `URGENT`.
  - A list of named places.
  - Simulated load, secure and release times.
  - A 10 s wait before a pre-authorized release when the link is lost.
- **New definitions:** the fault catalog and the test injection API.

**One value to fix before the demo.** 1000 kg in a 60 × 40 × 40 cm box is about 10,400 kg/m³, denser than steel. It is a config value, so the build does not care. But a reviewer will ask about it.

## How it runs

Three processes. Each one is a plain `asyncio` Python program.

```
 Browser: Operator Screen (React)
        |  WebSocket  ws://localhost:8080/ws    (I1)
 +--------------------------------------------------------------+
 | GROUND process        python -m aegis.ground                 |
 |  Command Manager · Status Monitor · Alert Manager            |
 |  Mission Log · UI server · Fault Injector API                |
 |  Team 1 stand-in (later: Team 1 adapter)                     |
 +--------------------------------------------------------------+
        |  TCP :7101, one JSON message per line
 +--------------------------------------------------------------+
 | LINK process          python -m aegis.standins.link          |
 |  Team 3 stand-in: latency, loss, outages, priority order,    |
 |  link.health (I8). Later replaced by Team 3's link.          |
 +--------------------------------------------------------------+
        |  TCP :7102, one JSON message per line
 +--------------------------------------------------------------+
 | VEHICLE process       python -m aegis.vehicle                |
 |  Payload Controller · Payload Simulator · Event Buffer       |
 |  Team 2 stand-in · Team 4 stand-in (later: adapters)         |
 +--------------------------------------------------------------+
```

- **Start everything:** `python -m aegis.run_all`. With `--single-process`, the three sides run in one process joined by an in-memory link. Tests and fast local work use this mode.
- **Inside each process:** modules talk over an in-memory publish/subscribe bus (`LocalBus`). A `LinkPort` forwards any message whose `dst` is on the other side to the link connection.
- **Why this shape:** it matches Figure 1. It makes "the link is down" a real condition you can test. And it lets you kill the ground process to prove the vehicle stays safe alone (GEN-004, AEG-514).

## Technology

| Area | Choice | Why |
|---|---|---|
| Backend | Python 3.11+, `asyncio`, pydantic v2, PyYAML | Trade study decision; pydantic checks every message at runtime, which answers the "no compile-time checks" concern in the trade study |
| UI server | FastAPI + uvicorn, used only for `/ws`, `/api/test/inject` and serving the built screen | Small, well known to coding agents |
| Transport | `asyncio` streams, newline-delimited JSON. No broker. | Nothing to install. Easy to put behind whatever Team 1 chooses. |
| Backend tests | pytest, pytest-asyncio, hypothesis (safety property test), httpx (API tests), and a `ManualClock` so 5 s timeouts run instantly | |
| Lint | ruff (Python), eslint + prettier (TypeScript) | |
| Frontend | React 18, TypeScript, Vite, zustand for the one store, CSS Modules with design tokens | No UI component library: they bring their own look |
| Fonts | IBM Plex Sans and IBM Plex Mono from `@fontsource` packages, bundled | The screen must work with no internet in a forward area |
| Frontend tests | Vitest and React Testing Library; Playwright for layout checks at 1366 × 768 | |

## Repository layout

```
aegis-team5/
  AGENTS.md                      rules every coding agent follows
  CLAUDE.md                      one line: @AGENTS.md
  HANDOFF-ZIZWE.md               Zizwe's task list and start-up questions
  HANDOFF-EMMANUEL.md            Emmanuel's task list and start-up questions
  contracts/                     exported JSON Schemas (messages.schema.json, ui.schema.json, ui.from-ts.schema.json)
  README.md                      how to install, run and test
  config/config.yaml             every limit and timing value
  docs/                          this plan pack; docs/decisions.md holds the answered start-up questions
  backend/
    pyproject.toml
    aegis/
      common/                    Zizwe: models.py, envelope.py, clock.py, config.py
                                 Emmanuel: ui_models.py
      bus/                       Zizwe: local_bus.py, link_port.py, endpoints.py, tcp.py
      vehicle/                   Zizwe: payload_controller.py, rules.py, simulator.py, link_watch.py,
                                        faults.py, event_buffer.py, main.py
      ground/                    Emmanuel: command_manager.py, status_monitor.py, alert_manager.py,
                                           mission_log.py, ui_server.py, snapshot.py
                                 Zizwe: permissions.py, heartbeat.py
                                 shared: main.py (Zizwe creates it on day 2, Emmanuel adds his components)
      standins/                  Zizwe: link.py (Team 3), nav.py (Team 2), power.py (Team 4)
                                 Emmanuel: team1.py
      adapters/                  Zizwe: team2.py, team3.py, team4.py. Emmanuel: team1.py. Empty until each team is ready
      testing/                   Zizwe: fault_injector.py. Emmanuel: scenario_runner.py
      run_all.py                 Zizwe
    scripts/export_schemas.py    Zizwe writes it for messages; Emmanuel adds the UI schema
    scenarios/                   Emmanuel owns, Zizwe reviews: iron_hawk.yaml and the others (run from backend/)
    tests/                       each builder adds tests for their own modules
  frontend/                      Emmanuel owns everything here
    src/contracts/ui.ts          copied from docs/02-contracts.md section 9, frozen
    src/mock/                    scripted snapshots for building without the backend
  tools/
    verification_report.py       builds the evidence table from test results (doc 06)
```

Put a `CODEOWNERS` file in place so each folder needs its owner's review.

## Who builds what

Two builders, each driving a coding agent. The split is **vertical**: one person owns the vehicle and the message plumbing, the other owns the ground application and the screen. That means the screen data format (contracts section 9) has one owner from end to end. The only thing the two share is the message catalog (contracts sections 2 to 4, 7 and 10), which is fully written down.

| | Zizwe: vehicle and plumbing | Emmanuel: ground app and Operator Screen |
|---|---|---|
| Handoff file | `HANDOFF-ZIZWE.md` | `HANDOFF-EMMANUEL.md` |
| Tasks | A0 to A9, B1, B3, B4, B5, B6, B8, B14; later the Team 2, 3 and 4 adapters (B16) | B0, B2, B7, B9 to B13, B15, C0 to C12, `ui_models.py`; later the Team 1 adapter (B16) |
| Task detail | `03-workstream-A-vehicle.md`, plus the listed tasks in `04-...` | the listed tasks in `04-...`, plus `05-workstream-C-operator-screen.md` |
| Phase 0 share | config, clock, models, envelope, bus, `tests/fakes.py`, link stand-in, `run_all` | repo and CI, Mission Log, `ui_models.py`, `ui.ts`, frontend scaffold, tokens, mock feed |
| Hardest part | proving release can never happen when it shouldn't | command lifecycle, per-field ages, and alerts that are clear in under 2 s |

Emmanuel has more task IDs, but many of them are small screen components. Zizwe has the safety-critical logic and the property test.

**Changes from the task files:**
- B8 (permissions) goes to Zizwe because it repeats the vehicle's release guard order. It takes only the `ui_models` views (payload, nav, link, alerts, mission) as input, so it doesn't depend on Emmanuel's internals.
- B14 (Fault Injector) goes to Zizwe as a plain class, `FaultInjector.inject(target, action, params)`. Emmanuel's UI server (B12) mounts it at `POST /api/test/inject` and tests the HTTP route.
- `tests/fakes.py` is written by Zizwe with B1. `FakeLog` matches the B2 interface exactly.
- The `POWER_LOW` check in B6's Done-when moves to Emmanuel's B11.

Cut items from the bottom of the cut list below before you cut any safety item.

## Phases

The team doc has no dates after Sprint 3. Fill in real dates; the day counts are working days.

| Phase | Days | What exists at the end (exit check) | Course milestone |
|---|---|---|---|
| 0. Foundations | 1 to 2 | Contracts in code and frozen. `run_all` starts three processes that exchange heartbeats through the link stand-in, and the heartbeats appear in the log. The screen renders a mock snapshot at 1366 × 768. | |
| 1. Walking skeleton | 3 to 7 | One happy-path mission, driven from the real screen with the stand-ins: assign, load, secure, travel, arrive, release, delivered. Commands show SENT, RECEIVED, COMPLETED. | Show at CDR |
| 2. Off-nominal | 8 to 13 | Link degrade and outage, stale marking, command timeouts, Event Buffer, faults and alerts with sound, emergency stop and HELD, route blocked, payload update, mission queue, test panel. The full IRON HAWK scenario passes automatically. | Show at TRR |
| 3. Integration and evidence | 14 onward | Stand-ins replaced by real team software one team at a time, running in Team 1's environment. Usability test done (OI-014). Verification report generated. Demo rehearsed. | Sprint 6 demo and SVR |

This deliberately differs from the Sprint 2 build order, which built inside-out and left the screen for last. With two people working in parallel, a thin end-to-end path by day 7 finds integration problems while there is still time to fix them. Inside Workstream A the safety logic still comes first.

### Critical handoffs

| When | From | To | What |
|---|---|---|---|
| Day 1 | both | both | Start-up questions in `docs/decisions.md` answered (each agent asks its builder first) |
| Day 1 | Zizwe | Emmanuel | Draft `models.py` and `envelope.py`, and `tests/fakes.py` |
| Day 1 | Emmanuel | Zizwe | `pyproject.toml`, CI, and the `MissionLog` class (B2 API) |
| End of day 2 | both | both | Contracts frozen in code: `models.py`, `ui_models.py`, `ui.ts`, `config.yaml` |
| Day 3 | Zizwe | Emmanuel | Bus, LinkPort, link stand-in, heartbeat and `run_all` working. Payload Controller accepts `cmd.assign_mission` and emits `payload.status` |
| Day 4 | Zizwe | Emmanuel | `permissions.py` (B8), Team 2 and Team 4 stand-ins sending `nav.state` and `power.status` |
| Day 5 | Emmanuel | Emmanuel | `/ws` serves real snapshots; schema comparison test |
| Day 7 | both | both | Happy-path mission works from the screen |
| Day 10 | Zizwe | Emmanuel | All vehicle faults, the Event Buffer, `FaultInjector` and `vehicle.test_agent` |
| Day 12 | Emmanuel | both | Scenario runner passes `iron_hawk.yaml` in CI; real snapshot fixtures for the screen |

### If time runs short

The doc shows no Sprint 4 build, so you may have less than three weeks. Cut in this order, from the top:

1. The three-process mode. Demo in `--single-process` with the in-memory link (still shows outages).
2. The route drawing in the center panel. Keep the progress bar, ETA and reroute notice.
3. Changing payload details on screen. Keep it in the backend and test it through the API.
4. Polish of the test panel. A scenario file can trigger the same faults.

Never cut:
- The payload safety interlocks and their tests.
- The 5 s timeouts.
- The emergency stop.
- Alerts with recommended actions.
- The Mission Log.
- The scenario runner, which produces your verification evidence.

## Working agreement

- **Branches:** short-lived, one per task, named `feature/<TASK-ID>-short-name`, for example `feature/A4-payload-controller` or `feature/C7-command-panel`. Merge to `main` at least once a day.
- **Pull requests:** every PR is reviewed by the other builder (US-13). PR titles start with the task ID and requirement IDs: `[A4][AEG-506] Block release while moving`.
- **CI on every PR:** ruff, pytest, eslint, vitest, frontend build, and the scenario smoke test (`iron_hawk_short.yaml`).
- **Requirement IDs everywhere:**
  - Tests are named by the requirement they prove: `test_AEG_506_release_refused_while_moving`.
  - Commit messages name the requirement IDs they touch.
- **Done** means:
  - The code is merged.
  - Its tests are named by requirement and passing.
  - The Mission Log shows the behaviour.
  - The doc is updated if a decision changed (handbook Definition of Done).

## Open items that can change the build

| Item | Owner | Effect if it changes |
|---|---|---|
| How Team 1 wants teams to exchange messages | Team 1, asked by B | Only `adapters/` and `bus/tcp.py` change. Offer them our envelope as the program format (doc 06). |
| Team 2 message formats, the interlock, emergency stop ownership | Team 2, asked by B | Only `adapters/team2.py` |
| Team 3 link limits and priority support | Team 3, asked by B | `config.yaml` only |
| Team 4 accepting 500 to 1000 kg and 3.2 / 5.0 Wh | Team 4, asked by B | `config.yaml` only |
| Payload mass versus box size | Team 5 | `config.yaml` only |
