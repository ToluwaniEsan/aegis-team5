"""Capture checked-in screen fixtures from actual fast scenario snapshots."""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.ground.mission_log import MissionLog
from aegis.run_all import build_system
from aegis.testing.scenario_runner import Runner

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = {
    "iron_hawk": {
        "S01": "idle",
        "S02": "assigned",
        "S04": "secured",
        "S07": "travelling",
        "S09": "degraded",
        "S13": "link_lost",
        "S15": "route_blocked",
        "S17": "queued",
        "S18": "fault_shift",
        "S21": "at_destination",
        "S23": "delivered",
    },
    "estop": {"E01": "estop_held"},
}


async def capture(name, directory):
    document = yaml.safe_load((ROOT / "backend/scenarios" / f"{name}.yaml").read_text())
    base = load_settings()
    cfg = base.model_copy(
        update={"logging": base.logging.model_copy(update={"dir": str(directory)})}
    )
    clock = ManualClock(datetime(2026, 11, 19, 15, 4, 5, tzinfo=UTC))
    system = build_system(cfg, clock, f"fixture-{name}", MissionLog)
    await system.start()
    captured = {}
    try:
        runner = Runner(cfg, clock, f"fixture-{name}", system=system)
        for step in document["steps"]:
            result = await runner.run_step(step, 1)
            if not result["passed"]:
                raise RuntimeError(f"{name} {step['id']} failed: {result.get('error')}")
            if step["id"] in CAPTURES[name]:
                captured[CAPTURES[name][step["id"]]] = runner.current()
    finally:
        await system.stop()
    return captured


async def main():
    with tempfile.TemporaryDirectory(prefix="aegis-fixtures-") as tmp:
        fixtures = {}
        for scenario in CAPTURES:
            fixtures.update(await capture(scenario, Path(tmp)))
    expected = {name for captures in CAPTURES.values() for name in captures.values()}
    if fixtures.keys() != expected:
        raise RuntimeError(f"Missing captures: {expected - fixtures.keys()}")
    destination = ROOT / "frontend/src/mock/fixtures"
    for name, snapshot in fixtures.items():
        (destination / f"{name}.json").write_text(
            json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
        )
        print(name)


if __name__ == "__main__":
    asyncio.run(main())
