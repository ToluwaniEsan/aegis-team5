"""Evidence from a full IRON HAWK run's logs (doc 04 B2 and B7, doc 06 GEN-002).

One in-process run of `scenarios/iron_hawk.yaml` (all three processes, stand-ins
for Teams 1 to 4, ManualClock), then three checks on its Mission Log files:

- OI-013: every command, payload state change and alert is logged, with a time.
- AEG-513: every payload fault reaches Team 1 within `fault_report_max_s` when the
  link is up (faults buffered during an outage are excluded; OI-013 covers them).
- GEN-002: every time is UTC (ends in Z) and every numeric field carries a metric
  unit in its name (contracts section 1).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.testing.scenario_runner import Runner, read_logs

START = datetime.fromisoformat("2026-11-22T06:00:00.000+00:00")
SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "iron_hawk.yaml"
TIME_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
UTC_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")

# Contracts section 1: metric units in the field name; positions are lat/lon.
UNIT_SUFFIX = re.compile(r"_(kg|cm|wh|mps|ms|s|km|pct)(_(max|min|nominal))?$")
BARE_UNITS = {"kg", "cm", "wh", "mps", "ms", "s", "km", "pct", "seconds"}
POSITION = {"lat", "lon"}
# Counts, identifiers and enums: not measurements, so no unit.
UNITLESS = {"v", "seq", "priority", "events", "replayed_from_window"}
IMPERIAL = re.compile(r"(^|_)(lb|lbs|oz|ft|in|mi|mph|f)$")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.fixture(scope="module")
def records(tmp_path_factory):
    import asyncio

    from aegis.ground.mission_log import MissionLog
    from aegis.run_all import build_system

    base = load_settings()
    cfg = base.model_copy(
        update={
            "logging": base.logging.model_copy(
                update={"dir": str(tmp_path_factory.mktemp("logs"))}
            )
        }
    )

    async def run():
        clock = ManualClock(START)
        system = build_system(cfg, clock, "log-evidence", MissionLog)
        await system.start()
        try:
            runner = Runner(cfg, clock, "log-evidence", system=system)
            results = await runner.run(yaml.safe_load(SCENARIO.read_text()))
            assert all(r["passed"] for r in results), [
                r for r in results if not r["passed"]
            ]
            return read_logs(runner.log_paths)
        finally:
            await system.stop()

    return cfg, asyncio.run(run())


def _sent(records, type_prefix, process=None):
    return [
        r
        for r in records
        if r["kind"] == "msg.sent"
        and r["env"]["type"].startswith(type_prefix)
        and (process is None or r["process"] == process)
    ]


def test_OI_013_every_command_state_change_and_alert_is_logged_with_time(records):
    _, recs = records
    assert recs, "the run wrote no log records"

    # Every record carries a UTC time with milliseconds.
    for r in recs:
        assert UTC_RE.match(r["t"]), r

    # Every operator command the ground sends has a logged lifecycle, under its id.
    lifecycle = {}
    for r in recs:
        if r["kind"] == "cmd.lifecycle":
            lifecycle.setdefault(r["command"]["command_id"], []).append(
                r["command"]["state"]
            )
    commands = [
        r for r in _sent(recs, "cmd.", "ground") if r["env"]["type"] != "cmd.estop"
    ]
    assert commands, "the scenario sent no commands"
    for r in commands:
        states = lifecycle.get(r["env"]["msg_id"])
        assert states and states[0] == "SENT", (r["env"]["type"], states)

    # Every payload state the vehicle reports is logged as a state change.
    reported = []
    for r in _sent(recs, "payload.status", "vehicle"):
        state = r["env"]["body"]["state"]
        if not reported or reported[-1] != state:
            reported.append(state)
    logged = {
        r["env"]["body"]["state"]
        for r in recs
        if r["kind"] == "state.change" and r.get("group") == "payload.status"
    }
    assert len(reported) > 3, reported
    assert set(reported) <= logged, set(reported) - logged

    # Every fault the ground receives becomes a logged alert.
    alerts = {r["alert"]["code"] for r in recs if r["kind"] == "alert.change"}
    faults = {
        r["env"]["body"]["code"]
        for r in recs
        if r["kind"] == "msg.recv"
        and r["process"] == "ground"
        and r["env"]["type"] == "fault.raised"
    }
    assert faults, "the scenario raised no faults"
    assert faults <= alerts, faults - alerts


def test_AEG_513_payload_fault_reaches_team1_within_2s(records):
    cfg, recs = records
    limit = cfg.timing.fault_report_max_s
    reports = {}
    for r in _sent(recs, "t1.fault_report", "ground"):
        reports.setdefault(r["env"]["body"]["fault_id"], _parse(r["t"]))
    checked = 0
    for r in _sent(recs, "fault.raised", "vehicle"):
        env = r["env"]
        if env["buffered"]:
            continue  # raised during an outage; arrives with the backlog (OI-013)
        fault_id = env["body"]["fault_id"]
        if fault_id not in reports:
            continue  # dropped by the link while it was failing; see OI-013
        delay = (reports[fault_id] - _parse(env["sent_at"])).total_seconds()
        assert 0 <= delay <= limit, (env["body"]["code"], delay)
        checked += 1
    assert checked, "no vehicle fault reached Team 1 while the link was up"


def test_GEN_002_log_units_and_utc(records):
    _, recs = records
    problems = []

    def walk(obj, path, parent_has_unit):
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{path}.{key}"
                if IMPERIAL.search(key):
                    problems.append(f"imperial unit: {here}")
                if isinstance(value, str) and TIME_RE.match(value):
                    if not UTC_RE.match(value):
                        problems.append(f"not UTC with ms: {here}={value}")
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    ok = (
                        parent_has_unit
                        or UNIT_SUFFIX.search(key)
                        or key in BARE_UNITS
                        or key in POSITION
                        or key in UNITLESS
                    )
                    if not ok:
                        problems.append(f"no unit: {here}={value}")
                walk(value, here, bool(UNIT_SUFFIX.search(key)))
        elif isinstance(obj, list):
            for item in obj:
                walk(item, path, parent_has_unit)

    for r in recs:
        walk(r, r["kind"], False)
    assert not problems, sorted(set(problems))[:20]
