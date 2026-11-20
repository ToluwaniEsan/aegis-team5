"""Ground process entry point: `python -m aegis.ground`.

Shared file. Zizwe created it with the plumbing (settings, Mission Log, bus,
LinkPort, heartbeat). Emmanuel adds his components at the places marked
`EMMANUEL:` below.
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from typing import TYPE_CHECKING

from aegis.bus.link_port import LinkPort
from aegis.bus.local_bus import Link, LocalBus
from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.ground.heartbeat import Heartbeat

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

        # EMMANUEL: Command Manager (B7). Subscribe it to "ground.command_manager".
        # EMMANUEL: Status Monitor (B9). Subscribe it to "ground.status_monitor".
        # EMMANUEL: Alert Manager (B10/B11). Subscribe it to "ground.alert_manager".
        # EMMANUEL: Team 1 stand-in (standins/team1.py). Subscribe it to "team1.integration".
        # EMMANUEL: UI server (B12), serving the screen and /ws on network.ui_port,
        #           with the Fault Injector (B14) mounted at POST /api/test/inject.

    async def start(self) -> None:
        self.log.record("process.start")
        if self.link_port is not None:
            await self.link_port.start()
        # EMMANUEL: start the Command Manager, Status Monitor, Alert Manager,
        #           Team 1 stand-in and UI server here.
        await self.heartbeat.start()

    async def stop(self) -> None:
        await self.heartbeat.stop()
        # EMMANUEL: stop your components here, in reverse order of start.
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
