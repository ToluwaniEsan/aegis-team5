"""Build a full operator-screen snapshot from ground components."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from aegis.common.models import format_timestamp
from aegis.common.ui_models import (
    AlertView,
    Dims,
    Limits,
    MissionView,
    PayloadView,
    Permissions,
    Place,
    Sensors,
    Snapshot,
)

if TYPE_CHECKING:
    from aegis.common.clock import Clock
    from aegis.common.config import Settings
    from aegis.ground.command_manager import CommandManager
    from aegis.ground.status_monitor import StatusMonitor


def awaiting_payload() -> PayloadView:
    """D-21: serialization placeholder; never inserted into StatusMonitor."""
    return PayloadView(
        updated_at=None,
        age_s=None,
        stale=True,
        state="EMPTY",
        held_from=None,
        payload_id=None,
        secured=False,
        locked=False,
        mass_kg=None,
        shift_cm=None,
        release_energy_wh=None,
        sensor_health="UNKNOWN",
        sensors=Sensors(load_cell="UNKNOWN", lock="UNKNOWN", shift="UNKNOWN"),
        prerelease_authorized=False,
        departure_permitted=False,
        departure_reason="Awaiting payload status",
    )


def estop_from_alerts(alerts: list[AlertView]) -> bool:
    """D-22: false without B11 is a placeholder, not proof E-STOP is inactive."""
    return any(
        alert.code == "ESTOP_ACTIVE" and (alert.active or not alert.acknowledged)
        for alert in alerts
    )


class SnapshotBuilder:
    def __init__(
        self,
        cfg: Settings,
        clock: Clock,
        status: StatusMonitor,
        commands: CommandManager,
        missing_payload: Callable[[], PayloadView] = awaiting_payload,
        estop_active: Callable[[list[AlertView]], bool] = estop_from_alerts,
    ):
        self.cfg, self.clock, self.status, self.commands = cfg, clock, status, commands
        self.missing_payload = missing_payload
        self.estop_active = estop_active
        self.seq = 0

    def build(self) -> Snapshot:
        self.status.resolve_deliveries()
        payload = self.status.payload_view() or self.missing_payload()
        active = self.commands.active
        alerts = self.commands.alerts_for() if self.commands.alerts_for else []
        alerts = [alert for alert in alerts if alert.active or not alert.acknowledged]
        alerts.sort(key=lambda alert: alert.raised_at, reverse=True)
        alerts.sort(
            key=lambda alert: {"CRITICAL": 0, "WARNING": 1, "CAUTION": 2}[
                alert.severity
            ]
        )
        self.seq += 1
        return Snapshot(
            kind="snapshot",
            seq=self.seq,
            server_time=format_timestamp(self.clock.now()),
            test_mode=self.cfg.test_mode,
            link=self.status.link_view(),
            vehicle_health=self.status.vehicle_health(),
            payload=payload,
            nav=self.status.nav_view(
                origin=active.origin if active else None,
                destination=active.destination if active else None,
            ),
            mission=MissionView(
                active=active,
                queue=list(self.commands.queue),
                next_ids=self.commands.next_ids(),
            ),
            commands=list(reversed(list(self.commands.commands.values())))[
                : self.cfg.ui.commands_shown
            ],
            allowed=Permissions.model_validate(self.commands.allowed()),
            alerts=alerts,
            estop_active=self.estop_active(alerts),
            delivery=self.status.delivery,
            places=[Place(**p.model_dump()) for p in self.cfg.places],
            limits=Limits(
                mass_min_kg=self.cfg.payload.mass_min_kg,
                mass_max_kg=self.cfg.payload.mass_max_kg,
                dims_max_cm=Dims(**self.cfg.payload.dims_max_cm.model_dump()),
                stale_after_s=self.cfg.timing.stale_after_s,
                unsecured_shift_cm=self.cfg.payload.unsecured_shift_cm,
                release_energy_wh_max=self.cfg.payload.release_energy_wh_max,
            ),
        )
