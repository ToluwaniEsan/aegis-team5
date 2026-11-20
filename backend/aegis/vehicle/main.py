"""Vehicle process entry point: `python -m aegis.vehicle`.

Phase 0 skeleton (B4): settings, Mission Log, bus and LinkPort, so heartbeats
from the ground arrive and are logged. Task A9 completes it with the
components marked `A9:` below.
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

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog


class Vehicle:
    """Everything that runs in the vehicle process.

    `link=None` connects to the link process over TCP (LinkPort). In
    single-process mode `run_all` passes the in-memory link stand-in's port.
    """

    def __init__(
        self, cfg: Settings, clock: Clock, log: MissionLog, link: Link | None = None
    ):
        self.cfg = cfg
        self.clock = clock
        self.log = log
        self.bus = LocalBus("vehicle", clock, log)
        self.link_port: LinkPort | None = None
        if link is None:
            self.link_port = LinkPort.from_settings(
                cfg, "vehicle", self.bus, clock, log
            )
        else:
            self.bus.attach_link(link)

        # A9: Payload Simulator (A3), Payload Controller (A4), Link Watch (A5),
        #     Event Buffer (A7, as an outbound filter), test agent (A9),
        #     Team 2 stand-in (B5) and Team 4 stand-in (B6).

    async def start(self) -> None:
        self.log.record("process.start")
        if self.link_port is not None:
            await self.link_port.start()
        # A9: start the components above.

    async def stop(self) -> None:
        # A9: stop the components above, in reverse order of start.
        if self.link_port is not None:
            await self.link_port.stop()
        self.log.record("process.stop")


async def run(run_id: str) -> None:
    from aegis.common.clock import RealClock
    from aegis.common.config import load_settings
    from aegis.ground.mission_log import MissionLog

    cfg = load_settings()
    clock = RealClock()
    vehicle = Vehicle(cfg, clock, MissionLog("vehicle", run_id, clock, cfg))
    await vehicle.start()
    try:
        await asyncio.Event().wait()  # until cancelled (Ctrl+C or run_all stops us)
    finally:
        await vehicle.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Team 5 vehicle process")
    parser.add_argument("--run-id", default=None, help="shared run ID from run_all")
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.run_id or uuid.uuid4().hex[:8]))
    except KeyboardInterrupt:
        pass
