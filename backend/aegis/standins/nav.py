"""Team 2 stand-in: navigation (task B5). Runs in the vehicle process.

- `nav.assign`: plan a straight route of `standins.nav.route_points` points.
- Departs only while the last `payload.interlock` permits it (AEG-511), and,
  with `auto_depart: false`, only after the test action `nav/depart`.
- Moves at `speed_mps × standins.time_scale` and sends `nav.state` at 1 Hz
  and on every change to the controller and the Status Monitor.
- `cmd.abort` and `cmd.return_to_origin` route home; `cmd.change_destination`
  re-plans from the current position; `cmd.estop` stops at once, and the
  vehicle stays stopped until a new command (decision D-06).
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make, make_ack
from aegis.common.models import Envelope, LatLon, NavState, Place, RouteBlocked

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "team2.nav"
EARTH_RADIUS_M = 6_371_000.0  # a physical constant, not a limit
TYPES = {
    "nav.assign",
    "payload.interlock",
    "cmd.abort",
    "cmd.return_to_origin",
    "cmd.change_destination",
    "cmd.estop",
}


def distance_m(a: LatLon, b: LatLon) -> float:
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def straight_route(a: LatLon, b: LatLon, points: int) -> list[LatLon]:
    return [
        LatLon(
            lat=a.lat + (b.lat - a.lat) * i / (points - 1),
            lon=a.lon + (b.lon - a.lon) * i / (points - 1),
        )
        for i in range(points)
    ]


def _lerp(a: LatLon, b: LatLon, f: float) -> LatLon:
    return LatLon(lat=a.lat + (b.lat - a.lat) * f, lon=a.lon + (b.lon - a.lon) * f)


class NavStandin:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.speed_mps = cfg.standins.nav.speed_mps * cfg.standins.time_scale
        self.period_s = 1.0 / cfg.timing.status_rate_hz

        home = cfg.places[0]
        self.origin: Place | None = None
        self.destination: Place | None = None
        self.mission_id: str | None = None
        self.position = LatLon(lat=home.lat, lon=home.lon)
        self.route: list[LatLon] = []
        self.traveled_m = 0.0  # along the current route
        self.trip_done_m = 0.0  # on earlier routes of this trip (for progress)
        self.heading: str | None = None  # "destination" or "origin"
        self.moving = False
        self.at_destination = False
        self.at_origin = True
        self.health = "OK"
        self.permitted = False  # from the last payload.interlock
        self.depart_requested = False
        self._loop: asyncio.Task[None] | None = None

    # -- lifecycle -----------------------------------------------------------------

    async def start(self) -> None:
        self.bus.subscribe(ENDPOINT, self._on_message, types=TYPES)
        if self._loop is None:
            self._loop = asyncio.create_task(self._run(), name="nav-standin")

    async def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
            try:
                await self._loop
            except asyncio.CancelledError:
                pass
            self._loop = None

    # -- messages --------------------------------------------------------------------

    async def _on_message(self, env: Envelope) -> None:
        if env.type == "payload.interlock":
            self.permitted = env.body.departure_permitted
            await self._maybe_depart()
            return
        await self._ack(env, "RECEIVED")
        body = env.body
        if env.type == "nav.assign":
            self.mission_id = body.mission_id
            self.origin, self.destination = body.origin, body.destination
            self.position = LatLon(lat=body.origin.lat, lon=body.origin.lon)
            self._plan(self.destination, "destination", new_trip=True)
            self.moving = False
            self.depart_requested = False
            self.at_origin, self.at_destination = True, False
        elif env.type in ("cmd.abort", "cmd.return_to_origin"):
            if self.origin is not None:
                self._plan(self.origin, "origin")
                self._go()
        elif env.type == "cmd.change_destination":
            self.destination = body.destination
            self._plan(self.destination, "destination")
            if self.heading and not self.at_origin:
                self._go()
        elif env.type == "cmd.estop":
            self.moving = False
        await self._ack(env, "COMPLETED")
        await self.emit()

    async def _ack(self, env: Envelope, result: str) -> None:
        await self.bus.publish(make_ack(env, ENDPOINT, result, self.clock))

    # -- route and movement ------------------------------------------------------------

    def _plan(self, target: Place, heading: str, new_trip: bool = False) -> None:
        if new_trip:
            self.trip_done_m = 0.0
        else:
            self.trip_done_m += self.traveled_m
        self.route = straight_route(
            self.position, target, self.cfg.standins.nav.route_points
        )
        self.traveled_m = 0.0
        self.heading = heading

    def _go(self) -> None:
        if self.remaining_m() > 0:
            self.moving = True
            self.at_origin = self.at_destination = False

    async def _maybe_depart(self) -> None:
        """Leave the origin only while the interlock permits it (AEG-511)."""
        ready = self.cfg.standins.nav.auto_depart or self.depart_requested
        if (
            self.permitted
            and ready
            and not self.moving
            and self.at_origin
            and self.heading == "destination"
        ):
            self.depart_requested = False
            self._go()
            self.log.record("nav.depart", mission_id=self.mission_id)
            await self.emit()

    def route_length_m(self) -> float:
        return sum(distance_m(a, b) for a, b in zip(self.route, self.route[1:]))

    def remaining_m(self) -> float:
        return max(0.0, self.route_length_m() - self.traveled_m)

    def _point_at(self, d: float) -> LatLon:
        for a, b in zip(self.route, self.route[1:]):
            seg = distance_m(a, b)
            if d <= seg:
                return _lerp(a, b, d / seg if seg else 1.0)
            d -= seg
        return self.route[-1]

    async def _step(self) -> None:
        if not self.moving:
            return
        self.traveled_m += self.speed_mps * self.period_s
        if self.traveled_m >= self.route_length_m():
            await self._arrive()
            return
        self.position = self._point_at(self.traveled_m)

    async def _arrive(self) -> None:
        self.traveled_m = self.route_length_m()
        self.position = self.route[-1]
        self.moving = False
        self.at_destination = self.heading == "destination"
        self.at_origin = self.heading == "origin"
        self.log.record("nav.arrive", heading=self.heading, mission_id=self.mission_id)
        await self.emit()

    # -- nav.state -------------------------------------------------------------------

    def state(self) -> NavState:
        total = self.trip_done_m + self.route_length_m()
        done = self.trip_done_m + self.traveled_m
        has_route = bool(self.route)
        return NavState(
            moving=self.moving,
            speed_mps=self.speed_mps if self.moving else 0.0,
            position=self.position,
            at_destination=self.at_destination,
            at_origin=self.at_origin,
            eta_s=self.remaining_m() / self.speed_mps if has_route else None,
            progress_pct=min(100.0, 100.0 * done / total) if total else 0.0,
            route=self.route,
            health=self.health,
        )

    async def emit(self) -> None:
        await self.bus.publish(
            make(
                "nav.state",
                ENDPOINT,
                self.state(),
                self.clock,
                mission_id=self.mission_id,
            )
        )

    async def _run(self) -> None:
        while True:
            await self._step()
            await self.emit()
            await self.clock.sleep(self.period_s)

    # -- test hooks (contracts section 10, target `nav`) -----------------------------

    async def depart(self) -> None:
        self.depart_requested = True
        await self._maybe_depart()

    async def arrive(self) -> None:
        if self.route:
            await self._arrive()

    async def halt(self) -> None:
        """Test action `nav/stop`."""
        self.moving = False
        await self.emit()

    async def block_route(self, reason: str) -> None:
        """Add a detour point, send nav.route_blocked, then carry on."""
        if not self.route or self.remaining_m() == 0:
            return
        end = self.route[-1]
        mid = _lerp(self.position, end, 0.5)
        # Offset the detour sideways by a quarter of the remaining leg.
        dlat, dlon = end.lat - self.position.lat, end.lon - self.position.lon
        detour = LatLon(lat=mid.lat - dlon * 0.25, lon=mid.lon + dlat * 0.25)
        blocked_at = self.position
        self.trip_done_m += self.traveled_m
        points = self.cfg.standins.nav.route_points
        half = max(2, points // 2)
        first = straight_route(self.position, detour, half)
        self.route = first + straight_route(detour, end, half)[1:]
        self.traveled_m = 0.0
        body = RouteBlocked(
            reason=reason,
            blocked_at=blocked_at,
            new_route=self.route,
            new_eta_s=self.remaining_m() / self.speed_mps,
        )
        await self.bus.publish(
            make(
                "nav.route_blocked",
                ENDPOINT,
                body,
                self.clock,
                mission_id=self.mission_id,
            )
        )
        await self.emit()

    async def set_health(self, health: str) -> None:
        self.health = health
        await self.emit()
