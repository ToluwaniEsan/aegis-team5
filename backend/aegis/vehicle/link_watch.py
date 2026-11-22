"""Link Watch (task A5): the vehicle decides on its own that the link is down.

Endpoint `vehicle.link_watch` watches `hb.ground`. With none for
`link.lost_after_s` it publishes `int.link_state LOST` to the controller and
the Event Buffer; the next heartbeat publishes `RESTORED`. The first heartbeat
after start-up also publishes `RESTORED`, so the Event Buffer can send a
backlog it saved before a restart. It never trusts the ground to say the link
is down (AEG-507, AEG-514).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make
from aegis.common.models import Envelope, LinkState

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "vehicle.link_watch"


class LinkWatch:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.lost_after_s = cfg.link.lost_after_s
        self.period_s = 1.0 / cfg.timing.heartbeat_rate_hz
        self.last_heartbeat: datetime | None = None
        self.lost = False
        self._started_at: datetime | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.bus.subscribe(ENDPOINT, self._on_heartbeat, types={"hb.ground"})
        self._started_at = self.clock.now()
        if self._task is None:
            self._task = asyncio.create_task(self._watch(), name="link-watch")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _on_heartbeat(self, env: Envelope) -> None:
        first = self.last_heartbeat is None
        self.last_heartbeat = self.clock.now()
        if self.lost or first:
            self.lost = False
            await self._publish("RESTORED", self.last_heartbeat)

    def silent_for_s(self) -> float:
        since = self.last_heartbeat or self._started_at
        return (self.clock.now() - since).total_seconds()

    async def _watch(self) -> None:
        while True:
            remaining = self.lost_after_s - self.silent_for_s()
            if remaining <= 0 and not self.lost:
                self.lost = True
                await self._publish("LOST", self.last_heartbeat or self._started_at)
                remaining = 0
            await self.clock.sleep(remaining if remaining > 0 else self.period_s)

    async def _publish(self, state: str, since: datetime) -> None:
        body = LinkState(state=state, since=since)
        await self.bus.publish(make("int.link_state", ENDPOINT, body, self.clock))
