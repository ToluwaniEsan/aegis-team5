"""Payload Simulator (task A3): the payload bay, its lock and its sensors.

It talks to the Payload Controller only through `sim.command` and
`sim.reading`, so real hardware can replace it later.

GEN-004: the lock state belongs here. Nothing opens the lock except an
UNLOCK, RELEASE or UNLOAD command, so a dead controller leaves it locked.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make
from aegis.common.models import Envelope, Sensors, SimReading

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "vehicle.payload_simulator"
SENSOR_NAMES = ("load_cell", "lock", "shift")


class PayloadSimulator:
    def __init__(
        self,
        bus,
        clock: Clock,
        cfg: Settings,
        log: MissionLog,
        rng: random.Random | None = None,
    ):
        p = cfg.payload
        if p.sim_noise_kg >= p.weight_accuracy_kg:
            raise ValueError(
                "payload.sim_noise_kg must be below payload.weight_accuracy_kg"
            )
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.rng = rng or random.Random()

        self.bay_mass_kg = 0.0  # true mass
        self.locked = False
        self.shift_cm = 0.0
        self.sensors = {name: "OK" for name in SENSOR_NAMES}
        self.release_jam = False
        self.release_in_progress = False
        self.release_done = False
        self.settled = True
        self.mass_override_kg: float | None = None
        self.releases = 0

        self._ops: dict[str, asyncio.Task[None]] = {}  # mechanism steps in progress
        self._loop: asyncio.Task[None] | None = None

    # -- lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        self.bus.subscribe(ENDPOINT, self._on_message, types={"sim.command"})
        if self._loop is None:
            self._loop = asyncio.create_task(self._report_loop(), name="simulator")

    async def stop(self) -> None:
        tasks = [*self._ops.values(), *([self._loop] if self._loop else [])]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._ops.clear()
        self._loop = None

    # -- sim.command -------------------------------------------------------------

    async def _on_message(self, env: Envelope) -> None:
        body = env.body
        if body.action == "LOAD":
            await self.load(body.mass_kg)
        elif body.action == "LOCK":
            self._run("lock", self._lock())
        elif body.action == "UNLOCK":
            self._cancel("lock")
            self.locked = False
            await self.emit()
        elif body.action == "RELEASE":
            await self.release()
        elif body.action == "UNLOAD":
            await self.unload()

    async def load(self, mass_kg: float) -> None:
        """From an empty bay: placed after load_time_s. With a payload aboard
        (a payload update): the lock stays closed and the new mass settles
        after reweigh_time_s."""
        delay = (
            self.cfg.payload.reweigh_time_s
            if self.bay_mass_kg > 0
            else self.cfg.payload.load_time_s
        )
        self.settled = False
        self.release_done = False
        await self.emit()
        self._run("load", self._settle(mass_kg, delay))

    async def release(self) -> None:
        self.locked = False
        self.release_in_progress = True
        self.release_done = False
        await self.emit()
        self._run("release", self._release())

    async def unload(self) -> None:
        for kind in list(self._ops):
            self._cancel(kind)
        self.locked = False
        self.bay_mass_kg = 0.0
        self.mass_override_kg = None
        self.shift_cm = 0.0
        self.settled = True
        self.release_in_progress = False
        self.release_done = False
        await self.emit()

    async def _settle(self, mass_kg: float, delay: float) -> None:
        await self.clock.sleep(delay)
        self.bay_mass_kg = mass_kg
        self.mass_override_kg = None
        self.settled = True
        await self.emit()

    async def _lock(self) -> None:
        await self.clock.sleep(self.cfg.payload.secure_time_s)
        self.locked = True
        await self.emit()

    async def _release(self) -> None:
        await self.clock.sleep(self.cfg.payload.release_time_s)
        if self.release_jam:
            return  # a jam means it never finishes
        self.bay_mass_kg = 0.0
        self.mass_override_kg = None
        self.shift_cm = 0.0
        self.release_in_progress = False
        self.release_done = True
        self.releases += 1
        await self.emit()

    def _run(self, kind: str, coro) -> None:
        """One step of each kind at a time; a new one replaces the old."""
        self._cancel(kind)
        self._ops[kind] = asyncio.create_task(coro, name=f"simulator-{kind}")

    def _cancel(self, kind: str) -> None:
        task = self._ops.pop(kind, None)
        if task is not None and not task.done():
            task.cancel()

    @property
    def release_energy_wh(self) -> float | None:
        """Energy of the last release (AEG-509): the configured nominal value."""
        return self.cfg.payload.release_energy_wh_nominal if self.releases else None

    # -- test hooks (contracts section 10, target `payload`) ---------------------

    async def inject_shift(self, cm: float) -> None:
        self.shift_cm = cm
        await self.emit()

    async def set_sensor(self, name: str, health: str) -> None:
        if name not in self.sensors:
            raise ValueError(f"unknown sensor {name!r}; expected one of {SENSOR_NAMES}")
        self.sensors[name] = health
        await self.emit()

    async def override_mass(self, kg: float) -> None:
        self.mass_override_kg = kg
        await self.emit()

    async def set_release_jam(self, on: bool) -> None:
        self.release_jam = on

    # -- sim.reading ---------------------------------------------------------------

    def reading(self) -> SimReading:
        true_mass = (
            self.mass_override_kg
            if self.mass_override_kg is not None
            else self.bay_mass_kg
        )
        mass: float | None = None
        if self.sensors["load_cell"] != "FAULT":
            noise = self.cfg.payload.sim_noise_kg
            mass = (
                max(0.0, true_mass + self.rng.uniform(-noise, noise))
                if true_mass
                else 0.0
            )
        shift = None if self.sensors["shift"] == "FAULT" else self.shift_cm
        return SimReading(
            mass_kg=mass,
            settled=self.settled,
            shift_cm=shift,
            locked=self.locked,
            release_done=self.release_done,
            sensors=Sensors(**self.sensors),
        )

    async def emit(self) -> None:
        env = make("sim.reading", ENDPOINT, self.reading(), self.clock)
        await self.bus.publish(env)

    async def _report_loop(self) -> None:
        period = 1.0 / self.cfg.timing.status_rate_hz
        while True:
            await self.emit()
            await self.clock.sleep(period)
