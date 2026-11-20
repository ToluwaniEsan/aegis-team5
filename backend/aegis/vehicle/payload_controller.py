"""Payload Controller (task A4): the thin async shell around `rules.step`.

Bus handlers only queue events. One worker takes them in order, runs the pure
`step`, and carries out the actions, so the controller never handles a message
in the middle of its own publish. A 1 Hz tick drives timers and the periodic
`payload.status` and `payload.interlock`.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make, make_ack
from aegis.common.models import Envelope
from aegis.vehicle import rules
from aegis.vehicle.rules import CtrlState

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "vehicle.payload_controller"
TYPES = {
    *rules.COMMANDS,
    "cmd.estop",
    "nav.state",
    "power.status",
    "sim.reading",
    "int.link_state",
}


def to_event(env: Envelope) -> rules.Event | None:
    if env.type.startswith("cmd."):
        return rules.Command(env)
    if env.type == "sim.reading":
        return rules.Reading(env.body)
    if env.type == "nav.state":
        return rules.Nav(env.body)
    if env.type == "power.status":
        return rules.Power(env.body)
    if env.type == "int.link_state":
        return rules.LinkLost() if env.body.state == "LOST" else rules.LinkRestored()
    return None


class PayloadController:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.state = CtrlState()
        self.period_s = 1.0 / cfg.timing.status_rate_hz
        self._queue: asyncio.Queue[rules.Event] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._last_status = None
        self._last_interlock = None

    # -- lifecycle -----------------------------------------------------------------

    async def start(self) -> None:
        self.bus.subscribe(ENDPOINT, self._on_message, types=TYPES)
        if not self._tasks:
            self._tasks = [
                asyncio.create_task(self._worker(), name="controller"),
                asyncio.create_task(self._ticker(), name="controller-tick"),
            ]

    async def stop(self) -> None:
        """Also the GEN-004 crash hook: the simulator keeps the lock closed."""
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks = []

    @property
    def running(self) -> bool:
        return bool(self._tasks) and not any(t.done() for t in self._tasks)

    async def drain(self) -> None:
        """Wait until every queued event has been handled (for tests)."""
        if self.running:
            await self._queue.join()

    # -- inputs ------------------------------------------------------------------------

    async def _on_message(self, env: Envelope) -> None:
        if not self.running:
            return  # stopped or crashed: nothing handles events any more
        event = to_event(env)
        if event is not None:
            self._queue.put_nowait(event)

    async def unload(self) -> None:
        """Test action payload/unload."""
        self._queue.put_nowait(rules.Unload())

    async def _ticker(self) -> None:
        while True:
            self._queue.put_nowait(rules.Tick())
            await self.clock.sleep(self.period_s)

    async def _worker(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._handle(event)
            except Exception as exc:  # noqa: BLE001 - log it and keep the controller alive
                self.log.record(
                    "controller.error",
                    event=type(event).__name__,
                    error=f"{type(exc).__name__}: {exc}",
                )
            finally:
                self._queue.task_done()

    # -- step and actions -------------------------------------------------------------

    async def _handle(self, event: rules.Event) -> None:
        before = self.state
        after, actions = rules.step(before, event, self.clock.now(), self.cfg)
        self.state = after
        if after.state != before.state or after.held_from != before.held_from:
            self.log.record(
                "state.change",
                previous=before.state,
                state=after.state,
                held_from=after.held_from,
                mission_id=self._mission_id(after, before),
            )
        for action in actions:
            await self._do(action, after, before)
        await self._publish_status(force=isinstance(event, rules.Tick))

    def _mission_id(self, *states: CtrlState) -> str | None:
        return next((s.mission.mission_id for s in states if s.mission), None)

    def _payload_id(self, *states: CtrlState) -> str | None:
        return next((s.mission.payload_id for s in states if s.mission), None)

    async def _do(
        self, action: rules.Action, after: CtrlState, before: CtrlState
    ) -> None:
        if isinstance(action, rules.Ack):
            env = make_ack(
                action.command,
                ENDPOINT,
                action.result,
                self.clock,
                reason_code=action.reason_code,
                reason=action.reason,
            )
        elif isinstance(action, rules.Send):
            env = make(
                action.type,
                ENDPOINT,
                action.body,
                self.clock,
                mission_id=self._mission_id(after, before),
                payload_id=self._payload_id(after, before),
            )
        else:
            self.log.record(action.kind, **action.fields)
            return
        await self.bus.publish(env)

    async def _publish_status(self, force: bool) -> None:
        """payload.status and payload.interlock at 1 Hz and on every change."""
        status = rules.status(self.state, self.cfg)
        if force or status != self._last_status:
            self._last_status = status
            await self.bus.publish(self._make("payload.status", status))
        lock = rules.interlock(self.state, self.cfg)
        if force or lock != self._last_interlock:
            self._last_interlock = lock
            await self.bus.publish(self._make("payload.interlock", lock))

    def _make(self, type_: str, body) -> Envelope:
        return make(
            type_,
            ENDPOINT,
            body,
            self.clock,
            mission_id=self._mission_id(self.state),
            payload_id=self._payload_id(self.state),
        )
