"""Task A7: the Event Buffer."""

import uuid

import pytest

from aegis.bus.local_bus import LocalBus
from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.common.models import FAULT_CATALOG
from aegis.run_all import build_system
from aegis.vehicle.event_buffer import EventBuffer
from tests.fakes import FAKE_START, FakeLog, advance, settle

PC = "vehicle.payload_controller"
SENSORS = {"load_cell": "OK", "lock": "OK", "shift": "OK"}


def settings(tmp_path, **event_buffer):
    cfg = load_settings()
    eb = cfg.event_buffer.model_copy(
        update={"file": str(tmp_path / "event_buffer.jsonl")} | event_buffer
    )
    return cfg.model_copy(update={"event_buffer": eb})


class Link:
    def __init__(self):
        self.sent = []

    async def send(self, env):
        self.sent.append(env)

    def batches(self):
        return [e for e in self.sent if e.type == "backlog.batch"]

    def replayed(self):
        return [ev for b in self.batches() for ev in b.body.events]


class Rig:
    def __init__(self, cfg, clock=None):
        self.cfg = cfg
        self.clock = clock or ManualClock(FAKE_START)
        self.log = FakeLog("vehicle", clock=self.clock)
        self.bus = LocalBus("vehicle", self.clock, self.log)
        self.link = Link()
        self.bus.attach_link(self.link)
        self.buffer = EventBuffer(self.bus, self.clock, cfg, self.log)

    async def start(self):
        await self.buffer.start()

    async def link_state(self, state):
        body = {"state": state, "since": self.clock.now()}
        await self.bus.publish(
            make("int.link_state", "vehicle.link_watch", body, self.clock)
        )
        await settle()

    async def send(self, type_, body):
        env = make(type_, PC, body, self.clock)
        await self.bus.publish(env)
        return env

    async def fault(self, code="PAYLOAD_SHIFT"):
        spec = FAULT_CATALOG[code]
        return await self.send(
            "fault.raised",
            {
                "fault_id": str(uuid.uuid4()),
                "code": code,
                "severity": spec.severity,
                "source": "Payload",
                "message": code,
                "recommended_action": spec.recommended_action,
                "holds_payload": spec.holds_payload,
            },
        )

    async def status(self, state="SECURED"):
        return await self.send(
            "payload.status",
            {
                "state": state,
                "held_from": None,
                "secured": False,
                "locked": True,
                "mass_kg": 742.0,
                "shift_cm": 0.0,
                "release_energy_wh": None,
                "sensors": SENSORS,
                "prerelease_authorized": False,
                "departure_permitted": False,
                "departure_reason": "Payload is not secured",
                "mission_id": "MSN-2026-001",
            },
        )

    async def delivered(self):
        return await self.send(
            "payload.delivered",
            {
                "mission_id": "MSN-2026-001",
                "payload_id": "PAY-2026-001",
                "released_at": self.clock.now(),
                "position": {"lat": 34.76, "lon": -86.58},
                "mass_kg": 742.0,
                "energy_used_wh": 3.2,
            },
        )


@pytest.fixture
async def rig(tmp_path):
    r = Rig(settings(tmp_path, batch_size=2))
    await r.start()
    return r


async def test_event_buffer_preserves_order(rig):
    await rig.link_state("LOST")
    held = []
    for _ in range(2):
        held.append(await rig.fault())
        rig.clock.advance(1.0)
    held.append(await rig.delivered())
    held.append(await rig.fault("CLOCK_SKEW"))
    held.append(await rig.fault())
    assert rig.link.sent == []  # nothing goes out while LOST

    await rig.link_state("RESTORED")
    batches = rig.link.batches()
    assert [len(b.body.events) for b in batches] == [2, 2, 1]  # batch_size = 2
    replayed = rig.link.replayed()
    assert [e.msg_id for e in replayed] == [e.msg_id for e in held]
    assert all(e.buffered for e in replayed)
    assert [e.sent_at for e in replayed] == [e.sent_at for e in held]  # original times

    # Live sending resumes after the backlog.
    live = await rig.fault()
    assert rig.link.sent[-1] == live and live.buffered is False
    assert not rig.buffer.path.exists()


async def test_status_keeps_only_the_newest(rig):
    await rig.link_state("LOST")
    for _ in range(5):
        await rig.status()
    newest = await rig.status()
    f = await rig.fault()
    await rig.link_state("RESTORED")
    replayed = rig.link.replayed()
    assert [e.msg_id for e in replayed] == [newest.msg_id, f.msg_id]


async def test_first_seconds_of_an_outage_go_to_the_front(rig):
    old = await rig.fault()
    rig.clock.advance(rig.cfg.link.lost_after_s + 5)  # outside the window
    early = await rig.fault()  # sent while the link was failing, not yet LOST
    await rig.status()  # status is never kept in the window
    rig.clock.advance(rig.cfg.link.lost_after_s - 1)
    await rig.link_state("LOST")
    later = await rig.fault()
    await rig.link_state("RESTORED")
    ids = [e.msg_id for e in rig.link.replayed()]
    assert ids == [early.msg_id, later.msg_id]
    assert old.msg_id not in ids


async def test_cap_drops_status_then_caution_faults_and_logs_it(tmp_path):
    rig = Rig(settings(tmp_path, max_events=3, batch_size=1))
    await rig.start()
    await rig.link_state("LOST")
    status = await rig.status()
    caution = await rig.fault("CLOCK_SKEW")
    warning = await rig.fault("PAYLOAD_SHIFT")
    d1 = await rig.delivered()  # 4 > 3: the status goes
    d2 = await rig.delivered()  # then the CAUTION fault
    dropped = [r["msg_id"] for r in rig.log.of("buffer.drop")]
    assert dropped == [str(status.msg_id), str(caution.msg_id)]
    await rig.link_state("RESTORED")
    assert [e.msg_id for e in rig.link.replayed()] == [
        warning.msg_id,
        d1.msg_id,
        d2.msg_id,
    ]


async def test_event_buffer_survives_vehicle_restart(tmp_path):
    cfg = settings(tmp_path)
    first = Rig(cfg)
    await first.start()
    await first.link_state("LOST")
    a = await first.fault()
    b = await first.delivered()
    await first.buffer.stop()  # the vehicle process dies here
    assert first.buffer.path.exists()

    second = Rig(cfg, clock=first.clock)  # a new process, same file
    await second.start()
    assert second.buffer.link_lost  # holds until the link is known to be up
    c = await second.fault()
    assert second.link.sent == []
    await second.link_state("RESTORED")  # the first heartbeat after start-up
    assert [e.msg_id for e in second.link.replayed()] == [a.msg_id, b.msg_id, c.msg_id]
    assert second.log.of("buffer.restored_from_disk")[0]["events"] == 2


async def test_OI_013_delivery_during_outage_reaches_ground_after_restore(tmp_path):
    """AEG-508 during an outage: a pre-authorized release happens with the link
    down, and the ground gets payload.delivered with the original released_at
    once the link returns."""
    cfg = settings(tmp_path)
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, c, s):
        logs[process] = FakeLog(process, run_id, c, s)
        return logs[process]

    system = build_system(cfg, clock, "run-outage", make_log)
    await system.start()
    await advance(clock, 1.0)
    origin, dest = cfg.places[0].model_dump(), cfg.places[1].model_dump()
    gc = "ground.command_manager"
    await system.ground.bus.publish(
        make(
            "cmd.assign_mission",
            gc,
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
    await system.ground.bus.publish(
        make(
            "nav.assign",
            gc,
            {
                "mission_id": "MSN-2026-001",
                "origin": origin,
                "destination": dest,
                "priority": "ROUTINE",
            },
            clock,
        )
    )
    p = cfg.payload
    await advance(clock, p.load_time_s + p.secure_time_s + 1.5)
    v = system.vehicle
    await v.nav.depart()
    await advance(clock, 1.0)
    await v.nav.arrive()
    await advance(clock, 1.0)
    assert v.controller.state.state == "AT_DESTINATION"

    outage = cfg.link.lost_after_s + cfg.link.prerelease_wait_s + p.release_time_s + 20
    await system.link.outage(outage)
    await advance(clock, outage - 5, step=0.5)
    assert v.controller.state.state == "DELIVERED"  # released on its own, link down
    [vehicle_sent] = [
        r["env"]
        for r in logs["vehicle"].of("msg.sent")
        if r["env"]["type"] == "payload.delivered"
    ]

    def ground_delivered():
        return [
            e
            for r in logs["ground"].of("msg.recv")
            if r["env"]["type"] == "backlog.batch"
            for e in r["env"]["body"]["events"]
            if e["type"] == "payload.delivered"
        ]

    assert ground_delivered() == []  # not yet: still in the outage
    await advance(clock, 10.0, step=0.5)  # the link returns, heartbeats resume
    [got] = ground_delivered()
    assert got["msg_id"] == vehicle_sent["msg_id"]
    assert got["body"]["released_at"] == vehicle_sent["body"]["released_at"]
    assert got["buffered"] is True
    await system.stop()
