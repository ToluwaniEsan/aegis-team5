"""Team 3 link stand-in (task B3): latency, loss, outages, priority, link.health.

Works two ways:
- In-process (single-process mode): `port(side)` gives each LocalBus an object
  to `attach_link`, and `attach(side, bus.deliver_from_link)` hands relayed
  messages to the other bus.
- As a process: `python -m aegis.standins.link` listens on
  `network.link_ground_port` and `network.link_vehicle_port`.

Relay rules:
- Each message is delayed by `base_latency_ms ± jitter_ms` and dropped at
  `loss_pct` (or the values set by the `link/set` test action).
- Strict priority in each direction: a message is never delivered ahead of a
  higher-priority message that entered the link no later than it did, nor
  ahead of an earlier message of the same priority.
- During an outage everything is dropped, including messages in flight. A real
  link loses messages; it does not hold them.
- Never delayed or dropped (the test control plane): `test.inject`, messages
  to `team3.link`, and the stand-in's own `link.health`.

Logs `link.relay` and `link.drop` with the msg_id and type, never `msg.sent`
(contracts section 2, logging rule).
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import random
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from aegis.bus import tcp
from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import dumps, make, parse
from aegis.common.models import Envelope, LinkHealth

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

Side = Literal["ground", "vehicle"]
Sink = Callable[[Envelope], Awaitable[None]]
LinkStateName = Literal["CONNECTED", "DEGRADED", "LOST"]

OTHER: dict[str, Side] = {"ground": "vehicle", "vehicle": "ground"}
SELF = "team3.link"


@dataclass
class _InFlight:
    env: Envelope
    seq: int
    arrived: datetime
    ready: bool = False
    done: bool = False


class _SidePort:
    """What a LocalBus attaches as its link in single-process mode."""

    def __init__(self, standin: LinkStandin, side: Side):
        self._standin = standin
        self._side = side

    async def send(self, env: Envelope) -> None:
        await self._standin.submit(self._side, env)


class LinkStandin:
    def __init__(
        self,
        clock: Clock,
        cfg: Settings,
        log: MissionLog,
        rng: random.Random | None = None,
    ):
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.rng = rng or random.Random()
        s = cfg.standins.link
        self.latency_ms: float = s.base_latency_ms
        self.loss_pct: float = s.loss_pct
        self.jitter_ms: float = s.jitter_ms
        self._sinks: dict[Side, Sink] = {}
        self._pending: dict[Side, list[_InFlight]] = {"ground": [], "vehicle": []}
        self._locks: dict[Side, asyncio.Lock] = {
            "ground": asyncio.Lock(),
            "vehicle": asyncio.Lock(),
        }
        self._seq = itertools.count()
        self._tasks: set[asyncio.Task[None]] = set()
        self._outage_start: datetime | None = None
        self._outage_until: datetime | None = None
        self._state_before_outage: LinkStateName = self._threshold_state()
        self._last_state: LinkStateName | None = None
        self._health_task: asyncio.Task[None] | None = None

    # -- wiring --------------------------------------------------------------

    def attach(self, side: Side, sink: Sink) -> None:
        """Messages relayed towards `side` are handed to `sink`."""
        self._sinks[side] = sink

    def detach(self, side: Side) -> None:
        self._sinks.pop(side, None)

    def port(self, side: Side) -> _SidePort:
        """The link object a `side` LocalBus attaches (single-process mode)."""
        return _SidePort(self, side)

    async def start(self) -> None:
        if self._health_task is None:
            self._health_task = asyncio.create_task(
                self._health_loop(), name="link-health"
            )

    async def stop(self) -> None:
        tasks = list(self._tasks)
        if self._health_task is not None:
            tasks.append(self._health_task)
            self._health_task = None
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass

    # -- test controls (contracts section 10, target `link`) -----------------

    async def set(self, latency_ms: float, loss_pct: float) -> None:
        self.latency_ms = latency_ms
        self.loss_pct = loss_pct
        if not self.in_outage():
            self._state_before_outage = self._threshold_state()
        await self.emit_health()

    async def outage(self, seconds: float) -> None:
        now = self.clock.now()
        if not self.in_outage():
            self._state_before_outage = self._threshold_state()
            self._outage_start = now
        self._outage_until = now + timedelta(seconds=seconds)
        self.log.record("link.outage", seconds=seconds)
        # Messages already in flight are lost too.
        for side in ("ground", "vehicle"):
            for item in self._pending[side]:
                if not item.done:
                    item.done = True
                    self._drop(item.env, "outage")
            self._pending[side].clear()

    def in_outage(self) -> bool:
        return self._outage_until is not None and self.clock.now() < self._outage_until

    # -- relay ---------------------------------------------------------------

    async def submit(self, from_side: Side, env: Envelope) -> None:
        """A message entering the link from `from_side`."""
        if SELF in env.dst:
            await self._handle_own(env)
            if env.dst == [SELF]:
                return
        to_side = OTHER[from_side]
        if env.type == "test.inject":
            await self._deliver(to_side, env)  # control plane: immediate
            return
        if self.in_outage():
            self._drop(env, "outage")
            return
        if self.rng.random() * 100 < self.loss_pct:
            self._drop(env, "loss")
            return
        item = _InFlight(env, next(self._seq), self.clock.now())
        self._pending[to_side].append(item)
        delay_s = max(
            0.0, self.latency_ms + self.rng.uniform(-self.jitter_ms, self.jitter_ms)
        )
        task = asyncio.create_task(self._carry(to_side, item, delay_s / 1000))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _carry(self, to_side: Side, item: _InFlight, delay_s: float) -> None:
        await self.clock.sleep(delay_s)
        if item.done:
            return  # lost in an outage
        item.ready = True
        await self._flush(to_side)

    async def _flush(self, to_side: Side) -> None:
        async with self._locks[to_side]:
            while True:
                item = self._next_deliverable(to_side)
                if item is None:
                    return
                item.done = True
                self._pending[to_side].remove(item)
                if self.in_outage():
                    self._drop(item.env, "outage")
                    continue
                await self._deliver(to_side, item.env)

    def _next_deliverable(self, to_side: Side) -> _InFlight | None:
        """The best ready message with nothing in front of it. In front means
        a higher priority that arrived no later, or the same priority earlier."""
        pending = self._pending[to_side]

        def in_front(other: _InFlight, item: _InFlight) -> bool:
            if other.env.priority < item.env.priority:
                return other.arrived <= item.arrived
            return other.env.priority == item.env.priority and other.seq < item.seq

        for item in sorted(pending, key=lambda i: (i.env.priority, i.seq)):
            if item.ready and not any(
                in_front(o, item) for o in pending if o is not item
            ):
                return item
        return None

    async def _deliver(self, to_side: Side, env: Envelope) -> None:
        sink = self._sinks.get(to_side)
        if sink is None:
            self._drop(env, f"{to_side} side not connected")
            return
        try:
            await sink(env)
        except (ConnectionError, OSError) as exc:
            self._drop(env, f"write to {to_side} failed: {exc}")
            return
        self.log.record("link.relay", msg_id=str(env.msg_id), type=env.type, to=to_side)

    def _drop(self, env: Envelope, reason: str) -> None:
        self.log.record(
            "link.drop", msg_id=str(env.msg_id), type=env.type, reason=reason
        )

    async def _handle_own(self, env: Envelope) -> None:
        if env.type != "test.inject":
            return
        self.log.record("test.inject", env=env.model_dump(mode="json"))
        body = env.body
        if body.target != "link":
            return
        if body.action == "set":
            await self.set(body.params["latency_ms"], body.params["loss_pct"])
        elif body.action == "outage":
            await self.outage(body.params["seconds"])

    # -- link.health (I8) ----------------------------------------------------

    def _threshold_state(self) -> LinkStateName:
        lim = self.cfg.link
        if (
            self.latency_ms > lim.degraded_latency_ms
            or self.loss_pct > lim.degraded_loss_pct
        ):
            return "DEGRADED"
        return "CONNECTED"

    def state(self) -> LinkStateName:
        """LOST once an outage has lasted `link.lost_after_s`; in the first
        seconds of an outage, the state from before it (A-15)."""
        if self.in_outage():
            lasted = (self.clock.now() - self._outage_start).total_seconds()
            if lasted >= self.cfg.link.lost_after_s:
                return "LOST"
            return self._state_before_outage
        self._outage_start = None
        return self._threshold_state()

    def health(self) -> LinkHealth:
        return LinkHealth(
            state=self.state(), latency_ms=self.latency_ms, loss_pct=self.loss_pct
        )

    async def emit_health(self) -> None:
        body = self.health()
        if body.state != self._last_state:
            self.log.record("link.state", state=body.state, previous=self._last_state)
            self._last_state = body.state
        if "ground" not in self._sinks:
            return  # nobody to tell yet
        env = make("link.health", SELF, body, self.clock)
        await self._deliver("ground", env)  # control plane: never delayed or dropped

    async def _health_loop(self) -> None:
        period = 1.0 / self.cfg.timing.status_rate_hz
        while True:
            await self.emit_health()
            await self.clock.sleep(period)


# -- process mode ------------------------------------------------------------


class LinkServer:
    """Serves the stand-in on the two TCP ports, one client per side."""

    def __init__(self, standin: LinkStandin, cfg: Settings):
        self.standin = standin
        self.cfg = cfg
        self.log = standin.log
        self._servers: list[asyncio.Server] = []
        self._writers: dict[Side, asyncio.StreamWriter] = {}

    async def start(
        self, ground_port: int | None = None, vehicle_port: int | None = None
    ) -> None:
        net = self.cfg.network
        ports: dict[Side, int] = {
            "ground": net.link_ground_port if ground_port is None else ground_port,
            "vehicle": net.link_vehicle_port if vehicle_port is None else vehicle_port,
        }
        for side, port in ports.items():
            server = await tcp.serve(net.link_host, port, self._handler(side))
            self._servers.append(server)
            self.standin.attach(side, self._sink(side))
        await self.standin.start()

    def port_of(self, side: Side) -> int:
        index = 0 if side == "ground" else 1
        return self._servers[index].sockets[0].getsockname()[1]

    async def stop(self) -> None:
        await self.standin.stop()
        for w in list(self._writers.values()):
            await tcp.close(w)
        for s in self._servers:
            s.close()
            await s.wait_closed()

    def _sink(self, side: Side) -> Sink:
        async def write(env: Envelope) -> None:
            writer = self._writers.get(side)
            if writer is None:
                raise ConnectionError(f"no {side} client")
            await tcp.write_line(writer, dumps(env))

        return write

    def _handler(self, side: Side):
        async def on_connect(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            old = self._writers.get(side)
            if old is not None:
                await tcp.close(old)  # a reconnecting client replaces the old one
            self._writers[side] = writer
            self.log.record("link.client_connected", side=side)
            try:
                while True:
                    try:
                        line = await tcp.read_line(reader)
                    except tcp.LineTooLong as exc:
                        self.log.record(
                            "bus.invalid", raw=None, error=str(exc), side=side
                        )
                        break
                    except (ConnectionError, OSError):
                        break
                    if line is None:
                        break
                    if not line.strip():
                        continue
                    try:
                        env = parse(line)
                    except ValidationError as exc:
                        self.log.record(
                            "bus.invalid", raw=line, error=str(exc), side=side
                        )
                        continue
                    await self.standin.submit(side, env)
            finally:
                if self._writers.get(side) is writer:
                    del self._writers[side]
                    self.log.record("link.client_disconnected", side=side)
                await tcp.close(writer)

        return on_connect


async def run(run_id: str) -> None:
    from aegis.common.clock import RealClock
    from aegis.common.config import load_settings
    from aegis.ground.mission_log import MissionLog

    cfg = load_settings()
    clock = RealClock()
    log = MissionLog("link", run_id, clock, cfg)
    server = LinkServer(LinkStandin(clock, cfg, log), cfg)
    await server.start()
    log.record(
        "process.start", ports=[server.port_of("ground"), server.port_of("vehicle")]
    )
    try:
        await asyncio.Event().wait()  # until cancelled (Ctrl+C or run_all stops us)
    finally:
        await server.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Team 3 link stand-in")
    parser.add_argument("--run-id", default=None, help="shared run ID from run_all")
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.run_id or uuid.uuid4().hex[:8]))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
