"""Task B8: command permissions (contracts section 5)."""

import pytest

from aegis.common.config import load_settings
from aegis.common.models import PAYLOAD_STATES
from aegis.common.ui_models import (
    AlertView,
    Dims,
    LinkView,
    Mission,
    NavView,
    PayloadView,
    Place,
    Sensors,
)
from aegis.ground.permissions import NEEDS_CONFIRMATION, permissions
from aegis.vehicle import rules
from tests.test_rules import cmd, in_state, run

CFG = load_settings()
COMMANDS = list(NEEDS_CONFIRMATION)
FOB = Place(**CFG.places[0].model_dump())
BRAVO = Place(**CFG.places[1].model_dump())


def payload_view(state="EMPTY", secured=False, held_from=None, **kw) -> PayloadView:
    fields = dict(
        updated_at=None,
        age_s=None,
        stale=False,
        state=state,
        held_from=held_from if state == "HELD" else None,
        payload_id=None,
        secured=secured,
        locked=secured,
        mass_kg=None,
        shift_cm=None,
        release_energy_wh=None,
        sensor_health="OK",
        sensors=Sensors(load_cell="OK", lock="OK", shift="OK"),
        prerelease_authorized=False,
        departure_permitted=False,
        departure_reason="x",
    )
    return PayloadView(**(fields | kw))


def nav_view(moving=False) -> NavView:
    return NavView(
        updated_at=None,
        age_s=None,
        stale=False,
        origin=FOB,
        destination=BRAVO,
        position=None,
        route=[],
        progress_pct=None,
        moving=moving,
        speed_mps=None,
        eta_s=None,
        blocked=None,
    )


def link_view(state="CONNECTED") -> LinkView:
    return LinkView(
        updated_at=None,
        age_s=None,
        stale=False,
        state=state,
        latency_ms=None,
        loss_pct=None,
    )


def alert(severity="WARNING", acknowledged=False, active=True) -> AlertView:
    return AlertView(
        alert_id="a1",
        code="PAYLOAD_SHIFT",
        severity=severity,
        title="t",
        source="Payload",
        recommended_action="r",
        raised_at="2026-11-20T12:00:00.000Z",
        acknowledged=acknowledged,
        active=active,
    )


def mission(status="ACTIVE") -> Mission:
    return Mission(
        mission_id="MSN-2026-001",
        payload_id="PAY-2026-001",
        status=status,
        origin=FOB,
        destination=BRAVO,
        priority="ROUTINE",
        declared_mass_kg=742.0,
        dims_cm=Dims(length=60.0, width=40.0, height=40.0),
        prerelease_authorized=False,
        created_at="2026-11-20T12:00:00.000Z",
    )


def perms(
    state="EMPTY",
    *,
    secured=None,
    moving=False,
    link="CONNECTED",
    alerts=(),
    active=None,
    queue=(),
):
    if secured is None:
        secured = state in ("SECURED", "TRAVELLING", "AT_DESTINATION", "RETURNING")
    held_from = "SECURED" if state == "HELD" else None
    return permissions(
        payload_view(state, secured, held_from),
        nav_view(moving),
        link_view(link),
        list(alerts),
        active,
        list(queue),
        CFG,
    )


CONDITIONS = {
    "nominal": {},
    "link_lost": {"link": "LOST"},
    "critical_alert": {"alerts": [alert("CRITICAL")]},
    "queued_mission": {"queue": [mission("QUEUED")]},
}


@pytest.mark.parametrize("condition", list(CONDITIONS))
@pytest.mark.parametrize("state", PAYLOAD_STATES)
def test_OI_004_every_command_every_state_has_a_reason_when_refused(state, condition):
    kw = dict(CONDITIONS[condition])
    if state not in ("EMPTY", "DELIVERED"):
        kw.setdefault("active", mission())
    result = perms(state, **kw)
    assert set(result) == set(COMMANDS)
    for name, p in result.items():
        assert p.needs_confirmation == NEEDS_CONFIRMATION[name]  # OI-003
        if p.allowed:
            assert p.reason is None
        else:
            assert p.reason, f"{name} refused in {state} ({condition}) without a reason"


def test_OI_003_confirmation_flags_match_the_contract():
    assert {n for n, c in NEEDS_CONFIRMATION.items() if c} == {
        "start_queued_mission",
        "abort",
        "return_to_origin",
        "change_destination",
        "release",
    }
    assert NEEDS_CONFIRMATION["estop"] is False  # OI-019


@pytest.mark.parametrize("state", PAYLOAD_STATES)
def test_estop_always_allowed(state):
    for kw in CONDITIONS.values():
        assert perms(state, **kw)["estop"].allowed


def test_release_allowed_only_when_every_guard_holds():
    ok = perms("AT_DESTINATION", active=mission())["release"]
    assert ok.allowed and ok.needs_confirmation

    assert (
        perms("AT_DESTINATION", moving=True, active=mission())["release"].reason
        == "Vehicle is moving"
    )
    assert (
        perms("AT_DESTINATION", secured=False, active=mission())["release"].reason
        == "Payload is not secured"
    )
    assert (
        perms("AT_DESTINATION", alerts=[alert("CRITICAL")], active=mission())[
            "release"
        ].reason
        == "A critical fault is active"
    )
    assert (
        perms("TRAVELLING", active=mission())["release"].reason
        == "Not at the destination"
    )
    lost = perms("AT_DESTINATION", link="LOST", active=mission())["release"]
    assert not lost.allowed and "Link is lost" in lost.reason
    # An acknowledged-but-cleared critical alert does not block.
    cleared = alert("CRITICAL", acknowledged=True, active=False)
    assert perms("AT_DESTINATION", alerts=[cleared], active=mission())[
        "release"
    ].allowed


@pytest.mark.parametrize("name", PAYLOAD_STATES)
def test_OI_004_release_reason_matches_the_vehicle(name):
    """The screen and the vehicle give the same reason in every state."""
    s = in_state(name)
    _, acts = run(s, rules.Command(cmd("cmd.release")))
    vehicle = next(
        (a for a in acts if isinstance(a, rules.Ack) and a.result == "REJECTED"), None
    )

    st = rules.status(s, CFG)
    view = payload_view(st.state, st.secured, st.held_from)
    ground = permissions(
        view,
        nav_view(bool(s.nav and s.nav.moving)),
        link_view(),
        [],
        mission() if s.mission_open else None,
        [],
        CFG,
    )["release"]
    if vehicle is not None:
        assert not ground.allowed
        assert ground.reason == vehicle.reason
    else:
        assert ground.allowed


def test_held_allows_only_ack_fault_estop_and_queue_edits():
    result = perms(
        "HELD", active=mission(), alerts=[alert("CRITICAL")], queue=[mission("QUEUED")]
    )
    allowed = {n for n, p in result.items() if p.allowed}
    assert allowed == {"ack_fault", "estop", "assign_mission", "remove_queued_mission"}
    for name in (
        "abort",
        "release",
        "update_payload",
        "return_to_origin",
        "change_destination",
    ):
        assert result[name].reason == "Payload is held: acknowledge the fault first"


def test_assign_mission_rules():
    assert perms("EMPTY")["assign_mission"].allowed
    assert perms("DELIVERED")["assign_mission"].allowed
    assert perms("LOADED")["assign_mission"].reason == "Unload the payload first"
    # With an active mission it joins the queue (OI-015), in any state.
    assert perms("TRAVELLING", active=mission())["assign_mission"].allowed


def test_start_and_remove_queued_mission():
    q = [mission("QUEUED")]
    assert perms("EMPTY", queue=q)["start_queued_mission"].allowed
    assert perms("EMPTY")["start_queued_mission"].reason == "No mission in the queue"
    assert (
        perms("TRAVELLING", active=mission(), queue=q)["start_queued_mission"].reason
        == "Finish or abort the active mission first"
    )
    assert (
        perms("SECURED", queue=q)["start_queued_mission"].reason
        == "Unload the payload first"
    )
    assert perms("EMPTY", queue=q)["remove_queued_mission"].allowed
    assert not perms("EMPTY")["remove_queued_mission"].allowed


def test_abort_return_change_update_by_state():
    act = mission()
    allowed = {
        name: {s for s in PAYLOAD_STATES if perms(s, active=act)[name].allowed}
        for name in (
            "abort",
            "return_to_origin",
            "change_destination",
            "update_payload",
        )
    }
    assert allowed["abort"] == {"LOADED", "SECURED", "TRAVELLING", "AT_DESTINATION"}
    assert allowed["return_to_origin"] == {"TRAVELLING", "AT_DESTINATION", "DELIVERED"}
    assert allowed["change_destination"] == {"LOADED", "SECURED", "TRAVELLING"}
    assert allowed["update_payload"] == {"LOADED", "SECURED"}
    # A returned payload (SECURED, mission closed) cannot be aborted or redirected.
    assert not perms("SECURED")["abort"].allowed
    assert not perms("SECURED")["change_destination"].allowed
    # A-16: no update while moving.
    assert (
        perms("SECURED", moving=True, active=act)["update_payload"].reason
        == "Vehicle is moving"
    )


def test_ack_fault_needs_an_unacknowledged_alert():
    assert not perms("EMPTY")["ack_fault"].allowed
    assert perms("EMPTY", alerts=[alert()])["ack_fault"].allowed
    assert not perms("EMPTY", alerts=[alert(acknowledged=True)])["ack_fault"].allowed
