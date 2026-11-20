"""Team 4 stand-in: power and mobility (task B6). Runs in the vehicle process.

- Battery starts at `start_battery_pct` and drains at
  `drain_pct_per_min × standins.time_scale` while the vehicle moves.
- `power.status` at 1 Hz and on change, to the controller and the ground.
- Logs every `payload.mass_report` and acks `cmd.estop`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make, make_ack
from aegis.common.models import Envelope, PowerStatus

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "team4.power"


class PowerStandin:
    def __init__(
        self,
        bus,
        clock: Clock,
        cfg: Settings,
        log: MissionLog,
        moving: Callable[[], bool] = lambda: False,
    ):
        """`moving` says whether the vehicle is moving. nav.state is not
        addressed to team4.power, so the vehicle process passes the Team 2
        stand-in's flag in directly."""
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.moving = moving
        s = cfg.standins
        self.battery_pct = s.power.start_battery_pct
        self.drivetrain_health = "OK"
        self.drain_pct_per_s = s.power.drain_pct_per_min * s.time_scale / 60.0
        self.period_s = 1.0 / cfg.timing.status_rate_hz
        self.last_mass_kg: float | None = None
        self._loop: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.bus.subscribe(
            ENDPOINT, self._on_message, types={"payload.mass_report", "cmd.estop"}
        )
        if self._loop is None:
            self._loop = asyncio.create_task(self._run(), name="power-standin")

    async def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
            try:
                await self._loop
            except asyncio.CancelledError:
                pass
            self._loop = None

    async def _on_message(self, env: Envelope) -> None:
        if env.type == "payload.mass_report":
            self.last_mass_kg = env.body.mass_kg
            self.log.record(
                "power.mass_report",
                msg_id=str(env.msg_id),
                mass_kg=env.body.mass_kg,
                release_energy_wh_nominal=env.body.release_energy_wh_nominal,
                release_energy_wh_max=env.body.release_energy_wh_max,
            )
        elif env.type == "cmd.estop":
            await self.bus.publish(make_ack(env, ENDPOINT, "RECEIVED", self.clock))
            await self.bus.publish(make_ack(env, ENDPOINT, "COMPLETED", self.clock))

    def est_range_km(self) -> float:
        """Distance left at the configured drain rate and speed (not time-scaled:
        the scale speeds up both and cancels)."""
        p = self.cfg.standins
        if p.power.drain_pct_per_min == 0:
            return 0.0
        minutes = self.battery_pct / p.power.drain_pct_per_min
        return minutes * 60.0 * p.nav.speed_mps / 1000.0

    def status(self) -> PowerStatus:
        return PowerStatus(
            battery_pct=round(self.battery_pct, 1),
            est_range_km=round(self.est_range_km(), 1),
            drivetrain_health=self.drivetrain_health,
        )

    async def emit(self) -> None:
        await self.bus.publish(
            make("power.status", ENDPOINT, self.status(), self.clock)
        )

    async def _run(self) -> None:
        while True:
            if self.moving():
                self.battery_pct = max(
                    0.0, self.battery_pct - self.drain_pct_per_s * self.period_s
                )
            await self.emit()
            await self.clock.sleep(self.period_s)

    # -- test hooks (contracts section 10, target `power`) ------------------------

    async def battery(self, pct: float) -> None:
        self.battery_pct = pct
        await self.emit()

    async def drivetrain(self, health: str) -> None:
        self.drivetrain_health = health
        await self.emit()
