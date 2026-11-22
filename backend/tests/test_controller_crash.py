"""Task A9: the controller crash hook (GEN-004), in single-process mode."""

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.run_all import build_system
from tests.fakes import FAKE_START, FakeLog, advance

GC = "ground.command_manager"


async def test_GEN_004_controller_crash_leaves_payload_secured():
    cfg = load_settings()
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, c, s):
        logs[process] = FakeLog(process, run_id, c, s)
        return logs[process]

    system = build_system(cfg, clock, "run-crash", make_log)
    await system.start()
    await advance(clock, 1.0)
    origin, dest = cfg.places[0].model_dump(), cfg.places[1].model_dump()
    await system.ground.bus.publish(
        make(
            "cmd.assign_mission",
            GC,
            {
                "mission_id": "MSN-2026-001",
                "payload_id": "PAY-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
                "declared_mass_kg": 742.0,
                "dims_cm": {"length": 60, "width": 40, "height": 40},
                "prerelease_authorized": True,
            },
            clock,
        )
    )
    p = cfg.payload
    await advance(clock, p.load_time_s + p.secure_time_s + 1.5)
    v = system.vehicle
    assert v.controller.state.state == "SECURED" and v.simulator.locked

    # The crash, triggered from the test interface like any other fault.
    await system.ground.fault_injector.inject("payload", "controller_crash", {})
    await advance(clock, 1.0)
    assert not v.controller.running
    applied = [r["action"] for r in logs["vehicle"].of("test.applied")]
    assert "controller_crash" in applied

    # Nothing can open the lock now: release and abort go unanswered, and an
    # outage plus the pre-release wait does not release either.
    sim_commands_before = len(
        [r for r in logs["vehicle"].of("msg.sent") if r["env"]["type"] == "sim.command"]
    )
    for type_ in ("cmd.release", "cmd.abort"):
        await system.ground.bus.publish(make(type_, GC, {}, clock))
    await system.link.outage(cfg.link.lost_after_s + cfg.link.prerelease_wait_s + 30)
    await advance(clock, 600.0, step=1.0)  # ten minutes

    assert v.simulator.locked
    assert v.simulator.bay_mass_kg == 742.0
    sim_commands = [
        r for r in logs["vehicle"].of("msg.sent") if r["env"]["type"] == "sim.command"
    ]
    assert len(sim_commands) == sim_commands_before  # no RELEASE, no UNLOAD, no UNLOCK
    controller_acks = [
        r
        for r in logs["vehicle"].of("msg.sent")
        if r["env"]["type"] == "ack"
        and r["env"]["src"] == "vehicle.payload_controller"
        and r["t"] > logs["vehicle"].of("test.applied")[-1]["t"]
    ]
    assert controller_acks == []  # the ground sees no answer and times out (OI-009)

    # The simulator is still alive and keeps reporting the lock closed.
    last = [
        r for r in logs["vehicle"].of("msg.sent") if r["env"]["type"] == "sim.reading"
    ][-1]
    assert last["env"]["body"]["locked"] is True
    assert last["t"] > logs["vehicle"].of("test.applied")[-1]["t"]
    await system.stop()
