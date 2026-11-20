"""Task B1: LocalBus and endpoint sides."""

import pytest

from aegis.bus.endpoints import SIDES, side_of
from aegis.bus.local_bus import LocalBus
from aegis.common.clock import ManualClock
from aegis.common.envelope import make
from aegis.common.models import ENDPOINTS
from tests.fakes import FAKE_START, FakeLog

FAULT = {
    "fault_id": "6f1c2a9e-1d3b-4c55-9a51-2f2a0f3b7c11",
    "code": "PAYLOAD_SHIFT",
    "severity": "WARNING",
    "source": "Payload",
    "message": "Payload shifted 3.1 cm",
    "recommended_action": "Reduce speed and inspect the payload at the next stop",
    "holds_payload": False,
}
NAV_STATE = {
    "moving": False,
    "speed_mps": 0.0,
    "position": {"lat": 34.72, "lon": -86.64},
    "at_destination": False,
    "at_origin": True,
    "eta_s": None,
    "progress_pct": 0.0,
    "route": [],
    "health": "OK",
}


class FakeLink:
    def __init__(self):
        self.sent = []

    async def send(self, env):
        self.sent.append(env)


@pytest.fixture
def clock():
    return ManualClock(FAKE_START)


@pytest.fixture
def log(clock):
    return FakeLog(process="vehicle", clock=clock)


@pytest.fixture
def bus(clock, log):
    return LocalBus("vehicle", clock, log)


def _collector(into: list):
    async def handler(env):
        into.append(env)

    return handler


def test_every_endpoint_has_a_side():
    assert set(SIDES) == set(ENDPOINTS)
    assert side_of("team2.nav") == "vehicle"
    assert side_of("team1.integration") == "ground"
    assert side_of("team3.link") == "link"
    with pytest.raises(ValueError):
        side_of("team9.nobody")


@pytest.mark.asyncio
async def test_local_delivery_to_every_local_dst(bus, clock, log):
    pc, link_watch = [], []
    bus.subscribe("vehicle.payload_controller", _collector(pc))
    bus.subscribe("vehicle.link_watch", _collector(link_watch))
    link = FakeLink()
    bus.attach_link(link)

    env = make(
        "nav.state", "team2.nav", NAV_STATE, clock
    )  # dst: controller + status monitor
    await bus.publish(env)

    assert pc == [env]
    assert link_watch == []
    assert link.sent == [env]  # ground.status_monitor is across the link
    assert log.types("msg.sent") == ["nav.state"]
    assert log.of("msg.recv") == []


@pytest.mark.asyncio
async def test_same_side_message_never_touches_the_link(bus, clock):
    link = FakeLink()
    bus.attach_link(link)
    got = []
    bus.subscribe("vehicle.payload_simulator", _collector(got))
    await bus.publish(
        make("sim.command", "vehicle.payload_controller", {"action": "LOCK"}, clock)
    )
    assert len(got) == 1
    assert link.sent == []


@pytest.mark.asyncio
async def test_type_filter(bus, clock):
    got = []
    bus.subscribe("vehicle.payload_controller", _collector(got), types={"power.status"})
    await bus.publish(make("nav.state", "team2.nav", NAV_STATE, clock))
    await bus.publish(
        make(
            "power.status",
            "team4.power",
            {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"},
            clock,
        )
    )
    assert [e.type for e in got] == ["power.status"]


@pytest.mark.asyncio
async def test_subscribe_to_other_side_endpoint_fails(bus):
    with pytest.raises(ValueError):
        bus.subscribe("ground.status_monitor", _collector([]))


@pytest.mark.asyncio
async def test_outbound_filter_can_hold_or_replace(bus, clock):
    link = FakeLink()
    bus.attach_link(link)
    held = []

    async def hold_faults(env):
        if env.type == "fault.raised":
            held.append(env)
            return None
        return env.model_copy(update={"buffered": True})

    bus.add_outbound_filter(hold_faults)
    await bus.publish(make("fault.raised", "vehicle.payload_controller", FAULT, clock))
    await bus.publish(make("nav.state", "team2.nav", NAV_STATE, clock))

    assert [e.type for e in held] == ["fault.raised"]
    assert [e.type for e in link.sent] == ["nav.state"]
    assert link.sent[0].buffered is True


@pytest.mark.asyncio
async def test_no_link_attached_logs_a_drop(bus, clock, log):
    env = make("fault.raised", "vehicle.payload_controller", FAULT, clock)
    await bus.publish(env)
    [drop] = log.of("link.drop")
    assert drop["msg_id"] == str(env.msg_id)


@pytest.mark.asyncio
async def test_deliver_from_link_logs_recv_and_delivers_locally_only(bus, clock, log):
    link = FakeLink()
    bus.attach_link(link)
    pc, nav = [], []
    bus.subscribe("vehicle.payload_controller", _collector(pc))
    bus.subscribe("team2.nav", _collector(nav))

    env = make("cmd.abort", "ground.command_manager", {}, clock)
    await bus.deliver_from_link(env)

    assert pc == [env] and nav == [env]
    assert link.sent == []  # never sent back out
    assert log.types("msg.recv") == ["cmd.abort"]
    assert log.of("msg.sent") == []


@pytest.mark.asyncio
async def test_handler_error_is_logged_and_others_still_run(bus, clock, log):
    got = []

    async def broken(env):
        raise RuntimeError("boom")

    bus.subscribe("vehicle.payload_controller", broken)
    bus.subscribe("vehicle.payload_controller", _collector(got))
    await bus.publish(make("nav.state", "team2.nav", NAV_STATE, clock))

    assert len(got) == 1
    [err] = log.of("bus.handler_error")
    assert "boom" in err["error"]
    assert err["type"] == "nav.state"


@pytest.mark.asyncio
async def test_log_records_carry_the_whole_envelope(bus, clock, log):
    env = make("nav.state", "team2.nav", NAV_STATE, clock)
    await bus.publish(env)
    [rec] = log.of("msg.sent")
    assert rec["env"]["msg_id"] == str(env.msg_id)
    assert rec["env"]["sent_at"] == "2026-11-19T12:00:00.000Z"
    assert rec["env"]["body"]["position"] == NAV_STATE["position"]
