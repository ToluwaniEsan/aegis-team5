"""Task A8: safety properties of the Payload Controller rules, with hypothesis.

Random sequences of up to 200 events (commands of any age, nav states, sensor
readings, power, link loss and return, clock jumps, emergency stops) go into
`rules.step`. Each sequence starts from one of the 9 payload states, reached by
real events, so the deep states are covered too. After every step:

1. A RELEASE is only issued from AT_DESTINATION, stopped, secured, with no
   active CRITICAL fault, and either for a fresh operator release or after the
   full pre-release wait with the link LOST and release pre-authorized.
2. `departure_permitted` is never true unless SECURED, secured and a mission
   is open (contracts section 4).
3. In HELD, no RELEASE is issued.
4. `cmd.estop` always ends in HELD, whatever its age or the clock.
5. HELD always has a reason: some holding fault still active or
   unacknowledged. And once every condition clears and every fault is
   acknowledged, the payload leaves HELD (no permanent HELD).

Requirements: AEG-506, AEG-507, AEG-511, AEG-514, GEN-004.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from aegis.common.models import PAYLOAD_STATES, NavState, PowerStatus, SimReading
from aegis.vehicle import rules
from aegis.vehicle.rules import CtrlState
from tests.test_rules import BRAVO, CFG, DIMS, FOB, NOW, assign, cmd, in_state

T = CFG.timing
WAIT_S = CFG.link.prerelease_wait_s
EXAMPLES = 2000

# -- event specs: built against the state and clock at the time they run ---------


@dataclass(frozen=True)
class CommandSpec:
    type: str
    age_s: float  # how old the command is when it arrives; negative = from the future
    arg: int  # picks a mass, a destination or a fault


@dataclass(frozen=True)
class Jump:
    seconds: float


@dataclass(frozen=True)
class AckAll:
    """The operator acknowledges every open fault (fresh commands)."""


@dataclass(frozen=True)
class AllClear:
    """Conditions clear: a healthy reading, power OK, stopped at the destination."""


AGES = st.one_of(
    st.just(0.0),
    st.sampled_from(
        [
            T.command_max_age_s,  # at the limit: still fresh
            T.command_max_age_s + 0.1,  # stale
            -T.clock_skew_warn_s,  # at the skew limit: accepted
            -(T.clock_skew_warn_s + 0.1),  # from the future
            600.0,
            -600.0,
        ]
    ),
    st.floats(-10, 10, allow_nan=False),
)
COMMAND_TYPES = [
    "cmd.assign_mission",
    "cmd.update_payload",
    "cmd.release",
    "cmd.release",  # twice: release is what we care about most
    "cmd.ack_fault",
    "cmd.ack_fault",
    "cmd.abort",
    "cmd.return_to_origin",
    "cmd.change_destination",
    "cmd.estop",
]
MASSES = [742.0, 500.0, 1000.0, 1180.0, 100.0, CFG.payload.mass_min_kg]
HEALTH = st.sampled_from(["OK"] * 8 + ["WARN", "FAULT"])
GOOD = {"load_cell": "OK", "lock": "OK", "shift": "OK"}

commands = st.builds(
    CommandSpec, st.sampled_from(COMMAND_TYPES), AGES, st.integers(0, 50)
)

# Mostly healthy readings (so the release path is reached often), sometimes
# anything at all: unsettled, unlocked, shifted, out of range, failed sensors.
good_readings = st.builds(
    SimReading,
    mass_kg=st.sampled_from([742.0, 741.8, 742.3]),
    settled=st.just(True),
    shift_cm=st.sampled_from([0.0, 0.5, 2.0]),
    locked=st.just(True),
    release_done=st.just(False),
    sensors=st.just(GOOD),
)
any_readings = st.builds(
    SimReading,
    mass_kg=st.one_of(st.none(), st.sampled_from([0.0, 742.0, 742.3, 1180.0, 100.0])),
    settled=st.booleans(),
    shift_cm=st.one_of(st.none(), st.sampled_from([0.0, 1.0, 2.0, 2.1, 5.0])),
    locked=st.booleans(),
    release_done=st.booleans(),
    sensors=st.fixed_dictionaries(
        {"load_cell": HEALTH, "lock": HEALTH, "shift": HEALTH}
    ),
)
readings = st.one_of(good_readings, good_readings, any_readings)


@st.composite
def navs(draw):
    moving = draw(st.sampled_from([True, False, False]))
    at_destination = not moving and draw(st.sampled_from([True, True, False]))
    at_origin = not moving and not at_destination and draw(st.booleans())
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


powers = st.builds(
    PowerStatus,
    battery_pct=st.just(80.0),
    est_range_km=st.just(40.0),
    drivetrain_health=st.sampled_from(["OK"] * 6 + ["WARN", "FAULT"]),
)

events = st.one_of(
    commands,
    readings.map(rules.Reading),
    navs().map(rules.Nav),
    powers.map(rules.Power),
    st.sampled_from([rules.LinkLost(), rules.LinkRestored(), rules.Unload()]),
    st.just(rules.Tick()),
    st.sampled_from([0.5, 1.0, 2.0, 5.0, WAIT_S, 60.0, 600.0]).map(Jump),
    st.sampled_from([AckAll(), AllClear()]),
)

starts = st.tuples(st.sampled_from(PAYLOAD_STATES), st.booleans(), st.booleans())


def build_command(spec: CommandSpec, s: CtrlState, now):
    sent_at = now - timedelta(seconds=spec.age_s)
    if spec.type == "cmd.assign_mission":
        mass = MASSES[spec.arg % len(MASSES)]
        env = assign(mass, prerelease=spec.arg % 2 == 0)
        return env.model_copy(update={"sent_at": sent_at})
    if spec.type == "cmd.update_payload":
        body = {"declared_mass_kg": MASSES[spec.arg % len(MASSES)], "dims_cm": DIMS}
    elif spec.type == "cmd.ack_fault":
        ids = [f.fault_id for f in s.faults] or [str(uuid.uuid4())]
        body = {"fault_id": ids[spec.arg % len(ids)]}
    elif spec.type == "cmd.change_destination":
        body = {"destination": CFG.places[spec.arg % len(CFG.places)].model_dump()}
    elif spec.type == "cmd.estop":
        body = {"reason": "Operator stop", "source": "OPERATOR"}
    else:
        body = {}
    return cmd(spec.type, body, sent_at=sent_at)


def expand(sequence, state):
    """Yield events, unpacking AckAll and AllClear into their single steps.
    Acks are built lazily, against the state at the time they run."""
    for spec in sequence:
        if isinstance(spec, AckAll):
            for f in list(state().faults):
                yield lambda now, fid=f.fault_id: rules.Command(
                    cmd("cmd.ack_fault", {"fault_id": fid}, sent_at=now)
                )
        elif isinstance(spec, AllClear):
            yield rules.Reading(
                SimReading(
                    mass_kg=742.0,
                    settled=True,
                    shift_cm=0.0,
                    locked=True,
                    release_done=False,
                    sensors=GOOD,
                )
            )
            yield rules.Power(
                PowerStatus(battery_pct=80, est_range_km=40, drivetrain_health="OK")
            )
            yield rules.Nav(
                NavState(
                    moving=False,
                    speed_mps=0.0,
                    position={"lat": BRAVO["lat"], "lon": BRAVO["lon"]},
                    at_destination=True,
                    at_origin=False,
                    eta_s=None,
                    progress_pct=100.0,
                    route=[],
                    health="OK",
                )
            )
        else:
            yield spec


# -- the properties -----------------------------------------------------------------


def releases(actions) -> int:
    return sum(
        1
        for a in actions
        if isinstance(a, rules.Send)
        and a.type == "sim.command"
        and a.body.action == "RELEASE"
    )


def fresh(env, now) -> bool:
    age = (now - env.sent_at).total_seconds()
    return -age <= T.clock_skew_warn_s and age <= T.command_max_age_s


def check_release(before: CtrlState, event, now, actions) -> None:
    if not releases(actions):
        return
    # Properties 1 and 3.
    assert before.state == "AT_DESTINATION", f"RELEASE from {before.state}"
    assert not rules.moving(before), "RELEASE while moving"
    assert rules.at_destination(before), "RELEASE away from the destination"
    assert rules.is_secured(before, CFG), "RELEASE while not secured"
    assert not rules.critical_active(before), "RELEASE with a CRITICAL fault"
    operator = (
        isinstance(event, rules.Command)
        and event.env.type == "cmd.release"
        and fresh(event.env, now)
    )
    preauthorized = (
        isinstance(event, rules.Tick)
        and before.prerelease_authorized
        and before.link_lost
        and before.prerelease_from is not None
        and (now - before.prerelease_from).total_seconds() >= WAIT_S
    )
    assert operator or preauthorized, "RELEASE without a fresh command or the full wait"


def check_state(after: CtrlState) -> None:
    # The published messages are always valid (pydantic checks them).
    status = rules.status(after, CFG)
    lock = rules.interlock(after, CFG)
    assert lock.departure_permitted == status.departure_permitted
    # Property 2.
    if status.departure_permitted:
        assert after.state == "SECURED"
        assert status.secured and rules.is_secured(after, CFG)
        assert after.mission_open and status.mission_id
    # Property 5, part one: HELD always has a holding fault behind it.
    if after.state == "HELD":
        assert after.held_from is not None and after.held_from != "HELD"
        assert any(f.holds and (f.active or not f.acknowledged) for f in after.faults)


def recover(s: CtrlState, now):
    """Clear every fault condition, then acknowledge every fault."""
    nav = rules.Nav(
        NavState(
            moving=False,
            speed_mps=0.0,
            position={"lat": BRAVO["lat"], "lon": BRAVO["lon"]},
            at_destination=False,
            at_origin=False,
            eta_s=None,
            progress_pct=0.0,
            route=[],
            health="OK",
        )
    )
    ok = {"load_cell": "OK", "lock": "OK", "shift": "OK"}
    for event in [
        nav,
        rules.Power(
            PowerStatus(battery_pct=80, est_range_km=40, drivetrain_health="OK")
        ),
        # The release finishes (clears RELEASE_FAILED) and the lock reads closed.
        rules.Reading(
            SimReading(
                mass_kg=0.0,
                settled=True,
                shift_cm=0.0,
                locked=True,
                release_done=True,
                sensors=ok,
            )
        ),
    ]:
        s, _ = rules.step(s, event, now, CFG)
    for _ in range(len(s.faults) + 1):
        for f in list(s.faults):
            ack = cmd("cmd.ack_fault", {"fault_id": f.fault_id}, sent_at=now)
            s, _ = rules.step(s, rules.Command(ack), now, CFG)
    return s


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    derandomize=True,  # the same 2,000 examples every run, so CI is repeatable
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(start=starts, sequence=st.lists(events, min_size=20, max_size=200))
def test_AEG_506_safety_properties_hold_for_any_event_sequence(start, sequence):
    name, prerelease, link_lost = start
    s = in_state(name)
    if prerelease and s.mission is not None:
        s = rules.replace(s, prerelease_authorized=True)
    now = NOW
    if link_lost:
        s, _ = rules.step(s, rules.LinkLost(), now, CFG)
    check_state(s)

    for event in expand(sequence, lambda: s):
        if isinstance(event, Jump):
            now += timedelta(seconds=event.seconds)
            continue
        if isinstance(event, CommandSpec):
            event = rules.Command(build_command(event, s, now))
        elif callable(event):
            event = event(now)
        before = s
        s, actions = rules.step(s, event, now, CFG)

        check_release(before, event, now, actions)
        if before.state == "HELD":  # property 3
            assert not releases(actions), "RELEASE while HELD"
        if isinstance(event, rules.Command) and event.env.type == "cmd.estop":
            assert s.state == "HELD", "estop did not end in HELD"  # property 4
        check_state(s)

    # Property 5, part two: no permanent HELD.
    s = recover(s, now)
    assert s.state != "HELD", (
        f"stuck in HELD with {[(f.code, f.active, f.acknowledged) for f in s.faults]}"
    )


# -- focused on the release decision ---------------------------------------------

release_commands = st.builds(
    CommandSpec, st.just("cmd.release"), AGES, st.integers(0, 50)
)
release_events = st.one_of(
    release_commands,
    release_commands,
    commands,
    readings.map(rules.Reading),
    navs().map(rules.Nav),
    powers.map(rules.Power),
    st.sampled_from([rules.LinkLost(), rules.LinkRestored()]),
    st.just(rules.Tick()),
    st.just(rules.Tick()),
    st.sampled_from([1.0, 5.0, WAIT_S - 1, WAIT_S, WAIT_S + 1, 60.0]).map(Jump),
    st.sampled_from([AckAll(), AllClear()]),
)


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    prerelease=st.booleans(),
    link_lost=st.booleans(),
    sequence=st.lists(release_events, min_size=5, max_size=60),
)
def test_AEG_507_release_decisions_at_destination(prerelease, link_lost, sequence):
    """Every sequence starts at AT_DESTINATION, where release is possible, and
    is weighted toward the events that decide it."""
    test_AEG_506_safety_properties_hold_for_any_event_sequence.hypothesis.inner_test(
        start=("AT_DESTINATION", prerelease, link_lost), sequence=sequence
    )
