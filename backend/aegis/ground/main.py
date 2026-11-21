"""Ground process entry point: `python -m aegis.ground`.

Shared file. Zizwe created it with the plumbing (settings, Mission Log, bus,
LinkPort, heartbeat). Emmanuel adds his components at the places marked
`EMMANUEL:` below.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import uuid
from typing import TYPE_CHECKING

import uvicorn

from aegis.bus.link_port import LinkPort
from aegis.bus.local_bus import Link, LocalBus
from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.ground.alert_manager import AlertManager
from aegis.ground.command_manager import CommandManager
from aegis.ground.heartbeat import Heartbeat
from aegis.ground.snapshot import SnapshotBuilder
from aegis.ground.status_monitor import StatusMonitor
from aegis.ground.ui_server import UiServer
from aegis.standins.team1 import Team1Standin
from aegis.testing.fault_injector import FaultInjector

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog


class Ground:
    """Everything that runs in the ground process.

    `link=None` connects to the link process over TCP (LinkPort). In
    single-process mode `run_all` passes the in-memory link stand-in's port.
    """

    def __init__(
        self, cfg: Settings, clock: Clock, log: MissionLog, link: Link | None = None
    ):
        self.cfg = cfg
        self.clock = clock
        self.log = log
        self.bus = LocalBus("ground", clock, log)
        self.link_port: LinkPort | None = None
        if link is None:
            self.link_port = LinkPort.from_settings(cfg, "ground", self.bus, clock, log)
        else:
            self.bus.attach_link(link)
        self.heartbeat = Heartbeat(self.bus, clock, cfg)
        # B14: the UI server mounts this at POST /api/test/inject (test_mode only).
        self.fault_injector = FaultInjector(self.bus, clock, cfg, log)

        self.status_monitor = StatusMonitor(self.bus, clock, cfg, log, lambda _: None)
        self.alert_manager = AlertManager(
            self.bus, clock, cfg, log, self.status_monitor
        )
        self.command_manager = CommandManager(
            self.bus,
            clock,
            cfg,
            log,
            self.status_monitor,
            alerts_for=self.alert_manager.views,
            on_failure=self.alert_manager.command_failed,
            ack_ground_alert=self.alert_manager.acknowledge_ground,
            on_fault_ack=self.alert_manager.acknowledge_vehicle,
        )
        self.team1 = Team1Standin(self.bus, clock, cfg, log)
        self.snapshot_builder = SnapshotBuilder(
            cfg, clock, self.status_monitor, self.command_manager
        )
        self.ui = UiServer(
            cfg, clock, self.snapshot_builder, self.command_manager, self.fault_injector
        )
        self.alert_manager.on_change = self.ui.changed
        self._ui_server: uvicorn.Server | None = None
        self._ui_task: asyncio.Task | None = None

    async def start(self) -> None:
        self.log.record("process.start")
        if self.link_port is not None:
            await self.link_port.start()
        await self.team1.start()
        await self.alert_manager.start()
        config = uvicorn.Config(
            self.ui.app,
            host=self.cfg.network.link_host,
            port=self.cfg.network.ui_port,
            log_level="warning",
            access_log=False,
        )
        self._ui_server = uvicorn.Server(config)
        # The ground process owns signal handling, not this nested server.
        self._ui_server.capture_signals = contextlib.nullcontext
        self._ui_task = asyncio.create_task(self._ui_server.serve())
        while not self._ui_server.started:
            if self._ui_task.done():
                await self._ui_task
                raise RuntimeError("UI server stopped before startup")
            await asyncio.sleep(0)
        await self.heartbeat.start()

    async def stop(self) -> None:
        await self.heartbeat.stop()
        await self.alert_manager.stop()
        self.command_manager.close()
        await self.team1.stop()
        if self._ui_server is not None:
            self._ui_server.should_exit = True
        if self._ui_task is not None:
            await self._ui_task
        if self.link_port is not None:
            await self.link_port.stop()
        self.log.record("process.stop")


async def run(run_id: str) -> None:
    from aegis.common.clock import RealClock
    from aegis.common.config import load_settings
    from aegis.ground.mission_log import MissionLog

    cfg = load_settings()
    clock = RealClock()
    ground = Ground(cfg, clock, MissionLog("ground", run_id, clock, cfg))
    await ground.start()
    try:
        await asyncio.Event().wait()  # until cancelled (Ctrl+C or run_all stops us)
    finally:
        await ground.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Team 5 ground process")
    parser.add_argument("--run-id", default=None, help="shared run ID from run_all")
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.run_id or uuid.uuid4().hex[:8]))
    except KeyboardInterrupt:
        pass
