# 04. Workstream B: ground station backend and team connections

> **Two-builder split.** This file's tasks are shared. Zizwe does B1, B3, B4, B5, B6, B8, B14 and the Team 2, 3 and 4 adapters. Emmanuel does B0, B2, B7, B9 to B13, B15 and the Team 1 adapter. `HANDOFF-ZIZWE.md` and `HANDOFF-EMMANUEL.md` at the repo root list the changes to individual tasks; where they differ from this file, the handoff wins.

**Owns:**
- Backend code: `backend/aegis/bus/`, `ground/`, `standins/`, `adapters/`, `testing/` and `run_all.py`.
- Repo setup: `scenarios/`, `tools/` and CI.
- Talking to Teams 1 to 4 about interfaces (doc 06).

**Goal:** everything between the vehicle and the screen works and is measurable:
- commands with honest status
- per-value data ages
- alerts within 2 s
- a log that proves what happened
- stand-ins good enough that the full IRON HAWK scenario runs before any other team is ready

Read `02-contracts.md` in full. Sections 5, 6, 8 and 9 are yours to implement on the ground side.

## Tasks

### Phase 0: foundations (days 1 to 2)

**B0. Repo, CI and fakes**
- **Files:**
  - Repo setup: `backend/pyproject.toml`, `.github/workflows/ci.yml`, `CODEOWNERS`, `README.md`.
  - Shared test fakes: `backend/tests/fakes.py`.
- **Dependencies:**
  - Runtime: `pydantic>=2`, `pyyaml`, `fastapi`, `uvicorn[standard]`.
  - Dev: `pytest`, `pytest-asyncio`, `hypothesis`, `ruff`, `httpx`.
  - Add the IDs of all Python tests to the junit output (`pytest --junitxml reports/pytest.xml`) so the verification report can read them.
- **CI jobs:**
  - Backend: ruff, then pytest.
  - Frontend: lint, test, build.
  - Smoke: `python -m aegis.testing.scenario_runner scenarios/iron_hawk_short.yaml --fast`, run from `backend/`. Add the job now but mark it allowed to fail until B15 lands, then make it required.
- **`tests/fakes.py`** gives `FakeBus` and `FakeLog` with exactly the B1 and B2 interfaces. Zizwe writes this file as part of B1, on day 1.
- **Done when:**
  - A pull request runs every job.
  - `main` is protected so it needs one review.

**B1. Bus and link port**
- **Files:** `aegis/bus/local_bus.py`, `aegis/bus/link_port.py`, `aegis/bus/endpoints.py`, `aegis/bus/tcp.py`
- **Interface. A depends on this, so build exactly this:**

```python
Handler = Callable[[Envelope], Awaitable[None]]
OutboundFilter = Callable[[Envelope], Awaitable[Envelope | None]]   # return None to hold a message

class LocalBus:
    def __init__(self, side: Literal["ground", "vehicle"], clock: Clock, log: MissionLog): ...
    def subscribe(self, endpoint: str, handler: Handler, types: set[str] | None = None) -> None: ...
    async def publish(self, env: Envelope) -> None:
        """Logs msg.sent. Delivers to local subscribers whose endpoint is in env.dst.
        If any dst endpoint is on the other side, passes the envelope through the
        outbound filters, then to the attached LinkPort."""
    def add_outbound_filter(self, f: OutboundFilter) -> None: ...   # the Event Buffer uses this
    def attach_link(self, port: "LinkPort") -> None: ...
    async def deliver_from_link(self, env: Envelope) -> None: ...   # logs msg.recv, delivers locally

class LinkPort:
    def __init__(self, host: str, port: int, bus: LocalBus, clock: Clock, log: MissionLog): ...
    async def start(self) -> None: ...   # connect to network.link_host; reconnect with backoff from
                                         # network.reconnect_min_s doubling to reconnect_max_s
    async def send(self, env: Envelope) -> None: ...   # priority queue: 0 before 1 before 2, FIFO within a priority.
        # While disconnected: drop the message and log link.drop. Never hold it for later:
        # a command sent late is worse than one that fails (decision: commands are never queued).
        # On the vehicle, the Event Buffer filter runs before this and keeps what must survive.
```

- **Endpoint sides:** `endpoints.py` maps every endpoint in contracts section 2 to `ground`, `vehicle` or `link`.
- **Invalid lines:** a line that fails `parse` is logged as `bus.invalid` with the raw text and dropped.
- **Done when:**
  - Tests cover local delivery, delivery across a socket pair, priority order and reconnect.
  - Invalid input is logged and does not crash the bus.

**B2. Mission Log**
- **Files:** `aegis/ground/mission_log.py`, used by both sides
- **Requirements:** OI-013, AEG-510, GEN-002
- **Output:** JSON Lines, one file per process per run:
  - Ground: `logs/run-<UTC>-ground.jsonl`.
  - Vehicle and link: `-vehicle.jsonl`, `-link.jsonl`.
  - `run_all` passes all three processes the same run ID.
- **Python API (A and B both call it; `tests/fakes.py` must match):**

```python
class MissionLog:
    def __init__(self, process: str, run_id: str, clock: Clock, cfg: Settings): ...
    def record(self, kind: str, **fields) -> None: ...   # writes one line, flushes
```

- **Every record:** `{"t": <UTC>, "run": <id>, "process": <name>, "kind": ..., ...fields}`. A record about a message puts the whole envelope under the key `env`, so scenarios can match `env.type`. Flush after every line so a crash loses nothing.
- **Folder:** `logging.dir` is resolved from the repository root, not the working directory.
- **Kinds:**
  - Messages: `msg.sent`, `msg.recv` (with the whole envelope), `bus.invalid`.
  - Payload and missions: `state.change`, `mission.change`.
  - Commands: `cmd.lifecycle`.
  - Alerts: `alert.raised`, `alert.cleared`, `alert.ack`.
  - Tests: `test.inject`, `scenario.step`.
- **Done when:** `test_OI_013_every_command_state_change_and_alert_is_logged_with_time` passes. It runs a mission with one fault and checks the log contains each item, with UTC times and the payload ID.

**B3. Link stand-in (Team 3)**
- **Files:** `aegis/standins/link.py`, written as a class that works in-process and as `python -m aegis.standins.link`
- **Requirements:** OI-007, OI-008, OI-009, OI-017; I8
- **Build:**
  - Listen on `link_ground_port` and `link_vehicle_port`.
  - Relay each line to the other side after `base_latency_ms ± jitter_ms`.
  - Drop messages at `loss_pct`.
  - During an outage, drop everything. A real link loses messages; it does not hold them.
  - Strict priority in each direction's queue.
- **Never delayed or dropped:** messages of type `test.inject`, messages to `team3.link` itself, and the stand-in's own `link.health`. They are the test control plane.
- **Logging:** log `link.relay` and `link.drop` with the envelope's `msg_id` and type. Never log `msg.sent` (contracts section 2, logging rule).
- **`link.health` at 1 Hz to the ground side.**
  - LOST once an outage has lasted `link.lost_after_s` (A-15 says "lost after 5 s with nothing received"). In the first seconds of an outage it is still the previous state.
  - Otherwise DEGRADED or CONNECTED by the A-15 thresholds, using the configured or injected latency and loss.
- **Test controls:** `set(latency_ms, loss_pct)` and `outage(seconds)`.
- **Done when:**
  - Tests show latency applied, loss rate within ±3 % over 2,000 messages, an outage drops everything, and priority 0 overtakes priority 2.
  - `link.health` follows the injected conditions within 1 s.

**B4. Run everything**
- **Files:** `aegis/run_all.py`, `aegis/ground/main.py`, and `aegis/standins/link.py` as a `__main__`
- **Multi-process:** `python -m aegis.run_all` starts link, vehicle and ground as subprocesses with one run ID, streams their output with a prefix, and stops all of them on Ctrl+C.
- **Single-process:** `--single-process` runs the three sides in one asyncio loop, joined by the B3 link class in memory. `--fast` additionally uses `ManualClock`, for the scenario runner.
- **Done when:**
  - Both modes start.
  - Heartbeats cross the link and appear in all three logs within 2 s.

### Phase 1: walking skeleton (days 3 to 7)

**B5. Team 2 stand-in (navigation)**
- **Files:** `aegis/standins/nav.py`, runs in the vehicle process
- **On `nav.assign`:** ack RECEIVED, build a straight route with `route_points` points from origin to destination, then ack COMPLETED.
- **Departure:** depart only when the last `payload.interlock` has `departure_permitted = true`. The stand-in honors the interlock, which demonstrates AEG-511; the real Team 2 must too.
  - With `standins.nav.auto_depart: false` (the default), it also waits for the test action `nav/depart`, so scenarios control when the trip starts.
  - With `true`, it departs as soon as it is permitted.
- **Movement:** move along the route at `speed_mps × standins.time_scale`. Send `nav.state` at 1 Hz to `vehicle.payload_controller` and `ground.status_monitor`, with `progress_pct` and `eta_s`.
- **Arrival:** at the end, `moving = false` and `at_destination = true`.
- **Commands:**
  - `cmd.abort` and `cmd.return_to_origin`: route back to the origin, and set `at_origin` on arrival.
  - `cmd.change_destination`: re-plan from the current position.
  - `cmd.estop`: stop at once, `moving = false`.
  - Ack each one COMPLETED when done.
- **Test hooks:** `depart`, `arrive`, `stop`, `block_route(reason)` and `health(h)`. `block_route` adds a detour point, sends `nav.route_blocked` with the new route and a longer ETA, then continues.
- **Done when:** a happy-path trip runs end to end with A's controller. The vehicle does not move while the interlock is false (`test_AEG_511_standin_waits_for_interlock`).

**B6. Team 4 stand-in (power and mobility)**
- **Files:** `aegis/standins/power.py`, runs in the vehicle process
- **Build:**
  - Battery starts at `start_battery_pct` and drains at `drain_pct_per_min × standins.time_scale` while moving.
  - `power.status` goes to the vehicle and the ground at 1 Hz.
  - Log every `payload.mass_report`.
  - Ack `cmd.estop`.
- **Test hooks:** `battery(pct)` and `drivetrain(health)`.
- **Done when:** a test shows mass reports logged and `power.status` reaching `ground.status_monitor`. (The `POWER_LOW` alert test belongs to B11.)

**B7. Team 1 stand-in**
- **Files:** `aegis/standins/team1.py`, runs in the ground process
- **Build:** log every `t1.*` message. Send `t1.system_mode` with `mode: "OPERATIONAL"` on start. Test hook `mode(m)`.
- **Done when:** `test_AEG_513_payload_fault_reaches_team1_within_2s` and `test_AEG_508_delivery_confirmation_reaches_team1` pass, end to end in `--fast` single-process mode.

**B8. Permissions**
- **Files:** `aegis/ground/permissions.py`
- **Requirements:** OI-003, OI-004
- **Build:** one pure function, `permissions(payload: PayloadView, nav: NavView, link: LinkView, alerts: list[AlertView], active: Mission | None, queue: list[Mission], cfg) -> dict[CommandName, Permission]`, using only the `ui_models` types, implementing the table in contracts section 5 with plain-language reasons. For `release`, check the guards in the order contracts section 4 gives (moving, destination, secured, critical fault) and use the same reason texts, so the screen and the vehicle always say the same thing. The UI server puts the result in `snapshot.allowed`; the Command Manager uses it to refuse early.
- **Done when:** a parametrized test covers every command against every payload state, with link LOST, with an active CRITICAL alert and with a mission in the queue. Each refusal has a non-empty reason.

**B9. Command Manager**
- **Files:** `aegis/ground/command_manager.py`
- **Requirements:** OI-001, OI-002, OI-003, OI-006, OI-009, OI-015, OI-019, AEG-510, AEG-512
- **`handle(ui_command) -> CommandResult`:**
  - Check permission.
  - Refuse if `needs_confirmation` and not `confirmed`.
  - Check `args` against the limits in `config.yaml`. Refuse with a reason that names the value and the limit, for example "Payload 1,180 kg exceeds the 1,000 kg limit" (OI-004, AEG-501). The vehicle checks again.
  - Build the envelope(s) per contracts section 5, with `dst` listing every recipient.
  - Publish, and return `accepted` with the `command_id`.
- **IDs:**
  - Generate `MSN-YYYY-NNN` and `PAY-YYYY-NNN` with the year from the clock.
  - Persist the counters in `logs/ids.json` so IDs never repeat across runs.
  - Expose the next pair in `snapshot.mission.next_ids` so the form can pre-fill them.
- **Lifecycle:**
  - `command_id` is the first envelope's `msg_id`. Keep a map from every envelope `msg_id` of the command to it (contracts section 5).
  - Record SENT.
  - Move to RECEIVED or COMPLETED on acks, and track each recipient separately.
  - Move to FAILED on any REJECTED, with the reason, at `command_timeout_s` with no RECEIVED, or at `command_complete_timeout_s` with no COMPLETED.
  - **Never resend.** `test_OI_009_*` must prove no second envelope with the same command is ever published.
  - Raise `COMMAND_FAILED` through the Alert Manager.
- **Missions and the queue:** apply contracts section 6. Send `t1.mission_report` on every mission status change.
- **Emergency stop:** priority 0, no confirmation, sent to all three recipients.
- **Done when these tests pass:**
  - `test_OI_009_command_fails_after_timeout_and_is_not_resent`
  - `test_OI_006_status_change_visible_within_2s`
  - `test_OI_003_risky_command_refused_without_confirmation`
  - `test_OI_015_queued_mission_never_starts_on_its_own`
  - `test_AEG_510_ids_unique_across_restarts`
  - `test_OI_019_estop_sent_with_priority_0_to_all_three`

**B10. Status Monitor**
- **Files:** `aegis/ground/status_monitor.py`
- **Requirements:** OI-005, OI-007, OI-008, OI-012, OI-016, OI-017, AEG-508
- **Keep the latest value of each group** with its `updated_at`: `payload.status`, `nav.state`, `power.status`, `link.health`.
  - `updated_at` is the envelope's `sent_at`, not when it arrived, so a delayed message shows its real age (OI-017).
  - Ages are computed against the ground clock at snapshot time.
  - A group is `stale` when its age exceeds `stale_after_s` or it has no data.
  - Stale values are kept and shown with their age, never blanked (OI-008).
- **Link state fallback:** if `link.health` itself stops for `lost_after_s`, the link is LOST.
- **Route blocked:** `nav.route_blocked` sets `nav.blocked`, with `old_route` taken from the last `nav.state`. It clears once the vehicle has passed the detour point or after `timing.route_blocked_clear_s`.
- **Delivery:** on `payload.delivered`, build `DeliverySummary`.
  - `confirm_latency_s` is the time from `released_at` to receipt. That number is the AEG-508 evidence.
  - Forward it to Team 1 as `t1.delivery_confirmation`.
- **`backlog.batch`:**
  - Skip any event whose `msg_id` was already received. The Event Buffer replays its last seconds before the outage was detected, so duplicates are expected.
  - Log each event with its original time.
  - Apply events in order. A status is applied only if it is newer than the current one.
  - Faults and deliveries are always applied.
- **Vehicle health roll-up** per contracts section 8, with `detail` strings ready to show.
- **Acks:** route every `ack` to the Command Manager.
- **Done when these tests pass:**
  - `test_OI_008_last_known_status_and_age_shown_when_link_lost`
  - `test_OI_017_values_older_than_5s_marked_stale`
  - `test_OI_007_link_state_follows_link_health`
  - `test_OI_007_link_lost_when_health_messages_stop`
  - `test_AEG_508_confirm_latency_recorded`

**B11. Alert Manager**
- **Files:** `aegis/ground/alert_manager.py`
- **Requirements:** OI-010, OI-011, OI-018, AEG-513
- **Sources:**
  - Vehicle `fault.raised` and `fault.cleared`.
  - Its own ground-side checks: `LINK_LOST`, `LINK_DEGRADED`, `COMMAND_FAILED`, `ROUTE_BLOCKED`, `STALE_DATA`, `POWER_LOW`, `NAV_SENSOR_FAULT`, `CLOCK_SKEW`.
- **Alert list:** keep active or unacknowledged alerts, ordered CRITICAL, WARNING, CAUTION, then newest first. Titles carry the live value, for example "Payload shifted 3.1 cm".
- **`ack_fault`:**
  - Vehicle faults: send `cmd.ack_fault` and mark acknowledged when the vehicle's ack arrives.
  - Ground faults: mark acknowledged locally.
  - An acknowledged alert whose condition is still active stays listed with `acknowledged = true`.
- **Team 1:** forward every fault to Team 1 as `t1.fault_report` the moment it is seen.
- **Done when:**
  - `test_OI_010_fault_on_screen_within_2s_with_action` passes, measured from injection to the snapshot containing it, through the link stand-in at default latency.
  - `test_OI_011_critical_stays_until_acknowledged` passes.
  - `test_AEG_513_*` passes.

**B12. UI server**
- **Files:** `aegis/ground/ui_server.py`
- **Requirements:** I1, OI-005, OI-006
- **FastAPI app inside the ground process:**
  - `GET /` serves `frontend/dist`.
  - `GET /api/health` returns ok.
  - `WS /ws` sends a full `Snapshot` on connect, then broadcasts at `status_rate_hz` and within 100 ms of any change (debounced). `seq` increases by one per snapshot.
  - Incoming `UiCommand` goes to the Command Manager, and the `CommandResult` goes back to that client only.
  - `POST /api/test/inject` exists only when `test_mode` is true (404 otherwise). It logs `test.inject` and routes to the target.
- **Done when:**
  - A WebSocket test receives a snapshot within 1 s of connecting and one per second after.
  - A command round-trip returns a `CommandResult`.
  - The inject endpoint is 404 with `test_mode: false`.

**B13. Contract test and fixtures**
- **Files:** `tests/test_contract_ui.py`, `tools/dump_snapshot_fixtures.py`
- **Build:**
  - Compare the JSON Schema of the pydantic `Snapshot` (A2) with the checked-in `contracts/ui.schema.json`. Any difference fails CI and needs a CONTRACT CHANGE.
  - Workstream C generates a JSON Schema from `ui.ts` with `ts-json-schema-generator` into `contracts/ui.from-ts.schema.json`. This test normalizes both schemas and fails if they differ. That is how `ui.ts` and the pydantic models are kept identical.
  - `dump_snapshot_fixtures.py` runs `iron_hawk.yaml` and `estop.yaml` in `--fast` mode (needs B15) and saves real snapshots at 12 named moments to `frontend/src/mock/fixtures/*.json`: idle, assigned, secured, travelling, degraded, link_lost, route_blocked, fault_shift, estop_held, at_destination, delivered, queued.
- **When:** the schema comparison is due on day 5; the fixtures are due on day 11. C uses hand-written fixtures until then.
- **Done when:** C's frontend type-checks all 12 fixtures against `ui.ts` (C does that half) and the mock feed uses them.

### Phase 2: off-nominal and evidence (days 8 to 13)

**B14. Fault Injector and test panel backend**
- **Files:** `aegis/testing/fault_injector.py`
- **Requirement:** GEN-001
- **Build:**
  - Implement every row of contracts section 10.
  - Payload targets go to A's simulator hooks; `controller_crash` cancels the controller task.
  - Link targets go to B3; `nav`, `power` and `team1` go to the stand-ins.
  - Validate params and return 400 with the reason if invalid.
- **Shape:** a plain class, `FaultInjector(bus, clock, cfg, log).inject(target, action, params) -> InjectResult`. It raises `ValueError` with the reason on bad params; B12 turns that into a 400.
- **Done when:** `test_GEN_001_every_fault_triggerable_without_code_change` calls `inject()` for each row and sees its effect in the log. Emmanuel's B12 adds a test of the HTTP route.

**B15. Scenario runner**
- **Files:** `aegis/testing/scenario_runner.py`, `scenarios/iron_hawk.yaml`, `scenarios/iron_hawk_short.yaml`
- **Format and the full scenario:** doc 06, section 2.
- **`--fast` mode:** single-process with `ManualClock`.
  - The runner calls `CommandManager.handle()` and `FaultInjector.inject()` directly instead of going through the WebSocket and HTTP, and reads snapshots from the snapshot builder.
  - It advances the clock in 0.1 s steps and yields to the event loop after each step, so a full IRON HAWK run takes seconds. Use it for CI.
- **`--live` mode:** real time against a running `run_all`, through `/ws` and `/api/test/inject`. Use it for the demo, so the audience watches the screen while the scenario drives it.
- **Log checks:** read every log file of the run (all processes, same run ID).
- **`repeat: N`:** runs a step N times and records each result, for the "10 out of 10" requirements.
- **Output:** writes `reports/scenario-<name>-<UTC>.json`. Each step records pass or fail, the requirement IDs it proves, the measured times and the log file names.
- **Done when:** `iron_hawk.yaml` passes in `--fast` mode in CI, and in `--live` mode on a laptop.

### Phase 3: real teams (day 14 onward)

**B16. Adapters for the real teams.** One file per team in `aegis/adapters/`. Each translates between our envelope and whatever that team actually sends, and registers the same endpoint name the stand-in used, so nothing else changes. Doc 06 section 1 has the steps per team. Swap one team at a time, and run the full scenario after each swap.

## What Workstream B hands to others

| Day | To | What |
|---|---|---|
| 1 | A | `tests/fakes.py` |
| 3 | A, C | Bus, link stand-in, `run_all` |
| 5 | C | `/ws` with real snapshots, `/api/test/inject`, `ui.schema.json` |
| 5 | C | The schema comparison test, so `ui.ts` and the backend cannot drift |
| 11 | C | The 12 snapshot fixtures from a real run |
| 11 | all | Scenario runner and `iron_hawk.yaml` passing with stand-ins |
