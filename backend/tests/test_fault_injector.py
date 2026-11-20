"""Task B14: the Fault Injector, with the vehicle test agent, in single-process mode."""

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.common.models import INJECT_ACTIONS
from aegis.run_all import build_system
from aegis.testing.fault_injector import FaultInjector
from tests.fakes import FAKE_START, FakeBus, FakeLog, advance
from tests.test_envelope import INJECT_PARAMS

GC = "ground.command_manager"


class System:
    def __init__(self):
        self.cfg = load_settings()
        self.clock = ManualClock(FAKE_START)
        self.logs = {}
        self.sys = build_system(self.cfg, self.clock, "run-inject", self._log)
        self.injector = self.sys.ground.fault_injector
        self.vehicle = self.sys.vehicle

    def _log(self, process, run_id, clock, cfg):
        self.logs[process] = FakeLog(process, run_id, clock, cfg)
        return self.logs[process]

    def applied(self, target, action):
        return [
            r
            for r in self.logs["vehicle"].of("test.applied")
            if (r["target"], r["action"]) == (target, action)
        ]


@pytest.fixture
async def s():
    system = System()
    await system.sys.start()
    await advance(system.clock, 1.0)
    yield system
    await system.sys.stop()


# Rows whose effect can be read straight off the component they target.
EFFECTS = {
    ("payload", "shift"): lambda v: v.simulator.shift_cm == 3.1,
    ("payload", "sensor"): lambda v: v.simulator.sensors["lock"] == "FAULT",
    ("payload", "mass_override"): lambda v: v.simulator.mass_override_kg == 1180,
    ("payload", "release_jam"): lambda v: v.simulator.release_jam is True,
    ("payload", "controller_crash"): lambda v: not v.controller.running,
    ("nav", "health"): lambda v: v.nav.health == "FAULT",
    ("power", "battery"): lambda v: v.power.battery_pct == 15,
    ("power", "drivetrain"): lambda v: v.power.drivetrain_health == "FAULT",
}


async def test_GEN_001_every_fault_triggerable_without_code_change(s):
    rows = sorted(INJECT_ACTIONS, key=lambda r: r == ("payload", "controller_crash"))
    for target, action in rows:  # the controller crash last
        result = await s.injector.inject(
            target, action, INJECT_PARAMS[(target, action)]
        )
        await advance(s.clock, 0.5)

        # The ground logs every injection as test.inject (section 10).
        logged = [r["env"]["msg_id"] for r in s.logs["ground"].of("test.inject")]
        assert result.msg_id in logged

        if target == "link":
            assert result.dst == "team3.link"
            assert result.msg_id in [
                r["env"]["msg_id"] for r in s.logs["link"].of("test.inject")
            ]
        elif target == "team1":
            # Handled on the ground by the Team 1 stand-in (Emmanuel's B7).
            assert result.dst == "team1.integration"
        else:
            assert result.dst == "vehicle.test_agent"
            assert s.applied(target, action), f"{target}/{action} not applied"
            check = EFFECTS.get((target, action))
            if check:
                assert check(s.vehicle), f"{target}/{action} had no effect"

    # The link rows changed the link.
    link = s.sys.link
    assert (link.latency_ms, link.loss_pct) == (1500, 12)
    assert s.logs["link"].of("link.outage")
    assert s.logs["vehicle"].of("test.error") == []


async def test_injection_crosses_the_link_even_during_an_outage(s):
    await s.injector.inject("link", "outage", {"seconds": 60})
    await s.injector.inject("power", "battery", {"pct": 30})
    await advance(s.clock, 0.5)
    assert s.applied("power", "battery")


async def test_day_7_departure_from_the_ground(s):
    """Assign from the ground, then depart through the injector, as the
    screen's test panel will."""
    origin, dest = s.cfg.places[0].model_dump(), s.cfg.places[1].model_dump()
    for type_, body in [
        (
            "cmd.assign_mission",
            {
                "mission_id": "MSN-2026-001",
                "payload_id": "PAY-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
                "declared_mass_kg": 742.0,
                "dims_cm": {"length": 60, "width": 40, "height": 40},
                "prerelease_authorized": False,
            },
        ),
        (
            "nav.assign",
            {
                "mission_id": "MSN-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
            },
        ),
    ]:
        await s.sys.ground.bus.publish(make(type_, GC, body, s.clock))
    p = s.cfg.payload
    await advance(s.clock, p.load_time_s + p.secure_time_s + 1.5)
    assert s.vehicle.controller.state.state == "SECURED"

    await s.injector.inject("nav", "depart", {})
    await advance(s.clock, 2.0)
    assert s.vehicle.nav.moving
    assert s.vehicle.controller.state.state == "TRAVELLING"


@pytest.mark.parametrize(
    "target, action, params, message",
    [
        ("payload", "explode", {}, "unknown action 'explode' for target 'payload'"),
        ("payload", "shift", {}, "cm"),
        ("payload", "shift", {"cm": -2}, "cm"),
        ("link", "outage", {"seconds": 0}, "seconds"),
        ("power", "battery", {"pct": 120}, "pct"),
        ("nav", "health", {"health": "GREAT"}, "health"),
        ("rover", "depart", {}, "target"),
    ],
)
async def test_bad_params_raise_value_error_with_reason(
    target, action, params, message
):
    bus = FakeBus("ground")
    injector = FaultInjector(bus, bus.clock, load_settings(), bus.log)
    with pytest.raises(ValueError, match=message):
        await injector.inject(target, action, params)
    assert bus.published == []  # nothing sent
    assert bus.log.of("test.inject") == []


async def test_refused_when_test_mode_is_off():
    cfg = load_settings().model_copy(update={"test_mode": False})
    bus = FakeBus("ground")
    injector = FaultInjector(bus, bus.clock, cfg, bus.log)
    with pytest.raises(ValueError, match="Test mode is off"):
        await injector.inject("power", "battery", {"pct": 50})
    assert bus.published == []
