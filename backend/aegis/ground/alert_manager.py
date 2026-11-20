"""Ground alerts and forwarding of vehicle faults to Team 1."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from pydantic import ValidationError

from aegis.common.envelope import make, parse
from aegis.common.models import FAULT_CATALOG, Envelope, format_timestamp
from aegis.common.ui_models import AlertView, CommandView


class AlertManager:
    def __init__(self, bus, clock, cfg, log, status):
        self.bus, self.clock, self.cfg, self.log, self.status = (
            bus,
            clock,
            cfg,
            log,
            status,
        )
        self.alerts: dict[str, AlertView] = {}
        self._vehicle_ids: set[str] = set()
        self._ground_active: dict[str, str] = {}
        self._seen: set[UUID] = set()
        self._cleared: set[str] = set()
        self._reports: dict[UUID, Envelope] = {}
        self._reported: set[UUID] = set()
        self._task: asyncio.Task | None = None
        self.on_change = None
        bus.subscribe(
            "ground.alert_manager", self.handle, {"fault.raised", "fault.cleared"}
        )
        bus.subscribe(
            "ground.status_monitor",
            self._status_changed,
            {
                "payload.status",
                "nav.state",
                "power.status",
                "link.health",
                "nav.route_blocked",
            },
        )
        status.on_fault = self.handle

    def views(self) -> list[AlertView]:
        values = [a for a in self.alerts.values() if a.active or not a.acknowledged]
        values.sort(key=lambda a: a.raised_at, reverse=True)
        values.sort(
            key=lambda a: {"CRITICAL": 0, "WARNING": 1, "CAUTION": 2}[a.severity]
        )
        return values

    def _set(self, alert: AlertView) -> None:
        if self.alerts.get(alert.alert_id) == alert:
            return
        self.log.record("alert.change", alert=alert.model_dump(mode="json"))
        self.alerts[alert.alert_id] = alert
        if self.on_change:
            self.on_change()

    async def handle(self, incoming: Envelope) -> None:
        try:
            env = parse(incoming.model_dump_json())
        except (ValidationError, ValueError, TypeError) as exc:
            self.log.record("bus.invalid", error=str(exc))
            return
        if env.msg_id in self._seen or env.type not in {
            "fault.raised",
            "fault.cleared",
        }:
            return
        fault_id = str(env.body.fault_id)
        if env.type == "fault.cleared":
            self._cleared.add(fault_id)
            if fault_id in self.alerts:
                self._set(self.alerts[fault_id].model_copy(update={"active": False}))
        else:
            body = env.body
            if env.msg_id not in self._reports:
                self._reports[env.msg_id] = make(
                    "t1.fault_report",
                    "ground.alert_manager",
                    body,
                    self.clock,
                    mission_id=env.mission_id,
                    payload_id=env.payload_id,
                )
            if env.msg_id not in self._reported:
                await self.bus.publish(self._reports[env.msg_id])
                self._reported.add(env.msg_id)
            if fault_id not in self.alerts:
                self._vehicle_ids.add(fault_id)
                self._set(
                    AlertView(
                        alert_id=fault_id,
                        code=body.code,
                        severity=body.severity,
                        title=body.message,
                        source=body.source,
                        recommended_action=body.recommended_action,
                        raised_at=format_timestamp(env.sent_at),
                        acknowledged=False,
                        active=fault_id not in self._cleared,
                    )
                )
        self._seen.add(env.msg_id)

    async def acknowledge_ground(self, alert_id: str) -> bool:
        alert = self.alerts.get(alert_id)
        if not alert or alert_id in self._vehicle_ids or alert.acknowledged:
            return False
        self._set(alert.model_copy(update={"acknowledged": True}))
        return True

    async def acknowledge_vehicle(self, alert_id: str) -> None:
        if alert_id in self._vehicle_ids and alert_id in self.alerts:
            self._set(self.alerts[alert_id].model_copy(update={"acknowledged": True}))

    async def _ground(self, code: str, active: bool, title: str, source: str) -> None:
        alert_id = self._ground_active.get(code)
        if not active:
            if alert_id is not None:
                self._set(self.alerts[alert_id].model_copy(update={"active": False}))
                del self._ground_active[code]
            return
        if alert_id is not None:
            self._set(self.alerts[alert_id].model_copy(update={"title": title}))
            return
        spec = FAULT_CATALOG[code]
        fault_id = str(uuid4())
        body = {
            "fault_id": fault_id,
            "code": code,
            "severity": spec.severity,
            "source": source,
            "message": title,
            "recommended_action": spec.recommended_action,
            "holds_payload": spec.holds_payload,
        }
        await self.bus.publish(
            make("t1.fault_report", "ground.alert_manager", body, self.clock)
        )
        self._ground_active[code] = fault_id
        self._set(
            AlertView(
                alert_id=fault_id,
                code=code,
                severity=spec.severity,
                title=title,
                source=source,
                recommended_action=spec.recommended_action,
                raised_at=format_timestamp(self.clock.now()),
                acknowledged=False,
                active=True,
            )
        )

    async def command_failed(self, view: CommandView) -> None:
        await self._ground(
            "COMMAND_FAILED", True, f"{view.label}: {view.reason or 'Failed'}", "Ground"
        )
        await self._ground("COMMAND_FAILED", False, "", "Ground")

    async def _status_changed(self, env: Envelope) -> None:
        await self.refresh()

    async def refresh(self) -> None:
        latest = self.status.latest
        power = latest.get("power.status")
        nav = latest.get("nav.state")
        link = latest.get("link.health")
        if power:
            await self._ground(
                "POWER_LOW",
                power.body.battery_pct < self.cfg.alerts.power_low_pct,
                f"Battery {power.body.battery_pct:g} %",
                "Team 4 Power",
            )
        if nav:
            await self._ground(
                "NAV_SENSOR_FAULT",
                nav.body.health == "FAULT",
                "Navigation sensor fault",
                "Team 2 Navigation",
            )
        if link:
            view = self.status.link_view()
            await self._ground(
                "LINK_LOST", view.state == "LOST", "Link lost", "Team 3 Link"
            )
            await self._ground(
                "LINK_DEGRADED",
                view.state == "DEGRADED",
                f"Link degraded: {view.latency_ms:g} ms",
                "Team 3 Link",
            )
        blocked = self.status.blocked()
        if blocked:
            await self._ground(
                "ROUTE_BLOCKED",
                True,
                f"Route blocked: {blocked.reason}",
                "Team 2 Navigation",
            )
        stale = [
            key
            for key in ("payload.status", "nav.state", "power.status", "link.health")
            if key in latest and self.status.freshness(key).stale
        ]
        await self._ground(
            "STALE_DATA", bool(stale), f"Out of date: {', '.join(stale)}", "Ground"
        )
        skewed = [
            key
            for key, env in latest.items()
            if (env.sent_at - self.clock.now()).total_seconds()
            > self.cfg.timing.clock_skew_warn_s
        ]
        await self._ground(
            "CLOCK_SKEW",
            bool(skewed),
            f"Future timestamp: {', '.join(skewed)}",
            "Ground",
        )

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            await self.refresh()
            await self.clock.sleep(1 / self.cfg.timing.status_rate_hz)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
