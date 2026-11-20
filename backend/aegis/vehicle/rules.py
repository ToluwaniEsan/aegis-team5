"""Payload Controller rules (task A4): one pure function.

    step(state, event, now, cfg) -> (state, actions)

No IO and no clock reads: `now` is passed in. This is contracts section 4,
row by row. `payload_controller.py` feeds it bus messages and a 1 Hz tick and
carries out the actions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime

from pydantic import BaseModel

from aegis.common.config import Settings
from aegis.common.models import (
    FAULT_CATALOG,
    REASON_TEXT,
    AssignMission,
    Envelope,
    FaultCleared,
    FaultRaised,
    LatLon,
    MassReport,
    NavState,
    PayloadDelivered,
    PayloadInterlock,
    PayloadStatus,
    PowerStatus,
    Sensors,
    SimCommand,
    SimReading,
)

# -- state ------------------------------------------------------------------------


@dataclass(frozen=True)
class Fault:
    fault_id: str
    code: str
    acknowledged: bool = False
    active: bool = True

    @property
    def holds(self) -> bool:
        return FAULT_CATALOG[self.code].holds_payload

    @property
    def severity(self) -> str:
        return FAULT_CATALOG[self.code].severity


@dataclass(frozen=True)
class CtrlState:
    state: str = "EMPTY"
    held_from: str | None = None
    mission: AssignMission | None = None
    mission_open: bool = False
    prerelease_authorized: bool = False
    lock_requested: bool = False
    # LOAD progress: None, "sent" (LOAD sent), "settling" (unsettled reading seen)
    load_phase: str | None = None
    reading: SimReading | None = None
    nav: NavState | None = None
    power: PowerStatus | None = None
    link_lost: bool = False
    arrived_at: datetime | None = None
    prerelease_from: datetime | None = None  # when the pre-release wait started
    faults: tuple[Fault, ...] = ()
    pending_assign: Envelope | None = None
    pending_update: Envelope | None = None
    pending_release: Envelope | None = None
    release_started: datetime | None = None
    unlock_expected: bool = False  # we commanded RELEASE or UNLOAD
    lock_seen_closed: bool = False
    mass_at_release: float | None = None
    delivered_sent: bool = False
    released: bool = False


# -- events -----------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    env: Envelope


@dataclass(frozen=True)
class Reading:
    body: SimReading


@dataclass(frozen=True)
class Nav:
    body: NavState


@dataclass(frozen=True)
class Power:
    body: PowerStatus


@dataclass(frozen=True)
class LinkLost:
    pass


@dataclass(frozen=True)
class LinkRestored:
    pass


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Unload:
    """Test action payload/unload: the ground crew unloads a returned payload."""


Event = Command | Reading | Nav | Power | LinkLost | LinkRestored | Tick | Unload

# -- actions ----------------------------------------------------------------------


@dataclass(frozen=True)
class Send:
    type: str
    body: BaseModel


@dataclass(frozen=True)
class Ack:
    command: Envelope
    result: str
    reason_code: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Log:
    kind: str
    fields: dict = field(default_factory=dict)


Action = Send | Ack | Log

# -- shared helpers (also used by ground/permissions.py) --------------------------


def release_refusal(
    moving: bool, at_destination: bool, secured: bool, critical_fault: bool
) -> tuple[str, str] | None:
    """The release guards, in contracts section 4 order. The first failure is
    the reason given. The ground's permissions.py uses this same function."""
    if moving:
        return "VEHICLE_MOVING", REASON_TEXT["VEHICLE_MOVING"]
    if not at_destination:
        return "NOT_AT_DESTINATION", REASON_TEXT["NOT_AT_DESTINATION"]
    if not secured:
        return "NOT_SECURED", REASON_TEXT["NOT_SECURED"]
    if critical_fault:
        return "CRITICAL_FAULT", REASON_TEXT["CRITICAL_FAULT"]
    return None


def fmt(value: float) -> str:
    """1180 -> "1,180"; 226.8 -> "226.8"."""
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"


def invalid_state_text(state: str) -> str:
    return f"Not possible while the payload is {state}"


def stale_text(cfg: Settings) -> str:
    return f"Command is older than {fmt(cfg.timing.command_max_age_s)} s"


def limits_refusal(mass_kg: float, dims, cfg: Settings) -> str | None:
    """AEG-501 and AEG-503 on the declared values."""
    p = cfg.payload
    if mass_kg > p.mass_max_kg:
        return f"Payload {fmt(mass_kg)} kg exceeds the {fmt(p.mass_max_kg)} kg limit"
    if mass_kg < p.mass_min_kg:
        return f"Payload {fmt(mass_kg)} kg is below the {fmt(p.mass_min_kg)} kg minimum"
    m = p.dims_max_cm
    if dims.length > m.length or dims.width > m.width or dims.height > m.height:
        return (
            f"Payload {fmt(dims.length)} × {fmt(dims.width)} × {fmt(dims.height)} cm "
            f"exceeds the {fmt(m.length)} × {fmt(m.width)} × {fmt(m.height)} cm limit"
        )
    return None


def mass_in_range(mass_kg: float | None, cfg: Settings) -> bool:
    """Measured mass within limits. A reading within the scale's accuracy of a
    limit cannot be judged outside it (AEG-504)."""
    if mass_kg is None:
        return False
    p = cfg.payload
    tol = p.weight_accuracy_kg
    return p.mass_min_kg - tol <= mass_kg <= p.mass_max_kg + tol


def is_secured(s: CtrlState, cfg: Settings) -> bool:
    """Lock closed, lock sensor OK, mass settled and in range, shift within
    the limit (contracts section 4)."""
    r = s.reading
    return bool(
        r is not None
        and r.locked
        and r.sensors.lock == "OK"
        and r.settled
        and s.load_phase is None
        and mass_in_range(r.mass_kg, cfg)
        and r.shift_cm is not None
        and r.shift_cm <= cfg.payload.unsecured_shift_cm
    )


def moving(s: CtrlState) -> bool:
    return bool(s.nav and s.nav.moving)


def at_destination(s: CtrlState) -> bool:
    return bool(s.nav and s.nav.at_destination)


def critical_active(s: CtrlState) -> bool:
    return any(f.active and f.severity == "CRITICAL" for f in s.faults)


def departure_permitted(s: CtrlState, cfg: Settings) -> bool:
    """The one definition: SECURED, secured true and a mission open."""
    return s.state == "SECURED" and is_secured(s, cfg) and s.mission_open


def departure_reason(s: CtrlState, cfg: Settings) -> str | None:
    if departure_permitted(s, cfg):
        return None
    if s.state == "HELD":
        return REASON_TEXT["PAYLOAD_HELD"]
    if s.mission is None:
        return "No mission assigned"
    if not s.mission_open:
        return "Mission closed: unload the payload and assign a new mission"
    if s.state not in ("LOADED", "SECURED"):
        return f"Payload is {s.state}"
    return REASON_TEXT["NOT_SECURED"]


def status(s: CtrlState, cfg: Settings) -> PayloadStatus:
    r = s.reading
    permitted = departure_permitted(s, cfg)
    return PayloadStatus(
        state=s.state,
        held_from=s.held_from,
        secured=is_secured(s, cfg),
        locked=bool(r and r.locked),
        mass_kg=r.mass_kg if r else None,
        shift_cm=r.shift_cm if r else None,
        release_energy_wh=cfg.payload.release_energy_wh_nominal if s.released else None,
        sensors=r.sensors if r else Sensors(load_cell="OK", lock="OK", shift="OK"),
        prerelease_authorized=s.prerelease_authorized,
        departure_permitted=permitted,
        departure_reason=None if permitted else departure_reason(s, cfg),
        mission_id=s.mission.mission_id if s.mission else None,
    )


def interlock(s: CtrlState, cfg: Settings) -> PayloadInterlock:
    permitted = departure_permitted(s, cfg)
    return PayloadInterlock(
        departure_permitted=permitted,
        reason=None if permitted else departure_reason(s, cfg),
    )


# -- faults -----------------------------------------------------------------------

FAULT_SOURCE = {"DRIVETRAIN_FAULT": "Team 4 Power"}


def _fault(s: CtrlState, code: str) -> Fault | None:
    return next((f for f in s.faults if f.code == code), None)


def _put(s: CtrlState, fault: Fault) -> CtrlState:
    others = tuple(f for f in s.faults if f.code != fault.code)
    return replace(s, faults=(*others, fault))


def raise_fault(
    s: CtrlState, code: str, message: str
) -> tuple[CtrlState, list[Action]]:
    """Raise once. A holding fault puts the payload in HELD."""
    existing = _fault(s, code)
    if existing is not None and existing.active:
        return s, []
    fault = (
        replace(existing, active=True, acknowledged=False)
        if existing
        else Fault(fault_id=str(uuid.uuid4()), code=code)
    )
    s = _put(s, fault)
    spec = FAULT_CATALOG[code]
    body = FaultRaised(
        fault_id=fault.fault_id,
        code=code,
        severity=spec.severity,
        source=FAULT_SOURCE.get(code, "Payload"),
        message=message,
        recommended_action=spec.recommended_action,
        holds_payload=spec.holds_payload,
    )
    acts: list[Action] = [Send("fault.raised", body)]
    if spec.holds_payload and s.state != "HELD":
        s = replace(s, held_from=s.state, state="HELD")
    return s, acts


def clear_fault(s: CtrlState, code: str) -> tuple[CtrlState, list[Action]]:
    """The condition has ended. A holding fault stays listed until acknowledged."""
    f = _fault(s, code)
    if f is None or not f.active:
        return s, []
    acts: list[Action] = [
        Send("fault.cleared", FaultCleared(fault_id=f.fault_id, code=code))
    ]
    if f.holds and not f.acknowledged:
        return _put(s, replace(f, active=False)), acts
    return replace(s, faults=tuple(x for x in s.faults if x.code != code)), acts


def _set_fault(s: CtrlState, code: str, present: bool, message: str):
    return raise_fault(s, code, message) if present else clear_fault(s, code)


def held_exit(s: CtrlState, now: datetime) -> CtrlState:
    """Leave HELD once every holding fault is acknowledged and cleared."""
    if s.state != "HELD":
        return s
    if any(f.holds and (f.active or not f.acknowledged) for f in s.faults):
        return s
    back = s.held_from or "EMPTY"
    s = replace(s, state=back, held_from=None)
    if back == "AT_DESTINATION" and s.link_lost:
        s = replace(s, prerelease_from=now)  # the wait restarts after a HELD exit
    return s


# -- step -------------------------------------------------------------------------


def step(
    s: CtrlState, event: Event, now: datetime, cfg: Settings
) -> tuple[CtrlState, list[Action]]:
    if isinstance(event, Command):
        s, acts = _command(s, event.env, now, cfg)
    elif isinstance(event, Reading):
        s, acts = _reading(s, event.body, now, cfg)
    elif isinstance(event, Nav):
        s, acts = _nav(s, event.body, now, cfg)
    elif isinstance(event, Power):
        s = replace(s, power=event.body)
        s, acts = _set_fault(
            s,
            "DRIVETRAIN_FAULT",
            event.body.drivetrain_health == "FAULT",
            "Team 4 reports a drivetrain fault",
        )
    elif isinstance(event, LinkLost):
        s = replace(s, link_lost=True)
        if s.state == "AT_DESTINATION":
            s = replace(s, prerelease_from=now)  # the later of arrival and link loss
        acts = []
    elif isinstance(event, LinkRestored):
        s, acts = replace(s, link_lost=False, prerelease_from=None), []
    elif isinstance(event, Tick):
        s, acts = _tick(s, now, cfg)
    elif isinstance(event, Unload):
        s, acts = _unload(s)
    else:
        raise TypeError(f"unknown event {event!r}")
    return held_exit(s, now), acts


# -- commands ---------------------------------------------------------------------


def _reject(env: Envelope, code: str, text: str | None = None) -> Ack:
    return Ack(env, "REJECTED", code, text or REASON_TEXT[code])


def _command(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    acts: list[Action] = [Ack(env, "RECEIVED")]

    # 1. The emergency stop skips every check (OI-019).
    if env.type == "cmd.estop":
        s, more = raise_fault(s, "ESTOP_ACTIVE", "Emergency stop pressed")
        return s, [*acts, *more, Ack(env, "COMPLETED")]

    # 2. Future timestamp, 3. stale command: the two-sided timeout (A-17).
    age_s = (now - env.sent_at).total_seconds()
    if -age_s > cfg.timing.clock_skew_warn_s:
        s, more = raise_fault(
            s,
            "CLOCK_SKEW",
            f"Command time is {fmt(-age_s)} s ahead of the vehicle clock",
        )
        return s, [*acts, *more, _reject(env, "FUTURE_TIMESTAMP")]
    s, more = clear_fault(s, "CLOCK_SKEW")
    acts += more
    if age_s > cfg.timing.command_max_age_s:
        return s, [*acts, _reject(env, "STALE_COMMAND", stale_text(cfg))]

    # 4. HELD: only ack_fault (and estop, above).
    if s.state == "HELD" and env.type != "cmd.ack_fault":
        return s, [*acts, _reject(env, "PAYLOAD_HELD")]

    # 5. The state row.
    handler = COMMANDS.get(env.type)
    if handler is None:
        return s, [*acts, _reject(env, "INVALID_STATE", invalid_state_text(s.state))]
    s, more = handler(s, env, now, cfg)
    return s, [*acts, *more]


def _assign(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    if s.state not in ("EMPTY", "DELIVERED"):
        return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]
    body: AssignMission = env.body
    refusal = limits_refusal(body.declared_mass_kg, body.dims_cm, cfg)
    if refusal:
        return s, [_reject(env, "OUT_OF_LIMITS", refusal)]
    s = replace(
        CtrlState(),
        state="LOADED",
        mission=body,
        mission_open=True,
        prerelease_authorized=body.prerelease_authorized,
        load_phase="sent",
        pending_assign=env,
        reading=s.reading,
        nav=s.nav,
        power=s.power,
        link_lost=s.link_lost,
        faults=s.faults,
    )
    return s, [
        Send("sim.command", SimCommand(action="LOAD", mass_kg=body.declared_mass_kg))
    ]


def _update(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    if s.state not in ("LOADED", "SECURED") or not s.mission_open:
        return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]
    if moving(s):
        return s, [_reject(env, "VEHICLE_MOVING")]
    body = env.body
    refusal = limits_refusal(body.declared_mass_kg, body.dims_cm, cfg)
    if refusal:
        return s, [_reject(env, "OUT_OF_LIMITS", refusal)]
    mission = s.mission.model_copy(
        update={"declared_mass_kg": body.declared_mass_kg, "dims_cm": body.dims_cm}
    )
    s = replace(s, mission=mission, load_phase="sent", pending_update=env)
    return s, [
        Send("sim.command", SimCommand(action="LOAD", mass_kg=body.declared_mass_kg))
    ]


def _start_release(s: CtrlState, now: datetime, env: Envelope | None):
    mass = s.reading.mass_kg if s.reading else None
    s = replace(
        s,
        state="RELEASED",
        pending_release=env,
        release_started=now,
        unlock_expected=True,
        mass_at_release=mass if mass is not None else s.mission.declared_mass_kg,
        prerelease_from=None,
    )
    return s, [Send("sim.command", SimCommand(action="RELEASE"))]


def _release(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    refusal = release_refusal(
        moving(s), at_destination(s), is_secured(s, cfg), critical_active(s)
    )
    if refusal:
        return s, [_reject(env, *refusal)]
    if s.state != "AT_DESTINATION":
        return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]
    return _start_release(s, now, env)


def _ack_fault(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    fault_id = str(env.body.fault_id)
    f = next((x for x in s.faults if x.fault_id == fault_id), None)
    if f is None:
        return s, [_reject(env, "INVALID_STATE", "No such fault")]
    acts: list[Action] = []
    s = _put(s, replace(f, acknowledged=True))
    if f.code == "ESTOP_ACTIVE":  # acknowledging the stop clears it
        s, acts = clear_fault(s, "ESTOP_ACTIVE")
    f = _fault(s, f.code)
    if f is not None and not f.active:
        s = replace(s, faults=tuple(x for x in s.faults if x is not f))
    return s, [*acts, Ack(env, "COMPLETED")]


def _abort(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    if s.state in ("TRAVELLING", "AT_DESTINATION"):
        s = replace(s, state="RETURNING", prerelease_from=None)
        return s, [Log("mission.aborted"), Ack(env, "COMPLETED")]
    if s.state in ("LOADED", "SECURED") and s.mission_open:
        acts: list[Action] = [Send("sim.command", SimCommand(action="UNLOAD"))]
        if s.pending_assign is not None:
            acts.append(_reject(s.pending_assign, "INVALID_STATE", "Mission aborted"))
        s = replace(
            s,
            state="EMPTY",
            mission=None,
            mission_open=False,
            pending_assign=None,
            pending_update=None,
            unlock_expected=True,
            lock_requested=False,
            load_phase=None,
        )
        return s, [*acts, Log("mission.aborted"), Ack(env, "COMPLETED")]
    if s.state == "RETURNING":
        return s, [_reject(env, "INVALID_STATE", "Already returning to origin")]
    return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]


def _return_to_origin(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    if s.state in ("TRAVELLING", "AT_DESTINATION"):
        s = replace(s, state="RETURNING", prerelease_from=None)
        return s, [Ack(env, "COMPLETED")]
    if s.state == "DELIVERED":
        return s, [Ack(env, "COMPLETED")]  # navigation only
    if s.state == "RETURNING":
        return s, [_reject(env, "INVALID_STATE", "Already returning to origin")]
    return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]


def _change_destination(s: CtrlState, env: Envelope, now: datetime, cfg: Settings):
    ok = s.state == "TRAVELLING" or (
        s.state in ("LOADED", "SECURED") and s.mission_open
    )
    if not ok:
        return s, [_reject(env, "INVALID_STATE", invalid_state_text(s.state))]
    mission = s.mission.model_copy(update={"destination": env.body.destination})
    return replace(s, mission=mission), [Ack(env, "COMPLETED")]


COMMANDS = {
    "cmd.assign_mission": _assign,
    "cmd.update_payload": _update,
    "cmd.release": _release,
    "cmd.ack_fault": _ack_fault,
    "cmd.abort": _abort,
    "cmd.return_to_origin": _return_to_origin,
    "cmd.change_destination": _change_destination,
}

# -- sim.reading ------------------------------------------------------------------


def _reading(s: CtrlState, r: SimReading, now: datetime, cfg: Settings):
    acts: list[Action] = []
    s = replace(s, reading=r)

    # LOAD progress: ignore settled readings from before the LOAD took effect.
    settled_now = False
    if s.load_phase == "sent" and not r.settled:
        s = replace(s, load_phase="settling")
    elif s.load_phase == "settling" and r.settled:
        s = replace(s, load_phase=None)
        settled_now = True

    # The lock opening outside our own RELEASE or UNLOAD.
    if r.locked:
        s = replace(s, lock_seen_closed=True)
    unexpected_open = not r.locked and s.lock_seen_closed and not s.unlock_expected
    s, more = _set_fault(
        s, "PAYLOAD_UNSECURED", unexpected_open, "Lock reports open without a release"
    )
    acts += more

    s, more = _set_fault(
        s, "LOCK_SENSOR_FAULT", r.sensors.lock == "FAULT", "Lock sensor reports FAULT"
    )
    acts += more
    s, more = _set_fault(
        s, "LOAD_CELL_FAULT", r.sensors.load_cell == "FAULT", "Load cell reports FAULT"
    )
    acts += more
    if r.shift_cm is not None:
        s, more = _set_fault(
            s,
            "PAYLOAD_SHIFT",
            r.shift_cm > cfg.payload.unsecured_shift_cm,
            f"Payload shifted {fmt(r.shift_cm)} cm",
        )
        acts += more

    # Mass is judged only on settled readings with a payload aboard.
    aboard = s.mission is not None and not s.unlock_expected
    if aboard and r.settled and s.load_phase is None and r.mass_kg is not None:
        p = cfg.payload
        s, more = _set_fault(
            s,
            "WEIGHT_OUT_OF_RANGE",
            not mass_in_range(r.mass_kg, cfg),
            f"Measured mass {fmt(r.mass_kg)} kg is outside "
            f"{fmt(p.mass_min_kg)} to {fmt(p.mass_max_kg)} kg",
        )
        acts += more

    if settled_now and r.mass_kg is not None:  # AEG-512
        acts.append(
            Send(
                "payload.mass_report",
                MassReport(
                    mass_kg=r.mass_kg,
                    release_energy_wh_nominal=cfg.payload.release_energy_wh_nominal,
                    release_energy_wh_max=cfg.payload.release_energy_wh_max,
                ),
            )
        )
        if s.pending_update is not None:
            acts.append(Ack(s.pending_update, "COMPLETED"))
            s = replace(s, pending_update=None)

    # LOADED: lock once the mass has settled in range, then SECURED.
    if s.state == "LOADED" and r.settled and s.load_phase is None:
        if mass_in_range(r.mass_kg, cfg) and not s.lock_requested:
            s = replace(s, lock_requested=True)
            acts.append(Send("sim.command", SimCommand(action="LOCK")))
        if r.locked and is_secured(s, cfg):
            s = replace(s, state="SECURED")
            if s.pending_assign is not None:
                acts.append(Ack(s.pending_assign, "COMPLETED"))
                s = replace(s, pending_assign=None)

    # Release finished.
    if r.release_done and not s.delivered_sent:
        if s.state == "RELEASED":
            s, more = _delivered(s, now, cfg)
            s = replace(s, state="DELIVERED")
            acts += more
        elif s.state == "HELD" and s.held_from == "RELEASED":
            s, more = _delivered(s, now, cfg)
            s = replace(s, held_from="DELIVERED")
            acts += more
    return s, acts


def _delivered(s: CtrlState, now: datetime, cfg: Settings):
    m = s.mission
    position = (
        s.nav.position
        if s.nav
        else LatLon(lat=m.destination.lat, lon=m.destination.lon)
    )
    body = PayloadDelivered(
        mission_id=m.mission_id,
        payload_id=m.payload_id,
        released_at=now,
        position=position,
        mass_kg=s.mass_at_release,
        energy_used_wh=cfg.payload.release_energy_wh_nominal,
    )
    acts: list[Action] = [Send("payload.delivered", body)]
    if s.pending_release is not None:
        acts.append(Ack(s.pending_release, "COMPLETED"))
    s = replace(
        s,
        delivered_sent=True,
        released=True,
        mission_open=False,
        pending_release=None,
        lock_seen_closed=False,
    )
    s, more = clear_fault(s, "RELEASE_FAILED")
    return s, [*acts, *more]


# -- nav.state --------------------------------------------------------------------


def _nav(s: CtrlState, n: NavState, now: datetime, cfg: Settings):
    acts: list[Action] = []
    was_permitted = departure_permitted(s, cfg)
    s = replace(s, nav=n)

    unsecured_departure = n.moving and (
        s.state in ("EMPTY", "LOADED") or (s.state == "SECURED" and not was_permitted)
    )
    if unsecured_departure:
        s, acts = raise_fault(
            s, "DEPARTED_UNSECURED", "Vehicle moved while the payload was not secured"
        )
    elif not n.moving:
        s, acts = clear_fault(s, "DEPARTED_UNSECURED")

    if s.state == "SECURED" and n.moving and was_permitted:
        s = replace(s, state="TRAVELLING")
    elif s.state == "TRAVELLING" and n.at_destination and not n.moving:
        s = replace(s, state="AT_DESTINATION", arrived_at=now)
        if s.link_lost:
            s = replace(s, prerelease_from=now)
    elif s.state == "AT_DESTINATION" and n.moving:
        s = replace(s, state="TRAVELLING", arrived_at=None, prerelease_from=None)
    elif s.state == "RETURNING" and n.at_origin and not n.moving:
        s = replace(s, state="SECURED", mission_open=False, prerelease_authorized=False)
    return s, acts


# -- tick -------------------------------------------------------------------------


def _tick(s: CtrlState, now: datetime, cfg: Settings):
    acts: list[Action] = []
    p = cfg.payload

    # A release that does not finish in time.
    if s.state == "RELEASED" and s.release_started is not None:
        limit = p.release_time_s + cfg.timing.release_grace_s
        if (now - s.release_started).total_seconds() > limit:
            s, acts = raise_fault(
                s, "RELEASE_FAILED", f"Release did not finish in {fmt(limit)} s"
            )

    # Pre-authorized release with the link LOST at the destination (AEG-507).
    if (
        s.state == "AT_DESTINATION"
        and s.link_lost
        and s.prerelease_authorized
        and s.prerelease_from is not None
        and (now - s.prerelease_from).total_seconds() >= cfg.link.prerelease_wait_s
        and release_refusal(
            moving(s), at_destination(s), is_secured(s, cfg), critical_active(s)
        )
        is None
    ):
        s, more = _start_release(s, now, None)
        acts += [Log("release.preauthorized"), *more]
    return s, acts


def _unload(s: CtrlState):
    """Ground crew unloads a payload that came back (SECURED, mission closed)."""
    if s.state != "SECURED" or s.mission_open:
        return s, [Log("unload.refused", {"state": s.state})]
    s = replace(
        s,
        state="EMPTY",
        mission=None,
        unlock_expected=True,
        lock_requested=False,
        lock_seen_closed=False,
    )
    return s, [Send("sim.command", SimCommand(action="UNLOAD"))]
