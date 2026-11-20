"""Build and read envelopes (contracts section 2).

`make` fills `msg_id`, `sent_at`, `dst`, `iface` and `priority` from the
routing table below, so no caller ever chooses its own routing. `parse`
validates one JSON line, including the body against its type; a line that
fails raises `pydantic.ValidationError` and the bus logs it as `bus.invalid`.
"""

from __future__ import annotations

import uuid
from typing import Any, NamedTuple

from pydantic import BaseModel

from aegis.common.clock import Clock
from aegis.common.models import (
    BODIES,
    ENVELOPE_ADAPTER,
    ENVELOPE_CLASSES,
    Ack,
    Envelope,
)


class Route(NamedTuple):
    src: frozenset[str]  # endpoints allowed to send this type
    dst: tuple[str, ...]
    iface: str | None  # None: the caller passes it (ack: same as the command)
    priority: int


GROUND_CMD = frozenset({"ground.command_manager"})
PC = "vehicle.payload_controller"
NAV = "team2.nav"
POWER = "team4.power"
SM = "ground.status_monitor"
AM = "ground.alert_manager"


def _r(
    src: str | set[str], dst: tuple[str, ...], iface: str | None, priority: int
) -> Route:
    return Route(
        frozenset({src} if isinstance(src, str) else src), dst, iface, priority
    )


# The routing table in contracts section 2. Builders use exactly these values.
ROUTES: dict[str, Route] = {
    "cmd.assign_mission": _r("ground.command_manager", (PC,), "I2", 1),
    "cmd.update_payload": _r("ground.command_manager", (PC,), "I2", 1),
    "cmd.release": _r("ground.command_manager", (PC,), "I2", 1),
    "cmd.ack_fault": _r("ground.command_manager", (PC,), "I2", 1),
    "cmd.abort": _r("ground.command_manager", (PC, NAV), "I2", 1),
    "cmd.return_to_origin": _r("ground.command_manager", (PC, NAV), "I2", 1),
    "cmd.change_destination": _r("ground.command_manager", (PC, NAV), "I2", 1),
    "nav.assign": _r("ground.command_manager", (NAV,), "I4", 1),
    "cmd.estop": _r("ground.command_manager", (PC, NAV, POWER), "I5", 0),
    "hb.ground": _r("ground.command_manager", ("vehicle.link_watch",), "I2", 2),
    "ack": _r({PC, NAV, POWER}, ("ground.command_manager",), None, 1),
    "payload.status": _r(PC, (SM,), "I3", 2),
    "payload.delivered": _r(PC, (SM,), "I3", 1),
    "fault.raised": _r(PC, (AM, SM), "I3", 1),
    "fault.cleared": _r(PC, (AM, SM), "I3", 1),
    "backlog.batch": _r("vehicle.event_buffer", (SM,), "I3", 2),
    "payload.interlock": _r(PC, (NAV,), "I6", 1),
    "payload.mass_report": _r(PC, (POWER,), "I7", 1),
    "nav.state": _r(NAV, (PC, SM), "I6", 2),
    "nav.route_blocked": _r(NAV, (SM, AM), "I6", 1),
    "power.status": _r(POWER, (PC, SM), "I7", 2),
    "link.health": _r("team3.link", (SM,), "I8", 2),
    "t1.mission_report": _r(
        {"ground.command_manager", AM, SM}, ("team1.integration",), "I9", 1
    ),
    "t1.fault_report": _r(
        {"ground.command_manager", AM, SM}, ("team1.integration",), "I9", 1
    ),
    "t1.delivery_confirmation": _r(
        {"ground.command_manager", AM, SM}, ("team1.integration",), "I9", 1
    ),
    "t1.system_mode": _r("team1.integration", (SM,), "I9", 2),
    "int.link_state": _r("vehicle.link_watch", (PC, "vehicle.event_buffer"), "INT", 1),
    "sim.command": _r(PC, ("vehicle.payload_simulator",), "INT", 1),
    "sim.reading": _r("vehicle.payload_simulator", (PC,), "INT", 1),
    # dst depends on the target: see INJECT_DST.
    "test.inject": _r("ground.fault_injector", (), "INT", 0),
}
assert set(ROUTES) == set(BODIES), "ROUTES and BODIES must list the same types"

# Contracts section 10: where a test.inject goes, by target.
INJECT_DST: dict[str, str] = {
    "payload": "vehicle.test_agent",
    "nav": "vehicle.test_agent",
    "power": "vehicle.test_agent",
    "link": "team3.link",
    "team1": "team1.integration",
}

# An ack goes back over the interface its command came on.
ACK_IFACES = frozenset({"I2", "I4", "I5"})


def make(
    type: str,
    src: str,
    body: BaseModel | dict[str, Any],
    clock: Clock,
    *,
    iface: str | None = None,
    mission_id: str | None = None,
    payload_id: str | None = None,
    corr_id: uuid.UUID | str | None = None,
) -> Envelope:
    """Build a validated envelope for `type`.

    `dst`, `iface` and `priority` come from the routing table. `iface` may be
    passed only for an `ack`, where it must be the iface of the command it
    answers; `make_ack` does that for you. Raises ValueError for a type or
    src that is not in the routing table, and pydantic.ValidationError for a
    body that does not match its type.
    """
    route = ROUTES.get(type)
    if route is None:
        raise ValueError(f"unknown message type {type!r}")
    if src not in route.src:
        raise ValueError(f"{src!r} may not send {type!r}; allowed: {sorted(route.src)}")

    if route.iface is None:
        if iface not in ACK_IFACES:
            raise ValueError(f"{type!r} needs iface, one of {sorted(ACK_IFACES)}")
    elif iface is not None:
        raise ValueError(f"{type!r} always uses iface {route.iface}; do not pass one")
    else:
        iface = route.iface

    if isinstance(body, BaseModel):
        body = body.model_dump()
    body_model = BODIES[type].model_validate(body)

    dst = route.dst
    if type == "test.inject":
        dst = (INJECT_DST[body_model.target],)

    return ENVELOPE_CLASSES[type](
        msg_id=uuid.uuid4(),
        type=type,
        iface=iface,
        src=src,
        dst=list(dst),
        sent_at=clock.now(),
        priority=route.priority,
        mission_id=mission_id,
        payload_id=payload_id,
        corr_id=corr_id,
        body=body_model,
    )


def make_ack(
    command: Envelope,
    src: str,
    result: str,
    clock: Clock,
    *,
    reason_code: str | None = None,
    reason: str | None = None,
) -> Envelope:
    """Answer `command` with an ack from `src` (its iface, ids and corr_id)."""
    body = Ack(result=result, reason_code=reason_code, reason=reason, responder=src)
    return make(
        "ack",
        src,
        body,
        clock,
        iface=command.iface,
        mission_id=command.mission_id,
        payload_id=command.payload_id,
        corr_id=command.msg_id,
    )


def parse(line: str | bytes) -> Envelope:
    """Validate one JSON line into its per-type envelope.

    Raises pydantic.ValidationError for invalid JSON, an unknown type, a
    missing or extra field, or a body that does not match its type.
    """
    return ENVELOPE_ADAPTER.validate_json(line)


def dumps(env: Envelope) -> str:
    """One JSON line, timestamps as `...Z` with milliseconds (GEN-002)."""
    return env.model_dump_json()
