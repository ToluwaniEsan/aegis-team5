import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aegis.common.ui_models import CommandResult, Snapshot, UiCommand
from scripts import export_schemas


@pytest.fixture
def snapshot():
    fresh = {"updated_at": None, "age_s": None, "stale": True}
    place = {"id": "FOB_ALPHA", "name": "FOB Alpha", "lat": 1, "lon": 2}
    dims = {"length": 60, "width": 40, "height": 40}
    mission = {
        "mission_id": "MSN-2026-001",
        "payload_id": "PAY-2026-001",
        "status": "QUEUED",
        "origin": place,
        "destination": place,
        "priority": "URGENT",
        "declared_mass_kg": 500,
        "dims_cm": dims,
        "prerelease_authorized": False,
        "created_at": "2026-11-19T00:00:00.000Z",
    }
    permission = {"allowed": False, "reason": None, "needs_confirmation": False}
    return {
        "kind": "snapshot",
        "seq": 1,
        "server_time": "2026-11-19T00:00:00.000Z",
        "test_mode": True,
        "link": {**fresh, "state": "LOST", "latency_ms": None, "loss_pct": None},
        "vehicle_health": {
            "overall": "DEGRADED",
            "subsystems": [
                {
                    **fresh,
                    "key": "power",
                    "label": "Power",
                    "team": 4,
                    "status": "UNKNOWN",
                    "detail": "",
                }
            ],
        },
        "payload": {
            **fresh,
            "state": "EMPTY",
            "held_from": None,
            "payload_id": None,
            "secured": False,
            "locked": False,
            "mass_kg": None,
            "shift_cm": None,
            "release_energy_wh": None,
            "sensor_health": "UNKNOWN",
            "sensors": {"load_cell": "UNKNOWN", "lock": "UNKNOWN", "shift": "UNKNOWN"},
            "prerelease_authorized": False,
            "departure_permitted": False,
            "departure_reason": None,
        },
        "nav": {
            **fresh,
            "origin": place,
            "destination": None,
            "position": None,
            "route": [{"lat": 1, "lon": 2}],
            "progress_pct": None,
            "moving": False,
            "speed_mps": None,
            "eta_s": None,
            "blocked": {
                "reason": "blocked",
                "at": {"lat": 1, "lon": 2},
                "old_route": [],
                "new_eta_s": None,
                "since": "time",
            },
        },
        "mission": {
            "active": None,
            "queue": [mission],
            "next_ids": {"mission_id": "MSN-2026-002", "payload_id": "PAY-2026-002"},
        },
        "commands": [
            {
                "command_id": "id",
                "command": "release",
                "label": "Release",
                "state": "FAILED",
                "reason": None,
                "sent_at": "time",
                "updated_at": "time",
            }
        ],
        "allowed": {
            name: permission
            for name in (
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
            )
        },
        "alerts": [
            {
                "alert_id": "id",
                "code": "FAULT",
                "severity": "WARNING",
                "title": "Fault",
                "source": "Payload",
                "recommended_action": "Inspect",
                "raised_at": "time",
                "acknowledged": False,
                "active": True,
            }
        ],
        "estop_active": False,
        "delivery": {
            "mission_id": "MSN-2026-001",
            "payload_id": "PAY-2026-001",
            "destination": place,
            "released_at": "time",
            "confirmed_at": "time",
            "confirm_latency_s": 1,
            "mass_kg": 500,
            "energy_used_wh": 3.2,
        },
        "places": [place],
        "limits": {
            "mass_min_kg": 500,
            "mass_max_kg": 1000,
            "dims_max_cm": dims,
            "stale_after_s": 5,
            "unsecured_shift_cm": 2,
            "release_energy_wh_max": 5,
        },
    }


def test_OI_017_snapshot_nested_serialization(snapshot):
    assert json.loads(Snapshot.model_validate(snapshot).model_dump_json()) == snapshot


def test_OI_003_command_and_result_serialization():
    command = {
        "kind": "command",
        "client_req_id": "id",
        "command": "release",
        "args": {"arbitrary": [None, {"nested": True}]},
        "confirmed": True,
    }
    result = {
        "kind": "command_result",
        "client_req_id": "id",
        "accepted": False,
        "command_id": None,
        "reason": None,
    }
    assert UiCommand.model_validate(command).model_dump(mode="json") == command
    assert CommandResult.model_validate(result).model_dump(mode="json") == result


@pytest.mark.parametrize(
    "path",
    [
        ("link", "updated_at"),
        ("payload", "held_from"),
        ("nav", "blocked"),
        ("mission", "active"),
        ("delivery",),
        ("allowed", "release", "reason"),
    ],
)
def test_OI_017_nullable_fields_are_required(snapshot, path):
    obj = snapshot
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = None
    Snapshot.model_validate(snapshot)
    del obj[path[-1]]
    with pytest.raises(ValidationError):
        Snapshot.model_validate(snapshot)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.update(kind="command"),
        lambda s: s["link"].update(state="UNKNOWN"),
        lambda s: s["payload"]["sensors"].update(lock="BROKEN"),
        lambda s: s["vehicle_health"]["subsystems"][0].update(team=1),
        lambda s: s["allowed"].pop("estop"),
        lambda s: s["nav"].update(moving="false"),
    ],
)
def test_OI_017_invalid_snapshot_inputs_rejected(snapshot, change):
    value = copy.deepcopy(snapshot)
    change(value)
    with pytest.raises(ValidationError):
        Snapshot.model_validate(value)


def test_OI_003_command_result_required_nulls_and_invalid_command():
    with pytest.raises(ValidationError):
        CommandResult.model_validate(
            {"kind": "command_result", "client_req_id": "id", "accepted": False}
        )
    with pytest.raises(ValidationError):
        UiCommand.model_validate(
            {
                "kind": "command",
                "client_req_id": "id",
                "command": "launch",
                "args": {},
                "confirmed": True,
            }
        )


def test_ui_schema_export_matches_snapshot(tmp_path, monkeypatch):
    fake_script = tmp_path / "backend" / "scripts" / "export_schemas.py"
    monkeypatch.setattr(export_schemas, "__file__", str(fake_script))
    result = export_schemas.export_ui_schema()
    assert result == tmp_path / "contracts" / "ui.schema.json"
    assert json.loads(result.read_text()) == Snapshot.model_json_schema()
    checked_in = Path(__file__).resolve().parents[2] / "contracts" / "ui.schema.json"
    assert json.loads(checked_in.read_text()) == Snapshot.model_json_schema()
