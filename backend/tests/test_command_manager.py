import asyncio

import pytest
import pytest_asyncio

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make, make_ack
from aegis.common.ui_models import UiCommand
from aegis.ground.command_manager import CommandManager
from aegis.ground.status_monitor import StatusMonitor
from tests.fakes import FAKE_START, FakeBus, FakeLog


@pytest_asyncio.fixture
async def harness(tmp_path):
    clock = ManualClock(FAKE_START)
    cfg = load_settings()
    cfg = cfg.model_copy(
        update={"logging": cfg.logging.model_copy(update={"dir": str(tmp_path)})}
    )
    log = FakeLog(clock=clock)
    bus = FakeBus("ground", clock, log)
    status = StatusMonitor(bus, clock, cfg, log, lambda _: None)
    manager = CommandManager(bus, clock, cfg, log, status, alerts_for=lambda: [])
    await set_status(bus, clock, "EMPTY")
    await bus.inject(
        make(
            "nav.state",
            "team2.nav",
            {
                "moving": False,
                "speed_mps": 0,
                "position": {"lat": 34, "lon": -86},
                "at_destination": True,
                "at_origin": False,
                "eta_s": 0,
                "progress_pct": 100,
                "route": [],
                "health": "OK",
            },
            clock,
        )
    )
    await bus.inject(
        make(
            "link.health",
            "team3.link",
            {
                "state": "CONNECTED",
                "latency_ms": 80,
                "loss_pct": 0,
            },
            clock,
        )
    )
    yield manager, status, bus, clock, cfg, log
    manager.close()


def command(name, args=None, confirmed=False):
    return UiCommand(
        kind="command",
        client_req_id="request",
        command=name,
        args=args or {},
        confirmed=confirmed,
    )


def mission_args():
    return {
        "origin_id": "FOB_ALPHA",
        "destination_id": "OP_BRAVO",
        "priority": "PRIORITY",
        "declared_mass_kg": 742,
        "dims_cm": {"length": 58, "width": 38, "height": 36},
        "prerelease_authorized": False,
    }


async def settle():
    await asyncio.sleep(0)


async def set_status(bus, clock, state, mission_id=None):
    clock.advance(0.001)
    await bus.inject(
        make(
            "payload.status",
            "vehicle.payload_controller",
            {
                "state": state,
                "held_from": "TRAVELLING" if state == "HELD" else None,
                "secured": state not in {"EMPTY", "HELD"},
                "locked": state != "EMPTY",
                "mass_kg": None if state == "EMPTY" else 742,
                "shift_cm": 0,
                "release_energy_wh": None,
                "sensors": {"load_cell": "OK", "lock": "OK", "shift": "OK"},
                "prerelease_authorized": False,
                "departure_permitted": False,
                "departure_reason": "Not ready",
                "mission_id": mission_id,
            },
            clock,
        )
    )


@pytest.mark.asyncio
async def test_OI_009_command_fails_after_timeout_and_is_not_resent(harness):
    manager, _, bus, clock, cfg, log = harness
    await set_status(bus, clock, "AT_DESTINATION")
    res = await manager.handle(command("release", confirmed=True))
    await settle()
    clock.advance(cfg.timing.command_timeout_s)
    await settle()
    assert manager.commands[res.command_id].state == "FAILED"
    assert "Not resent" in manager.commands[res.command_id].reason
    assert len(bus.sent("cmd.release")) == 1
    assert len(manager.failed_alerts) == 1
    assert any(r["command"]["state"] == "FAILED" for r in log.of("cmd.lifecycle"))


@pytest.mark.asyncio
async def test_OI_013_failed_alert_callback_retries_without_duplicate_transition(
    harness,
):
    manager, _, bus, clock, _, _ = harness
    attempts = []

    async def notify(view):
        attempts.append(view.command_id)
        if len(attempts) == 1:
            raise RuntimeError("temporary notification failure")

    manager.on_failure = notify
    await set_status(bus, clock, "TRAVELLING")
    result = await manager.handle(command("abort", confirmed=True))
    env = bus.last("cmd.abort")
    ack = make_ack(
        env,
        "vehicle.payload_controller",
        "REJECTED",
        clock,
        reason_code="REJECTED",
        reason="Refused",
    )
    with pytest.raises(RuntimeError, match="temporary"):
        await manager.handle_ack(ack)
    await manager.handle_ack(ack)
    await manager.handle_ack(ack)
    assert attempts == [result.command_id, result.command_id]
    assert len(manager.failed_alerts) == 1


@pytest.mark.asyncio
async def test_OI_006_status_change_visible_within_2s(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "TRAVELLING")
    res = await manager.handle(command("abort", confirmed=True))
    env = bus.last("cmd.abort")
    await bus.inject(make_ack(env, "vehicle.payload_controller", "RECEIVED", clock))
    assert manager.commands[res.command_id].state == "RECEIVED"
    await bus.inject(make_ack(env, "vehicle.payload_controller", "COMPLETED", clock))
    assert manager.commands[res.command_id].state == "RECEIVED"
    await bus.inject(make_ack(env, "team2.nav", "COMPLETED", clock))
    assert manager.commands[res.command_id].state == "COMPLETED"


@pytest.mark.asyncio
async def test_OI_003_risky_command_refused_without_confirmation(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    result = await manager.handle(command("release"))
    assert not result.accepted and result.reason == "Confirmation required"
    assert not bus.sent("cmd.release")


@pytest.mark.asyncio
async def test_OI_015_queued_mission_never_starts_on_its_own(harness):
    manager, _, bus, clock, _, _ = harness
    first = await manager.handle(command("assign_mission", mission_args()))
    second = await manager.handle(command("assign_mission", mission_args()))
    assert first.accepted and second.accepted
    queued = manager.queue[0]
    assert queued.status == "QUEUED"
    body = {
        "mission_id": manager.active.mission_id,
        "payload_id": manager.active.payload_id,
        "released_at": clock.now(),
        "position": {"lat": 34, "lon": -86},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    await bus.inject(
        make("payload.delivered", "vehicle.payload_controller", body, clock)
    )
    assert manager.active is None and manager.queue[0] == queued
    assert len(bus.sent("cmd.assign_mission")) == 1
    await set_status(bus, clock, "DELIVERED", manager.queue[0].mission_id)
    started = await manager.handle(
        command("start_queued_mission", {"mission_id": queued.mission_id}, True)
    )
    assert started.accepted and manager.active.mission_id == queued.mission_id
    assert len(bus.sent("cmd.assign_mission")) == 2


@pytest.mark.asyncio
async def test_AEG_510_ids_unique_across_restarts(harness):
    manager, status, bus, clock, cfg, log = harness
    first = manager.next_ids()
    await manager.handle(command("assign_mission", mission_args()))
    manager.close()
    other_status = StatusMonitor(
        FakeBus("ground", clock, log), clock, cfg, log, lambda _: None
    )
    other = CommandManager(other_status.bus, clock, cfg, log, other_status)
    try:
        second = other.next_ids()
        assert first.mission_id != second.mission_id
        assert first.payload_id != second.payload_id
        assert status.destination_for(first.mission_id) is not None
    finally:
        other.close()


@pytest.mark.asyncio
async def test_OI_019_estop_sent_with_priority_0_to_all_three(harness):
    manager, _, bus, _, _, _ = harness
    result = await manager.handle(command("estop"))
    env = bus.last("cmd.estop")
    assert result.accepted and env.priority == 0
    assert set(env.dst) == {"vehicle.payload_controller", "team2.nav", "team4.power"}
    assert not bus.sent("hb.ground")


@pytest.mark.asyncio
async def test_OI_006_replayed_and_direct_ack_deduplicate(harness):
    manager, _, bus, clock, _, log = harness
    await set_status(bus, clock, "AT_DESTINATION")
    result = await manager.handle(command("release", confirmed=True))
    env = bus.last("cmd.release")
    ack = make_ack(env, "vehicle.payload_controller", "COMPLETED", clock)
    batch = make("backlog.batch", "vehicle.event_buffer", {"events": [ack, ack]}, clock)
    await bus.inject(batch)
    await bus.inject(ack)
    assert manager.commands[result.command_id].state == "COMPLETED"
    transitions = [r["command"]["state"] for r in log.of("cmd.lifecycle")]
    assert transitions == ["SENT", "COMPLETED"]


@pytest.mark.asyncio
async def test_AEG_512_payload_limits_rejected_without_send(harness):
    manager, _, bus, clock, cfg, _ = harness
    await manager.handle(command("assign_mission", mission_args()))
    await set_status(bus, clock, "SECURED", manager.active.mission_id)
    args = {
        "declared_mass_kg": cfg.payload.mass_max_kg + 1,
        "dims_cm": {"length": 1, "width": 1, "height": 1},
    }
    result = await manager.handle(command("update_payload", args))
    assert not result.accepted and str(int(cfg.payload.mass_max_kg)) in result.reason
    assert not bus.sent("cmd.update_payload")


@pytest.mark.asyncio
async def test_OI_006_multiple_envelopes_require_each_recipient(harness):
    manager, _, bus, clock, _, _ = harness
    result = await manager.handle(command("assign_mission", mission_args()))
    first = bus.last("cmd.assign_mission")
    second = bus.last("nav.assign")
    await bus.inject(make_ack(first, "vehicle.payload_controller", "COMPLETED", clock))
    assert manager.commands[result.command_id].state == "RECEIVED"
    await bus.inject(make_ack(second, "team2.nav", "COMPLETED", clock))
    assert manager.commands[result.command_id].state == "COMPLETED"


@pytest.mark.asyncio
async def test_OI_009_received_command_fails_after_completion_timeout(harness):
    manager, _, bus, clock, cfg, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    result = await manager.handle(command("release", confirmed=True))
    await settle()
    await bus.inject(
        make_ack(
            bus.last("cmd.release"), "vehicle.payload_controller", "RECEIVED", clock
        )
    )
    clock.advance(cfg.timing.command_timeout_s)
    await settle()
    assert manager.commands[result.command_id].state == "RECEIVED"
    clock.advance(cfg.timing.command_complete_timeout_s - cfg.timing.command_timeout_s)
    await settle()
    assert manager.commands[result.command_id].state == "FAILED"
    assert len(bus.sent("cmd.release")) == 1


@pytest.mark.asyncio
async def test_OI_015_replayed_delivery_completes_mission_and_retains_destination(
    harness,
):
    manager, status, bus, clock, _, _ = harness
    await manager.handle(command("assign_mission", mission_args()))
    mission = manager.active
    body = {
        "mission_id": mission.mission_id,
        "payload_id": mission.payload_id,
        "released_at": clock.now(),
        "position": {"lat": 34, "lon": -86},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    delivered = make("payload.delivered", "vehicle.payload_controller", body, clock)
    batch = make(
        "backlog.batch", "vehicle.event_buffer", {"events": [delivered]}, clock
    )
    await bus.inject(batch)
    assert manager.active is None
    assert manager.missions[mission.mission_id].status == "COMPLETE"
    assert manager.destination_for(mission.mission_id) == mission.destination
    assert status.delivery.destination == mission.destination
    assert bus.last("t1.mission_report").body.status == "COMPLETE"


@pytest.mark.asyncio
async def test_AEG_512_update_changes_mission_only_after_completion(harness):
    manager, _, bus, clock, _, _ = harness
    await manager.handle(command("assign_mission", mission_args()))
    await set_status(bus, clock, "SECURED", manager.active.mission_id)
    result = await manager.handle(
        command(
            "update_payload",
            {
                "declared_mass_kg": 800,
                "dims_cm": {"length": 50, "width": 35, "height": 30},
            },
        )
    )
    env = bus.last("cmd.update_payload")
    assert manager.active.declared_mass_kg == 742
    await bus.inject(make_ack(env, "vehicle.payload_controller", "COMPLETED", clock))
    assert manager.commands[result.command_id].state == "COMPLETED"
    assert manager.active.declared_mass_kg == 800
    assert manager.active.dims_cm.length == 50


@pytest.mark.asyncio
async def test_OI_009_rejection_calls_failure_alert_hook(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    failures = []

    async def on_failure(view):
        failures.append(view)

    manager.on_failure = on_failure
    result = await manager.handle(command("release", confirmed=True))
    await bus.inject(
        make_ack(
            bus.last("cmd.release"),
            "vehicle.payload_controller",
            "REJECTED",
            clock,
            reason_code="VEHICLE_MOVING",
            reason="Vehicle is moving",
        )
    )
    assert manager.commands[result.command_id].state == "FAILED"
    assert failures[0].reason == "Vehicle is moving"


@pytest.mark.asyncio
async def test_OI_004_real_permissions_refuse_moving_release_without_publish(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    clock.advance(0.001)
    await bus.inject(
        make(
            "nav.state",
            "team2.nav",
            {
                "moving": True,
                "speed_mps": 2,
                "position": {"lat": 34, "lon": -86},
                "at_destination": False,
                "at_origin": False,
                "eta_s": 5,
                "progress_pct": 50,
                "route": [],
                "health": "OK",
            },
            clock,
        )
    )
    before = list(bus.published)
    result = await manager.handle(command("release", confirmed=True))
    assert not result.accepted and result.reason == "Vehicle is moving"
    assert bus.published == before


@pytest.mark.asyncio
async def test_OI_004_real_permissions_refuse_held_payload_commands(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "HELD")
    before = list(bus.published)
    result = await manager.handle(command("abort", confirmed=True))
    assert not result.accepted and "held" in result.reason.lower()
    assert bus.published == before


@pytest.mark.asyncio
async def test_OI_003_real_permissions_allow_confirmed_release(harness):
    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    before = list(bus.published)
    refused = await manager.handle(command("release"))
    assert not refused.accepted and refused.reason == "Confirmation required"
    assert bus.published == before
    accepted = await manager.handle(command("release", confirmed=True))
    assert accepted.accepted and bus.last("cmd.release").msg_id


@pytest.mark.asyncio
async def test_OI_019_estop_survives_missing_status_and_alert_source(harness):
    manager, status, bus, _, _, _ = harness
    status.latest.clear()
    manager.alerts_for = None
    before = list(bus.published)
    assert not (await manager.handle(command("release", confirmed=True))).accepted
    assert bus.published == before
    accepted = await manager.handle(command("estop"))
    assert accepted.accepted
    assert bus.last("cmd.estop").priority == 0
    assert set(bus.last("cmd.estop").dst) == {
        "vehicle.payload_controller",
        "team2.nav",
        "team4.power",
    }


@pytest.mark.asyncio
async def test_OI_004_missing_alert_source_and_critical_alert_block_release(harness):
    from aegis.common.ui_models import AlertView

    manager, _, bus, clock, _, _ = harness
    await set_status(bus, clock, "AT_DESTINATION")
    manager.alerts_for = None
    before = list(bus.published)
    result = await manager.handle(command("release", confirmed=True))
    assert not result.accepted and result.reason == "Alert status unavailable"
    assert bus.published == before
    alert = AlertView(
        alert_id="alert",
        code="ESTOP_ACTIVE",
        severity="CRITICAL",
        title="Stop",
        source="Payload",
        recommended_action="Check",
        raised_at="2026-11-19T12:00:00.000Z",
        acknowledged=False,
        active=True,
    )
    manager.alerts_for = lambda: [alert]
    result = await manager.handle(command("release", confirmed=True))
    assert not result.accepted and result.reason == "A critical fault is active"
    assert bus.published == before
