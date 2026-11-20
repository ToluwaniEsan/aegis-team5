"""Task B1: LinkPort over a real local socket."""

import asyncio
import json
import socket

import pytest
import pytest_asyncio

from aegis.bus import tcp
from aegis.bus.link_port import LinkPort
from aegis.bus.local_bus import LocalBus
from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import dumps, make
from tests.fakes import FAKE_START, FakeLog

HOST = "127.0.0.1"
MIN_S = 0.5
MAX_S = 5.0


async def until(cond, steps: int = 5000) -> None:
    """Yield to the event loop (and socket IO) until cond() holds. No real sleeps."""
    for _ in range(steps):
        if cond():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition not met")


def free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


class FakeLinkServer:
    """Stands in for the link process: records lines, can send lines."""

    def __init__(self):
        self.lines: list[str] = []
        self.writers: list[asyncio.StreamWriter] = []
        self.server: asyncio.Server | None = None

    async def start(self, port: int = 0) -> int:
        self.server = await tcp.serve(HOST, port, self._on_connect)
        return self.server.sockets[0].getsockname()[1]

    async def _on_connect(self, reader, writer):
        self.writers.append(writer)
        while (line := await tcp.read_line(reader)) is not None:
            self.lines.append(line)

    async def send(self, line: str) -> None:
        await tcp.write_line(self.writers[-1], line)

    async def drop_clients(self) -> None:
        for w in self.writers:
            await tcp.close(w)
        self.writers.clear()

    async def stop(self) -> None:
        await self.drop_clients()
        self.server.close()
        await self.server.wait_closed()


@pytest.fixture
def clock():
    return ManualClock(FAKE_START)


@pytest.fixture
def log(clock):
    return FakeLog(process="vehicle", clock=clock)


@pytest.fixture
def bus(clock, log):
    return LocalBus("vehicle", clock, log)


@pytest_asyncio.fixture
async def server():
    srv = FakeLinkServer()
    yield srv
    if srv.server is not None:
        await srv.stop()


def _port(port, bus, clock, log) -> LinkPort:
    return LinkPort(
        HOST, port, bus, clock, log, reconnect_min_s=MIN_S, reconnect_max_s=MAX_S
    )


@pytest.mark.asyncio
async def test_delivery_across_a_socket_both_ways(server, bus, clock, log):
    received = []

    async def handler(env):
        received.append(env)

    bus.subscribe("vehicle.payload_controller", handler)
    lp = _port(await server.start(), bus, clock, log)
    await lp.start()
    await until(lambda: lp.connected and server.writers)

    # inbound: link -> vehicle bus
    cmd = make("cmd.release", "ground.command_manager", {}, clock)
    await server.send(dumps(cmd))
    await until(lambda: received)
    assert received == [cmd]
    assert log.types("msg.recv") == ["cmd.release"]

    # outbound: vehicle bus -> link (status monitor is on the ground)
    hb_like = make(
        "power.status",
        "team4.power",
        {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"},
        clock,
    )
    await bus.publish(hb_like)
    await until(lambda: server.lines)
    assert json.loads(server.lines[0])["msg_id"] == str(hb_like.msg_id)
    assert log.of("link.relay")[0]["msg_id"] == str(hb_like.msg_id)
    await lp.stop()


@pytest.mark.asyncio
async def test_priority_order_0_before_1_before_2_fifo_within(server, bus, clock, log):
    lp = _port(await server.start(), bus, clock, log)
    await lp.start()
    await until(lambda: lp.connected)

    status = {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"}
    p2a = make("power.status", "team4.power", status, clock)
    p2b = make("power.status", "team4.power", status, clock)
    p1 = make(
        "payload.mass_report",
        "vehicle.payload_controller",
        {
            "mass_kg": 700,
            "release_energy_wh_nominal": 3.2,
            "release_energy_wh_max": 5.0,
        },
        clock,
    )
    p0 = make(
        "test.inject",
        "ground.fault_injector",
        {"target": "link", "action": "outage", "params": {"seconds": 5}},
        clock,
    )
    # Queued without yielding, so the writer sees all four at once.
    for env in (p2a, p2b, p1, p0):
        await lp.send(env)
    await until(lambda: len(server.lines) == 4)

    order = [json.loads(line)["msg_id"] for line in server.lines]
    assert order == [str(e.msg_id) for e in (p0, p1, p2a, p2b)]
    await lp.stop()


@pytest.mark.asyncio
async def test_send_while_disconnected_is_dropped_not_held(server, bus, clock, log):
    port = free_port()
    lp = _port(port, bus, clock, log)
    cmd = make("cmd.release", "ground.command_manager", {}, clock)
    await lp.send(cmd)  # never started: disconnected
    [drop] = log.of("link.drop")
    assert drop["msg_id"] == str(cmd.msg_id)

    # Connecting later must not deliver the dropped message.
    await server.start(port)
    await lp.start()
    await until(lambda: lp.connected and server.writers)
    for _ in range(50):
        await asyncio.sleep(0)
    assert server.lines == []
    await lp.stop()


@pytest.mark.asyncio
async def test_reconnect_with_backoff_doubling_to_max(server, bus, clock, log):
    port = free_port()  # nothing listening yet
    lp = _port(port, bus, clock, log)
    await lp.start()

    expected = [0.5, 1.0, 2.0, 4.0, 5.0, 5.0]
    for i, delay in enumerate(expected):
        await until(
            lambda n=i: len(log.of("link.connect_failed")) == n + 1 and clock.pending
        )
        assert log.of("link.connect_failed")[-1]["retry_in_s"] == delay
        if i < len(expected) - 1:
            clock.advance(delay)

    # The link comes up: the next retry connects.
    await server.start(port)
    clock.advance(5.0)
    await until(lambda: lp.connected and server.writers)

    # The link process drops us: reconnect after reconnect_min_s.
    await server.drop_clients()
    await until(lambda: not lp.connected and clock.pending)
    assert log.kinds().count("link.disconnected") == 1
    clock.advance(MIN_S)
    await until(lambda: lp.connected)
    assert log.kinds().count("link.connected") == 2
    await lp.stop()


@pytest.mark.asyncio
async def test_invalid_line_is_logged_and_the_bus_keeps_going(server, bus, clock, log):
    received = []

    async def handler(env):
        received.append(env)

    bus.subscribe("vehicle.payload_controller", handler)
    lp = _port(await server.start(), bus, clock, log)
    await lp.start()
    await until(lambda: lp.connected and server.writers)

    bad_type = dumps(make("cmd.release", "ground.command_manager", {}, clock)).replace(
        '"cmd.release"', '"cmd.explode"'
    )
    await server.send("this is not json")
    await server.send(bad_type)
    good = make("cmd.release", "ground.command_manager", {}, clock)
    await server.send(dumps(good))
    await until(lambda: received)

    assert received == [good]
    invalid = log.of("bus.invalid")
    assert [r["raw"] for r in invalid] == ["this is not json", bad_type]
    assert all(r["error"] for r in invalid)
    assert lp.connected
    await lp.stop()


@pytest.mark.asyncio
async def test_from_settings_picks_the_side_port(bus, clock, log):
    cfg = load_settings()
    ground = LinkPort.from_settings(
        cfg, "ground", LocalBus("ground", clock, log), clock, log
    )
    vehicle = LinkPort.from_settings(cfg, "vehicle", bus, clock, log)
    assert ground.port == cfg.network.link_ground_port
    assert vehicle.port == cfg.network.link_vehicle_port
    assert vehicle.reconnect_min_s == cfg.network.reconnect_min_s
    assert vehicle.reconnect_max_s == cfg.network.reconnect_max_s
