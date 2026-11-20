"""Message models: docs/02-contracts.md sections 2 to 4, 7 and 10.

FROZEN CONTRACT after the end-of-day-2 freeze. Change only through a
`CONTRACT CHANGE` pull request that edits docs/02-contracts.md too.

Every message is an `Envelope`. Each message type has its own envelope
subclass whose `body` is that type's model, and `AnyEnvelope` is the
discriminated union of them all, so validating a message also validates its
body against its `type`. Build envelopes with `aegis.common.envelope.make`
and read them with `aegis.common.envelope.parse`.

The screen protocol (section 9) is in `ui_models.py` (Emmanuel).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal, NamedTuple, Union, get_args

from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    TypeAdapter,
    ValidationError,
    create_model,
    model_validator,
)

# ---------------------------------------------------------------------------
# Section 1: conventions
# ---------------------------------------------------------------------------


def _to_utc_ms(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must include a time zone (UTC)")
    value = value.astimezone(UTC)
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


def format_timestamp(value: datetime) -> str:
    """ISO 8601, UTC, milliseconds, `Z` (GEN-002): 2026-11-19T15:04:05.123Z"""
    value = _to_utc_ms(value)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


# A UTC timestamp, truncated to milliseconds, written as `...Z` in JSON.
Timestamp = Annotated[
    datetime,
    AfterValidator(_to_utc_ms),
    PlainSerializer(format_timestamp, return_type=str, when_used="json"),
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


Health3 = Literal["OK", "WARN", "FAULT"]
MissionPriority = Literal["ROUTINE", "PRIORITY", "URGENT"]
NonNeg = Annotated[float, Field(ge=0)]
Pct = Annotated[float, Field(ge=0, le=100)]


class LatLon(_Model):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Place(LatLon):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Dims(_Model):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Sensors(_Model):
    load_cell: Health3
    lock: Health3
    shift: Health3


# ---------------------------------------------------------------------------
# Section 2: envelope fields
# ---------------------------------------------------------------------------

Endpoint = Literal[
    # ground
    "ground.command_manager",
    "ground.status_monitor",
    "ground.alert_manager",
    "ground.mission_log",
    "ground.ui_server",
    "ground.fault_injector",
    "team1.integration",
    # link
    "team3.link",
    # vehicle
    "vehicle.payload_controller",
    "vehicle.payload_simulator",
    "vehicle.event_buffer",
    "vehicle.link_watch",
    "vehicle.test_agent",
    "team2.nav",
    "team4.power",
]
ENDPOINTS: tuple[str, ...] = get_args(Endpoint)

Iface = Literal["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "INT"]
MsgPriority = Literal[0, 1, 2]  # 0 emergency stop, 1 commands and acks, 2 status

# ---------------------------------------------------------------------------
# Section 4: payload states and reason codes
# ---------------------------------------------------------------------------

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
PAYLOAD_STATES: tuple[str, ...] = get_args(PayloadState)

ReasonCode = Literal[
    "VEHICLE_MOVING",
    "NOT_AT_DESTINATION",
    "NOT_SECURED",
    "CRITICAL_FAULT",
    "PAYLOAD_HELD",
    "OUT_OF_LIMITS",
    "INVALID_STATE",
    "STALE_COMMAND",
    "FUTURE_TIMESTAMP",
]

# Reason texts shown to the operator. OUT_OF_LIMITS, INVALID_STATE and
# STALE_COMMAND have values filled in by the code that rejects the command.
REASON_TEXT: dict[str, str] = {
    "VEHICLE_MOVING": "Vehicle is moving",
    "NOT_AT_DESTINATION": "Not at the destination",
    "NOT_SECURED": "Payload is not secured",
    "CRITICAL_FAULT": "A critical fault is active",
    "PAYLOAD_HELD": "Payload is held: acknowledge the fault first",
    "FUTURE_TIMESTAMP": "Command time is ahead of the vehicle clock",
}

# ---------------------------------------------------------------------------
# Section 7: fault catalog
# ---------------------------------------------------------------------------

Severity = Literal["CRITICAL", "WARNING", "CAUTION"]

FaultCode = Literal[
    "ESTOP_ACTIVE",
    "PAYLOAD_UNSECURED",
    "DEPARTED_UNSECURED",
    "RELEASE_FAILED",
    "LOCK_SENSOR_FAULT",
    "DRIVETRAIN_FAULT",
    "PAYLOAD_SHIFT",
    "WEIGHT_OUT_OF_RANGE",
    "LOAD_CELL_FAULT",
    "LINK_LOST",
    "POWER_LOW",
    "NAV_SENSOR_FAULT",
    "LINK_DEGRADED",
    "COMMAND_FAILED",
    "ROUTE_BLOCKED",
    "STALE_DATA",
    "CLOCK_SKEW",
]


class FaultSpec(NamedTuple):
    severity: Severity
    raised_by: Literal["vehicle", "ground", "vehicle or ground"]
    holds_payload: bool
    recommended_action: str


# Severity and holds_payload are fixed by the contract. The recommended-action
# texts are data and may be revised (decision D-14).
FAULT_CATALOG: dict[str, FaultSpec] = {
    "ESTOP_ACTIVE": FaultSpec(
        "CRITICAL",
        "vehicle",
        True,
        "Check the vehicle is safe, then acknowledge to clear the stop",
    ),
    "PAYLOAD_UNSECURED": FaultSpec(
        "CRITICAL",
        "vehicle",
        True,
        "Stop the vehicle at the next safe point and inspect the payload",
    ),
    "DEPARTED_UNSECURED": FaultSpec(
        "CRITICAL", "vehicle", True, "Stop the vehicle now and secure the payload"
    ),
    "RELEASE_FAILED": FaultSpec(
        "CRITICAL",
        "vehicle",
        True,
        "Do not move the vehicle. Inspect the release mechanism",
    ),
    "LOCK_SENSOR_FAULT": FaultSpec(
        "CRITICAL",
        "vehicle",
        True,
        "Treat the payload as unsecured. Stop at the next safe point",
    ),
    "DRIVETRAIN_FAULT": FaultSpec(
        "CRITICAL", "vehicle", True, "Stop the mission and contact Team 4 support"
    ),
    "PAYLOAD_SHIFT": FaultSpec(
        "WARNING",
        "vehicle",
        False,
        "Reduce speed and inspect the payload at the next stop",
    ),
    "WEIGHT_OUT_OF_RANGE": FaultSpec(
        "WARNING", "vehicle", False, "Correct the load before departure"
    ),
    "LOAD_CELL_FAULT": FaultSpec(
        "WARNING",
        "vehicle",
        False,
        "Weight readings are unreliable. Verify the load manually",
    ),
    "LINK_LOST": FaultSpec(
        "WARNING",
        "ground",
        False,
        "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
    ),
    "POWER_LOW": FaultSpec("WARNING", "ground", False, "Consider returning to origin"),
    "NAV_SENSOR_FAULT": FaultSpec(
        "WARNING",
        "ground",
        False,
        "Expect position errors. Monitor the route closely",
    ),
    "LINK_DEGRADED": FaultSpec(
        "CAUTION", "ground", False, "Check data ages before acting"
    ),
    "COMMAND_FAILED": FaultSpec(
        "CAUTION",
        "ground",
        False,
        "Check the reason and send the command again if still needed",
    ),
    "ROUTE_BLOCKED": FaultSpec(
        "CAUTION", "ground", False, "Review the new route and arrival time"
    ),
    "STALE_DATA": FaultSpec(
        "CAUTION", "ground", False, "Values marked OUT OF DATE may be wrong"
    ),
    "CLOCK_SKEW": FaultSpec(
        "CAUTION",
        "vehicle or ground",
        False,
        "Report to Team 1. Command timeouts may be wrong",
    ),
}

# ---------------------------------------------------------------------------
# Section 3: message bodies
# ---------------------------------------------------------------------------


class Empty(_Model):
    """`{}`: cmd.release, cmd.abort, cmd.return_to_origin."""


# I2: ground to vehicle


class AssignMission(_Model):
    mission_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    origin: Place
    destination: Place
    priority: MissionPriority
    # Not range-checked here: the Payload Controller rejects out-of-limits
    # values with OUT_OF_LIMITS (AEG-501) instead of dropping the message.
    declared_mass_kg: float
    dims_cm: Dims
    prerelease_authorized: bool


class UpdatePayload(_Model):
    declared_mass_kg: float
    dims_cm: Dims


class AckFault(_Model):
    fault_id: UUID4


class ChangeDestination(_Model):
    destination: Place


class HeartbeatGround(_Model):
    seq: int = Field(ge=0)


# I3: vehicle to ground


class Ack(_Model):
    result: Literal["RECEIVED", "COMPLETED", "REJECTED"]
    reason_code: str | None
    reason: str | None
    responder: Endpoint

    @model_validator(mode="after")
    def _check(self) -> Ack:
        if self.result == "REJECTED" and not (self.reason_code and self.reason):
            raise ValueError("a REJECTED ack needs reason_code and reason")
        return self


class PayloadStatus(_Model):
    state: PayloadState
    held_from: PayloadState | None
    secured: bool
    locked: bool
    mass_kg: float | None
    shift_cm: NonNeg | None
    release_energy_wh: NonNeg | None
    sensors: Sensors
    prerelease_authorized: bool
    departure_permitted: bool
    departure_reason: str | None
    mission_id: str | None

    @model_validator(mode="after")
    def _check(self) -> PayloadStatus:
        if (self.state == "HELD") != (self.held_from is not None):
            raise ValueError("held_from is set exactly when state is HELD")
        if self.held_from == "HELD":
            raise ValueError("held_from cannot be HELD")
        if self.departure_permitted:
            # The one definition, contracts section 4.
            if not (self.state == "SECURED" and self.secured and self.mission_id):
                raise ValueError(
                    "departure_permitted needs state SECURED, secured true and a mission open"
                )
            if self.departure_reason is not None:
                raise ValueError(
                    "departure_reason must be null when departure is permitted"
                )
        elif not self.departure_reason:
            raise ValueError(
                "departure_reason is required when departure is not permitted"
            )
        return self


class PayloadDelivered(_Model):
    mission_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    released_at: Timestamp
    position: LatLon
    mass_kg: float
    energy_used_wh: NonNeg


class FaultRaised(_Model):
    fault_id: UUID4
    code: FaultCode
    severity: Severity
    source: str = Field(min_length=1)
    message: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    holds_payload: bool

    @model_validator(mode="after")
    def _check(self) -> FaultRaised:
        spec = FAULT_CATALOG[self.code]
        if self.severity != spec.severity:
            raise ValueError(
                f"{self.code} has severity {spec.severity} in the fault catalog"
            )
        if self.holds_payload != spec.holds_payload:
            raise ValueError(
                f"{self.code} has holds_payload {spec.holds_payload} in the fault catalog"
            )
        return self


class FaultCleared(_Model):
    fault_id: UUID4
    code: FaultCode


class BacklogBatch(_Model):
    events: list[AnyEnvelope]


# I4: ground to Team 2


class NavAssign(_Model):
    mission_id: str = Field(min_length=1)
    origin: Place
    destination: Place
    priority: MissionPriority


# I5: emergency stop


class EStop(_Model):
    reason: str = Field(min_length=1)
    source: Literal["OPERATOR"]


# I6: Team 2


class NavState(_Model):
    moving: bool
    speed_mps: NonNeg
    position: LatLon
    at_destination: bool
    at_origin: bool
    eta_s: NonNeg | None
    progress_pct: Pct
    route: list[LatLon]
    health: Health3


class RouteBlocked(_Model):
    reason: str = Field(min_length=1)
    blocked_at: LatLon
    new_route: list[LatLon]
    new_eta_s: NonNeg


class PayloadInterlock(_Model):
    """PROPOSED, needs Team 2 (decision D-02: keep)."""

    departure_permitted: bool
    reason: str | None

    @model_validator(mode="after")
    def _check(self) -> PayloadInterlock:
        if self.departure_permitted and self.reason is not None:
            raise ValueError("reason must be null when departure is permitted")
        if not self.departure_permitted and not self.reason:
            raise ValueError("reason is required when departure is not permitted")
        return self


# I7: Team 4


class MassReport(_Model):
    mass_kg: NonNeg
    release_energy_wh_nominal: NonNeg
    release_energy_wh_max: NonNeg


class PowerStatus(_Model):
    battery_pct: Pct
    est_range_km: NonNeg
    drivetrain_health: Health3


# I8: Team 3


class LinkHealth(_Model):
    state: Literal["CONNECTED", "DEGRADED", "LOST"]
    latency_ms: NonNeg
    loss_pct: Pct


# I9: Team 1


class T1MissionReport(_Model):
    mission_id: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    status: Literal["ASSIGNED", "ACTIVE", "COMPLETE", "ABORTED"]


class T1SystemMode(_Model):
    mode: str  # format unknown until Team 1 answers


# INT: inside the vehicle


class SimCommand(_Model):
    action: Literal["LOAD", "LOCK", "UNLOCK", "RELEASE", "UNLOAD"]
    mass_kg: NonNeg | None = None

    @model_validator(mode="after")
    def _check(self) -> SimCommand:
        if (self.action == "LOAD") != (self.mass_kg is not None):
            raise ValueError("mass_kg is set for LOAD and only for LOAD")
        return self


class SimReading(_Model):
    mass_kg: float | None  # null while the load cell reports FAULT
    settled: bool
    shift_cm: NonNeg | None
    locked: bool
    release_done: bool
    sensors: Sensors


class LinkState(_Model):
    state: Literal["LOST", "RESTORED"]
    since: Timestamp


# ---------------------------------------------------------------------------
# Section 10: test interface
# ---------------------------------------------------------------------------


class _NoParams(_Model):
    pass


class _Cm(_Model):
    cm: NonNeg


class _Sensor(_Model):
    sensor: Literal["load_cell", "lock", "shift"]
    health: Health3


class _Kg(_Model):
    kg: float


class _On(_Model):
    on: bool


class _LinkSet(_Model):
    latency_ms: NonNeg
    loss_pct: Pct


class _Seconds(_Model):
    seconds: float = Field(gt=0)


class _Reason(_Model):
    reason: str = Field(min_length=1)


class _Health(_Model):
    health: Health3


class _Pct(_Model):
    pct: Pct


class _Mode(_Model):
    mode: str = Field(min_length=1)


InjectTarget = Literal["payload", "link", "nav", "power", "team1"]

# (target, action) -> params model. Every row of contracts section 10.
INJECT_ACTIONS: dict[tuple[str, str], type[_Model]] = {
    ("payload", "shift"): _Cm,
    ("payload", "sensor"): _Sensor,
    ("payload", "mass_override"): _Kg,
    ("payload", "release_jam"): _On,
    ("payload", "controller_crash"): _NoParams,
    ("payload", "unload"): _NoParams,
    ("link", "set"): _LinkSet,
    ("link", "outage"): _Seconds,
    ("nav", "depart"): _NoParams,
    ("nav", "arrive"): _NoParams,
    ("nav", "stop"): _NoParams,
    ("nav", "block_route"): _Reason,
    ("nav", "health"): _Health,
    ("power", "battery"): _Pct,
    ("power", "drivetrain"): _Health,
    ("team1", "mode"): _Mode,
}


class TestInject(_Model):
    __test__ = False  # not a pytest test class

    target: InjectTarget
    action: str
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> TestInject:
        model = INJECT_ACTIONS.get((self.target, self.action))
        if model is None:
            actions = sorted(a for t, a in INJECT_ACTIONS if t == self.target)
            raise ValueError(
                f"unknown action {self.action!r} for target {self.target!r}; "
                f"expected one of {actions}"
            )
        try:
            model.model_validate(self.params)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or 'params'}: {e['msg']}"
                for e in exc.errors()
            )
            raise ValueError(
                f"bad params for {self.target}/{self.action}: {problems}"
            ) from None
        return self


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------

# Message type -> body model. The catalog in contracts section 3.
BODIES: dict[str, type[_Model]] = {
    "cmd.assign_mission": AssignMission,
    "cmd.update_payload": UpdatePayload,
    "cmd.release": Empty,
    "cmd.ack_fault": AckFault,
    "cmd.abort": Empty,
    "cmd.return_to_origin": Empty,
    "cmd.change_destination": ChangeDestination,
    "cmd.estop": EStop,
    "hb.ground": HeartbeatGround,
    "nav.assign": NavAssign,
    "ack": Ack,
    "payload.status": PayloadStatus,
    "payload.delivered": PayloadDelivered,
    "fault.raised": FaultRaised,
    "fault.cleared": FaultCleared,
    "backlog.batch": BacklogBatch,
    "payload.interlock": PayloadInterlock,
    "payload.mass_report": MassReport,
    "nav.state": NavState,
    "nav.route_blocked": RouteBlocked,
    "power.status": PowerStatus,
    "link.health": LinkHealth,
    "t1.mission_report": T1MissionReport,
    "t1.fault_report": FaultRaised,
    "t1.delivery_confirmation": PayloadDelivered,
    "t1.system_mode": T1SystemMode,
    "int.link_state": LinkState,
    "sim.command": SimCommand,
    "sim.reading": SimReading,
    "test.inject": TestInject,
}

MessageType = Literal[
    "cmd.assign_mission",
    "cmd.update_payload",
    "cmd.release",
    "cmd.ack_fault",
    "cmd.abort",
    "cmd.return_to_origin",
    "cmd.change_destination",
    "cmd.estop",
    "hb.ground",
    "nav.assign",
    "ack",
    "payload.status",
    "payload.delivered",
    "fault.raised",
    "fault.cleared",
    "backlog.batch",
    "payload.interlock",
    "payload.mass_report",
    "nav.state",
    "nav.route_blocked",
    "power.status",
    "link.health",
    "t1.mission_report",
    "t1.fault_report",
    "t1.delivery_confirmation",
    "t1.system_mode",
    "int.link_state",
    "sim.command",
    "sim.reading",
    "test.inject",
]
assert set(get_args(MessageType)) == set(BODIES), (
    "MessageType and BODIES must list the same types"
)


class Envelope(_Model):
    """Contracts section 2. The base of every per-type envelope.

    Build with `envelope.make`, read with `envelope.parse`. Never construct
    this base class directly: it does not know which body model to use.
    """

    v: Literal[1] = 1
    msg_id: UUID4
    type: MessageType
    iface: Iface
    src: Endpoint
    dst: list[Endpoint] = Field(min_length=1)
    sent_at: Timestamp
    priority: MsgPriority
    mission_id: str | None = None
    payload_id: str | None = None
    corr_id: UUID4 | None = None
    buffered: bool = False
    body: _Model

    @model_validator(mode="after")
    def _check(self) -> Envelope:
        if self.type == "ack":
            if self.corr_id is None:
                raise ValueError(
                    "an ack needs corr_id, the msg_id of the command it answers"
                )
            if self.body.responder != self.src:
                raise ValueError("ack body.responder must equal src")
        elif self.corr_id is not None:
            raise ValueError("corr_id is set only on an ack")
        if len(set(self.dst)) != len(self.dst):
            raise ValueError("dst lists an endpoint twice")
        return self


def _class_name(message_type: str) -> str:
    words = message_type.replace(".", "_").split("_")
    return "".join(w.capitalize() for w in words) + "Envelope"


# One envelope subclass per message type: `type` fixed, `body` typed.
ENVELOPE_CLASSES: dict[str, type[Envelope]] = {
    t: create_model(
        _class_name(t),
        __base__=Envelope,
        __module__=__name__,
        type=(Literal[t], ...),
        body=(body, ...),
    )
    for t, body in BODIES.items()
}

AnyEnvelope = Annotated[
    Union[tuple(ENVELOPE_CLASSES.values())],  # noqa: UP007
    Field(discriminator="type"),
]

# BacklogBatch refers to AnyEnvelope, which needs the envelope classes first.
BacklogBatch.model_rebuild()
for _cls in ENVELOPE_CLASSES.values():
    _cls.model_rebuild()

ENVELOPE_ADAPTER: TypeAdapter[Envelope] = TypeAdapter(AnyEnvelope)
