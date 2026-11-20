import asyncio

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make, make_ack
from aegis.common.ui_models import UiCommand
from aegis.ground.command_manager import CommandManager
from aegis.ground.status_monitor import StatusMonitor
from tests.fakes import FAKE_START, FakeBus, FakeLog


@pytest.fixture
def harness(tmp_path):
    clock = ManualClock(FAKE_START)
    cfg = load_settings()
    cfg = cfg.model_copy(
        update={"logging": cfg.logging.model_copy(update={"dir": str(tmp_path)})}
    )
    log = FakeLog(clock=clock)
    bus = FakeBus("ground", clock, log)
    status = StatusMonitor(bus, clock, cfg, log, lambda _: None)
    manager = CommandManager(bus, clock, cfg, log, status)
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


@pytest.mark.asyncio
async def test_OI_009_command_fails_after_timeout_and_is_not_resent(harness):
    manager, _, bus, clock, cfg, log = harness
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
async def test_OI_006_status_change_visible_within_2s(harness):
    manager, _, bus, clock, _, _ = harness
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
    manager, _, bus, _, _, _ = harness
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
    manager, _, bus, _, cfg, _ = harness
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
