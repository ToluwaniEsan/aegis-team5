"""Append-only mission records shared by the ground and vehicle processes."""

from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from aegis.common.clock import Clock
    from aegis.common.config import Settings


def _serialize(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class MissionLog:
    def __init__(self, process: str, run_id: str, clock: Clock, cfg: Settings):
        self.process = process
        self.run_id = run_id
        self.clock = clock
        directory = Path(cfg.logging.dir)
        if not directory.is_absolute():
            directory = Path(__file__).resolve().parents[3] / directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"run-{run_id}-{process}.jsonl"

    def record(self, kind: str, **fields: object) -> None:
        reserved = {"t", "run", "process", "kind"} & fields.keys()
        if reserved:
            raise ValueError(f"Reserved record fields: {', '.join(sorted(reserved))}")
        now = self.clock.now()
        if now.utcoffset() is None:
            raise ValueError("Clock must return a timezone-aware datetime")
        timestamp = now.astimezone(timezone.utc).isoformat(timespec="milliseconds")
        record = {
            "t": timestamp.replace("+00:00", "Z"),
            "run": self.run_id,
            "process": self.process,
            "kind": kind,
            **fields,
        }
        line = json.dumps(record, default=_serialize, allow_nan=False)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(line + "\n")
            output.flush()
