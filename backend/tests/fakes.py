"""Shared test fakes: `FakeLog` (the B2 MissionLog interface) and `FakeBus`
(the B1 LocalBus interface). Both builders' tests use them.

FakeLog keeps records in memory. Like the real log, it writes JSON, so a
field that cannot be serialized fails here too.

FakeBus records every published envelope and delivers it to subscribers of
any endpoint in `dst`, with no sides and no link, so a single component can be
tested alone. Use `inject` to hand it a message as if it came from elsewhere.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal

from aegis.common.clock import Clock, ManualClock
from aegis.common.config import Settings
from aegis.common.models import Envelope, format_timestamp

Handler = Callable[[Envelope], Awaitable[None]]
OutboundFilter = Callable[[Envelope], Awaitable[Envelope | None]]

FAKE_START = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)


class FakeLog:
    """`MissionLog(process, run_id, clock, cfg)` with `record(kind, **fields)`."""

    def __init__(
        self,
        process: str = "test",
        run_id: str = "test-run",
        clock: Clock | None = None,
        cfg: Settings | None = None,
    ):
        self.process = process
        self.run_id = run_id
        self.clock = clock or ManualClock(FAKE_START)
        self.cfg = cfg
        self.records: list[dict[str, Any]] = []

    def record(self, kind: str, **fields: Any) -> None:
        reserved = {"t", "run", "process", "kind"} & fields.keys()
        if reserved:  # the real MissionLog refuses these too
            raise ValueError(f"Reserved record fields: {', '.join(sorted(reserved))}")
        line = {
            "t": format_timestamp(self.clock.now()),
            "run": self.run_id,
            "process": self.process,
            "kind": kind,
            **fields,
        }
        # Round-trip through JSON exactly as the real log's file would.
        self.records.append(json.loads(json.dumps(line, allow_nan=False)))

    # Helpers for assertions

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r["kind"] == kind]

    def kinds(self) -> list[str]:
        return [r["kind"] for r in self.records]

    def types(self, kind: str) -> list[str]:
        """The `env.type` of every record of this kind, in order."""
        return [r["env"]["type"] for r in self.of(kind)]


class FakeBus:
    """`LocalBus(side, clock, log)` without sides or a link."""

    def __init__(
        self,
        side: Literal["ground", "vehicle"] = "vehicle",
        clock: Clock | None = None,
        log: FakeLog | None = None,
    ):
        self.side = side
        self.clock = clock or ManualClock(FAKE_START)
        self.log = log or FakeLog(clock=self.clock)
        self.published: list[Envelope] = []
        self.filters: list[OutboundFilter] = []
        self.link: Any = None
        self._subs: list[tuple[str, Handler, frozenset[str] | None]] = []

    def subscribe(
        self, endpoint: str, handler: Handler, types: set[str] | None = None
    ) -> None:
        self._subs.append(
            (endpoint, handler, frozenset(types) if types is not None else None)
        )

    def add_outbound_filter(self, f: OutboundFilter) -> None:
        self.filters.append(f)

    def attach_link(self, port: Any) -> None:
        self.link = port

    async def publish(self, env: Envelope) -> None:
        self.log.record("msg.sent", env=env.model_dump(mode="json"))
        self.published.append(env)
        await self._deliver(env)

    async def deliver_from_link(self, env: Envelope) -> None:
        self.log.record("msg.recv", env=env.model_dump(mode="json"))
        await self._deliver(env)

    async def inject(self, env: Envelope) -> None:
        """Deliver a message to subscribers without recording it as published."""
        await self._deliver(env)

    async def _deliver(self, env: Envelope) -> None:
        for endpoint, handler, types in list(self._subs):
            if endpoint in env.dst and (types is None or env.type in types):
                await handler(env)

    # Helpers for assertions

    def sent(self, type: str | None = None) -> list[Envelope]:
        return [e for e in self.published if type is None or e.type == type]

    def last(self, type: str) -> Envelope:
        found = self.sent(type)
        assert found, f"nothing of type {type!r} was published"
        return found[-1]

    def clear(self) -> None:
        self.published.clear()


async def settle(n: int = 20) -> None:
    """Let ready tasks run. Yields to the event loop; never sleeps."""
    import asyncio

    for _ in range(n):
        await asyncio.sleep(0)


async def advance(clock: ManualClock, seconds: float, step: float = 0.1) -> None:
    """Move a ManualClock forward in steps, letting woken tasks run after each."""
    for _ in range(round(seconds / step)):
        clock.advance(step)
        await settle(5)
