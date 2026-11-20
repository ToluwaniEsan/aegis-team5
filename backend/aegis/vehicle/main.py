"""Vehicle process entry point: `python -m aegis.vehicle`.

Runs the Payload Simulator, Payload Controller, Link Watch and the Team 2
and Team 4 stand-ins on the vehicle bus, joined to the ground through the
link. Task A9 adds the parts still marked `A9:` below.
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
from aegis.standins.nav import NavStandin
from aegis.standins.power import PowerStandin
from aegis.vehicle.link_watch import LinkWatch
from aegis.vehicle.payload_controller import PayloadController
from aegis.vehicle.simulator import PayloadSimulator

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

        bus = self.bus
        self.simulator = PayloadSimulator(bus, clock, cfg, log)
        self.nav = NavStandin(bus, clock, cfg, log)
        self.power = PowerStandin(bus, clock, cfg, log, moving=lambda: self.nav.moving)
        self.controller = PayloadController(bus, clock, cfg, log)
        self.link_watch = LinkWatch(bus, clock, cfg, log)
        # In start order. The simulator first, so the lock state exists before
        # the controller looks at it.
        self.parts = [
            self.simulator,
            self.nav,
            self.power,
            self.controller,
            self.link_watch,
        ]
        # A9: Event Buffer (A7, as an outbound filter) and the test agent
        #     (vehicle.test_agent, with the controller crash hook).

    async def start(self) -> None:
        self.log.record("process.start")
        if self.link_port is not None:
            await self.link_port.start()
        for part in self.parts:
            await part.start()

    async def stop(self) -> None:
        for part in reversed(self.parts):
            await part.stop()
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
