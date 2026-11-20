from uuid import uuid4

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make, make_ack
from aegis.common.ui_models import UiCommand
from aegis.ground.alert_manager import AlertManager
from aegis.ground.command_manager import CommandManager
from aegis.ground.status_monitor import StatusMonitor
from tests.fakes import FAKE_START, FakeBus, FakeLog


@pytest.fixture
def harness():
    clock = ManualClock(FAKE_START)
    log = FakeLog(clock=clock)
    bus = FakeBus(side="ground", clock=clock, log=log)
    cfg = load_settings()
    status = StatusMonitor(bus, clock, cfg, log, lambda _: None)
    return AlertManager(bus, clock, cfg, log, status), bus, clock, cfg


def fault(clock, fault_id=None):
    return make(
        "fault.raised",
        "vehicle.payload_controller",
        {
            "fault_id": fault_id or uuid4(),
            "code": "ESTOP_ACTIVE",
            "severity": "CRITICAL",
            "source": "Payload",
            "message": "Emergency stop active",
            "recommended_action": "Check vehicle",
            "holds_payload": True,
        },
        clock,
    )


@pytest.mark.asyncio
async def test_OI_011_critical_stays_until_acknowledged(harness):
    manager, bus, clock, _ = harness
    env = fault(clock)
    await bus.inject(env)
    assert manager.views()[0].active
    await bus.inject(
        make(
            "fault.cleared",
            "vehicle.payload_controller",
            {"fault_id": env.body.fault_id, "code": env.body.code},
            clock,
        )
    )
    assert not manager.views()[0].active
    await manager.acknowledge_vehicle(str(env.body.fault_id))
    assert manager.views() == []


@pytest.mark.asyncio
async def test_AEG_513_fault_forwarded_once_with_original_body(harness):
    manager, bus, clock, _ = harness
    env = fault(clock)
    await bus.inject(env)
    await manager.handle(env)
    reports = bus.sent("t1.fault_report")
    assert len(reports) == 1
    assert reports[0].body == env.body
    assert manager.views()[0].recommended_action == env.body.recommended_action


@pytest.mark.asyncio
async def test_OI_010_replayed_fault_is_deduplicated_and_sorted(harness):
    manager, bus, clock, _ = harness
    env = fault(clock)
    await bus.inject(env)
    await bus.inject(
        make("backlog.batch", "vehicle.event_buffer", {"events": [env]}, clock)
    )
    assert len(bus.sent("t1.fault_report")) == 1
    assert [a.code for a in manager.views()] == ["ESTOP_ACTIVE"]


@pytest.mark.asyncio
async def test_OI_011_cleared_before_replayed_raise_stays_cleared(harness):
    manager, bus, clock, _ = harness
    env = fault(clock)
    await bus.inject(
        make(
            "fault.cleared",
            "vehicle.payload_controller",
            {"fault_id": env.body.fault_id, "code": env.body.code},
            clock,
        )
    )
    await manager.handle(env)
    assert not manager.views()[0].active
    assert not manager.views()[0].acknowledged


@pytest.mark.asyncio
async def test_OI_017_stale_data_tracks_observed_groups(harness):
    manager, bus, clock, cfg = harness
    await bus.inject(
        make(
            "power.status",
            "team4.power",
            {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"},
            clock,
        )
    )
    clock.advance(cfg.timing.stale_after_s + 1)
    await manager.refresh()
    alert = next(a for a in manager.views() if a.code == "STALE_DATA")
    assert "power.status" in alert.title
    assert "payload.status" not in alert.title


@pytest.mark.asyncio
async def test_OI_010_notice_expiry_does_not_clear_blocked_alert(harness):
    manager, bus, clock, cfg = harness
    await bus.inject(
        make(
            "nav.route_blocked",
            "team2.nav",
            {
                "reason": "Bridge out",
                "blocked_at": {"lat": 1, "lon": 1},
                "new_route": [],
                "new_eta_s": 10,
            },
            clock,
        )
    )
    assert next(a for a in manager.views() if a.code == "ROUTE_BLOCKED").active
    clock.advance(cfg.timing.route_blocked_clear_s + 1)
    await manager.refresh()
    assert manager.status.blocked() is None
    assert next(a for a in manager.views() if a.code == "ROUTE_BLOCKED").active


@pytest.mark.asyncio
async def test_POWER_LOW_raised_below_threshold(harness):
    manager, bus, clock, cfg = harness

    def power(value):
        return make(
            "power.status",
            "team4.power",
            {"battery_pct": value, "est_range_km": 10, "drivetrain_health": "OK"},
            clock,
        )

    await bus.inject(power(cfg.alerts.power_low_pct))
    assert not any(a.code == "POWER_LOW" for a in manager.views())
    clock.advance(1)
    await bus.inject(power(cfg.alerts.power_low_pct - 1))
    low = next(a for a in manager.views() if a.code == "POWER_LOW")
    assert low.severity == "WARNING" and low.active
    assert await manager.acknowledge_ground(low.alert_id)
    assert next(a for a in manager.views() if a.code == "POWER_LOW").acknowledged
    clock.advance(1)
    await bus.inject(power(cfg.alerts.power_low_pct))
    assert not any(a.code == "POWER_LOW" for a in manager.views())


@pytest.mark.asyncio
async def test_OI_011_vehicle_fault_ack_waits_for_completed_ack(harness, tmp_path):
    alerts, bus, clock, cfg = harness
    cfg = cfg.model_copy(
        update={"logging": cfg.logging.model_copy(update={"dir": str(tmp_path)})}
    )
    commands = CommandManager(
        bus,
        clock,
        cfg,
        alerts.log,
        alerts.status,
        alerts_for=alerts.views,
        ack_ground_alert=alerts.acknowledge_ground,
        on_fault_ack=alerts.acknowledge_vehicle,
    )
    await bus.inject(
        make(
            "payload.status",
            "vehicle.payload_controller",
            {
                "state": "EMPTY",
                "held_from": None,
                "secured": False,
                "locked": False,
                "mass_kg": None,
                "shift_cm": None,
                "release_energy_wh": None,
                "sensors": {"load_cell": "OK", "lock": "OK", "shift": "OK"},
                "prerelease_authorized": False,
                "departure_permitted": False,
                "departure_reason": "No mission",
                "mission_id": None,
            },
            clock,
        )
    )
    raised = fault(clock)
    await bus.inject(raised)
    result = await commands.handle(
        UiCommand(
            kind="command",
            client_req_id="ack-1",
            command="ack_fault",
            args={"alert_id": str(raised.body.fault_id)},
            confirmed=False,
        )
    )
    assert result.accepted
    command = bus.last("cmd.ack_fault")
    await bus.inject(make_ack(command, "vehicle.payload_controller", "RECEIVED", clock))
    assert not alerts.views()[0].acknowledged
    await bus.inject(
        make_ack(command, "vehicle.payload_controller", "COMPLETED", clock)
    )
    assert alerts.views()[0].acknowledged and alerts.views()[0].active
    commands.close()


@pytest.mark.asyncio
async def test_OI_010_fault_on_screen_within_2s_with_action(tmp_path):
    from aegis.run_all import build_system
    from tests.fakes import advance

    cfg = load_settings()
    cfg = cfg.model_copy(
        update={"logging": cfg.logging.model_copy(update={"dir": str(tmp_path)})}
    )
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, clock, cfg):
        logs[process] = FakeLog(process, run_id, clock, cfg)
        return logs[process]

    system = build_system(cfg, clock, "b11", make_log)
    await system.start()
    try:
        await advance(clock, 1)
        injected = clock.now()
        await system.ground.fault_injector.inject(
            "payload", "sensor", {"sensor": "lock", "health": "FAULT"}
        )
        for _ in range(20):
            await advance(clock, 0.1)
            alerts = system.ground.snapshot_builder.build().alerts
            if any(a.code == "LOCK_SENSOR_FAULT" for a in alerts):
                break
        alert = next(a for a in alerts if a.code == "LOCK_SENSOR_FAULT")
        assert (clock.now() - injected).total_seconds() <= 2
        assert alert.recommended_action
        reports = [
            r
            for r in logs["ground"].of("team1.received")
            if r["env"]["type"] == "t1.fault_report"
            and r["env"]["body"]["fault_id"] == alert.alert_id
        ]
        assert len(reports) == 1
    finally:
        await system.stop()
