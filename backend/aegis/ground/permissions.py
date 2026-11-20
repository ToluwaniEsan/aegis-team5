"""Command permissions on the ground (task B8): contracts section 5.

One pure function. The UI server puts the result in `snapshot.allowed`; the
Command Manager uses it to refuse early. The vehicle checks again on its own
(hard rule 5), and `release` uses the vehicle's own guard function so the
screen and the vehicle always give the same reason (OI-004).
"""

from __future__ import annotations

from aegis.common.config import Settings
from aegis.common.models import REASON_TEXT
from aegis.common.ui_models import (
    AlertView,
    CommandName,
    LinkView,
    Mission,
    NavView,
    PayloadView,
    Permission,
)
from aegis.vehicle.rules import invalid_state_text, release_refusal

# OI-003: commands that need the confirmation dialog.
NEEDS_CONFIRMATION: dict[str, bool] = {
    "assign_mission": False,
    "start_queued_mission": True,
    "remove_queued_mission": False,
    "abort": True,
    "return_to_origin": True,
    "change_destination": True,
    "update_payload": False,
    "release": True,
    "ack_fault": False,
    "estop": False,  # OI-019: never a confirmation step
}

HELD = REASON_TEXT["PAYLOAD_HELD"]
UNLOAD_FIRST = "Unload the payload first"
LINK_LOST = "Link is lost: the vehicle cannot receive the command"

# Payload states in which the vehicle is at the destination. The screen has no
# at_destination flag, so this mirrors what Team 2 reports to the vehicle.
AT_DESTINATION_STATES = ("AT_DESTINATION", "RELEASED", "DELIVERED")


def _ok(name: str) -> Permission:
    return Permission(
        allowed=True, reason=None, needs_confirmation=NEEDS_CONFIRMATION[name]
    )


def _no(name: str, reason: str) -> Permission:
    return Permission(
        allowed=False, reason=reason, needs_confirmation=NEEDS_CONFIRMATION[name]
    )


def permissions(
    payload: PayloadView,
    nav: NavView,
    link: LinkView,
    alerts: list[AlertView],
    active: Mission | None,
    queue: list[Mission],
    cfg: Settings,
) -> dict[CommandName, Permission]:
    state = payload.state
    held = state == "HELD"
    mission_open = active is not None
    critical = any(a.active and a.severity == "CRITICAL" for a in alerts)
    empty_bay = state in ("EMPTY", "DELIVERED")

    def gate(name: str, allowed_states: tuple[str, ...], ok: bool = True) -> Permission:
        """HELD first (as on the vehicle), then the state rule."""
        if held:
            return _no(name, HELD)
        if state not in allowed_states or not ok:
            return _no(name, invalid_state_text(state))
        return _ok(name)

    out: dict[str, Permission] = {}

    # assign_mission: with an active mission it joins the queue (OI-015).
    if mission_open:
        out["assign_mission"] = _ok("assign_mission")
    elif held:
        out["assign_mission"] = _no("assign_mission", HELD)
    elif not empty_bay:
        out["assign_mission"] = _no("assign_mission", UNLOAD_FIRST)
    else:
        out["assign_mission"] = _ok("assign_mission")

    if mission_open:
        out["start_queued_mission"] = _no(
            "start_queued_mission", "Finish or abort the active mission first"
        )
    elif not queue:
        out["start_queued_mission"] = _no(
            "start_queued_mission", "No mission in the queue"
        )
    elif held:
        out["start_queued_mission"] = _no("start_queued_mission", HELD)
    elif not empty_bay:
        out["start_queued_mission"] = _no("start_queued_mission", UNLOAD_FIRST)
    else:
        out["start_queued_mission"] = _ok("start_queued_mission")

    out["remove_queued_mission"] = (
        _ok("remove_queued_mission")
        if queue
        else _no("remove_queued_mission", "No mission in the queue")
    )

    secured_open = state != "SECURED" or mission_open
    out["abort"] = gate(
        "abort", ("LOADED", "SECURED", "TRAVELLING", "AT_DESTINATION"), secured_open
    )
    out["return_to_origin"] = gate(
        "return_to_origin", ("TRAVELLING", "AT_DESTINATION", "DELIVERED")
    )
    out["change_destination"] = gate(
        "change_destination", ("LOADED", "SECURED", "TRAVELLING"), secured_open
    )

    # update_payload: the state first, then movement (the vehicle's order, A-16).
    out["update_payload"] = gate("update_payload", ("LOADED", "SECURED"), mission_open)
    if out["update_payload"].allowed and nav.moving:
        out["update_payload"] = _no("update_payload", REASON_TEXT["VEHICLE_MOVING"])

    # release: HELD, then the vehicle's guards in order, then the state, then the link.
    refusal = release_refusal(
        moving=nav.moving,
        at_destination=state in AT_DESTINATION_STATES,
        secured=payload.secured,
        critical_fault=critical,
    )
    if held:
        out["release"] = _no("release", HELD)
    elif refusal:
        out["release"] = _no("release", refusal[1])
    elif state != "AT_DESTINATION":
        out["release"] = _no("release", invalid_state_text(state))
    elif link.state == "LOST":
        out["release"] = _no("release", LINK_LOST)
    else:
        out["release"] = _ok("release")

    out["ack_fault"] = (
        _ok("ack_fault")
        if any(not a.acknowledged for a in alerts)
        else _no("ack_fault", "No alert to acknowledge")
    )
    out["estop"] = _ok("estop")  # always (OI-019)
    return out
