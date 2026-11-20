"""Fault Injector (task B14): the test interface of contracts section 10.

A plain class. `inject(target, action, params)` checks the row and its params,
logs `test.inject`, and publishes one `test.inject` message:
- `payload`, `nav`, `power` go to `vehicle.test_agent`
- `link` goes to `team3.link`
- `team1` goes to `team1.integration` (the Team 1 stand-in, on the ground)

Bad input raises `ValueError` with the reason; the UI server (B12) turns that
into a 400 at `POST /api/test/inject`. Faults are triggered from the panel or
a scenario file, never by editing code (GEN-001).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make
from aegis.common.models import TestInject

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "ground.fault_injector"


@dataclass(frozen=True)
class InjectResult:
    msg_id: str
    target: str
    action: str
    dst: str


def _reason(exc: ValidationError) -> str:
    parts = []
    for e in exc.errors():
        msg = e["msg"].removeprefix("Value error, ")
        loc = ".".join(str(p) for p in e["loc"])
        parts.append(
            msg
            if not loc or msg.startswith(("unknown action", "bad params"))
            else f"{loc}: {msg}"
        )
    return "; ".join(parts)


class FaultInjector:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log

    async def inject(
        self, target: str, action: str, params: dict[str, Any] | None = None
    ) -> InjectResult:
        if not self.cfg.test_mode:
            raise ValueError("Test mode is off (test_mode: false in config.yaml)")
        try:
            body = TestInject(target=target, action=action, params=params or {})
        except ValidationError as exc:
            raise ValueError(_reason(exc)) from None
        env = make("test.inject", ENDPOINT, body, self.clock)
        self.log.record("test.inject", env=env.model_dump(mode="json"))
        await self.bus.publish(env)
        return InjectResult(
            msg_id=str(env.msg_id), target=target, action=action, dst=env.dst[0]
        )
