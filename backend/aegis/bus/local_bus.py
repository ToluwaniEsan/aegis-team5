"""The in-process message bus for one side (ground or vehicle).

Contracts section 2 logging rule: only `publish` logs `msg.sent` and only
`deliver_from_link` logs `msg.recv`, so every message is counted once.

Handlers are awaited in turn, in subscription order. A handler must not
block: anything long-running (a timer, a mechanism delay) belongs in its own
task. A handler that raises is logged as `bus.handler_error` and the other
handlers still run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal, Protocol

from aegis.bus.endpoints import side_of
from aegis.common.clock import Clock
from aegis.common.models import Envelope

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

Handler = Callable[[Envelope], Awaitable[None]]
OutboundFilter = Callable[[Envelope], Awaitable[Envelope | None]]  # return None to hold


class Link(Protocol):
    """What the bus needs from a LinkPort (or the in-memory link in single-process mode)."""

    async def send(self, env: Envelope) -> None: ...


def env_record(env: Envelope) -> dict:
    """The envelope as the Mission Log stores it under `env`."""
    return env.model_dump(mode="json")


class LocalBus:
    def __init__(
        self, side: Literal["ground", "vehicle"], clock: Clock, log: MissionLog
    ):
        self.side = side
        self.clock = clock
        self.log = log
        self._subs: list[tuple[str, Handler, frozenset[str] | None]] = []
        self._filters: list[OutboundFilter] = []
        self._link: Link | None = None

    def subscribe(
        self, endpoint: str, handler: Handler, types: set[str] | None = None
    ) -> None:
        if side_of(endpoint) != self.side:
            raise ValueError(f"{endpoint!r} is not a {self.side} endpoint")
        self._subs.append(
            (endpoint, handler, frozenset(types) if types is not None else None)
        )

    def add_outbound_filter(self, f: OutboundFilter) -> None:
        self._filters.append(f)

    def attach_link(self, port: Link) -> None:
        self._link = port

    async def publish(self, env: Envelope) -> None:
        """Logs msg.sent. Delivers to local subscribers whose endpoint is in env.dst.
        If any dst endpoint is on the other side, passes the envelope through the
        outbound filters, then to the attached LinkPort."""
        self.log.record("msg.sent", env=env_record(env))
        await self._deliver_local(env)
        if any(side_of(d) != self.side for d in env.dst):
            await self._send_remote(env)

    async def deliver_from_link(self, env: Envelope) -> None:
        """Logs msg.recv and delivers to local subscribers. Never sends back out."""
        self.log.record("msg.recv", env=env_record(env))
        await self._deliver_local(env)

    async def _deliver_local(self, env: Envelope) -> None:
        local = {d for d in env.dst if side_of(d) == self.side}
        if not local:
            return
        for endpoint, handler, types in list(self._subs):
            if endpoint not in local or (types is not None and env.type not in types):
                continue
            try:
                await handler(env)
            except Exception as exc:  # noqa: BLE001 - one bad handler must not stop the bus
                self.log.record(
                    "bus.handler_error",
                    endpoint=endpoint,
                    msg_id=str(env.msg_id),
                    type=env.type,
                    error=f"{type(exc).__name__}: {exc}",
                )

    async def _send_remote(self, env: Envelope) -> None:
        out: Envelope | None = env
        for f in self._filters:
            out = await f(out)
            if out is None:
                return  # held, for example by the Event Buffer during an outage
        if self._link is None:
            self.log.record(
                "link.drop",
                msg_id=str(out.msg_id),
                type=out.type,
                reason="no link attached",
            )
            return
        await self._link.send(out)
