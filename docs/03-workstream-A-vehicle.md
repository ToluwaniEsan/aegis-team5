# 03. Workstream A: vehicle software

**Owns:** `backend/aegis/common/` (except `ui_models.py`), `backend/aegis/vehicle/`, and their tests. Builder: Zizwe (`HANDOFF-ZIZWE.md`).
**Goal:** a Payload Controller that can be shown, by test, never to release the payload when it should not. It must keep working with the ground station and the link gone.

Read `02-contracts.md` sections 2 to 4 and 7 before starting. The state machine table in section 4 is your specification. Where this file and the contracts disagree, the contracts win; tell the team.

## How the pieces fit

```
                vehicle process
  +-----------------------------------------------------------+
  |  team2.nav (stand-in) --nav.state--> PayloadController     |
  |  team4.power (stand-in) --power.status--> PayloadController|
  |                                                            |
  |  PayloadController  <--sim.reading--  PayloadSimulator     |
  |                     --sim.command-->                       |
  |        |  payload.status, ack, fault.*, payload.delivered  |
  |        v                                                   |
  |  EventBuffer (holds ground-bound messages while link LOST) |
  |        |                                                   |
  |  LinkPort  <---- TCP :7102 ----> link process              |
  +-----------------------------------------------------------+
```

Every component has the same shape:

```python
class PayloadController:
    def __init__(self, bus: LocalBus, clock: Clock, cfg: Settings, log: MissionLog): ...
    async def start(self) -> None: ...   # subscribe, start the 1 Hz loop
    async def stop(self) -> None: ...
```

`LocalBus`, `LinkPort` and `MissionLog` come from Workstream B (task B1). Zizwe builds B1 too. Until it lands, use the in-memory fake in `tests/fakes.py` (written first, with B1), which matches the B1 interface.

## Tasks

### Phase 0: foundations (days 1 to 2)

**A0. Settings loader**
- **Files:** `aegis/common/config.py`
- **Build:** pydantic models that mirror every key in `config/config.yaml`, and `load_settings(path=None) -> Settings`.
  - With no path, use the `AEGIS_CONFIG` environment variable if set. Otherwise look for `config/config.yaml` from the current folder upward, so it works from the repo root and from `backend/`.
  - Unknown keys fail.
  - Missing keys fail.
  - Values out of range fail, for example a negative timeout or `mass_min_kg > mass_max_kg`.
- **Done when:**
  - The real `config.yaml` loads.
  - Three broken copies in `tests/fixtures/` each fail with a message that names the key.
  - Changing `timing.command_timeout_s` in the file changes behaviour with no code change (A-10).

**A1. Clock**
- **Files:** `aegis/common/clock.py`
- **Build:** the `Clock` protocol with `now() -> datetime` (UTC, aware) and `async sleep(seconds)`.
  - `RealClock` uses the system clock.
  - `ManualClock(start)` has `advance(seconds)`. Any `sleep` whose deadline has passed resolves, in deadline order.
- **Done when:**
  - Tests show a 5 s sleep resolves on `advance(5)` and not on `advance(4.9)`.
  - Two sleeps resolve in order.
  - `now()` is always UTC.

**A2. Models and envelope**
- **Files:** `aegis/common/models.py`, `aegis/common/envelope.py`, `scripts/export_schemas.py` (message schemas)
- **Build:**
  - A pydantic model for the envelope and for the body of every message type in contracts section 3. Use `Literal` for the enums.
  - `make(type, src, dst, body, clock, **ids) -> Envelope` fills `msg_id`, `sent_at`, `iface` and `priority` from a registry keyed by `type`.
  - `parse(line: str) -> Envelope` validates the body against its type.
  - The UI protocol models from section 9 are **not** in this task. Emmanuel writes them in `aegis/common/ui_models.py`.
  - `export_schemas.py` writes JSON Schema files for the message models to `contracts/messages.schema.json`. Emmanuel extends the same script for `ui.schema.json` (B13).
- **Done when:**
  - Every message type in the catalog round-trips (`make`, serialize, `parse`) in a parametrized test.
  - A message with a wrong unit field, a missing field or an unknown type is rejected.
  - Timestamps serialize as `...Z` with milliseconds (GEN-002).

End of day 2: contract freeze with B and C.

### Phase 1: walking skeleton (days 3 to 7)

**A3. Payload Simulator**
- **Files:** `aegis/vehicle/simulator.py`
- **Requirements:** AEG-502, AEG-504, AEG-505, AEG-509, GEN-004, GEN-005
- **State it keeps:** `bay_mass_kg` (true mass), `locked`, `shift_cm`, three sensor healths, `release_jam`, `release_in_progress`, `release_done`.
- **Handles `sim.command`:**
  - `LOAD(mass_kg)`: from EMPTY, after `load_time_s` the bay holds that mass. With a payload already aboard (a payload update), the lock stays closed and the new mass settles after `reweigh_time_s`. `settled` is false until then.
  - `LOCK`: after `secure_time_s`, `locked = true`.
  - `UNLOCK`: opens the lock. Only used inside `RELEASE` and `UNLOAD`.
  - `RELEASE`: unlock, wait `release_time_s`, mass goes to 0, `release_done = true`. A jam means it never finishes.
  - `UNLOAD`: unlock, mass goes to 0.
- **Emits `sim.reading` at 1 Hz and on change:**
  - The measured mass is the true mass plus uniform noise of ±`sim_noise_kg`. Fail at startup if `sim_noise_kg` is not below `weight_accuracy_kg`.
  - `settled` is false while loading or re-weighing. The controller judges mass only on settled readings.
  - A FAULT load cell reports `mass_kg = null`.
- **Test hooks for B's Fault Injector:** `inject_shift(cm)`, `set_sensor(name, health)`, `override_mass(kg)`, `set_release_jam(on)`.
- **Release energy:** report `release_energy_wh_nominal` from config for each release.
- **GEN-004:** the lock state belongs to the simulator. Nothing opens it except `UNLOCK`, `RELEASE` or `UNLOAD` commands, so a dead controller leaves it locked.
- **Done when:**
  - `test_AEG_504_twenty_readings_within_accuracy` passes.
  - `test_GEN_005_each_failure_can_be_triggered` covers shift, each sensor and the jam.
  - `test_GEN_004_lock_holds_without_controller` passes.

**A4. Payload Controller: core state machine**
- **Files:** `aegis/vehicle/payload_controller.py`, `aegis/vehicle/rules.py`
- **Requirements:** AEG-501, 503, 505, 506, 507, 508, 510, 511, 512, OI-004, OI-019
- **Pure core.** Write the logic in `rules.py` as one pure function: `step(state: CtrlState, event: Event, now: datetime, cfg) -> (CtrlState, list[Action])`.
  - No IO and no clock reads in `rules.py`.
  - Events: the commands, `nav.state`, `power.status`, `sim.reading`, `link_lost`, `link_restored`, `tick`.
  - Actions: send a message, send `sim.command`, raise or clear a fault.
  - This makes every rule testable with plain function calls.
- **Thin async shell.** `payload_controller.py` feeds bus messages and a 1 Hz tick into `step` and executes the actions.
- **Run the command checks in the order contracts section 4 gives:**
  1. Emergency stop bypass.
  2. Future timestamp.
  3. Stale command.
  4. HELD filter.
  5. The state row.
- **Keep `lock_requested` in `CtrlState`** so LOCK is sent once, not on every reading.
- **Implement the transition table in contracts section 4 row by row.**
  - Every refusal sends `ack REJECTED` with a reason a person can read: "Vehicle is moving", "Not at the destination", "Payload is not secured", "A critical fault is active", "Command is older than 5 s".
- **Acks:** `RECEIVED` as soon as a command parses; `COMPLETED` when its effect is done. For example, `cmd.release` completes when the simulator reports `release_done`.
- **Messages it sends:**
  - `payload.status` at 1 Hz and on every change (AEG-505).
  - `payload.interlock` at 1 Hz to `team2.nav`. `departure_permitted` follows the one definition in contracts section 4: SECURED, `secured` true and a mission open (AEG-511).
  - `payload.mass_report` to `team4.power` whenever the measured mass settles (AEG-512).
  - `payload.delivered` the moment the simulator reports `release_done`, with `payload_id`, position from the last `nav.state` and `released_at` (AEG-508, AEG-510).
- **Two-sided timeout:** reject any command except `cmd.estop` whose `sent_at` is more than `command_max_age_s` old by the vehicle clock (`STALE_COMMAND`), or more than `clock_skew_warn_s` in the future (`FUTURE_TIMESTAMP`, and raise `CLOCK_SKEW`).
- **Done when:**
  - These tests pass, at least one per row of the section 4 table:
    - `test_AEG_506_release_refused_while_moving`
    - `test_AEG_506_release_refused_in_every_state_except_at_destination` (parametrized over all 9 states)
    - `test_AEG_507_release_requires_operator_command`
    - `test_AEG_511_interlock_false_until_secured_and_in_range`
    - `test_AEG_501_assign_rejected_over_mass_limit`
    - `test_AEG_501_assign_rejected_over_dims`
    - `test_AEG_503_accepts_500_750_1000_kg`
    - `test_AEG_512_update_before_departure_only`
    - `test_AEG_508_delivered_sent_within_10_s_of_release`
    - `test_OI_019_estop_holds_payload_from_any_state`
    - `test_stale_command_rejected` (two-sided timeout)
    - `test_future_timestamp_rejected`
    - `test_OI_019_estop_never_rejected_for_age_or_clock`
    - `test_AEG_502_shift_over_limit_makes_payload_unsecured`
    - `test_returned_payload_cannot_depart_until_unloaded_and_reassigned`
    - `test_release_done_while_held_still_sends_delivered`
  - A happy path from EMPTY to DELIVERED runs against the simulator with the Team 2 stand-in, using `ManualClock`.

**A5. Link loss on the vehicle**
- **Files:** `aegis/vehicle/link_watch.py`
- **Requirements:** AEG-507, AEG-514
- **Build:** endpoint `vehicle.link_watch` watches `hb.ground`.
  - With none for `link.lost_after_s`, it publishes `int.link_state LOST` to the controller and the Event Buffer.
  - When the next heartbeat arrives, it publishes `int.link_state RESTORED`.
  - The vehicle decides this on its own and never trusts the ground to say the link is down.
- **Controller rules (contracts section 4):**
  - At AT_DESTINATION with the link lost: if `prerelease_authorized`, release after `link.prerelease_wait_s`, but only if every release guard still holds. Otherwise stay secured.
  - A release command that arrives after the link returns is accepted only if it is fresh (A4 stale check).
- **Done when:**
  - `test_AEG_514_link_lost_at_destination_without_preauth_stays_secured` passes (advance the clock 10 minutes; still secured).
  - `test_AEG_507_link_lost_with_preauth_releases_after_wait` passes.
  - `test_AEG_514_old_release_command_rejected_after_link_returns` passes.

### Phase 2: off-nominal (days 8 to 13)

**A6. Faults on the vehicle**
- **Files:** `aegis/vehicle/faults.py`, used by `rules.py`
- **Requirements:** AEG-502, AEG-513, OI-010, GEN-004
- **Detect, raise and clear** every vehicle-side code in contracts section 7:
  - `ESTOP_ACTIVE`, `PAYLOAD_UNSECURED`, `DEPARTED_UNSECURED`, `RELEASE_FAILED`, `LOCK_SENSOR_FAULT`
  - `DRIVETRAIN_FAULT` (from the local Team 4 status), `PAYLOAD_SHIFT`, `WEIGHT_OUT_OF_RANGE`, `LOAD_CELL_FAULT`, `CLOCK_SKEW`
- **Each `fault.raised` carries** a new `fault_id`, the severity, the recommended action from the catalog and `holds_payload`.
- **Raise within one tick.** That keeps the vehicle well inside the 2 s budget once the link adds its delay.
- **HELD:** holding faults move the payload to HELD. HELD exits to `held_from` only when every holding fault is both cleared and acknowledged with `cmd.ack_fault`.
- **Done when:** a test exists per code, named by its requirement:
  - `test_AEG_502_shift_over_2cm_raises_within_2s`
  - `test_AEG_513_payload_fault_reported_within_2s`
  - `test_OI_019_estop_cleared_only_by_ack`
  - `test_held_exits_only_when_cleared_and_acknowledged`

**A7. Event Buffer**
- **Files:** `aegis/vehicle/event_buffer.py`
- **Requirements:** OI-013, AEG-508 (delivery during an outage)
- **Build:** register as an outbound filter on the vehicle bus (B1 `add_outbound_filter`) for every message going to the ground. Follow `int.link_state` to know whether the link is LOST.
  - **While `link_lost`, buffer:** append to memory and to `event_buffer.file` on disk.
  - **What to keep:** `payload.status` only keeps the newest one; `hb` is never buffered; everything else is kept in order.
  - **Cap:** at `max_events`, drop the oldest `payload.status` first, then the oldest CAUTION faults, and log every drop.
- **The first seconds of an outage:** the link is only declared LOST after `lost_after_s`, and messages sent in those seconds are dropped by the link. So always keep a rolling copy of the last `lost_after_s` seconds of non-status messages (faults, acks, deliveries). Replay that copy at the front of the backlog. The ground de-duplicates by `msg_id` (B10).
- **On `int.link_state RESTORED`:** send the backlog as `backlog.batch` messages of up to `batch_size` events in original order, each with `buffered = true` and its original `sent_at`. Then resume live sending.
- **Done when:**
  - `test_OI_013_delivery_during_outage_reaches_ground_after_restore` passes. Release during an outage; after restore the ground receives `payload.delivered` with the original `released_at`.
  - `test_event_buffer_survives_vehicle_restart` passes.
  - `test_event_buffer_preserves_order` passes.

**A8. Safety property test**
- **Files:** `tests/test_safety_properties.py`, using `hypothesis` (dev dependency)
- **Requirements:** AEG-506, AEG-507, AEG-511, AEG-514, GEN-004
- **Build:** generate random sequences of up to 200 events (commands, nav states, sensor changes, link loss, clock jumps, emergency stops) and feed them to `rules.step`.
- **Assert after every step:**
  1. A `RELEASE` sim command is only ever issued from AT_DESTINATION, with the vehicle stopped, secured, no active CRITICAL fault, and either a fresh operator release or (`prerelease_authorized` and link lost for the full wait).
  2. `departure_permitted` is never true unless the state is SECURED, `secured` is true and a mission is open (contracts section 4).
  3. In HELD, no `RELEASE` is issued.
  4. `cmd.estop` always ends in HELD, whatever its age or the clock.
  5. HELD always exits once every holding fault is cleared and acknowledged (no permanent HELD).
- **Why:** this is the strongest evidence you can show at review that accidental release (risk rated 10, now 5) is controlled.
- **Done when:** 2,000 examples run in CI with no failure. Any failure hypothesis finds is added as a fixed regression test.

**A9. Vehicle process entry point**
- **Files:** `aegis/vehicle/main.py`
- **Build:** load settings, build the bus, LinkPort (connect to `link_vehicle_port`), simulator, controller, link watch, Event Buffer, and the Team 2 and Team 4 stand-ins from Workstream B. Handle Ctrl+C cleanly.
- **Test agent:** endpoint `vehicle.test_agent` receives `test.inject` and calls the simulator hooks (A3), the stand-in hooks (B5, B6) or the crash hook below.
- **Controller crash hook:** test injection `payload/controller_crash` cancels only the controller task. The simulator keeps running, the lock stays closed, and nothing can release. Restarting the controller is out of scope; say so at review.
- **Done when:**
  - `python -m aegis.vehicle` runs against the link stand-in.
  - `test_GEN_004_controller_crash_leaves_payload_secured` passes in single-process mode.

## What Workstream A hands to others

| Day | To | What |
|---|---|---|
| 2 | B, C | `models.py`, `envelope.py`, schema export |
| 3 | B | A Payload Controller that accepts `cmd.assign_mission` and emits `payload.status` (stubs allowed) |
| 7 | B | Full happy path with real acks |
| 11 | B | All vehicle faults and the Event Buffer, so the scenario runner can drive them |

## Review questions you should be able to answer with a test

- "Show me that release is impossible while moving." Use `test_AEG_506_*` and the property test.
- "What happens if the link drops at the destination?" Use the `test_AEG_514_*` tests.
- "What happens if your software crashes?" Use `test_GEN_004_*`.
- "How do you stop an old command running late?" Use `test_stale_command_rejected` and B's `test_OI_009_*`.
