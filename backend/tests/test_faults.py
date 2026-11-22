"""Task A6: faults on the vehicle. The behaviour lives in rules.py (A4); these
are the four named tests, run on the real components with a ManualClock."""

from datetime import datetime, timedelta

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.run_all import build_system
from aegis.vehicle import rules
from tests.fakes import FAKE_START, FakeLog, advance
from tests.test_payload_controller import Vehicle
from tests.test_rules import cmd, in_state, reading, run

CFG = load_settings()
NOW = FAKE_START
LIMIT_S = CFG.timing.fault_report_max_s


async def secured_vehicle():
    v = Vehicle()
    await v.start()
    await v.assign()
    await v.wait(CFG.payload.load_time_s + CFG.payload.secure_time_s + 1.0)
    assert v.status().state == "SECURED"
    return v


async def test_AEG_502_shift_over_2cm_raises_within_2s():
    v = await secured_vehicle()
    limit = CFG.payload.unsecured_shift_cm

    await v.sim.inject_shift(limit)  # at the limit: still secured
    await v.wait(0.5)
    assert v.bus.sent("fault.raised") == []
    assert v.status().secured

    t0 = v.clock.now()
    await v.sim.inject_shift(limit + 0.1)  # over it
    await v.wait(0.5)
    [fault] = v.bus.sent("fault.raised")
    assert fault.body.code == "PAYLOAD_SHIFT"
    assert (fault.sent_at - t0).total_seconds() <= LIMIT_S
    assert fault.body.severity == "WARNING" and fault.body.holds_payload is False
    assert fault.body.recommended_action  # from the catalog
    assert not v.status().secured  # AEG-502: unsecured, blocks release and departure
    assert v.bus.last("payload.interlock").body.departure_permitted is False
    await v.stop()


async def test_AEG_513_payload_fault_reported_within_2s():
    """End to end: the fault is injected on the vehicle and the ground receives
    fault.raised over the link stand-in within fault_report_max_s."""
    clock = ManualClock(FAKE_START)
    logs = {}

    def make_log(process, run_id, c, s):
        logs[process] = FakeLog(process, run_id, c, s)
        return logs[process]

    system = build_system(CFG, clock, "run-faults", make_log)
    await system.start()
    await advance(clock, 1.0)

    t0 = clock.now()
    await system.ground.fault_injector.inject(
        "payload", "sensor", {"sensor": "lock", "health": "FAULT"}
    )
    await advance(clock, LIMIT_S, step=0.05)

    received = [
        r
        for r in logs["ground"].of("msg.recv")
        if r["env"]["type"] == "fault.raised"
        and r["env"]["body"]["code"] == "LOCK_SENSOR_FAULT"
    ]
    assert received, "fault.raised did not reach the ground"
    got_at = datetime.fromisoformat(received[0]["t"].replace("Z", "+00:00"))
    assert (got_at - t0).total_seconds() <= LIMIT_S
    body = received[0]["env"]["body"]
    assert body["severity"] == "CRITICAL" and body["holds_payload"] is True
    assert received[0]["env"]["dst"] == [
        "ground.alert_manager",
        "ground.status_monitor",
    ]
    await system.stop()


def test_OI_019_estop_cleared_only_by_ack():
    s = in_state("TRAVELLING")
    stop = cmd("cmd.estop", {"reason": "Operator stop", "source": "OPERATOR"})
    s, _ = run(s, rules.Command(stop))
    assert s.state == "HELD" and s.held_from == "TRAVELLING"

    # Time, ticks, link changes and healthy readings do not clear it.
    later = NOW + timedelta(minutes=30)
    s, _ = run(
        s,
        rules.Tick(),
        rules.LinkLost(),
        rules.LinkRestored(),
        rules.Reading(reading(locked=True)),
        now=later,
    )
    assert s.state == "HELD"
    estop = next(f for f in s.faults if f.code == "ESTOP_ACTIVE")
    assert estop.active

    # Acknowledging another (unknown) fault does not clear it either.
    _, acts = run(
        s,
        rules.Command(
            cmd(
                "cmd.ack_fault",
                {"fault_id": "6f1c2a9e-1d3b-4c55-9a51-2f2a0f3b7c11"},
                later,
            )
        ),
        now=later,
    )
    assert any(isinstance(a, rules.Ack) and a.result == "REJECTED" for a in acts)

    # Only its own ack clears it, and the payload goes back to where it was.
    s, acts = run(
        s,
        rules.Command(cmd("cmd.ack_fault", {"fault_id": estop.fault_id}, later)),
        now=later,
    )
    assert s.state == "TRAVELLING" and s.held_from is None
    assert [
        a.body.code
        for a in acts
        if isinstance(a, rules.Send) and a.type == "fault.cleared"
    ] == ["ESTOP_ACTIVE"]


def _lock_sensor_held():
    s, _ = run(in_state("SECURED"), rules.Reading(reading(locked=True, lock="FAULT")))
    assert s.state == "HELD" and s.held_from == "SECURED"
    fault = next(f for f in s.faults if f.code == "LOCK_SENSOR_FAULT")
    return s, fault


def test_held_exits_only_when_cleared_and_acknowledged():
    ack = lambda f: rules.Command(cmd("cmd.ack_fault", {"fault_id": f.fault_id}))  # noqa: E731
    healthy = rules.Reading(reading(locked=True))

    # Acknowledged but still active: stays HELD.
    s, fault = _lock_sensor_held()
    s, _ = run(s, ack(fault))
    assert s.state == "HELD"
    s, _ = run(s, rules.Tick())
    assert s.state == "HELD"
    # ...then the condition clears: exits.
    s, _ = run(s, healthy)
    assert s.state == "SECURED" and s.held_from is None

    # Cleared but not acknowledged: stays HELD, however long we wait.
    s, fault = _lock_sensor_held()
    s, _ = run(s, healthy)
    assert s.state == "HELD"
    s, _ = run(s, rules.Tick(), now=NOW + timedelta(hours=1))
    assert s.state == "HELD"
    # ...then it is acknowledged: exits.
    s, _ = run(s, ack(fault))
    assert s.state == "SECURED" and s.faults == ()

    # Two holding faults: both must be cleared and acknowledged.
    s, fault = _lock_sensor_held()
    stop = cmd("cmd.estop", {"reason": "t", "source": "OPERATOR"})
    s, _ = run(s, rules.Command(stop))
    estop = next(f for f in s.faults if f.code == "ESTOP_ACTIVE")
    s, _ = run(s, healthy, ack(fault))
    assert s.state == "HELD"  # the stop is still open
    s, _ = run(s, ack(estop))
    assert s.state == "SECURED"

    # A non-holding fault never puts the payload in HELD.
    s, _ = run(in_state("SECURED"), rules.Reading(reading(locked=True, shift=5.0)))
    assert s.state == "SECURED"
    assert [f.code for f in s.faults] == ["PAYLOAD_SHIFT"]
