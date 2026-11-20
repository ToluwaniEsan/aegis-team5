"""Ground heartbeat: `hb.ground` to `vehicle.link_watch` at
`timing.heartbeat_rate_hz`. The vehicle uses it to detect link loss on its own."""

from __future__ import annotations

import asyncio

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make
from aegis.common.models import HeartbeatGround

SRC = "ground.command_manager"


class Heartbeat:
    def __init__(self, bus, clock: Clock, cfg: Settings):
        self.bus = bus
        self.clock = clock
        self.period_s = 1.0 / cfg.timing.heartbeat_rate_hz
        self.seq = 0
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="heartbeat")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def beat(self) -> None:
        env = make("hb.ground", SRC, HeartbeatGround(seq=self.seq), self.clock)
        self.seq += 1
        await self.bus.publish(env)

    async def _run(self) -> None:
        while True:
            await self.beat()
            await self.clock.sleep(self.period_s)
