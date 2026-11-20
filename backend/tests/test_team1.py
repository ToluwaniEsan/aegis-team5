from datetime import datetime

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.run_all import build_system
from aegis.standins.team1 import Team1Standin
from aegis.testing.fault_injector import FaultInjector
from tests.fakes import FAKE_START, FakeBus, FakeLog, advance


@pytest.fixture
async def team1():
    cfg = load_settings()
    clock = ManualClock(FAKE_START)
    log = FakeLog(clock=clock)
    bus = FakeBus("ground", clock, log)
    standin = Team1Standin(bus, clock, cfg, log)
    await standin.start()
    yield standin, bus, clock, cfg, log
    await standin.stop()


@pytest.mark.asyncio
async def test_OI_013_team1_logs_all_i9_reports_with_full_envelopes(team1):
    _, bus, clock, _, log = team1
    body_fault = {
        "fault_id": "de117211-9930-4fe2-9a6f-b6e96b75ead0",
        "code": "PAYLOAD_SHIFT",
        "severity": "WARNING",
        "source": "Payload",
        "message": "Payload shifted",
        "recommended_action": "Reduce speed and inspect the payload at the next stop",
        "holds_payload": False,
    }
    delivery = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": clock.now(),
        "position": {"lat": 34, "lon": -86},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    reports = [
        make(
            "t1.mission_report",
            "ground.command_manager",
            {"mission_id": "MSN-1", "payload_id": "PAY-1", "status": "ACTIVE"},
            clock,
            mission_id="MSN-1",
            payload_id="PAY-1",
        ),
        make(
            "t1.fault_report",
            "ground.alert_manager",
            body_fault,
            clock,
            mission_id="MSN-1",
            payload_id="PAY-1",
        ),
        make(
            "t1.delivery_confirmation",
            "ground.status_monitor",
            delivery,
            clock,
            mission_id="MSN-1",
            payload_id="PAY-1",
        ),
    ]
    for report in reports:
        await bus.publish(report)
    assert [r["env"] for r in log.of("team1.received")] == [
        report.model_dump(mode="json") for report in reports
    ]


@pytest.mark.asyncio
async def test_OI_013_team1_operational_mode_published_once_on_start(team1):
    standin, bus, clock, _, log = team1
    env = bus.last("t1.system_mode")
    assert env.src == "team1.integration" and env.dst == ["ground.status_monitor"]
    assert env.body.mode == "OPERATIONAL" and env.sent_at == clock.now()
    assert standin.current_mode == "OPERATIONAL"
    assert log.of("state.change")[0]["mode"] == "OPERATIONAL"
    await standin.start()
    assert len(bus.sent("t1.system_mode")) == 1


@pytest.mark.asyncio
async def test_GEN_001_team1_mode_injection_uses_real_injector(team1):
    standin, bus, clock, cfg, log = team1
    injector = FaultInjector(bus, clock, cfg, log)
    result = await injector.inject("team1", "mode", {"mode": "DEGRADED"})
    assert result.dst == "team1.integration"
    assert standin.current_mode == "DEGRADED"
    assert bus.last("t1.system_mode").body.mode == "DEGRADED"
    assert log.of("test.applied")[-1]["msg_id"] == result.msg_id
    assert log.of("test.inject")[-1]["env"]["msg_id"] == result.msg_id
    with pytest.raises(ValueError):
        await injector.inject("team1", "mode", {"mode": ""})
    assert standin.current_mode == "DEGRADED"


@pytest.mark.asyncio
async def test_GEN_001_team1_injection_rejected_when_test_mode_is_off(team1):
    standin, bus, clock, cfg, log = team1
    disabled = cfg.model_copy(update={"test_mode": False})
    injector = FaultInjector(bus, clock, disabled, log)
    with pytest.raises(ValueError, match="Test mode is off"):
        await injector.inject("team1", "mode", {"mode": "DEGRADED"})
    standin.cfg = disabled
    await bus.inject(
        make(
            "test.inject",
            "ground.fault_injector",
            {"target": "team1", "action": "mode", "params": {"mode": "DEGRADED"}},
            clock,
        )
    )
    assert standin.current_mode == "OPERATIONAL"
    assert len(bus.sent("t1.system_mode")) == 1


@pytest.mark.asyncio
async def test_AEG_508_delivery_confirmation_reaches_team1(tmp_path):
    cfg = load_settings()
    cfg = cfg.model_copy(
        update={"logging": cfg.logging.model_copy(update={"dir": str(tmp_path)})}
    )
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, clock, cfg):
        logs[process] = FakeLog(process, run_id, clock, cfg)
        return logs[process]

    system = build_system(cfg, clock, "team1-test", make_log)
    await system.start()
    try:
        await advance(clock, 1)
        assert (
            system.ground.status_monitor.latest["t1.system_mode"].body.mode
            == "OPERATIONAL"
        )
        origin, destination = (place.model_dump() for place in cfg.places[:2])
        mission = {
            "mission_id": "MSN-1",
            "payload_id": "PAY-1",
            "origin": origin,
            "destination": destination,
            "priority": "ROUTINE",
            "declared_mass_kg": 742,
            "dims_cm": {"length": 58, "width": 38, "height": 36},
            "prerelease_authorized": False,
        }
        await system.ground.bus.publish(
            make(
                "cmd.assign_mission",
                "ground.command_manager",
                mission,
                clock,
                mission_id="MSN-1",
                payload_id="PAY-1",
            )
        )
        await system.ground.bus.publish(
            make(
                "nav.assign",
                "ground.command_manager",
                {
                    key: mission[key]
                    for key in ("mission_id", "origin", "destination", "priority")
                },
                clock,
                mission_id="MSN-1",
                payload_id="PAY-1",
            )
        )
        await advance(clock, cfg.payload.load_time_s + cfg.payload.secure_time_s + 2)
        assert system.vehicle.controller.state.state == "SECURED"
        await system.vehicle.nav.depart()
        await advance(clock, 1)
        await system.vehicle.nav.arrive()
        await advance(clock, 1)
        assert system.vehicle.controller.state.state == "AT_DESTINATION"
        await system.ground.bus.publish(
            make(
                "cmd.release",
                "ground.command_manager",
                {},
                clock,
                mission_id="MSN-1",
                payload_id="PAY-1",
            )
        )
        await advance(clock, cfg.payload.release_time_s + 2)
        delivered = [
            r["env"]
            for r in logs["vehicle"].of("msg.sent")
            if r["env"]["type"] == "payload.delivered"
        ]
        assert len(delivered) == 1
        received = [
            r
            for r in logs["ground"].of("team1.received")
            if r["env"]["type"] == "t1.delivery_confirmation"
        ]
        assert len(received) == 1
        assert received[0]["env"]["body"] == delivered[0]["body"]
        assert received[0]["env"]["mission_id"] == "MSN-1"
        confirmed_at = datetime.fromisoformat(received[0]["t"].replace("Z", "+00:00"))
        released_at = datetime.fromisoformat(
            delivered[0]["body"]["released_at"].replace("Z", "+00:00")
        )
        assert (
            confirmed_at - released_at
        ).total_seconds() <= cfg.timing.delivery_confirm_max_s
        await system.ground.fault_injector.inject("team1", "mode", {"mode": "DEGRADED"})
        assert (
            system.ground.status_monitor.latest["t1.system_mode"].body.mode
            == "DEGRADED"
        )
    finally:
        await system.stop()


@pytest.mark.asyncio
async def test_OI_013_invalid_team1_message_is_logged_and_dropped(team1):
    _, bus, clock, _, log = team1
    valid = make(
        "t1.mission_report",
        "ground.command_manager",
        {
            "mission_id": "MSN-1",
            "payload_id": "PAY-1",
            "status": "ACTIVE",
        },
        clock,
    )
    invalid = valid.model_copy(
        update={"body": valid.body.model_copy(update={"status": "INVALID"})}
    )
    await bus.inject(invalid)
    assert len(log.of("bus.invalid")) == 1
    assert not log.of("team1.received")
