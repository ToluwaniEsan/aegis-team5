"""Task A4: the Payload Controller rules, tested as plain function calls."""

from dataclasses import replace
from datetime import timedelta

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.common.models import PAYLOAD_STATES, NavState, PowerStatus, SimReading
from aegis.vehicle import rules
from aegis.vehicle.rules import (
    Ack,
    Command,
    CtrlState,
    LinkLost,
    Nav,
    Power,
    Reading,
    Send,
    Tick,
    Unload,
    step,
)
from tests.fakes import FAKE_START

CFG = load_settings()
NOW = FAKE_START
GC = "ground.command_manager"
FOB, BRAVO = CFG.places[0].model_dump(), CFG.places[1].model_dump()
DIMS = {"length": 60, "width": 40, "height": 40}


# -- builders ---------------------------------------------------------------------


def cmd(type_, body=None, sent_at=None):
    return make(type_, GC, body or {}, ManualClock(sent_at or NOW))


def assign(mass=742.0, dims=None, prerelease=False):
    return cmd(
        "cmd.assign_mission",
        {
            "mission_id": "MSN-2026-001",
            "payload_id": "PAY-2026-001",
            "origin": FOB,
            "destination": BRAVO,
            "priority": "ROUTINE",
            "declared_mass_kg": mass,
            "dims_cm": dims or DIMS,
            "prerelease_authorized": prerelease,
        },
    )


def reading(mass=742.0, settled=True, locked=False, shift=0.0, done=False, **sensors):
    return SimReading(
        mass_kg=mass,
        settled=settled,
        shift_cm=shift,
        locked=locked,
        release_done=done,
        sensors={"load_cell": "OK", "lock": "OK", "shift": "OK"} | sensors,
    )


def nav(moving=False, at_destination=False, at_origin=False):
    pos = BRAVO if at_destination else FOB
    return NavState(
        moving=moving,
        speed_mps=8.0 if moving else 0.0,
        position={"lat": pos["lat"], "lon": pos["lon"]},
        at_destination=at_destination,
        at_origin=at_origin,
        eta_s=None,
        progress_pct=0.0,
        route=[],
        health="OK",
    )


def run(s, *events, now=NOW):
    acts = []
    for e in events:
        s, more = step(s, e, now, CFG)
        acts += more
    return s, acts


def acks(acts, result=None):
    return [
        a for a in acts if isinstance(a, Ack) and (result is None or a.result == result)
    ]


def sent(acts, type_):
    return [a.body for a in acts if isinstance(a, Send) and a.type == type_]


def sim_actions(acts):
    return [b.action for b in sent(acts, "sim.command")]


def rejected(acts):
    [a] = acks(acts, "REJECTED")
    return a.reason_code, a.reason


def secured(mass=742.0, prerelease=False):
    s, _ = run(
        CtrlState(),
        Command(assign(mass, prerelease=prerelease)),
        Reading(reading(mass, settled=False)),
        Reading(reading(mass)),
        Reading(reading(mass, locked=True)),
        Nav(nav(at_origin=True)),
    )
    assert s.state == "SECURED"
    return s


def in_state(name: str) -> CtrlState:
    """Each of the 9 states, reached by real events."""
    if name == "EMPTY":
        return CtrlState()
    if name == "LOADED":
        return run(CtrlState(), Command(assign()))[0]
    if name == "SECURED":
        return secured()
    s = run(secured(), Nav(nav(moving=True)))[0]
    if name == "TRAVELLING":
        return s
    if name == "RETURNING":
        return run(s, Command(cmd("cmd.abort")))[0]
    s = run(s, Nav(nav(at_destination=True)))[0]
    if name == "AT_DESTINATION":
        return s
    s = run(s, Command(cmd("cmd.release")))[0]
    if name == "RELEASED":
        return s
    if name == "DELIVERED":
        return run(s, Reading(reading(0.0, done=True)))[0]
    if name == "HELD":
        return run(
            secured(), Command(cmd("cmd.estop", {"reason": "t", "source": "OPERATOR"}))
        )[0]
    raise ValueError(name)


@pytest.mark.parametrize("name", PAYLOAD_STATES)
def test_every_state_is_reachable(name):
    assert in_state(name).state == name


# -- AEG-501, AEG-503: limits on assignment ---------------------------------------


def test_AEG_501_assign_rejected_over_mass_limit():
    s, acts = run(CtrlState(), Command(assign(1180.0)))
    assert s.state == "EMPTY"
    assert rejected(acts) == (
        "OUT_OF_LIMITS",
        "Payload 1,180 kg exceeds the 1,000 kg limit",
    )
    assert sim_actions(acts) == []


def test_AEG_501_assign_rejected_over_dims():
    s, acts = run(
        CtrlState(), Command(assign(dims={"length": 70, "width": 40, "height": 40}))
    )
    assert s.state == "EMPTY"
    code, text = rejected(acts)
    assert code == "OUT_OF_LIMITS"
    assert text == "Payload 70 × 40 × 40 cm exceeds the 60 × 40 × 40 cm limit"


@pytest.mark.parametrize("mass", [500.0, 750.0, 1000.0])
def test_AEG_503_accepts_500_750_1000_kg(mass):
    s = secured(mass)  # assigned, locked and SECURED
    assert s.state == "SECURED"
    # A reading just over the limit, within the scale's accuracy, still counts.
    s, _ = run(s, Reading(reading(mass + CFG.payload.sim_noise_kg, locked=True)))
    assert rules.departure_permitted(s, CFG)


def test_AEG_503_rejects_below_minimum():
    _, acts = run(CtrlState(), Command(assign(100.0)))
    assert rejected(acts) == (
        "OUT_OF_LIMITS",
        "Payload 100 kg is below the 226.8 kg minimum",
    )


# -- loading, locking and the interlock -------------------------------------------


def test_load_lock_secure_sequence_and_acks():
    a = assign()
    s, acts = run(CtrlState(), Command(a))
    assert s.state == "LOADED"
    assert [x.result for x in acks(acts)] == ["RECEIVED"]
    assert sim_actions(acts) == ["LOAD"]
    assert sent(acts, "sim.command")[0].mass_kg == 742.0

    # A stale settled reading from before the LOAD is ignored.
    s, acts = run(s, Reading(reading(0.0)))
    assert sim_actions(acts) == []

    s, acts = run(s, Reading(reading(settled=False)), Reading(reading()))
    assert sim_actions(acts) == ["LOCK"]
    assert len(sent(acts, "payload.mass_report")) == 1

    s, acts = run(s, Reading(reading()))  # LOCK only once
    assert sim_actions(acts) == []

    s, acts = run(s, Reading(reading(locked=True)))
    assert s.state == "SECURED"
    [done] = acks(acts, "COMPLETED")
    assert done.command is a


def test_AEG_511_interlock_false_until_secured_and_in_range():
    s, _ = run(CtrlState(), Command(assign()))
    assert rules.interlock(s, CFG).departure_permitted is False

    # Mass settles out of range: no LOCK, WEIGHT_OUT_OF_RANGE, interlock false.
    s, acts = run(s, Reading(reading(settled=False)), Reading(reading(1180.0)))
    assert sim_actions(acts) == []
    assert [f.code for f in sent(acts, "fault.raised")] == ["WEIGHT_OUT_OF_RANGE"]
    lock = rules.interlock(s, CFG)
    assert lock.departure_permitted is False and lock.reason == "Payload is not secured"

    # Back in range: LOCK, then SECURED, then the interlock opens.
    s, acts = run(s, Reading(reading()))
    assert sim_actions(acts) == ["LOCK"]
    assert rules.interlock(s, CFG).departure_permitted is False
    s, _ = run(s, Reading(reading(locked=True)))
    assert s.state == "SECURED"
    assert rules.interlock(s, CFG).departure_permitted is True
    assert rules.status(s, CFG).departure_reason is None


def test_departed_unsecured_holds_payload():
    s, _ = run(CtrlState(), Command(assign()))
    s, acts = run(s, Nav(nav(moving=True)))
    assert s.state == "HELD" and s.held_from == "LOADED"
    assert [f.code for f in sent(acts, "fault.raised")] == ["DEPARTED_UNSECURED"]


def test_secured_and_moving_is_travelling():
    s, _ = run(secured(), Nav(nav(moving=True)))
    assert s.state == "TRAVELLING"
    assert rules.interlock(s, CFG).departure_permitted is False  # SECURED only


# -- AEG-502: shift ---------------------------------------------------------------


def test_AEG_502_shift_over_limit_makes_payload_unsecured():
    s = secured()
    limit = CFG.payload.unsecured_shift_cm
    s, acts = run(s, Reading(reading(locked=True, shift=limit + 1.0)))
    assert s.state == "SECURED"  # the lock is still closed
    assert rules.is_secured(s, CFG) is False
    assert rules.departure_permitted(s, CFG) is False
    raised = sent(acts, "fault.raised")
    assert [f.code for f in raised] == ["PAYLOAD_SHIFT"]
    assert raised[0].severity == "WARNING" and raised[0].holds_payload is False

    # At the destination, the shift blocks release.
    s = in_state("AT_DESTINATION")
    s, _ = run(s, Reading(reading(locked=True, shift=limit + 1.0)))
    _, acts = run(s, Command(cmd("cmd.release")))
    assert rejected(acts) == ("NOT_SECURED", "Payload is not secured")

    # Shift back within the limit: the fault clears.
    s, acts = run(s, Reading(reading(locked=True, shift=0.5)))
    assert [f.code for f in sent(acts, "fault.cleared")] == ["PAYLOAD_SHIFT"]


# -- AEG-506: release -------------------------------------------------------------


def test_AEG_506_release_refused_while_moving():
    s = in_state("TRAVELLING")
    _, acts = run(s, Command(cmd("cmd.release")))
    assert rejected(acts) == ("VEHICLE_MOVING", "Vehicle is moving")
    # Even with the state still AT_DESTINATION, a moving vehicle is refused.
    s = replace(in_state("AT_DESTINATION"), nav=nav(moving=True, at_destination=True))
    s2, acts = run(s, Command(cmd("cmd.release")))
    assert rejected(acts)[0] == "VEHICLE_MOVING"
    assert "RELEASE" not in sim_actions(acts)


@pytest.mark.parametrize("name", PAYLOAD_STATES)
def test_AEG_506_release_refused_in_every_state_except_at_destination(name):
    s = in_state(name)
    after, acts = run(s, Command(cmd("cmd.release")))
    if name == "AT_DESTINATION":
        assert after.state == "RELEASED"
        assert sim_actions(acts) == ["RELEASE"]
        return
    assert after.state == s.state
    assert "RELEASE" not in sim_actions(acts)
    code, reason = rejected(acts)
    assert reason
    if name == "HELD":
        assert code == "PAYLOAD_HELD"


def test_release_guard_order_matches_contract():
    assert rules.release_refusal(True, False, False, True)[0] == "VEHICLE_MOVING"
    assert rules.release_refusal(False, False, False, True)[0] == "NOT_AT_DESTINATION"
    assert rules.release_refusal(False, True, False, True)[0] == "NOT_SECURED"
    assert rules.release_refusal(False, True, True, True)[0] == "CRITICAL_FAULT"
    assert rules.release_refusal(False, True, True, False) is None


def test_release_refused_with_critical_fault():
    s = in_state("AT_DESTINATION")
    s, _ = run(
        s,
        Power(PowerStatus(battery_pct=50, est_range_km=10, drivetrain_health="FAULT")),
    )
    assert s.state == "HELD"  # DRIVETRAIN_FAULT holds the payload
    fault = next(f for f in s.faults if f.code == "DRIVETRAIN_FAULT")
    # Acknowledge it while still active: it stays HELD, and the critical fault blocks release.
    s, _ = run(s, Command(cmd("cmd.ack_fault", {"fault_id": fault.fault_id})))
    assert s.state == "HELD"
    s = replace(s, state="AT_DESTINATION", held_from=None)
    _, acts = run(s, Command(cmd("cmd.release")))
    assert rejected(acts) == ("CRITICAL_FAULT", "A critical fault is active")


def test_AEG_507_release_requires_operator_command():
    s = in_state("AT_DESTINATION")
    # Link up, no command: nothing happens, however long we wait.
    for minutes in range(1, 11):
        s, acts = run(s, Tick(), now=NOW + timedelta(minutes=minutes))
        assert s.state == "AT_DESTINATION"
        assert "RELEASE" not in sim_actions(acts)
    # Pre-authorized but the link is up: still needs the operator.
    s = replace(s, prerelease_authorized=True)
    s, acts = run(s, Tick(), now=NOW + timedelta(minutes=20))
    assert s.state == "AT_DESTINATION"
    # The operator's command releases.
    s, acts = run(
        s,
        Command(cmd("cmd.release", sent_at=NOW + timedelta(minutes=20))),
        now=NOW + timedelta(minutes=20),
    )
    assert s.state == "RELEASED"


def test_AEG_508_delivered_sent_when_release_done():
    s = in_state("RELEASED")
    s, acts = run(s, Reading(reading(0.0, done=True)), now=NOW + timedelta(seconds=4))
    assert s.state == "DELIVERED"
    [d] = sent(acts, "payload.delivered")
    assert d.mission_id == "MSN-2026-001" and d.payload_id == "PAY-2026-001"  # AEG-510
    assert d.released_at == NOW + timedelta(seconds=4)
    assert d.mass_kg == 742.0
    assert d.energy_used_wh == CFG.payload.release_energy_wh_nominal
    assert (d.position.lat, d.position.lon) == (BRAVO["lat"], BRAVO["lon"])
    assert [a.command.type for a in acks(acts, "COMPLETED")] == ["cmd.release"]
    assert (
        rules.status(s, CFG).release_energy_wh == CFG.payload.release_energy_wh_nominal
    )


def test_release_failed_after_time_plus_grace():
    s = in_state("RELEASED")
    limit = CFG.payload.release_time_s + CFG.timing.release_grace_s
    s, acts = run(s, Tick(), now=NOW + timedelta(seconds=limit))
    assert s.state == "RELEASED"
    s, acts = run(s, Tick(), now=NOW + timedelta(seconds=limit + 1))
    assert s.state == "HELD" and s.held_from == "RELEASED"
    assert [f.code for f in sent(acts, "fault.raised")] == ["RELEASE_FAILED"]


def test_release_done_while_held_still_sends_delivered():
    s = in_state("RELEASED")
    limit = CFG.payload.release_time_s + CFG.timing.release_grace_s
    s, _ = run(s, Tick(), now=NOW + timedelta(seconds=limit + 1))
    assert s.state == "HELD"

    s, acts = run(s, Reading(reading(0.0, done=True)), now=NOW + timedelta(seconds=30))
    assert len(sent(acts, "payload.delivered")) == 1
    assert s.state == "HELD" and s.held_from == "DELIVERED"
    assert [f.code for f in sent(acts, "fault.cleared")] == ["RELEASE_FAILED"]
    # The timer is never restarted: later ticks raise nothing new.
    s, acts = run(s, Tick(), now=NOW + timedelta(seconds=120))
    assert sent(acts, "fault.raised") == []

    # Acknowledge it: back to DELIVERED.
    fault = next(f for f in s.faults if f.code == "RELEASE_FAILED")
    s, _ = run(
        s,
        Command(
            cmd(
                "cmd.ack_fault",
                {"fault_id": fault.fault_id},
                sent_at=NOW + timedelta(seconds=120),
            )
        ),
        now=NOW + timedelta(seconds=120),
    )
    assert s.state == "DELIVERED" and s.held_from is None


# -- AEG-512: payload update ------------------------------------------------------


def test_AEG_512_update_before_departure_only():
    upd = cmd("cmd.update_payload", {"declared_mass_kg": 800.0, "dims_cm": DIMS})
    s, acts = run(secured(), Command(upd))
    assert sim_actions(acts) == ["LOAD"]
    assert acks(acts, "COMPLETED") == []
    s, acts = run(
        s,
        Reading(reading(742.0, settled=False, locked=True)),
        Reading(reading(800.0, locked=True)),
    )
    assert [a.command for a in acks(acts, "COMPLETED")] == [upd]
    assert sent(acts, "payload.mass_report")[0].mass_kg == 800.0
    assert s.mission.declared_mass_kg == 800.0
    assert s.state == "SECURED" and rules.departure_permitted(s, CFG)

    # Moving: refused.
    s2 = replace(secured(), nav=nav(moving=True))
    _, acts = run(s2, Command(upd))
    assert rejected(acts) == ("VEHICLE_MOVING", "Vehicle is moving")
    # After departure: refused.
    _, acts = run(in_state("TRAVELLING"), Command(upd))
    assert rejected(acts)[0] == "INVALID_STATE"
    # Out of limits: refused.
    big = cmd("cmd.update_payload", {"declared_mass_kg": 1180.0, "dims_cm": DIMS})
    _, acts = run(secured(), Command(big))
    assert rejected(acts)[0] == "OUT_OF_LIMITS"


# -- two-sided timeout and OI-019 -------------------------------------------------


def test_stale_command_rejected():
    s = in_state("AT_DESTINATION")
    old = NOW - timedelta(seconds=CFG.timing.command_max_age_s + 0.1)
    s2, acts = run(s, Command(cmd("cmd.release", sent_at=old)))
    assert s2.state == "AT_DESTINATION"
    assert rejected(acts) == ("STALE_COMMAND", "Command is older than 5 s")
    # Exactly at the limit is still fresh.
    edge = NOW - timedelta(seconds=CFG.timing.command_max_age_s)
    s3, _ = run(s, Command(cmd("cmd.release", sent_at=edge)))
    assert s3.state == "RELEASED"


def test_future_timestamp_rejected():
    s = in_state("AT_DESTINATION")
    ahead = NOW + timedelta(seconds=CFG.timing.clock_skew_warn_s + 0.5)
    s2, acts = run(s, Command(cmd("cmd.release", sent_at=ahead)))
    assert s2.state == "AT_DESTINATION"
    assert rejected(acts) == (
        "FUTURE_TIMESTAMP",
        "Command time is ahead of the vehicle clock",
    )
    assert [f.code for f in sent(acts, "fault.raised")] == ["CLOCK_SKEW"]
    # The next normal command clears CLOCK_SKEW.
    _, acts = run(s2, Command(cmd("cmd.return_to_origin")))
    assert [f.code for f in sent(acts, "fault.cleared")] == ["CLOCK_SKEW"]


@pytest.mark.parametrize("name", PAYLOAD_STATES)
def test_OI_019_estop_holds_payload_from_any_state(name):
    s = in_state(name)
    stop = cmd("cmd.estop", {"reason": "Operator stop", "source": "OPERATOR"})
    after, acts = run(s, Command(stop))
    assert after.state == "HELD"
    assert after.held_from == (s.held_from if name == "HELD" else name)
    assert [a.result for a in acks(acts)] == ["RECEIVED", "COMPLETED"]
    assert any(f.code == "ESTOP_ACTIVE" and f.active for f in after.faults)


def test_OI_019_estop_never_rejected_for_age_or_clock():
    s = in_state("TRAVELLING")
    for sent_at in (NOW - timedelta(minutes=10), NOW + timedelta(minutes=10)):
        stop = cmd(
            "cmd.estop", {"reason": "Operator stop", "source": "OPERATOR"}, sent_at
        )
        after, acts = run(s, Command(stop))
        assert after.state == "HELD"
        assert acks(acts, "REJECTED") == []
        assert [a.result for a in acks(acts)] == ["RECEIVED", "COMPLETED"]


def test_estop_cleared_by_acknowledgement_returns_to_previous_state():
    s = in_state("HELD")
    fault = next(f for f in s.faults if f.code == "ESTOP_ACTIVE")
    s, acts = run(s, Command(cmd("cmd.ack_fault", {"fault_id": fault.fault_id})))
    assert s.state == "SECURED" and s.held_from is None
    assert [f.code for f in sent(acts, "fault.cleared")] == ["ESTOP_ACTIVE"]
    assert s.faults == ()


def test_held_refuses_everything_but_ack_fault():
    s = in_state("HELD")
    for t, body in [
        ("cmd.release", {}),
        ("cmd.abort", {}),
        ("cmd.return_to_origin", {}),
        ("cmd.update_payload", {"declared_mass_kg": 800.0, "dims_cm": DIMS}),
    ]:
        _, acts = run(s, Command(cmd(t, body)))
        assert rejected(acts) == (
            "PAYLOAD_HELD",
            "Payload is held: acknowledge the fault first",
        )


def test_every_command_gets_received_first():
    for name in PAYLOAD_STATES:
        _, acts = run(in_state(name), Command(cmd("cmd.release")))
        assert acks(acts)[0].result == "RECEIVED"


# -- abort, return, change destination --------------------------------------------


def test_abort_before_departure_unloads():
    s, acts = run(secured(), Command(cmd("cmd.abort")))
    assert s.state == "EMPTY" and s.mission is None
    assert sim_actions(acts) == ["UNLOAD"]
    # Our own UNLOAD opening the lock is not PAYLOAD_UNSECURED.
    s, acts = run(s, Reading(reading(0.0, locked=False)))
    assert sent(acts, "fault.raised") == []


def test_abort_while_travelling_returns():
    s, acts = run(in_state("TRAVELLING"), Command(cmd("cmd.abort")))
    assert s.state == "RETURNING"
    _, acts = run(s, Command(cmd("cmd.abort")))
    assert rejected(acts) == ("INVALID_STATE", "Already returning to origin")


def test_return_to_origin_from_delivered_is_navigation_only():
    s, acts = run(in_state("DELIVERED"), Command(cmd("cmd.return_to_origin")))
    assert s.state == "DELIVERED"
    assert [a.result for a in acks(acts)] == ["RECEIVED", "COMPLETED"]


def test_change_destination_recorded():
    new = CFG.places[2].model_dump()
    s, acts = run(
        in_state("TRAVELLING"),
        Command(cmd("cmd.change_destination", {"destination": new})),
    )
    assert s.mission.destination.id == new["id"]
    assert acks(acts, "COMPLETED")
    _, acts = run(
        in_state("AT_DESTINATION"),
        Command(cmd("cmd.change_destination", {"destination": new})),
    )
    assert rejected(acts)[0] == "INVALID_STATE"


def test_returned_payload_cannot_depart_until_unloaded_and_reassigned():
    s = in_state("RETURNING")
    s, _ = run(s, Nav(nav(at_origin=True)))
    assert s.state == "SECURED" and not s.mission_open
    assert s.prerelease_authorized is False
    lock = rules.interlock(s, CFG)
    assert lock.departure_permitted is False
    assert lock.reason == "Mission closed: unload the payload and assign a new mission"

    # Moving anyway is an unsecured departure.
    held, acts = run(s, Nav(nav(moving=True)))
    assert held.state == "HELD"
    assert [f.code for f in sent(acts, "fault.raised")] == ["DEPARTED_UNSECURED"]

    # Assigning without unloading is refused.
    _, acts = run(s, Command(assign()))
    assert rejected(acts)[0] == "INVALID_STATE"

    # Unload, then assign, then secure: departure permitted again.
    s, acts = run(s, Unload())
    assert s.state == "EMPTY" and sim_actions(acts) == ["UNLOAD"]
    s, _ = run(
        s,
        Reading(reading(0.0)),
        Command(assign()),
        Reading(reading(settled=False)),
        Reading(reading()),
        Reading(reading(locked=True)),
    )
    assert rules.departure_permitted(s, CFG)


# -- faults -----------------------------------------------------------------------


def test_lock_opening_unexpectedly_raises_payload_unsecured():
    s = in_state("TRAVELLING")
    s, acts = run(s, Reading(reading(locked=False)))
    assert s.state == "HELD"
    raised = sent(acts, "fault.raised")
    assert "PAYLOAD_UNSECURED" in [f.code for f in raised]


def test_lock_sensor_fault_holds_and_load_cell_fault_does_not():
    s, acts = run(secured(), Reading(reading(None, locked=True, load_cell="FAULT")))
    assert s.state == "SECURED"
    assert "LOAD_CELL_FAULT" in [f.code for f in sent(acts, "fault.raised")]
    assert not rules.is_secured(s, CFG)

    s, acts = run(secured(), Reading(reading(locked=True, lock="FAULT")))
    assert s.state == "HELD"
    assert "LOCK_SENSOR_FAULT" in [f.code for f in sent(acts, "fault.raised")]


def test_fault_raised_once_while_active():
    s = secured()
    s, a1 = run(s, Reading(reading(locked=True, shift=5.0)))
    s, a2 = run(s, Reading(reading(locked=True, shift=5.0)))
    assert len(sent(a1, "fault.raised")) == 1
    assert sent(a2, "fault.raised") == []


def test_unknown_fault_ack_rejected():
    _, acts = run(
        secured(),
        Command(
            cmd("cmd.ack_fault", {"fault_id": "6f1c2a9e-1d3b-4c55-9a51-2f2a0f3b7c11"})
        ),
    )
    assert rejected(acts) == ("INVALID_STATE", "No such fault")


def test_status_body_is_always_valid():
    for name in PAYLOAD_STATES:
        s = in_state(name)
        assert rules.status(s, CFG).state == name
        assert rules.interlock(s, CFG)


def test_prerelease_wait_starts_from_later_of_arrival_and_link_loss():
    s = replace(in_state("AT_DESTINATION"), prerelease_authorized=True)
    later = NOW + timedelta(seconds=30)
    s, _ = run(s, LinkLost(), now=later)
    assert s.prerelease_from == later
