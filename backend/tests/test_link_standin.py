"""Task B3: the Team 3 link stand-in."""

import asyncio
import itertools
import json
import random
from datetime import timedelta

import pytest

from aegis.bus import tcp
from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import dumps, make
from aegis.standins.link import LinkServer, LinkStandin
from tests.fakes import FAKE_START, FakeLog

POWER = {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"}


def settings(**link):
    """Real settings with standins.link overridden."""
    cfg = load_settings()
    s = cfg.standins
    return cfg.model_copy(
        update={
            "standins": s.model_copy(update={"link": s.link.model_copy(update=link)})
        }
    )


async def settle(n: int = 20) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class Harness:
    def __init__(self, **link):
        self.clock = ManualClock(FAKE_START)
        self.log = FakeLog(process="link", clock=self.clock)
        self.cfg = settings(**link)
        self.link = LinkStandin(self.clock, self.cfg, self.log, rng=random.Random(5))
        self.at_ground: list = []
        self.at_vehicle: list = []

        async def to_ground(env):
            self.at_ground.append(env)

        async def to_vehicle(env):
            self.at_vehicle.append(env)

        self.link.attach("ground", to_ground)
        self.link.attach("vehicle", to_vehicle)

    def status(self):
        return make("power.status", "team4.power", POWER, self.clock)

    def estop(self):
        return make(
            "cmd.estop",
            "ground.command_manager",
            {"reason": "test", "source": "OPERATOR"},
            self.clock,
        )

    def relayed(self) -> list:
        """Messages delivered to either side, excluding link.health."""
        return [e for e in self.at_ground + self.at_vehicle if e.type != "link.health"]

    async def advance(self, seconds: float, step: float = 0.001) -> None:
        steps = round(seconds / step)
        for _ in range(steps):
            self.clock.advance(step)
            await settle(3)


@pytest.mark.asyncio
async def test_latency_applied():
    h = Harness(base_latency_ms=80, jitter_ms=20, loss_pct=0)
    env = h.status()
    await h.link.submit("vehicle", env)
    await h.advance(0.059)
    assert h.at_ground == []
    await h.advance(0.042)
    assert h.at_ground == [env]
    [relay] = h.log.of("link.relay")
    assert relay["msg_id"] == str(env.msg_id) and relay["type"] == "power.status"


@pytest.mark.asyncio
async def test_latency_follows_link_set():
    h = Harness(base_latency_ms=80, jitter_ms=0, loss_pct=0)
    await h.link.set(latency_ms=1500, loss_pct=0)
    await h.link.submit("vehicle", h.status())
    await h.advance(1.49, step=0.01)
    assert h.relayed() == []
    await h.advance(0.02, step=0.01)
    assert len(h.relayed()) == 1


@pytest.mark.asyncio
async def test_loss_rate_within_3_percent_over_2000_messages():
    h = Harness(base_latency_ms=0, jitter_ms=0, loss_pct=10)
    for _ in range(2000):
        await h.link.submit("vehicle", h.status())
    await settle(50)
    drops = len(h.log.of("link.drop"))
    assert 0.07 * 2000 <= drops <= 0.13 * 2000
    assert len(h.relayed()) == 2000 - drops
    assert {r["reason"] for r in h.log.of("link.drop")} == {"loss"}


@pytest.mark.asyncio
async def test_OI_009_outage_drops_everything_including_in_flight():
    h = Harness(base_latency_ms=80, jitter_ms=0, loss_pct=0)
    in_flight = h.status()
    await h.link.submit("vehicle", in_flight)
    await h.link.outage(10)
    await h.link.submit("ground", h.estop())  # a command is lost, never held
    await h.link.submit("vehicle", h.status())
    await h.advance(9.9, step=0.1)
    assert h.relayed() == []
    assert [r["reason"] for r in h.log.of("link.drop")] == ["outage"] * 3

    # After the outage the link carries traffic again; nothing old is replayed.
    await h.advance(0.2, step=0.1)
    after = h.status()
    await h.link.submit("vehicle", after)
    await h.advance(0.1, step=0.01)
    assert h.relayed() == [after]


@pytest.mark.asyncio
async def test_priority_0_overtakes_priority_2():
    h = Harness(base_latency_ms=80, jitter_ms=20, loss_pct=0)
    statuses = [h.status() for _ in range(10)]
    for env in statuses:
        await h.link.submit("ground", env)
    stop = h.estop()
    await h.link.submit("ground", stop)
    await h.advance(0.2)
    assert h.at_vehicle[0] == stop
    assert h.at_vehicle[1:] == statuses  # FIFO within a priority


@pytest.mark.asyncio
async def test_fifo_within_priority_despite_jitter():
    h = Harness(base_latency_ms=80, jitter_ms=40, loss_pct=0)
    sent = []
    for _ in range(30):
        env = h.status()
        sent.append(env)
        await h.link.submit("vehicle", env)
        h.clock.advance(0.003)
        await settle(3)
    await h.advance(0.3)
    assert h.relayed() == sent


@pytest.mark.asyncio
async def test_control_plane_never_delayed_or_dropped():
    h = Harness(base_latency_ms=500, jitter_ms=0, loss_pct=100)
    await h.link.outage(60)
    inject = make(
        "test.inject",
        "ground.fault_injector",
        {"target": "payload", "action": "shift", "params": {"cm": 3}},
        h.clock,
    )
    await h.link.submit("ground", inject)
    assert h.at_vehicle == [inject]  # at once, during an outage, at 100 % loss


@pytest.mark.asyncio
async def test_link_inject_is_handled_by_the_link_itself():
    h = Harness(base_latency_ms=80, jitter_ms=0, loss_pct=0)
    set_ = make(
        "test.inject",
        "ground.fault_injector",
        {
            "target": "link",
            "action": "set",
            "params": {"latency_ms": 1200, "loss_pct": 4},
        },
        h.clock,
    )
    await h.link.submit("ground", set_)
    assert h.link.latency_ms == 1200 and h.link.loss_pct == 4
    assert h.at_vehicle == []  # consumed, not relayed
    assert h.log.types("test.inject") == ["test.inject"]

    outage = make(
        "test.inject",
        "ground.fault_injector",
        {"target": "link", "action": "outage", "params": {"seconds": 7}},
        h.clock,
    )
    await h.link.submit("ground", outage)
    assert h.link.in_outage()


@pytest.mark.asyncio
async def test_OI_007_link_health_follows_injected_conditions_within_1s():
    h = Harness(base_latency_ms=80, jitter_ms=20, loss_pct=0)
    await h.link.start()
    await settle()

    def last_health():
        return [e for e in h.at_ground if e.type == "link.health"][-1].body

    assert last_health().state == "CONNECTED"
    assert last_health().latency_ms == 80

    await h.link.set(latency_ms=1500, loss_pct=0)  # over degraded_latency_ms
    assert last_health().state == "DEGRADED"

    await h.link.set(latency_ms=80, loss_pct=15)  # over degraded_loss_pct
    assert last_health().state == "DEGRADED"
    assert last_health().loss_pct == 15

    await h.link.set(latency_ms=80, loss_pct=0)
    assert last_health().state == "CONNECTED"
    await h.link.stop()


@pytest.mark.asyncio
async def test_OI_007_link_health_lost_only_after_lost_after_s():
    h = Harness(base_latency_ms=80, jitter_ms=0, loss_pct=0)
    lost_after = h.cfg.link.lost_after_s
    await h.link.start()
    await settle()
    await h.link.outage(30)

    def states():
        return [e.body.state for e in h.at_ground if e.type == "link.health"]

    # Early in the outage: still the previous state.
    await h.advance(lost_after - 1.0, step=0.5)
    assert states()[-1] == "CONNECTED"
    # Within 1 s of lost_after_s: LOST.
    await h.advance(2.0, step=0.5)
    assert states()[-1] == "LOST"
    assert h.log.of("link.state")[-1]["state"] == "LOST"
    # After the outage ends: back to the threshold state within 1 s.
    await h.advance(30 - lost_after, step=0.5)
    assert states()[-1] == "CONNECTED"
    await h.link.stop()


@pytest.mark.asyncio
async def test_link_health_is_1_hz():
    h = Harness()
    await h.link.start()
    await settle()
    await h.advance(5.0, step=0.25)
    times = [e.sent_at for e in h.at_ground if e.type == "link.health"]
    assert len(times) == 6  # t = 0, 1, 2, 3, 4, 5
    assert all(b - a == timedelta(seconds=1) for a, b in itertools.pairwise(times))
    await h.link.stop()


@pytest.mark.asyncio
async def test_side_not_connected_is_a_drop():
    h = Harness(base_latency_ms=0, jitter_ms=0, loss_pct=0)
    h.link.detach("ground")
    await h.link.submit("vehicle", h.status())
    await settle()
    assert h.log.of("link.drop")[0]["reason"] == "ground side not connected"


@pytest.mark.asyncio
async def test_single_process_wiring_with_two_buses():
    from aegis.bus.local_bus import LocalBus

    h = Harness(base_latency_ms=80, jitter_ms=0, loss_pct=0)
    glog, vlog = FakeLog("ground", clock=h.clock), FakeLog("vehicle", clock=h.clock)
    ground, vehicle = (
        LocalBus("ground", h.clock, glog),
        LocalBus("vehicle", h.clock, vlog),
    )
    ground.attach_link(h.link.port("ground"))
    vehicle.attach_link(h.link.port("vehicle"))
    h.link.attach("ground", ground.deliver_from_link)
    h.link.attach("vehicle", vehicle.deliver_from_link)

    got = []

    async def watch(env):
        got.append(env)

    vehicle.subscribe("vehicle.link_watch", watch)
    hb = make("hb.ground", "ground.command_manager", {"seq": 1}, h.clock)
    await ground.publish(hb)
    await h.advance(0.1, step=0.01)
    assert got == [hb]
    assert glog.types("msg.sent") == ["hb.ground"]
    assert vlog.types("msg.recv") == ["hb.ground"]
    assert h.log.of("msg.sent") == []  # the link never logs msg.sent


@pytest.mark.asyncio
async def test_tcp_mode_relays_between_sides():
    h = Harness(base_latency_ms=0, jitter_ms=0, loss_pct=0)
    server = LinkServer(h.link, h.cfg)
    await server.start(ground_port=0, vehicle_port=0)
    host = h.cfg.network.link_host
    g_reader, g_writer = await tcp.connect(host, server.port_of("ground"))
    v_reader, v_writer = await tcp.connect(host, server.port_of("vehicle"))
    for _ in range(500):
        if len(h.log.of("link.client_connected")) == 2:
            break
        await asyncio.sleep(0)

    hb = make("hb.ground", "ground.command_manager", {"seq": 7}, h.clock)
    await tcp.write_line(g_writer, "garbage")
    await tcp.write_line(g_writer, dumps(hb))
    line = await asyncio.wait_for(tcp.read_line(v_reader), timeout=5)
    assert json.loads(line)["msg_id"] == str(hb.msg_id)
    assert h.log.of("bus.invalid")[0]["raw"] == "garbage"

    # link.health reaches the ground client on the next 1 Hz tick.
    h.clock.advance(1.0)
    health = await asyncio.wait_for(tcp.read_line(g_reader), timeout=5)
    assert json.loads(health)["type"] == "link.health"

    await tcp.close(g_writer)
    await tcp.close(v_writer)
    await server.stop()
