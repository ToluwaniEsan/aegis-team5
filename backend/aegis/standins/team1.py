"""Team 1 integration stand-in (B7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from aegis.common.envelope import make, parse
from aegis.common.models import Envelope

if TYPE_CHECKING:
    from aegis.common.clock import Clock
    from aegis.common.config import Settings
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "team1.integration"


class Team1Standin:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus, self.clock, self.cfg, self.log = bus, clock, cfg, log
        self.current_mode: str | None = None
        self._subscribed = False
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        if not self._subscribed:
            self.bus.subscribe(ENDPOINT, self._on_message)
            self._subscribed = True
        self._running = True
        await self.mode("OPERATIONAL")

    async def stop(self) -> None:
        self._running = False

    async def mode(self, value: str) -> None:
        env = make("t1.system_mode", ENDPOINT, {"mode": value}, self.clock)
        if value != self.current_mode:
            self.log.record("state.change", group="team1.mode", mode=value)
        self.current_mode = value
        await self.bus.publish(env)

    async def _on_message(self, incoming: Envelope) -> None:
        if not self._running:
            return
        try:
            env = parse(incoming.model_dump_json())
        except (ValidationError, TypeError, ValueError) as exc:
            self.log.record("bus.invalid", error=str(exc))
            return
        if env.type.startswith("t1."):
            self.log.record("team1.received", env=env.model_dump(mode="json"))
        elif env.type == "test.inject" and env.body.target == "team1":
            if self.cfg.test_mode and env.body.action == "mode":
                await self.mode(env.body.params["mode"])
                self.log.record(
                    "test.applied",
                    target="team1",
                    action="mode",
                    msg_id=str(env.msg_id),
                )
