"""Run the whole system (task B4).

    python -m aegis.run_all                    # link, vehicle, ground as subprocesses
    python -m aegis.run_all --single-process   # all three sides in one asyncio loop
    python -m aegis.run_all --single-process --fast   # ...on a ManualClock

Multi-process: starts the three processes with one run ID, streams their
output with a `[side]` prefix, and stops all of them on Ctrl+C or when any one
exits.

Single-process: the ground and vehicle buses are joined by the link stand-in
in memory. `build_system` is the piece the scenario runner (B15) reuses.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aegis.common.clock import Clock, ManualClock, RealClock
from aegis.common.config import Settings, load_settings
from aegis.ground.main import Ground
from aegis.standins.link import LinkStandin
from aegis.vehicle.main import Vehicle

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

PROCESSES: dict[str, str] = {
    # start order: the link first, so the other two connect on their first try
    "link": "aegis.standins.link",
    "vehicle": "aegis.vehicle",
    "ground": "aegis.ground",
}

# --fast advances the ManualClock in steps of this size and yields to the
# event loop after each one (doc 04, B15). A simulation step, not a limit.
FAST_STEP_S = 0.1

LogFactory = Callable[[str, str, Clock, Settings], "MissionLog"]


def new_run_id(clock: Clock) -> str:
    return clock.now().strftime("%Y%m%dT%H%M%SZ")


def mission_log_factory() -> LogFactory:
    from aegis.ground.mission_log import MissionLog

    return MissionLog


# -- single process -----------------------------------------------------------


@dataclass
class System:
    cfg: Settings
    clock: Clock
    run_id: str
    link: LinkStandin
    vehicle: Vehicle
    ground: Ground

    async def start(self) -> None:
        await self.link.start()
        await self.vehicle.start()
        await self.ground.start()

    async def stop(self) -> None:
        await self.ground.stop()
        await self.vehicle.stop()
        await self.link.stop()


def build_system(
    cfg: Settings, clock: Clock, run_id: str, make_log: LogFactory
) -> System:
    """The three sides in one loop, joined by the link stand-in in memory."""
    link = LinkStandin(clock, cfg, make_log("link", run_id, clock, cfg))
    vehicle = Vehicle(
        cfg, clock, make_log("vehicle", run_id, clock, cfg), link=link.port("vehicle")
    )
    ground = Ground(
        cfg, clock, make_log("ground", run_id, clock, cfg), link=link.port("ground")
    )
    link.attach("vehicle", vehicle.bus.deliver_from_link)
    link.attach("ground", ground.bus.deliver_from_link)
    return System(cfg, clock, run_id, link, vehicle, ground)


async def run_single_process(fast: bool, run_id: str | None) -> None:
    cfg = load_settings()
    clock: Clock = ManualClock(RealClock().now()) if fast else RealClock()
    run_id = run_id or new_run_id(clock)
    system = build_system(cfg, clock, run_id, mission_log_factory())
    print(f"run {run_id}: single process{' (fast)' if fast else ''}", flush=True)
    await system.start()
    try:
        if isinstance(clock, ManualClock):
            while True:
                clock.advance(FAST_STEP_S)
                await asyncio.sleep(0)  # yield so woken tasks run; not a timed wait
        else:
            await asyncio.Event().wait()
    finally:
        await system.stop()


# -- multi process ------------------------------------------------------------


def command(side: str, run_id: str) -> list[str]:
    return [sys.executable, "-m", PROCESSES[side], "--run-id", run_id]


async def _pump(name: str, stream: asyncio.StreamReader) -> None:
    prefix = f"[{name}] "
    while line := await stream.readline():
        sys.stdout.write(prefix + line.decode("utf-8", errors="replace"))
        sys.stdout.flush()


async def run_multi_process(run_id: str | None) -> int:
    run_id = run_id or new_run_id(RealClock())
    print(f"run {run_id}: starting {', '.join(PROCESSES)}", flush=True)
    procs: dict[str, asyncio.subprocess.Process] = {}
    pumps: list[asyncio.Task[None]] = []
    for side in PROCESSES:
        proc = await asyncio.create_subprocess_exec(
            *command(side, run_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        procs[side] = proc
        pumps.append(asyncio.create_task(_pump(side, proc.stdout)))

    waits = {asyncio.create_task(p.wait()): side for side, p in procs.items()}
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows
            loop.add_signal_handler(sig, stop.set)
    stopper = asyncio.create_task(stop.wait())

    done, _ = await asyncio.wait([*waits, stopper], return_when=asyncio.FIRST_COMPLETED)
    exit_code = 0
    for task in done:
        if task in waits and not stop.is_set():
            side = waits[task]
            print(
                f"{side} exited with code {task.result()}; stopping the others",
                flush=True,
            )
            exit_code = 1

    for proc in procs.values():
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
    await asyncio.gather(*(p.wait() for p in procs.values()))
    await asyncio.gather(*pumps, return_exceptions=True)
    stopper.cancel()
    print(f"run {run_id}: stopped", flush=True)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ground, link and vehicle")
    parser.add_argument("--single-process", action="store_true")
    parser.add_argument(
        "--fast", action="store_true", help="ManualClock (single-process only)"
    )
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    if args.fast and not args.single_process:
        parser.error("--fast needs --single-process")
    try:
        if args.single_process:
            asyncio.run(run_single_process(args.fast, args.run_id))
            return 0
        return asyncio.run(run_multi_process(args.run_id))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
