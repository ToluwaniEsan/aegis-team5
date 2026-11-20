"""Ground-side status aggregation for the operator screen."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError

from aegis.common.envelope import make, parse
from aegis.common.models import Envelope, format_timestamp
from aegis.common.ui_models import (
    BlockedRoute,
    DeliverySummary,
    Freshness,
    LatLon,
    LinkView,
    NavView,
    PayloadView,
    Place,
    Sensors,
    Subsystem,
    VehicleHealth,
)

if TYPE_CHECKING:
    from aegis.bus.local_bus import LocalBus
    from aegis.common.clock import Clock
    from aegis.common.config import Settings
    from aegis.ground.mission_log import MissionLog


class StatusMonitor:
    """Receive validated events; views calculate age against the injected clock.

    The destination lookup uses mission IDs, including completed missions, so
    buffered deliveries can be resolved after the active mission has changed.
    Replayed faults are handed to the alert manager callback. The ack callback
    may be connected to the command manager when it becomes available.
    Delivery summaries are ordered by the original envelope sent_at; equal
    timestamps retain the order in which events were first processed.

    Retry progress is in memory and requires the sender to retry a failed
    batch. A callback or publish can take effect and then raise, so consumers
    must deduplicate by message ID. Delivery confirmations reuse the same ID
    across retries. Process crashes require durable replay and consumer-side
    idempotency; this class does not provide exactly-once delivery.
    """

    def __init__(
        self,
        bus: LocalBus,
        clock: Clock,
        cfg: Settings,
        log: MissionLog,
        destination_for: Callable[[str], Place | None],
        on_fault: Callable[[Envelope], Awaitable[None]] | None = None,
        on_ack: Callable[[Envelope], Awaitable[None]] | None = None,
    ) -> None:
        self.bus, self.clock, self.cfg, self.log = bus, clock, cfg, log
        self.destination_for = destination_for
        self.on_fault, self.on_ack = on_fault, on_ack
        self.latest: dict[str, Envelope] = {}
        self.seen: set[UUID] = set()
        self._last_link_received: datetime | None = None
        self._blocked: BlockedRoute | None = None
        self._blocked_at: datetime | None = None
        self._route_override: list[LatLon] | None = None
        self._route_override_at: datetime | None = None
        self.delivery: DeliverySummary | None = None
        self._pending_deliveries: dict[UUID, tuple[Envelope, datetime]] = {}
        self._delivery_order: dict[UUID, tuple[datetime, int]] = {}
        self._selected_delivery_order: tuple[datetime, int] | None = None
        self._confirmations: dict[UUID, Envelope] = {}
        self._replay_logged: set[UUID] = set()
        self.replayed_faults: list[Envelope] = []
        self.acks: list[Envelope] = []
        bus.subscribe("ground.status_monitor", self.handle)
        bus.subscribe("ground.command_manager", self.handle, {"ack"})

    async def handle(self, incoming: Envelope) -> None:
        try:
            env = parse(incoming.model_dump_json())
        except (ValidationError, ValueError, TypeError) as exc:
            self.log.record("bus.invalid", error=str(exc))
            return
        if env.msg_id in self.seen:
            return
        if env.type == "backlog.batch":
            for event in env.body.events:
                if event.msg_id in self.seen:
                    continue
                if event.msg_id not in self._replay_logged:
                    self.log.record(
                        "backlog.event",
                        env=event.model_dump(mode="json"),
                        original_time=format_timestamp(event.sent_at),
                    )
                    self._replay_logged.add(event.msg_id)
                await self._apply(event, replayed=True)
                self.seen.add(event.msg_id)
        else:
            await self._apply(env, replayed=False)
        self.seen.add(env.msg_id)

    async def _apply(self, env: Envelope, *, replayed: bool) -> None:
        if env.type in {"payload.status", "nav.state", "power.status", "link.health"}:
            if env.type == "link.health" and not replayed:
                self._last_link_received = self.clock.now()
            previous = self.latest.get(env.type)
            if previous is None or env.sent_at > previous.sent_at:
                if previous is None or previous.body != env.body:
                    self.log.record(
                        "state.change", group=env.type, env=env.model_dump(mode="json")
                    )
                self.latest[env.type] = env
                if (
                    env.type == "nav.state"
                    and self._route_override_at is not None
                    and env.sent_at > self._route_override_at
                ):
                    self._route_override = None
                    self._route_override_at = None
        elif env.type == "nav.route_blocked":
            previous = self.latest.get("nav.state")
            old_route = (
                []
                if previous is None
                else [LatLon(**p.model_dump()) for p in previous.body.route]
            )
            self._blocked = BlockedRoute(
                reason=env.body.reason,
                at=LatLon(**env.body.blocked_at.model_dump()),
                old_route=old_route,
                new_eta_s=env.body.new_eta_s,
                since=format_timestamp(env.sent_at),
            )
            self._blocked_at = env.sent_at
            if previous is None or env.sent_at >= previous.sent_at:
                self._route_override = [
                    LatLon(**p.model_dump()) for p in env.body.new_route
                ]
                self._route_override_at = env.sent_at
            self.log.record(
                "state.change", group="nav.blocked", env=env.model_dump(mode="json")
            )
        elif env.type == "payload.delivered":
            if env.msg_id not in self._delivery_order:
                received = self.clock.now()
                self._delivery_order[env.msg_id] = (
                    env.sent_at,
                    len(self._delivery_order),
                )
                self._pending_deliveries[env.msg_id] = (env, received)
            self.resolve_deliveries()
            if env.msg_id not in self._confirmations:
                self._confirmations[env.msg_id] = make(
                    "t1.delivery_confirmation",
                    "ground.status_monitor",
                    env.body,
                    self.clock,
                    mission_id=env.body.mission_id,
                    payload_id=env.body.payload_id,
                )
            await self.bus.publish(self._confirmations[env.msg_id])
        elif env.type in {"fault.raised", "fault.cleared"} and replayed:
            if self.on_fault is not None:
                await self.on_fault(env)
            self.replayed_faults.append(env)
        elif env.type == "ack":
            if self.on_ack is not None:
                await self.on_ack(env)
            self.acks.append(env)
        elif env.type == "t1.system_mode":
            self.latest[env.type] = env

    def resolve_deliveries(self) -> None:
        for msg_id, (env, received) in list(self._pending_deliveries.items()):
            body = env.body
            destination = self.destination_for(body.mission_id)
            if destination is None:
                continue
            order = self._delivery_order[msg_id]
            if (
                self._selected_delivery_order is not None
                and order <= self._selected_delivery_order
            ):
                del self._pending_deliveries[msg_id]
                continue
            delivery = DeliverySummary(
                mission_id=body.mission_id,
                payload_id=body.payload_id,
                destination=destination,
                released_at=format_timestamp(body.released_at),
                confirmed_at=format_timestamp(received),
                confirm_latency_s=(received - body.released_at).total_seconds(),
                mass_kg=body.mass_kg,
                energy_used_wh=body.energy_used_wh,
            )
            self.log.record(
                "state.change",
                group="delivery",
                delivery=delivery.model_dump(mode="json"),
            )
            self.delivery = delivery
            self._selected_delivery_order = order
            del self._pending_deliveries[msg_id]

    def freshness(self, group: str) -> Freshness:
        env = self.latest.get(group)
        if env is None:
            return Freshness(updated_at=None, age_s=None, stale=True)
        age = (self.clock.now() - env.sent_at).total_seconds()
        return Freshness(
            updated_at=format_timestamp(env.sent_at),
            age_s=age,
            stale=age > self.cfg.timing.stale_after_s,
        )

    def payload_view(self) -> PayloadView | None:
        env = self.latest.get("payload.status")
        if env is None:
            return None
        body = env.body
        sensors = Sensors(**body.sensors.model_dump())
        sensor_health = max(
            (sensors.load_cell, sensors.lock, sensors.shift),
            key={"OK": 0, "WARN": 1, "FAULT": 2, "UNKNOWN": 1}.get,
        )
        return PayloadView(
            **self.freshness("payload.status").model_dump(),
            state=body.state,
            held_from=body.held_from,
            payload_id=env.payload_id,
            secured=body.secured,
            locked=body.locked,
            mass_kg=body.mass_kg,
            shift_cm=body.shift_cm,
            release_energy_wh=body.release_energy_wh,
            sensor_health=sensor_health,
            sensors=sensors,
            prerelease_authorized=body.prerelease_authorized,
            departure_permitted=body.departure_permitted,
            departure_reason=body.departure_reason,
        )

    def nav_view(
        self, origin: Place | None = None, destination: Place | None = None
    ) -> NavView:
        env = self.latest.get("nav.state")
        body = None if env is None else env.body
        return NavView(
            **self.freshness("nav.state").model_dump(),
            origin=origin,
            destination=destination,
            position=None if body is None else LatLon(**body.position.model_dump()),
            route=self.route(),
            progress_pct=None if body is None else body.progress_pct,
            moving=False if body is None else body.moving,
            speed_mps=None if body is None else body.speed_mps,
            eta_s=None if body is None else body.eta_s,
            blocked=self.blocked(),
        )

    def link_view(self) -> LinkView:
        env = self.latest.get("link.health")
        if env is None:
            return LinkView(
                **self.freshness("link.health").model_dump(),
                state="LOST",
                latency_ms=None,
                loss_pct=None,
            )
        lost = (
            self._last_link_received is None
            or (self.clock.now() - self._last_link_received).total_seconds()
            >= self.cfg.link.lost_after_s
        )
        return LinkView(
            **self.freshness("link.health").model_dump(),
            state="LOST" if lost else env.body.state,
            latency_ms=env.body.latency_ms,
            loss_pct=env.body.loss_pct,
        )

    def blocked(self) -> BlockedRoute | None:
        if (
            self._blocked_at is not None
            and (self.clock.now() - self._blocked_at).total_seconds()
            >= self.cfg.timing.route_blocked_clear_s
        ):
            self._blocked = None
            self._blocked_at = None
            self.log.record("state.change", group="nav.blocked", value=None)
        return self._blocked

    def route(self) -> list[LatLon]:
        if self._route_override is not None:
            return self._route_override.copy()
        env = self.latest.get("nav.state")
        return [] if env is None else [LatLon(**p.model_dump()) for p in env.body.route]

    def vehicle_health(self) -> VehicleHealth:
        power, nav, payload = (
            self.latest.get(key)
            for key in ("power.status", "nav.state", "payload.status")
        )
        link = self.link_view()
        battery_status = (
            "UNKNOWN"
            if power is None
            else (
                "FAULT"
                if power.body.battery_pct <= self.cfg.alerts.power_fault_pct
                else "WARN"
                if power.body.battery_pct < self.cfg.alerts.power_low_pct
                else "OK"
            )
        )
        sensor_status = (
            "UNKNOWN"
            if payload is None
            else max(
                (
                    payload.body.sensors.load_cell,
                    payload.body.sensors.lock,
                    payload.body.sensors.shift,
                ),
                key={"OK": 0, "WARN": 1, "FAULT": 2}.get,
            )
        )
        rows = [
            (
                "power",
                "Power & Battery",
                4,
                "power.status",
                battery_status,
                ""
                if power is None
                else f"{power.body.battery_pct:g} % · {power.body.est_range_km:g} km",
            ),
            (
                "mobility",
                "Mobility & Drivetrain",
                4,
                "power.status",
                "UNKNOWN" if power is None else power.body.drivetrain_health,
                "" if power is None else power.body.drivetrain_health,
            ),
            (
                "navigation",
                "Navigation Sensors",
                2,
                "nav.state",
                "UNKNOWN" if nav is None else nav.body.health,
                "" if nav is None else f"{nav.body.speed_mps:g} m/s",
            ),
            (
                "comms",
                "Comms Link",
                3,
                "link.health",
                "UNKNOWN"
                if "link.health" not in self.latest
                else {"CONNECTED": "OK", "DEGRADED": "WARN", "LOST": "FAULT"}[
                    link.state
                ],
                ""
                if link.latency_ms is None
                else f"{link.latency_ms:g} ms · {link.loss_pct:g} %",
            ),
            (
                "payload_sensors",
                "Payload Bay Sensors",
                5,
                "payload.status",
                sensor_status,
                "" if payload is None else sensor_status,
            ),
        ]
        subsystems = [
            Subsystem(
                key=key,
                label=label,
                team=team,
                status=status,
                detail=detail,
                **self.freshness(group).model_dump(),
            )
            for key, label, team, group, status, detail in rows
        ]
        overall = (
            "FAULT"
            if any(row.status == "FAULT" for row in subsystems)
            else "DEGRADED"
            if any(row.status in {"WARN", "UNKNOWN"} or row.stale for row in subsystems)
            else "NOMINAL"
        )
        return VehicleHealth(overall=overall, subsystems=subsystems)
