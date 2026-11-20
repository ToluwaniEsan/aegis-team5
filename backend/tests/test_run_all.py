"""Task B4: run everything. Heartbeats cross the link and appear in all three logs."""

import asyncio
import socket
import sys

import pytest

from aegis.bus.link_port import LinkPort
from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.ground.main import Ground
from aegis.run_all import PROCESSES, build_system, command
from aegis.standins.link import LinkServer, LinkStandin
from aegis.vehicle.main import Vehicle
from tests.fakes import FAKE_START, FakeLog
from tests.test_link_standin import settle

LOGS: dict[str, FakeLog] = {}


def fake_logs(process, run_id, clock, cfg):
    LOGS[process] = FakeLog(process, run_id, clock, cfg)
    return LOGS[process]


def heartbeat_ids(log: FakeLog, kind: str) -> list[str]:
    if kind == "link.relay":
        return [r["msg_id"] for r in log.of(kind) if r["type"] == "hb.ground"]
    return [r["env"]["msg_id"] for r in log.of(kind) if r["env"]["type"] == "hb.ground"]


async def advance(clock: ManualClock, seconds: float, step: float = 0.1) -> None:
    for _ in range(round(seconds / step)):
        clock.advance(step)
        await settle(5)


@pytest.mark.asyncio
async def test_single_process_heartbeats_in_all_three_logs_within_2s():
    LOGS.clear()
    cfg = load_settings()
    clock = ManualClock(FAKE_START)
    system = build_system(cfg, clock, "run-test", fake_logs)
    await system.start()
    await advance(clock, 2.0)
    await system.stop()

    sent = heartbeat_ids(LOGS["ground"], "msg.sent")
    relayed = heartbeat_ids(LOGS["link"], "link.relay")
    received = heartbeat_ids(LOGS["vehicle"], "msg.recv")
    assert len(sent) >= 2
    assert sent[0] in relayed and sent[0] in received  # first beat crossed within 2 s
    assert {r["run"] for log in LOGS.values() for r in log.records} == {"run-test"}

    # link.health reaches the ground the same way.
    assert "link.health" in LOGS["ground"].types("msg.recv")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_tcp_heartbeats_cross_the_link_process():
    """The multi-process wiring (LinkPort <-> LinkServer) in one loop."""
    base = load_settings()
    net = base.network.model_copy(
        update={"link_ground_port": free_port(), "link_vehicle_port": free_port()}
    )
    cfg = base.model_copy(update={"network": net})
    clock = ManualClock(FAKE_START)
    logs = {p: FakeLog(p, "run-tcp", clock, cfg) for p in PROCESSES}

    server = LinkServer(LinkStandin(clock, cfg, logs["link"]), cfg)
    await server.start()
    vehicle = Vehicle(cfg, clock, logs["vehicle"])
    ground = Ground(cfg, clock, logs["ground"])
    assert isinstance(ground.link_port, LinkPort)
    await vehicle.start()
    await ground.start()

    for _ in range(5000):
        if (
            ground.link_port.connected
            and vehicle.link_port.connected
            and len(logs["link"].of("link.client_connected")) == 2
        ):
            break
        await asyncio.sleep(0)
    else:
        raise AssertionError("did not connect")

    for _ in range(3):  # beats every second; the link adds 80 +/- 20 ms
        clock.advance(0.5)
        for _ in range(200):
            await asyncio.sleep(0)
    for _ in range(5000):
        if heartbeat_ids(logs["vehicle"], "msg.recv"):
            break
        clock.advance(0.01)
        await asyncio.sleep(0)

    received = heartbeat_ids(logs["vehicle"], "msg.recv")
    assert received
    assert received[0] in heartbeat_ids(logs["ground"], "msg.sent")
    assert received[0] in heartbeat_ids(logs["link"], "link.relay")

    await ground.stop()
    await vehicle.stop()
    await server.stop()


def test_multi_process_commands_share_one_run_id():
    cmds = {side: command(side, "R1") for side in PROCESSES}
    assert list(cmds) == ["link", "vehicle", "ground"]  # link starts first
    for side, cmd in cmds.items():
        assert cmd[:3] == [sys.executable, "-m", PROCESSES[side]]
        assert cmd[-2:] == ["--run-id", "R1"]
