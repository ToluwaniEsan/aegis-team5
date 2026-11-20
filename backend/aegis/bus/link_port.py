"""One side's connection to the link process (Team 3 stand-in, later adapter).

Outbound: a priority queue, 0 before 1 before 2, FIFO within a priority.
While disconnected every message is dropped and logged as `link.drop`, never
held: a command sent late is worse than one that fails. On the vehicle the
Event Buffer filter runs before this and keeps what must survive.

Inbound: each line is parsed; a bad line is logged as `bus.invalid` with the
raw text and dropped, and the connection stays up.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from aegis.bus import tcp
from aegis.bus.local_bus import LocalBus
from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import dumps, parse
from aegis.common.models import Envelope

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog


class LinkPort:
    def __init__(
        self,
        host: str,
        port: int,
        bus: LocalBus,
        clock: Clock,
        log: MissionLog,
        *,
        reconnect_min_s: float,
        reconnect_max_s: float,
    ):
        self.host = host
        self.port = port
        self.bus = bus
        self.clock = clock
        self.log = log
        self.reconnect_min_s = reconnect_min_s
        self.reconnect_max_s = reconnect_max_s
        self._queue: asyncio.PriorityQueue[tuple[int, int, Envelope]] = (
            asyncio.PriorityQueue()
        )
        self._seq = itertools.count()
        self._connected = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        bus.attach_link(self)

    @classmethod
    def from_settings(
        cls,
        cfg: Settings,
        side: Literal["ground", "vehicle"],
        bus: LocalBus,
        clock: Clock,
        log: MissionLog,
    ) -> LinkPort:
        net = cfg.network
        port = net.link_ground_port if side == "ground" else net.link_vehicle_port
        return cls(
            net.link_host,
            port,
            bus,
            clock,
            log,
            reconnect_min_s=net.reconnect_min_s,
            reconnect_max_s=net.reconnect_max_s,
        )

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    async def wait_connected(self) -> None:
        await self._connected.wait()

    async def start(self) -> None:
        """Start connecting in the background. Reconnects with backoff from
        reconnect_min_s, doubling to reconnect_max_s, reset on success."""
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name=f"link-port-{self.port}")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def send(self, env: Envelope) -> None:
        if not self.connected:
            self._drop(env, "link disconnected")
            return
        self._queue.put_nowait((env.priority, next(self._seq), env))

    async def _run(self) -> None:
        delay = self.reconnect_min_s
        while True:
            try:
                reader, writer = await tcp.connect(self.host, self.port)
            except OSError as exc:
                self.log.record(
                    "link.connect_failed",
                    host=self.host,
                    port=self.port,
                    error=str(exc),
                    retry_in_s=delay,
                )
                await self.clock.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_s)
                continue
            delay = self.reconnect_min_s
            await self._session(reader, writer)
            await self.clock.sleep(delay)

    async def _session(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.log.record("link.connected", host=self.host, port=self.port)
        self._connected.set()
        writer_task = asyncio.create_task(self._write_loop(writer))
        try:
            await self._read_loop(reader)
        finally:
            self._connected.clear()
            writer_task.cancel()
            try:
                await writer_task
            except asyncio.CancelledError:
                pass
            while not self._queue.empty():
                _, _, env = self._queue.get_nowait()
                self._drop(env, "link disconnected")
            await tcp.close(writer)
            self.log.record("link.disconnected", host=self.host, port=self.port)

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        while True:
            try:
                line = await tcp.read_line(reader)
            except tcp.LineTooLong as exc:
                self.log.record("bus.invalid", raw=None, error=str(exc))
                return  # the stream is out of step; reconnect
            except (ConnectionError, OSError):
                return
            if line is None:
                return
            if not line.strip():
                continue
            try:
                env = parse(line)
            except ValidationError as exc:
                self.log.record("bus.invalid", raw=line, error=_summary(exc))
                continue
            await self.bus.deliver_from_link(env)

    async def _write_loop(self, writer: asyncio.StreamWriter) -> None:
        while True:
            _, _, env = await self._queue.get()
            try:
                await tcp.write_line(writer, dumps(env))
            except (ConnectionError, OSError):
                self._drop(env, "write failed")
                writer.close()  # ends the read loop too, so the session reconnects
                return
            self.log.record("link.relay", msg_id=str(env.msg_id), type=env.type)

    def _drop(self, env: Envelope, reason: str) -> None:
        self.log.record(
            "link.drop", msg_id=str(env.msg_id), type=env.type, reason=reason
        )


def _summary(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or '(line)'}: {e['msg']}"
        for e in exc.errors()
    )
