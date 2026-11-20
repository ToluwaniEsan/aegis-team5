"""Test agent (part of task A9): endpoint `vehicle.test_agent`.

Receives `test.inject` from the ground's Fault Injector (B14) and calls the
simulator hooks (A3), the stand-in hooks (B5, B6), or the controller crash
and unload hooks. Each injection is logged as `test.applied`, or
`test.error` if the hook fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aegis.common.models import Envelope

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog
    from aegis.standins.nav import NavStandin
    from aegis.standins.power import PowerStandin
    from aegis.vehicle.payload_controller import PayloadController
    from aegis.vehicle.simulator import PayloadSimulator

ENDPOINT = "vehicle.test_agent"


class TestAgent:
    __test__ = False  # not a pytest test class

    def __init__(
        self,
        bus,
        log: MissionLog,
        simulator: PayloadSimulator,
        controller: PayloadController,
        nav: NavStandin,
        power: PowerStandin,
    ):
        self.bus = bus
        self.log = log
        sim, ctrl = simulator, controller
        # (target, action) -> hook taking the params. Every vehicle row of
        # contracts section 10.
        self.hooks = {
            ("payload", "shift"): lambda p: sim.inject_shift(p["cm"]),
            ("payload", "sensor"): lambda p: sim.set_sensor(p["sensor"], p["health"]),
            ("payload", "mass_override"): lambda p: sim.override_mass(p["kg"]),
            ("payload", "release_jam"): lambda p: sim.set_release_jam(p["on"]),
            ("payload", "controller_crash"): lambda p: ctrl.stop(),
            ("payload", "unload"): lambda p: ctrl.unload(),
            ("nav", "depart"): lambda p: nav.depart(),
            ("nav", "arrive"): lambda p: nav.arrive(),
            ("nav", "stop"): lambda p: nav.halt(),
            ("nav", "block_route"): lambda p: nav.block_route(p["reason"]),
            ("nav", "health"): lambda p: nav.set_health(p["health"]),
            ("power", "battery"): lambda p: power.battery(p["pct"]),
            ("power", "drivetrain"): lambda p: power.drivetrain(p["health"]),
        }

    async def start(self) -> None:
        self.bus.subscribe(ENDPOINT, self._on_inject, types={"test.inject"})

    async def stop(self) -> None:
        pass

    async def _on_inject(self, env: Envelope) -> None:
        body = env.body
        fields = {
            "msg_id": str(env.msg_id),
            "target": body.target,
            "action": body.action,
            "params": body.params,
        }
        hook = self.hooks.get((body.target, body.action))
        if hook is None:
            self.log.record("test.error", **fields, error="not a vehicle target")
            return
        try:
            await hook(body.params)
        except Exception as exc:  # noqa: BLE001 - a bad injection must not stop the agent
            self.log.record(
                "test.error", **fields, error=f"{type(exc).__name__}: {exc}"
            )
            return
        self.log.record("test.applied", **fields)
