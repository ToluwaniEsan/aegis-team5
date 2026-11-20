"""Pydantic representation of the operator-screen protocol."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["CRITICAL", "WARNING", "CAUTION"]
Health = Literal["OK", "WARN", "FAULT", "UNKNOWN"]
LinkState = Literal["CONNECTED", "DEGRADED", "LOST"]
OverallHealth = Literal["NOMINAL", "DEGRADED", "FAULT"]
PayloadState = Literal[
    "EMPTY",
    "LOADED",
    "SECURED",
    "TRAVELLING",
    "AT_DESTINATION",
    "RELEASED",
    "DELIVERED",
    "RETURNING",
    "HELD",
]
MissionStatus = Literal["QUEUED", "ASSIGNED", "ACTIVE", "COMPLETE", "ABORTED"]
Priority = Literal["ROUTINE", "PRIORITY", "URGENT"]
CommandName = Literal[
    "assign_mission",
    "start_queued_mission",
    "remove_queued_mission",
    "abort",
    "return_to_origin",
    "change_destination",
    "update_payload",
    "release",
    "ack_fault",
    "estop",
]
CommandState = Literal["SENT", "RECEIVED", "COMPLETED", "FAILED"]


class UiModel(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)


class LatLon(UiModel):
    lat: float
    lon: float


class Place(LatLon):
    id: str
    name: str


class Dims(UiModel):
    length: float
    width: float
    height: float


class Freshness(UiModel):
    updated_at: str | None
    age_s: float | None
    stale: bool


class LinkView(Freshness):
    state: LinkState
    latency_ms: float | None
    loss_pct: float | None


class Subsystem(Freshness):
    key: Literal["power", "mobility", "navigation", "comms", "payload_sensors"]
    label: str
    team: Literal[2, 3, 4, 5]
    status: Health
    detail: str


class Sensors(UiModel):
    load_cell: Health
    lock: Health
    shift: Health


class PayloadView(Freshness):
    state: PayloadState
    held_from: PayloadState | None
    payload_id: str | None
    secured: bool
    locked: bool
    mass_kg: float | None
    shift_cm: float | None
    release_energy_wh: float | None
    sensor_health: Health
    sensors: Sensors
    prerelease_authorized: bool
    departure_permitted: bool
    departure_reason: str | None


class BlockedRoute(UiModel):
    reason: str
    at: LatLon
    old_route: list[LatLon]
    new_eta_s: float | None
    since: str


class NavView(Freshness):
    origin: Place | None
    destination: Place | None
    position: LatLon | None
    route: list[LatLon]
    progress_pct: float | None
    moving: bool
    speed_mps: float | None
    eta_s: float | None
    blocked: BlockedRoute | None


class Mission(UiModel):
    mission_id: str
    payload_id: str
    status: MissionStatus
    origin: Place
    destination: Place
    priority: Priority
    declared_mass_kg: float
    dims_cm: Dims
    prerelease_authorized: bool
    created_at: str


class CommandView(UiModel):
    command_id: str
    command: CommandName
    label: str
    state: CommandState
    reason: str | None
    sent_at: str
    updated_at: str


class Permission(UiModel):
    allowed: bool
    reason: str | None
    needs_confirmation: bool


class AlertView(UiModel):
    alert_id: str
    code: str
    severity: Severity
    title: str
    source: str
    recommended_action: str
    raised_at: str
    acknowledged: bool
    active: bool


class DeliverySummary(UiModel):
    mission_id: str
    payload_id: str
    destination: Place
    released_at: str
    confirmed_at: str
    confirm_latency_s: float
    mass_kg: float
    energy_used_wh: float


class VehicleHealth(UiModel):
    overall: OverallHealth
    subsystems: list[Subsystem]


class NextIds(UiModel):
    mission_id: str
    payload_id: str


class MissionView(UiModel):
    active: Mission | None
    queue: list[Mission]
    next_ids: NextIds


class Permissions(UiModel):
    assign_mission: Permission
    start_queued_mission: Permission
    remove_queued_mission: Permission
    abort: Permission
    return_to_origin: Permission
    change_destination: Permission
    update_payload: Permission
    release: Permission
    ack_fault: Permission
    estop: Permission


class Limits(UiModel):
    mass_min_kg: float
    mass_max_kg: float
    dims_max_cm: Dims
    stale_after_s: float
    unsecured_shift_cm: float
    release_energy_wh_max: float


class Snapshot(UiModel):
    kind: Literal["snapshot"]
    seq: float
    server_time: str
    test_mode: bool
    link: LinkView
    vehicle_health: VehicleHealth
    payload: PayloadView
    nav: NavView
    mission: MissionView
    commands: list[CommandView]
    allowed: Permissions
    alerts: list[AlertView]
    estop_active: bool
    delivery: DeliverySummary | None
    places: list[Place]
    limits: Limits


class UiCommand(UiModel):
    kind: Literal["command"]
    client_req_id: str
    command: CommandName
    args: dict[str, Any]
    confirmed: bool


class CommandResult(UiModel):
    kind: Literal["command_result"]
    client_req_id: str
    accepted: bool
    command_id: str | None
    reason: str | None


ServerMessage = Snapshot | CommandResult
