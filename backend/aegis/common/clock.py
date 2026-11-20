"""Clocks (contracts section 1: no module reads the wall clock directly).

Every component takes a `Clock`. Production uses `RealClock`; tests and the
scenario runner's `--fast` mode use `ManualClock`, so 5 s timeouts run
instantly and deterministically.
"""

from __future__ import annotations

import asyncio
import heapq
import itertools
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Wait `seconds` of this clock's time."""
        ...


class RealClock:
    """The system clock. The only place in the backend that reads it."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(max(0.0, seconds))


class ManualClock:
    """A clock that moves only when a test calls `advance`.

    `advance(seconds)` resolves every pending `sleep` whose deadline has been
    reached, in deadline order (ties in the order the sleeps started). The
    woken tasks run the next time the caller yields to the event loop.
    """

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("ManualClock start must be timezone-aware")
        self._now = start.astimezone(UTC)
        self._sleepers: list[tuple[datetime, int, asyncio.Future[None]]] = []
        self._seq = itertools.count()

    def now(self) -> datetime:
        return self._now

    async def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        deadline = self._now + timedelta(seconds=seconds)
        heapq.heappush(self._sleepers, (deadline, next(self._seq), future))
        await future

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("ManualClock cannot go backwards")
        self._now += timedelta(seconds=seconds)
        while self._sleepers and self._sleepers[0][0] <= self._now:
            _, _, future = heapq.heappop(self._sleepers)
            if not future.done():  # a cancelled sleep is simply dropped
                future.set_result(None)

    @property
    def pending(self) -> int:
        """Sleeps still waiting for their deadline (cancelled ones excluded)."""
        return sum(1 for _, _, f in self._sleepers if not f.done())
