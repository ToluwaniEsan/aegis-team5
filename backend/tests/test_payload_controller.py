"""Task A4: the Payload Controller shell, with the simulator and the Team 2
stand-in (B5) on one bus and a ManualClock."""

import pytest

from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.standins.nav import NavStandin, distance_m
from aegis.vehicle.payload_controller import PayloadController
from aegis.vehicle.simulator import PayloadSimulator
from tests.fakes import FakeBus, advance, settle

GC = "ground.command_manager"


class Vehicle:
    def __init__(self):
        self.cfg = load_settings()
        self.bus = FakeBus("vehicle")
        self.clock = self.bus.clock
        log = self.bus.log
        self.sim = PayloadSimulator(self.bus, self.clock, self.cfg, log)
        self.nav = NavStandin(self.bus, self.clock, self.cfg, log)
        self.ctrl = PayloadController(self.bus, self.clock, self.cfg, log)

    async def start(self):
        for part in (self.sim, self.nav, self.ctrl):
            await part.start()
        await settle()

    async def stop(self):
        for part in (self.ctrl, self.nav, self.sim):
            await part.stop()

    async def send(self, type_, body=None):
        env = make(type_, GC, body or {}, self.clock, mission_id="MSN-2026-001")
        await self.bus.publish(env)
        await settle()
        await self.ctrl.drain()
        await settle()
        return env

    async def wait(self, seconds, step=0.5):
        await advance(self.clock, seconds, step)
        await self.ctrl.drain()
        await settle()

    def status(self):
        return self.bus.last("payload.status").body

    def results(self, env):
        return [
            a.body.result
            for a in self.bus.sent("ack")
            if a.corr_id == env.msg_id and a.src == "vehicle.payload_controller"
        ]

    def trip_s(self):
        a, b = self.cfg.places[0], self.cfg.places[1]
        speed = self.cfg.standins.nav.speed_mps * self.cfg.standins.time_scale
        return distance_m(a, b) / speed

    async def assign(self, mass=742.0, prerelease=False):
        origin, dest = self.cfg.places[0].model_dump(), self.cfg.places[1].model_dump()
        env = await self.send(
            "cmd.assign_mission",
            {
                "mission_id": "MSN-2026-001",
                "payload_id": "PAY-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
                "declared_mass_kg": mass,
                "dims_cm": {"length": 60, "width": 40, "height": 40},
                "prerelease_authorized": prerelease,
            },
        )
        await self.send(
            "nav.assign",
            {
                "mission_id": "MSN-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
            },
        )
        return env


@pytest.fixture
async def v():
    vehicle = Vehicle()
    await vehicle.start()
    yield vehicle
    await vehicle.stop()


async def test_happy_path_empty_to_delivered(v):
    """A4 and B5 Done-when: a full trip with the simulator and the Team 2 stand-in."""
    p = v.cfg.payload
    assert v.status().state == "EMPTY"

    assign = await v.assign()
    assert v.status().state == "LOADED"
    assert v.results(assign) == ["RECEIVED"]

    await v.wait(p.load_time_s + p.secure_time_s + 1.0)
    assert v.status().state == "SECURED"
    assert v.status().secured and v.status().locked
    assert v.results(assign) == ["RECEIVED", "COMPLETED"]
    assert v.bus.last("payload.interlock").body.departure_permitted is True
    assert v.bus.sent("payload.mass_report")  # AEG-512, to Team 4
    assert v.bus.last("payload.mass_report").dst == ["team4.power"]

    await v.nav.depart()
    await v.wait(1.0)
    assert v.status().state == "TRAVELLING"

    await v.wait(v.trip_s() + 2.0, step=1.0)
    assert v.status().state == "AT_DESTINATION"

    release = await v.send("cmd.release")
    assert v.status().state == "RELEASED"
    await v.wait(p.release_time_s + 1.0)
    assert v.status().state == "DELIVERED"
    assert v.results(release) == ["RECEIVED", "COMPLETED"]
    assert v.status().release_energy_wh == p.release_energy_wh_nominal

    # Every state change is in the log (OI-013).
    changes = [r["state"] for r in v.bus.log.of("state.change")]
    assert changes == [
        "LOADED",
        "SECURED",
        "TRAVELLING",
        "AT_DESTINATION",
        "RELEASED",
        "DELIVERED",
    ]


async def test_AEG_508_delivered_sent_within_10_s_of_release(v):
    await v.assign()
    await v.wait(v.cfg.payload.load_time_s + v.cfg.payload.secure_time_s + 1.0)
    await v.nav.depart()
    await v.wait(1.0)
    await v.nav.arrive()
    await v.wait(1.0)
    release = await v.send("cmd.release")
    await v.wait(12.0)
    delivered = v.bus.last("payload.delivered")
    latency = (delivered.sent_at - release.sent_at).total_seconds()
    assert latency <= v.cfg.timing.delivery_confirm_max_s
    assert delivered.payload_id == "PAY-2026-001"  # AEG-510
    assert len(v.bus.sent("payload.delivered")) == 1


async def test_AEG_505_status_at_1_hz_and_on_change(v):
    v.bus.clear()
    await v.wait(5.0)
    statuses = v.bus.sent("payload.status")
    assert 5 <= len(statuses) <= 6
    assert all(e.dst == ["ground.status_monitor"] for e in statuses)
    interlocks = v.bus.sent("payload.interlock")
    assert 5 <= len(interlocks) <= 6
    assert all(e.dst == ["team2.nav"] for e in interlocks)

    v.bus.clear()
    await v.assign()  # a change sends status at once, not at the next tick
    assert v.bus.sent("payload.status")[-1].body.state == "LOADED"


async def test_rejection_reaches_the_ground_with_a_reason(v):
    release = await v.send("cmd.release")
    [rej] = [
        a
        for a in v.bus.sent("ack")
        if a.corr_id == release.msg_id and a.body.result == "REJECTED"
    ]
    assert rej.body.reason_code == "NOT_AT_DESTINATION"
    assert rej.body.reason == "Not at the destination"
    assert rej.dst == ["ground.command_manager"]


async def test_vehicle_waits_while_interlock_false(v):
    await v.assign()
    await v.nav.depart()  # asked to leave before the payload is secured
    await v.wait(1.0)
    assert v.status().state == "LOADED"
    assert not v.bus.last("nav.state").body.moving
    # Once secured, the waiting depart request goes ahead (AEG-511).
    await v.wait(v.cfg.payload.load_time_s + v.cfg.payload.secure_time_s + 1.0)
    assert v.status().state == "TRAVELLING"


async def test_crashed_controller_leaves_payload_locked(v):
    await v.assign()
    await v.wait(v.cfg.payload.load_time_s + v.cfg.payload.secure_time_s + 1.0)
    assert v.sim.locked
    await v.ctrl.stop()  # the A9 crash hook does exactly this
    assert not v.ctrl.running
    await v.wait(600.0, step=10.0)
    assert v.sim.locked and v.sim.bay_mass_kg == 742.0


async def test_unload_hook(v):
    await v.ctrl.unload()  # nothing to unload: refused and logged, no crash
    await v.ctrl.drain()
    assert v.bus.log.of("unload.refused")
