import json

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.testing.scenario_runner import Runner, check, lookup, matches
from tests.fakes import FAKE_START


def test_GEN_002_nested_paths_and_operators():
    snapshot = {"commands": [{"state": "FAILED"}], "value": 3, "alerts": []}
    assert lookup(snapshot, "commands.0.state") == "FAILED"
    assert matches(3, {"gt": 2, "lt": 4})
    assert matches("payload shift", {"contains": "shift"})
    assert matches([1, 2], {"len": 2})
    assert matches(None, {"not": 1})
    assert not matches(3, {"unknown": 3})
    assert not matches(True, 1)
    assert not check({"snapshot": {"unknown": None}}, snapshot, {}, [])
    assert not check({"no_alert": {"code": "FAULT"}}, {}, {}, [])
    assert not check({"unknown_expectation": True}, snapshot, {}, [])


def test_OI_009_log_counts_are_exact_across_process_records():
    records = [
        {"kind": "msg.sent", "env": {"type": "cmd.abort"}},
        {"kind": "msg.sent", "env": {"type": "cmd.abort"}},
    ]
    assert check(
        {"log": {"kind": "msg.sent", "env.type": "cmd.abort", "count": 2}},
        {},
        {},
        records,
    )
    assert not check(
        {"log": {"kind": "msg.sent", "env.type": "cmd.abort", "count": 1}},
        {},
        {},
        records,
    )


@pytest.mark.asyncio
async def test_GEN_002_repeat_records_each_attempt_and_missing_logs_fail(tmp_path):
    cfg = load_settings().model_copy(
        update={
            "logging": load_settings().logging.model_copy(update={"dir": str(tmp_path)})
        }
    )
    runner = Runner(cfg, ManualClock(FAKE_START), "run")
    runner.snapshot = {"alerts": []}
    document = {
        "steps": [
            {
                "id": "S1",
                "reqs": ["GEN-002"],
                "repeat": 3,
                "expect": {"within_s": 0, "no_alert": {"code": "FAULT"}},
            },
            {"id": "S2", "expect": {"log": {"kind": "msg.sent", "count": 0}}},
        ]
    }
    results = await runner.run(document)
    assert [item["iteration"] for item in results] == [1, 2, 3, 1]
    assert all(item["passed"] for item in results[:3])
    assert not results[-1]["passed"]
    for path in runner.log_paths:
        path.write_text(json.dumps({"kind": "msg.sent"}) + "\n", encoding="utf-8")
    assert len(runner.log_paths) == 3


@pytest.mark.asyncio
async def test_GEN_002_duplicate_steps_and_invalid_repeat_are_rejected(tmp_path):
    cfg = load_settings().model_copy(
        update={
            "logging": load_settings().logging.model_copy(update={"dir": str(tmp_path)})
        }
    )
    runner = Runner(cfg, ManualClock(FAKE_START), "run")
    with pytest.raises(ValueError, match="Duplicate step"):
        await runner.run({"steps": [{"id": "S1"}, {"id": "S1"}]})
    with pytest.raises(ValueError, match="Invalid repeat"):
        await runner.run({"steps": [{"id": "S1", "repeat": 0}]})


@pytest.mark.asyncio
async def test_OI_013_full_mission_with_fault_records_envelopes(tmp_path):
    from pathlib import Path

    import yaml

    from aegis.ground.mission_log import MissionLog
    from aegis.run_all import build_system
    from aegis.testing.scenario_runner import read_logs

    cfg = load_settings().model_copy(
        update={
            "logging": load_settings().logging.model_copy(update={"dir": str(tmp_path)})
        }
    )
    clock = ManualClock(FAKE_START)
    system = build_system(cfg, clock, "mission-fault", MissionLog)
    document = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "scenarios/iron_hawk.yaml").read_text()
    )
    await system.start()
    try:
        runner = Runner(cfg, clock, "mission-fault", system=system)
        results = await runner.run(document)
        assert all(item["passed"] for item in results), [
            item for item in results if not item["passed"]
        ]
        records = read_logs(runner.log_paths)
        sent = [record["env"] for record in records if record["kind"] == "msg.sent"]
        mission = next(env for env in sent if env["type"] == "cmd.assign_mission")
        fault = next(
            env
            for env in sent
            if env["type"] == "fault.raised" and env["body"]["code"] == "PAYLOAD_SHIFT"
        )
        assert mission["mission_id"] and mission["payload_id"]
        assert fault["mission_id"] == mission["mission_id"]
        assert fault["payload_id"] == mission["payload_id"]
        assert all(
            key in fault for key in ("msg_id", "type", "src", "dst", "sent_at", "body")
        )
    finally:
        await system.stop()
