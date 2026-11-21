"""Run scenario steps against the real ground interfaces and record evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

from aegis.common.clock import ManualClock, RealClock
from aegis.common.config import load_settings
from aegis.common.ui_models import UiCommand
from aegis.ground.mission_log import MissionLog
from aegis.run_all import FAST_STEP_S, build_system

MISSING = object()


def lookup(value, path):
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part, MISSING)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return MISSING
    return value


def matches(value, expected):
    if value is MISSING:
        return False
    if not isinstance(expected, dict):
        if isinstance(value, bool) != isinstance(expected, bool):
            return False
        return value == expected
    for op, operand in expected.items():
        try:
            ok = {
                "lt": lambda: value < operand,
                "gt": lambda: value > operand,
                "in": lambda: value in operand,
                "not": lambda: value != operand,
                "contains": lambda: operand in value,
                "len": lambda: len(value) == operand,
            }[op]()
        except (KeyError, TypeError):
            return False
        if not ok:
            return False
    return True


def logs_for(cfg, run_id):
    return [
        cfg.resolve(cfg.logging.dir) / f"run-{run_id}-{process}.jsonl"
        for process in ("ground", "vehicle", "link")
    ]


def read_logs(paths):
    records = []
    for path in paths:
        if path.exists():
            records.extend(
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    return records


def check(expect, snapshot, result, records):
    if set(expect) - {"within_s", "snapshot", "result", "alert", "no_alert", "log"}:
        return False
    for path, value in expect.get("snapshot", {}).items():
        if not matches(lookup(snapshot, path), value):
            return False
    for path, value in expect.get("result", {}).items():
        if not matches(lookup(result, path), value):
            return False
    for key in ("alert", "no_alert"):
        if key in expect:
            if "alerts" not in snapshot:
                return False
            present = any(
                all(
                    matches(lookup(alert, name), value)
                    for name, value in expect[key].items()
                )
                for alert in snapshot.get("alerts", [])
            )
            if present != (key == "alert"):
                return False
    if "log" in expect:
        query = expect["log"]
        count = sum(
            all(
                matches(lookup(record, key), value)
                for key, value in query.items()
                if key not in {"count", "min_count"}
            )
            for record in records
        )
        if "count" in query and count != query["count"]:
            return False
        if "min_count" in query and count < query["min_count"]:
            return False
    return True


class Runner:
    def __init__(self, cfg, clock, run_id, system=None, socket=None):
        self.cfg, self.clock, self.run_id = cfg, clock, run_id
        self.system, self.socket = system, socket
        self.snapshot = {}
        self.result = {}
        self.log_paths = logs_for(cfg, run_id)
        self._pending = {}
        self._reader = None

    async def start_live(self):
        self._reader = asyncio.create_task(self._read_socket())

    async def _read_socket(self):
        async for line in self.socket:
            message = json.loads(line)
            if message.get("kind") == "snapshot":
                self.snapshot = message
            elif message.get("kind") == "command_result":
                future = self._pending.get(message.get("client_req_id"))
                if future and not future.done():
                    future.set_result(message)

    async def tick(self, seconds):
        if isinstance(self.clock, ManualClock):
            remaining = seconds
            while remaining > 1e-9:
                step = min(FAST_STEP_S, remaining)
                self.clock.advance(step)
                remaining -= step
                for _ in range(10):
                    await asyncio.sleep(0)
        else:
            await self.clock.sleep(seconds)

    def current(self):
        if self.system:
            return self.system.ground.snapshot_builder.build().model_dump(mode="json")
        return self.snapshot

    async def send_ui(self, specification):
        args = dict(specification.get("args", {}))
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$alert."):
                code = value.removeprefix("$alert.")
                found = next(
                    (
                        alert
                        for alert in self.current().get("alerts", [])
                        if alert["code"] == code
                    ),
                    None,
                )
                if not found:
                    raise ValueError(f"No alert for {code}")
                args[key] = found["alert_id"]
        request = UiCommand(
            kind="command",
            client_req_id=str(uuid.uuid4()),
            command=specification["command"],
            args=args,
            confirmed=specification["confirmed"],
        )
        if self.system:
            self.result = (
                await self.system.ground.command_manager.handle(request)
            ).model_dump(mode="json")
        else:
            future = asyncio.get_running_loop().create_future()
            self._pending[request.client_req_id] = future
            try:
                await self.socket.send(request.model_dump_json())
                self.result = await asyncio.wait_for(
                    future, timeout=self.cfg.timing.command_timeout_s
                )
            finally:
                self._pending.pop(request.client_req_id, None)

    async def inject(self, specification):
        if self.system:
            await self.system.ground.fault_injector.inject(**specification)
            return
        url = f"http://{self.cfg.network.link_host}:{self.cfg.network.ui_port}/api/test/inject"

        def post():
            request = Request(
                url,
                data=json.dumps(specification).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(
                    request, timeout=self.cfg.timing.command_timeout_s
                ) as response:
                    return response.read()
            except HTTPError as exc:
                raise ValueError(exc.read().decode()) from exc

        await asyncio.to_thread(post)

    async def run_step(self, step, iteration):
        started = self.clock.now()
        item = {
            "id": step["id"],
            "iteration": iteration,
            "title": step.get("title", ""),
            "requirements": step.get("reqs", []),
            "passed": False,
            "measured_s": None,
            "logs": [str(path) for path in self.log_paths],
        }
        try:
            if "ui" in step:
                await self.send_ui(step["ui"])
            if "inject" in step:
                await self.inject(step["inject"])
            if "wait_s" in step:
                await self.tick(float(step["wait_s"]))
            expectation = step.get("expect", {})
            deadline = self.clock.now().timestamp() + float(
                expectation.get("within_s", 0)
            )
            while True:
                snapshot = self.current()
                logs_available = "log" not in expectation or all(
                    path.exists() for path in self.log_paths
                )
                if logs_available and check(
                    expectation, snapshot, self.result, read_logs(self.log_paths)
                ):
                    item["passed"] = True
                    break
                remaining = deadline - self.clock.now().timestamp()
                if remaining <= 1e-9:
                    item["error"] = "Expectation was not met"
                    break
                await self.tick(min(FAST_STEP_S, remaining))
        except Exception as exc:  # report failed steps and continue gathering evidence
            item["error"] = f"{type(exc).__name__}: {exc}"
        item["measured_s"] = (self.clock.now() - started).total_seconds()
        return item

    async def run(self, document):
        results = []
        seen = set()
        for step in document["steps"]:
            if step["id"] in seen:
                raise ValueError(f"Duplicate step id: {step['id']}")
            seen.add(step["id"])
            repeat = step.get("repeat", 1)
            if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
                raise ValueError(f"Invalid repeat count for {step['id']}")
            for iteration in range(1, repeat + 1):
                results.append(await self.run_step(step, iteration))
        return results


async def main_async(args):
    cfg = load_settings()
    document = yaml.safe_load(Path(args.scenario).read_text(encoding="utf-8"))
    clock = ManualClock(RealClock().now()) if args.fast else RealClock()
    run_id = args.run_id or (
        clock.now().strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    if args.live and not args.run_id:
        raise ValueError("--live requires --run-id for the running system's log files")
    if args.fast:
        system = build_system(cfg, clock, run_id, MissionLog)
        await system.start()
        try:
            results = await Runner(cfg, clock, run_id, system=system).run(document)
        finally:
            await system.stop()
    else:
        from websockets import connect

        uri = f"ws://{cfg.network.link_host}:{cfg.network.ui_port}/ws"
        async with connect(uri) as socket:
            runner = Runner(cfg, clock, run_id, socket=socket)
            await runner.start_live()
            try:
                results = await runner.run(document)
            finally:
                runner._reader.cancel()
                await asyncio.gather(runner._reader, return_exceptions=True)
    report = {
        "name": document["name"],
        "run_id": run_id,
        "mode": "fast" if args.fast else "live",
        "passed": all(item["passed"] for item in results),
        "steps": results,
    }
    directory = Path("reports")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"scenario-{document['name']}-{run_id}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in results:
        print(
            f"{item['id']} [{item['iteration']}]: {'PASS' if item['passed'] else 'FAIL'} ({item['measured_s']:.1f}s){' ' + item.get('error', '') if not item['passed'] else ''}"
        )
    print(f"Report: {path}")
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fast", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--run-id")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
