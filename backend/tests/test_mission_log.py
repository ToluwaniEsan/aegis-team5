import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import BaseModel

from aegis.ground.mission_log import MissionLog


class ManualClock:
    def __init__(self, start):
        self.current = start

    def now(self):
        return self.current

    def advance(self, seconds):
        self.current += timedelta(seconds=seconds)


class Envelope(BaseModel):
    v: int
    msg_id: UUID
    type: str
    iface: str
    src: str
    dst: list[str]
    sent_at: str
    priority: int
    mission_id: str
    payload_id: str
    corr_id: str | None
    buffered: bool
    body: dict


@pytest.fixture
def clock():
    return ManualClock(datetime(2026, 11, 19, 9, 4, 5, 123456, tzinfo=timezone.utc))


@pytest.fixture
def cfg(tmp_path):
    return SimpleNamespace(logging=SimpleNamespace(dir=tmp_path))


def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_OI_013_records_are_immediately_visible_and_append(clock, cfg):
    log = MissionLog("ground", "run1", clock, cfg)
    path = cfg.logging.dir / "run-run1-ground.jsonl"
    log.record("state.change", state="EMPTY")
    assert read_records(path)[0]["state"] == "EMPTY"
    MissionLog("ground", "run1", clock, cfg).record("alert.raised", code="FAULT")
    assert [record["kind"] for record in read_records(path)] == [
        "state.change",
        "alert.raised",
    ]


def test_GEN_002_clock_timestamps_are_utc_with_milliseconds(clock, cfg):
    log = MissionLog("ground", "run1", clock, cfg)
    log.record("first")
    clock.advance(1.5)
    log.record("second")
    assert [record["t"] for record in read_records(log.path)] == [
        "2026-11-19T09:04:05.123Z",
        "2026-11-19T09:04:06.623Z",
    ]
    clock.current = datetime(2026, 11, 19, 10, tzinfo=timezone(timedelta(hours=1)))
    log.record("offset")
    assert read_records(log.path)[-1]["t"] == "2026-11-19T09:00:00.000Z"


def test_AEG_510_full_envelope_and_ids_are_preserved(clock, cfg):
    env = Envelope(
        v=1,
        msg_id=UUID("6f1c2a9e-1d3b-4c55-9a51-2f2a0f3b7c11"),
        type="cmd.release",
        iface="I2",
        src="ground.command_manager",
        dst=["vehicle.payload_controller"],
        sent_at="2026-11-19T09:04:05.123Z",
        priority=1,
        mission_id="MSN-2026-007",
        payload_id="PAY-2026-007",
        corr_id=None,
        buffered=False,
        body={"nested": {"value": 42}},
    )
    log = MissionLog("ground", "run1", clock, cfg)
    log.record(
        "msg.sent", env=env, payload_id=env.payload_id, mission_id=env.mission_id
    )
    record = read_records(log.path)[0]
    assert record["env"] == env.model_dump(mode="json")
    assert record["payload_id"] == "PAY-2026-007"
    assert record["mission_id"] == "MSN-2026-007"
    assert (record["run"], record["process"], record["kind"]) == (
        "run1",
        "ground",
        "msg.sent",
    )


def test_OI_013_processes_and_runs_have_separate_files(clock, cfg):
    for process, run in [("ground", "one"), ("vehicle", "one"), ("ground", "two")]:
        MissionLog(process, run, clock, cfg).record("event")
    assert {path.name for path in cfg.logging.dir.iterdir()} == {
        "run-one-ground.jsonl",
        "run-one-vehicle.jsonl",
        "run-two-ground.jsonl",
    }


def test_OI_013_relative_directory_uses_repository_root(clock, monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2]
    relative = Path(os.path.relpath(tmp_path / "logs", root))
    cfg = SimpleNamespace(logging=SimpleNamespace(dir=relative))
    monkeypatch.chdir(tmp_path)
    log = MissionLog("ground", "relative", clock, cfg)
    log.record("event")
    assert (
        log.path.resolve() == (root / relative / "run-relative-ground.jsonl").resolve()
    )
    assert log.path.exists()


@pytest.mark.parametrize("field", ["t", "run", "process"])
def test_OI_013_reserved_metadata_is_rejected(clock, cfg, field):
    log = MissionLog("ground", "run1", clock, cfg)
    with pytest.raises(ValueError):
        log.record("event", **{field: "replacement"})
    assert not log.path.exists()


def test_OI_013_invalid_values_do_not_write_partial_records(clock, cfg):
    log = MissionLog("ground", "run1", clock, cfg)
    log.record("valid")
    before = log.path.read_bytes()
    for value, error in [(object(), TypeError), (float("nan"), ValueError)]:
        with pytest.raises(error):
            log.record("invalid", value=value)
        assert log.path.read_bytes() == before
    clock.current = datetime(2026, 1, 1)
    with pytest.raises(ValueError):
        log.record("invalid clock")
    assert log.path.read_bytes() == before


def test_OI_013_file_write_failure_propagates(clock, cfg, monkeypatch):
    log = MissionLog("ground", "run1", clock, cfg)

    def fail_open(*args, **kwargs):
        raise OSError("disk failure")

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(OSError, match="disk failure"):
        log.record("event")
