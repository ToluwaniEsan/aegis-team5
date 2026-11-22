"""The vehicle process wired up: a whole mission from the ground side, through
the link stand-in, in single-process mode on a ManualClock."""

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.run_all import build_system
from aegis.standins.nav import distance_m
from tests.fakes import FAKE_START, FakeLog, advance

GC = "ground.command_manager"


async def test_happy_path_from_the_ground_through_the_link():
    cfg = load_settings()
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, clock_, cfg_):
        logs[process] = FakeLog(process, run_id, clock_, cfg_)
        return logs[process]

    system = build_system(cfg, clock, "run-mission", make_log)
    ground, vehicle = system.ground, system.vehicle
    await system.start()
    await advance(clock, 2.0)

    async def send(type_, body):
        env = make(
            type_, GC, body, clock, mission_id="MSN-2026-001", payload_id="PAY-2026-001"
        )
        await ground.bus.publish(env)
        await advance(clock, 1.0)
        return env

    def ground_received(type_):
        return [
            r["env"] for r in logs["ground"].of("msg.recv") if r["env"]["type"] == type_
        ]

    def last_status():
        return ground_received("payload.status")[-1]["body"]

    origin, dest = cfg.places[0].model_dump(), cfg.places[1].model_dump()
    assign = await send(
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
    )
    await send(
        "nav.assign",
        {
            "mission_id": "MSN-2026-001",
            "origin": origin,
            "destination": dest,
            "priority": "ROUTINE",
        },
    )
    p = cfg.payload
    await advance(clock, p.load_time_s + p.secure_time_s + 1.0)
    assert last_status()["state"] == "SECURED"
    acks = [
        a["body"]["result"]
        for a in ground_received("ack")
        if a["corr_id"] == str(assign.msg_id)
    ]
    assert acks == ["RECEIVED", "COMPLETED"]

    # The ground sees Team 2 and Team 4 data over the link.
    assert ground_received("nav.state") and ground_received("power.status")

    await vehicle.nav.depart()
    speed = cfg.standins.nav.speed_mps * cfg.standins.time_scale
    trip_s = distance_m(cfg.places[0], cfg.places[1]) / speed
    await advance(clock, trip_s + 3.0, step=0.5)
    assert last_status()["state"] == "AT_DESTINATION"

    release = await send("cmd.release", {})
    await advance(clock, p.release_time_s + 2.0)
    assert last_status()["state"] == "DELIVERED"
    [delivered] = ground_received("payload.delivered")
    assert delivered["payload_id"] == "PAY-2026-001"
    acks = [
        a["body"]["result"]
        for a in ground_received("ack")
        if a["corr_id"] == str(release.msg_id)
    ]
    assert acks == ["RECEIVED", "COMPLETED"]

    # Heartbeats kept flowing, so the vehicle never saw the link as lost.
    states = [
        r["env"]["body"]["state"]
        for r in logs["vehicle"].of("msg.sent")
        if r["env"]["type"] == "int.link_state"
    ]
    assert states == ["RESTORED"]  # the first heartbeat only; never LOST
    await system.stop()
