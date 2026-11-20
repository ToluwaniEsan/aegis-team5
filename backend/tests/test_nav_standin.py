"""Task B5: the Team 2 stand-in."""

import pytest

from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.standins.nav import NavStandin, distance_m
from tests.fakes import FakeBus, advance, settle

GC = "ground.command_manager"
PC = "vehicle.payload_controller"


def settings(**nav):
    cfg = load_settings()
    s = cfg.standins
    return cfg.model_copy(
        update={"standins": s.model_copy(update={"nav": s.nav.model_copy(update=nav)})}
    )


@pytest.fixture
def cfg():
    return settings()


@pytest.fixture
def bus():
    return FakeBus("vehicle")


@pytest.fixture
async def nav(bus, cfg):
    n = NavStandin(bus, bus.clock, cfg, bus.log)
    await n.start()
    await settle()
    yield n
    await n.stop()


def places(cfg):
    a, b = cfg.places[0], cfg.places[1]
    return a.model_dump(), b.model_dump()


async def assign(bus, cfg):
    origin, dest = places(cfg)
    env = make(
        "nav.assign",
        GC,
        {
            "mission_id": "MSN-2026-001",
            "origin": origin,
            "destination": dest,
            "priority": "ROUTINE",
        },
        bus.clock,
    )
    await bus.publish(env)
    await settle()
    return env


async def interlock(bus, permitted: bool):
    body = {
        "departure_permitted": permitted,
        "reason": None if permitted else "Payload is not secured",
    }
    await bus.publish(make("payload.interlock", PC, body, bus.clock))
    await settle()


async def command(bus, type_, body=None):
    env = make(type_, GC, body or {}, bus.clock)
    await bus.publish(env)
    await settle()
    return env


def state(bus):
    return bus.last("nav.state").body


def acks_for(bus, env):
    return [a.body.result for a in bus.sent("ack") if a.corr_id == env.msg_id]


def trip_s(cfg) -> float:
    a, b = cfg.places[0], cfg.places[1]
    speed = cfg.standins.nav.speed_mps * cfg.standins.time_scale
    return distance_m(a, b) / speed


async def test_assign_plans_route_and_acks(bus, nav, cfg):
    env = await assign(bus, cfg)
    assert acks_for(bus, env) == ["RECEIVED", "COMPLETED"]
    s = state(bus)
    assert len(s.route) == cfg.standins.nav.route_points
    assert s.at_origin and not s.moving and not s.at_destination
    assert s.progress_pct == 0.0
    assert s.eta_s == pytest.approx(trip_s(cfg))


async def test_AEG_511_standin_waits_for_interlock(bus, nav, cfg):
    await assign(bus, cfg)
    await nav.depart()  # asked to go, but the interlock is false
    await advance(bus.clock, 10.0, step=1.0)
    assert not state(bus).moving and state(bus).at_origin

    await interlock(bus, False)
    await advance(bus.clock, 5.0, step=1.0)
    assert not state(bus).moving

    await interlock(bus, True)  # the pending depart request now goes ahead
    assert state(bus).moving and not state(bus).at_origin


async def test_waits_for_depart_action_when_auto_depart_is_off(bus, nav, cfg):
    assert cfg.standins.nav.auto_depart is False
    await assign(bus, cfg)
    await interlock(bus, True)
    await advance(bus.clock, 5.0, step=1.0)
    assert not state(bus).moving
    await nav.depart()
    assert state(bus).moving


async def test_auto_depart_goes_as_soon_as_permitted():
    cfg = settings(auto_depart=True)
    bus = FakeBus("vehicle")
    nav = NavStandin(bus, bus.clock, cfg, bus.log)
    await nav.start()
    await assign(bus, cfg)
    await interlock(bus, True)
    assert state(bus).moving
    await nav.stop()


async def test_trip_arrives_at_destination_on_time(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    expected = trip_s(cfg)

    await advance(bus.clock, expected * 0.5, step=1.0)
    s = state(bus)
    assert s.moving and 30 < s.progress_pct < 70
    assert s.speed_mps == cfg.standins.nav.speed_mps * cfg.standins.time_scale

    await advance(bus.clock, expected * 0.5 + 2.0, step=1.0)
    s = state(bus)
    assert not s.moving and s.at_destination and not s.at_origin
    assert s.progress_pct == 100.0 and s.eta_s == 0.0
    dest = cfg.places[1]
    assert (s.position.lat, s.position.lon) == (dest.lat, dest.lon)


async def test_nav_state_at_1_hz_to_controller_and_status_monitor(bus, nav, cfg):
    bus.clear()
    await advance(bus.clock, 5.0, step=0.5)
    sent = bus.sent("nav.state")
    assert len(sent) == 5 * cfg.timing.status_rate_hz
    assert all(e.dst == [PC, "ground.status_monitor"] for e in sent)


async def test_abort_returns_to_origin(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await advance(bus.clock, trip_s(cfg) * 0.5, step=1.0)

    env = await command(bus, "cmd.abort")
    assert acks_for(bus, env) == ["RECEIVED", "COMPLETED"]
    assert state(bus).moving
    await advance(bus.clock, trip_s(cfg) * 0.5 + 2.0, step=1.0)
    s = state(bus)
    assert s.at_origin and not s.at_destination and not s.moving


async def test_return_to_origin_from_destination(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await nav.arrive()
    assert state(bus).at_destination
    await command(bus, "cmd.return_to_origin")
    await advance(bus.clock, trip_s(cfg) + 2.0, step=1.0)
    assert state(bus).at_origin


async def test_change_destination_replans_from_current_position(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await advance(bus.clock, 10.0, step=1.0)
    here = state(bus).position
    new = cfg.places[2].model_dump()
    env = await command(bus, "cmd.change_destination", {"destination": new})
    assert acks_for(bus, env) == ["RECEIVED", "COMPLETED"]
    s = state(bus)
    assert s.route[0] == here
    assert (s.route[-1].lat, s.route[-1].lon) == (new["lat"], new["lon"])
    assert s.moving


async def test_estop_stops_at_once_and_stays_stopped_D_06(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await advance(bus.clock, 10.0, step=1.0)
    env = await command(bus, "cmd.estop", {"reason": "test", "source": "OPERATOR"})
    assert acks_for(bus, env) == ["RECEIVED", "COMPLETED"]
    assert not state(bus).moving
    stopped_at = state(bus).position
    await advance(bus.clock, 30.0, step=1.0)
    assert not state(bus).moving and state(bus).position == stopped_at
    # A new command moves it again.
    await command(bus, "cmd.return_to_origin")
    assert state(bus).moving


async def test_block_route_sends_new_route_and_longer_eta(bus, nav, cfg):
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await advance(bus.clock, 10.0, step=1.0)
    eta_before = state(bus).eta_s
    await nav.block_route("Bridge out")
    blocked = bus.last("nav.route_blocked").body
    assert blocked.reason == "Bridge out"
    assert blocked.new_eta_s > eta_before
    assert blocked.new_route == state(bus).route
    # It carries on and still arrives.
    await advance(bus.clock, blocked.new_eta_s + 2.0, step=1.0)
    assert state(bus).at_destination


async def test_health_and_halt_hooks(bus, nav, cfg):
    await nav.set_health("FAULT")
    assert state(bus).health == "FAULT"
    await assign(bus, cfg)
    await interlock(bus, True)
    await nav.depart()
    await nav.halt()
    assert not state(bus).moving
