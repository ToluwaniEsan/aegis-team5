"""Task A2: message models and the envelope."""

import json
import re
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from aegis.common.clock import ManualClock
from aegis.common.envelope import INJECT_DST, ROUTES, dumps, make, make_ack, parse
from aegis.common.models import (
    BODIES,
    ENVELOPE_CLASSES,
    FAULT_CATALOG,
    INJECT_ACTIONS,
    Envelope,
    format_timestamp,
)

CONTRACTS = Path(__file__).resolve().parents[2] / "docs" / "02-contracts.md"
START = datetime(2026, 11, 19, 15, 4, 5, 123456, tzinfo=UTC)
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

PLACE_A = {"id": "FOB_ALPHA", "name": "FOB Alpha", "lat": 34.7201, "lon": -86.6402}
PLACE_B = {"id": "OP_BRAVO", "name": "Outpost Bravo", "lat": 34.7612, "lon": -86.5810}
POS = {"lat": 34.73, "lon": -86.62}
DIMS = {"length": 60, "width": 40, "height": 40}
SENSORS = {"load_cell": "OK", "lock": "OK", "shift": "OK"}
FAULT = {
    "fault_id": str(uuid.uuid4()),
    "code": "PAYLOAD_SHIFT",
    "severity": "WARNING",
    "source": "Payload",
    "message": "Payload shifted 3.1 cm",
    "recommended_action": "Reduce speed and inspect the payload at the next stop",
    "holds_payload": False,
}
DELIVERED = {
    "mission_id": "MSN-2026-007",
    "payload_id": "PAY-2026-007",
    "released_at": "2026-11-19T15:04:00.500Z",
    "position": POS,
    "mass_kg": 742.3,
    "energy_used_wh": 3.1,
}

# One valid (src, body) per message type in contracts section 3.
SAMPLES: dict[str, tuple[str, dict]] = {
    "cmd.assign_mission": (
        "ground.command_manager",
        {
            "mission_id": "MSN-2026-007",
            "payload_id": "PAY-2026-007",
            "origin": PLACE_A,
            "destination": PLACE_B,
            "priority": "URGENT",
            "declared_mass_kg": 742.0,
            "dims_cm": DIMS,
            "prerelease_authorized": True,
        },
    ),
    "cmd.update_payload": (
        "ground.command_manager",
        {"declared_mass_kg": 800.0, "dims_cm": DIMS},
    ),
    "cmd.release": ("ground.command_manager", {}),
    "cmd.ack_fault": ("ground.command_manager", {"fault_id": str(uuid.uuid4())}),
    "cmd.abort": ("ground.command_manager", {}),
    "cmd.return_to_origin": ("ground.command_manager", {}),
    "cmd.change_destination": ("ground.command_manager", {"destination": PLACE_A}),
    "cmd.estop": (
        "ground.command_manager",
        {"reason": "Operator stop", "source": "OPERATOR"},
    ),
    "hb.ground": ("ground.command_manager", {"seq": 42}),
    "nav.assign": (
        "ground.command_manager",
        {
            "mission_id": "MSN-2026-007",
            "origin": PLACE_A,
            "destination": PLACE_B,
            "priority": "ROUTINE",
        },
    ),
    "ack": (
        "vehicle.payload_controller",
        {
            "result": "REJECTED",
            "reason_code": "VEHICLE_MOVING",
            "reason": "Vehicle is moving",
            "responder": "vehicle.payload_controller",
        },
    ),
    "payload.status": (
        "vehicle.payload_controller",
        {
            "state": "SECURED",
            "held_from": None,
            "secured": True,
            "locked": True,
            "mass_kg": 742.1,
            "shift_cm": 0.2,
            "release_energy_wh": None,
            "sensors": SENSORS,
            "prerelease_authorized": False,
            "departure_permitted": True,
            "departure_reason": None,
            "mission_id": "MSN-2026-007",
        },
    ),
    "payload.delivered": ("vehicle.payload_controller", DELIVERED),
    "fault.raised": ("vehicle.payload_controller", FAULT),
    "fault.cleared": (
        "vehicle.payload_controller",
        {"fault_id": FAULT["fault_id"], "code": "PAYLOAD_SHIFT"},
    ),
    "backlog.batch": ("vehicle.event_buffer", {"events": []}),  # filled in below
    "payload.interlock": (
        "vehicle.payload_controller",
        {"departure_permitted": False, "reason": "Payload is not secured"},
    ),
    "payload.mass_report": (
        "vehicle.payload_controller",
        {
            "mass_kg": 742.1,
            "release_energy_wh_nominal": 3.2,
            "release_energy_wh_max": 5.0,
        },
    ),
    "nav.state": (
        "team2.nav",
        {
            "moving": True,
            "speed_mps": 8.0,
            "position": POS,
            "at_destination": False,
            "at_origin": False,
            "eta_s": 61.0,
            "progress_pct": 40.0,
            "route": [POS, POS],
            "health": "OK",
        },
    ),
    "nav.route_blocked": (
        "team2.nav",
        {
            "reason": "Bridge out",
            "blocked_at": POS,
            "new_route": [POS],
            "new_eta_s": 90.0,
        },
    ),
    "power.status": (
        "team4.power",
        {"battery_pct": 82.0, "est_range_km": 41.0, "drivetrain_health": "OK"},
    ),
    "link.health": (
        "team3.link",
        {"state": "CONNECTED", "latency_ms": 80.0, "loss_pct": 0.0},
    ),
    "t1.mission_report": (
        "ground.status_monitor",
        {
            "mission_id": "MSN-2026-007",
            "payload_id": "PAY-2026-007",
            "status": "ACTIVE",
        },
    ),
    "t1.fault_report": ("ground.alert_manager", FAULT),
    "t1.delivery_confirmation": ("ground.status_monitor", DELIVERED),
    "t1.system_mode": ("team1.integration", {"mode": "EXERCISE"}),
    "int.link_state": (
        "vehicle.link_watch",
        {"state": "LOST", "since": "2026-11-19T15:04:00.000Z"},
    ),
    "sim.command": ("vehicle.payload_controller", {"action": "LOAD", "mass_kg": 742.0}),
    "sim.reading": (
        "vehicle.payload_simulator",
        {
            "mass_kg": None,
            "settled": True,
            "shift_cm": 0.0,
            "locked": True,
            "release_done": False,
            "sensors": {"load_cell": "FAULT", "lock": "OK", "shift": "OK"},
        },
    ),
    "test.inject": (
        "ground.fault_injector",
        {"target": "payload", "action": "shift", "params": {"cm": 3.1}},
    ),
}


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(START)


def _make(message_type: str, clock: ManualClock) -> Envelope:
    src, body = SAMPLES[message_type]
    kwargs = {}
    if message_type == "ack":
        kwargs = {"iface": "I2", "corr_id": uuid.uuid4()}
    if message_type == "backlog.batch":
        inner = make("fault.raised", "vehicle.payload_controller", FAULT, clock)
        body = {"events": [inner.model_copy(update={"buffered": True}).model_dump()]}
    return make(message_type, src, body, clock, mission_id="MSN-2026-007", **kwargs)


def test_every_catalog_type_has_a_sample():
    assert set(SAMPLES) == set(BODIES)


@pytest.mark.parametrize("message_type", sorted(BODIES))
def test_every_type_round_trips(message_type, clock):
    env = _make(message_type, clock)
    line = dumps(env)
    assert "\n" not in line
    back = parse(line)
    assert back == env
    assert type(back) is ENVELOPE_CLASSES[message_type]
    assert dumps(back) == line


@pytest.mark.parametrize("message_type", sorted(BODIES))
def test_make_fills_routing_from_the_table(message_type, clock):
    env = _make(message_type, clock)
    route = ROUTES[message_type]
    assert env.v == 1
    assert env.priority == route.priority
    assert env.iface == (route.iface or "I2")
    if message_type != "test.inject":
        assert tuple(env.dst) == route.dst
    assert isinstance(env.msg_id, uuid.UUID) and env.msg_id.version == 4
    assert env.sent_at == START.replace(microsecond=123000)


def test_routing_table_matches_the_contract_text():
    """Every row of the routing table in contracts section 2 matches ROUTES."""
    text = CONTRACTS.read_text(encoding="utf-8")
    table = text.split("**Routing table.**", 1)[1].split("\n\n", 2)[1]
    rows = [r for r in table.splitlines() if r.startswith("| `")]
    seen = set()
    for row in rows:
        types_cell, src_cell, dst_cell, iface_cell, prio_cell = [
            c.strip() for c in row.strip("|").split("|")
        ]
        types = re.findall(r"`([a-z0-9_.]+)`", types_cell)
        dst = tuple(re.findall(r"`([a-z0-9_.]+)`", dst_cell))
        for t in types:
            seen.add(t)
            route = ROUTES[t]
            assert route.priority == int(prio_cell), t
            if iface_cell.startswith(("I", "INT")):
                assert route.iface == iface_cell, t
            if t in ("sim.command", "sim.reading", "test.inject", "ack"):
                continue  # dst depends on direction or target; tested separately
            assert route.dst == dst, t
            assert route.src <= set(re.findall(r"`([a-z0-9_.]+)`", src_cell)), t
    assert seen == set(BODIES)


def test_GEN_002_timestamps_serialize_utc_with_milliseconds(clock):
    env = _make("payload.delivered", clock)
    data = json.loads(dumps(env))
    assert data["sent_at"] == "2026-11-19T15:04:05.123Z"
    assert TS_RE.match(data["body"]["released_at"])
    link = json.loads(dumps(_make("int.link_state", clock)))
    assert TS_RE.match(link["body"]["since"])


def test_GEN_002_other_time_zones_are_converted_to_utc():
    plus_two = timezone(timedelta(hours=2))
    assert (
        format_timestamp(datetime(2026, 11, 19, 17, 4, 5, 9000, tzinfo=plus_two))
        == "2026-11-19T15:04:05.009Z"
    )


def _line(message_type: str, clock: ManualClock) -> dict:
    return json.loads(dumps(_make(message_type, clock)))


def _rejected(data: dict) -> None:
    with pytest.raises(ValidationError):
        parse(json.dumps(data))


def test_wrong_unit_field_is_rejected(clock):
    data = _line("payload.mass_report", clock)
    data["body"]["mass_lb"] = data["body"].pop("mass_kg")
    _rejected(data)


def test_missing_body_field_is_rejected(clock):
    data = _line("nav.state", clock)
    del data["body"]["moving"]
    _rejected(data)


def test_missing_envelope_field_is_rejected(clock):
    data = _line("hb.ground", clock)
    del data["sent_at"]
    _rejected(data)


def test_unknown_type_is_rejected(clock):
    data = _line("hb.ground", clock)
    data["type"] = "hb.vehicle"
    _rejected(data)


def test_body_of_another_type_is_rejected(clock):
    data = _line("cmd.release", clock)
    data["body"] = {"seq": 1}
    _rejected(data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("v", 2),
        ("msg_id", "not-a-uuid"),
        ("iface", "I10"),
        ("src", "ground.nobody"),
        ("dst", []),
        ("dst", ["team9.unknown"]),
        ("priority", 3),
        ("sent_at", "2026-11-19T15:04:05.123"),  # no time zone
        ("extra_field", 1),
    ],
)
def test_bad_envelope_field_is_rejected(clock, field, value):
    data = _line("hb.ground", clock)
    data[field] = value
    _rejected(data)


def test_not_json_is_rejected():
    with pytest.raises(ValidationError):
        parse("{not json")


def test_nan_is_rejected(clock):
    line = dumps(_make("power.status", clock)).replace(
        '"battery_pct":82.0', '"battery_pct":NaN'
    )
    with pytest.raises(ValidationError):
        parse(line)


def test_ack_needs_corr_id(clock):
    data = _line("ack", clock)
    data["corr_id"] = None
    _rejected(data)


def test_corr_id_only_on_ack(clock):
    data = _line("hb.ground", clock)
    data["corr_id"] = str(uuid.uuid4())
    _rejected(data)


def test_ack_responder_must_be_src(clock):
    data = _line("ack", clock)
    data["body"]["responder"] = "team2.nav"
    _rejected(data)


def test_rejected_ack_needs_a_reason(clock):
    data = _line("ack", clock)
    data["body"]["reason"] = None
    _rejected(data)


def test_make_ack_answers_the_command(clock):
    cmd = make("cmd.estop", "ground.command_manager", SAMPLES["cmd.estop"][1], clock)
    ack = make_ack(cmd, "team4.power", "RECEIVED", clock)
    assert ack.corr_id == cmd.msg_id
    assert ack.iface == "I5"
    assert ack.dst == ["ground.command_manager"]
    assert ack.priority == 1
    assert parse(dumps(ack)) == ack


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "HELD"},  # HELD without held_from
        {"held_from": "SECURED"},  # held_from outside HELD
        {"state": "TRAVELLING"},  # departure_permitted outside SECURED
        {"secured": False},  # departure_permitted while unsecured
        {"mission_id": None},  # departure_permitted with no mission open
        {"departure_reason": "Payload is not secured"},  # permitted but a reason given
        {"departure_permitted": False},  # blocked with no reason
    ],
)
def test_payload_status_rejects_inconsistent_flags(clock, changes):
    data = _line("payload.status", clock)
    data["body"].update(changes)
    _rejected(data)


def test_payload_status_held_is_valid(clock):
    data = _line("payload.status", clock)
    data["body"].update(
        state="HELD",
        held_from="TRAVELLING",
        departure_permitted=False,
        departure_reason="Payload is held",
    )
    parse(json.dumps(data))


@pytest.mark.parametrize("code", sorted(FAULT_CATALOG))
def test_fault_catalog_entries_validate(clock, code):
    spec = FAULT_CATALOG[code]
    body = FAULT | {
        "code": code,
        "severity": spec.severity,
        "holds_payload": spec.holds_payload,
        "recommended_action": spec.recommended_action,
    }
    make("fault.raised", "vehicle.payload_controller", body, clock)


@pytest.mark.parametrize(
    "changes",
    [
        {"severity": "CRITICAL"},  # PAYLOAD_SHIFT is a WARNING
        {"holds_payload": True},  # PAYLOAD_SHIFT does not hold
        {"code": "NOT_A_FAULT"},
    ],
)
def test_fault_must_match_the_catalog(clock, changes):
    with pytest.raises(ValidationError):
        make("fault.raised", "vehicle.payload_controller", FAULT | changes, clock)


@pytest.mark.parametrize(
    "body",
    [
        {"action": "LOAD"},
        {"action": "LOCK", "mass_kg": 10.0},
    ],
)
def test_sim_command_mass_only_with_load(clock, body):
    with pytest.raises(ValidationError):
        make("sim.command", "vehicle.payload_controller", body, clock)


INJECT_PARAMS = {
    ("payload", "shift"): {"cm": 3.1},
    ("payload", "sensor"): {"sensor": "lock", "health": "FAULT"},
    ("payload", "mass_override"): {"kg": 1180},
    ("payload", "release_jam"): {"on": True},
    ("payload", "controller_crash"): {},
    ("payload", "unload"): {},
    ("link", "set"): {"latency_ms": 1500, "loss_pct": 12},
    ("link", "outage"): {"seconds": 30},
    ("nav", "depart"): {},
    ("nav", "arrive"): {},
    ("nav", "stop"): {},
    ("nav", "block_route"): {"reason": "Bridge out"},
    ("nav", "health"): {"health": "FAULT"},
    ("power", "battery"): {"pct": 15},
    ("power", "drivetrain"): {"health": "FAULT"},
    ("team1", "mode"): {"mode": "EXERCISE"},
}


def test_every_section_10_row_has_params():
    assert set(INJECT_PARAMS) == set(INJECT_ACTIONS)


@pytest.mark.parametrize("target, action", sorted(INJECT_PARAMS))
def test_test_inject_rows_route_to_their_target(clock, target, action):
    body = {
        "target": target,
        "action": action,
        "params": INJECT_PARAMS[(target, action)],
    }
    env = make("test.inject", "ground.fault_injector", body, clock)
    assert env.dst == [INJECT_DST[target]]
    assert env.priority == 0
    assert parse(dumps(env)) == env


@pytest.mark.parametrize(
    "body, message",
    [
        ({"target": "payload", "action": "explode", "params": {}}, "unknown action"),
        ({"target": "payload", "action": "shift", "params": {}}, "cm"),
        ({"target": "payload", "action": "shift", "params": {"cm": -1}}, "cm"),
        ({"target": "link", "action": "outage", "params": {"seconds": 0}}, "seconds"),
        ({"target": "nav", "action": "depart", "params": {"now": True}}, "now"),
        ({"target": "power", "action": "battery", "params": {"pct": 120}}, "pct"),
    ],
)
def test_test_inject_bad_params_name_the_problem(clock, body, message):
    with pytest.raises(ValidationError, match=message):
        make("test.inject", "ground.fault_injector", body, clock)


def test_make_refuses_unknown_type(clock):
    with pytest.raises(ValueError, match="unknown message type"):
        make("hb.vehicle", "ground.command_manager", {}, clock)


def test_make_refuses_wrong_src(clock):
    with pytest.raises(ValueError, match="may not send"):
        make("cmd.release", "ground.ui_server", {}, clock)


def test_make_refuses_iface_except_on_ack(clock):
    with pytest.raises(ValueError, match="always uses iface"):
        make("cmd.release", "ground.command_manager", {}, clock, iface="I4")
    with pytest.raises(ValueError, match="needs iface"):
        make("ack", "team2.nav", SAMPLES["ack"][1] | {"responder": "team2.nav"}, clock)


def test_make_validates_the_body(clock):
    with pytest.raises(ValidationError):
        make("hb.ground", "ground.command_manager", {"seq": -1}, clock)


def test_buffered_copy_round_trips(clock):
    env = _make("payload.delivered", clock).model_copy(update={"buffered": True})
    back = parse(dumps(env))
    assert back.buffered is True
    assert back == env


def test_envelopes_are_read_only(clock):
    env = _make("hb.ground", clock)
    with pytest.raises(ValidationError):
        env.priority = 0
