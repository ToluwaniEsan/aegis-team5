"""Event Buffer (task A7): holds ground-bound messages while the link is LOST.

An outbound filter on the vehicle bus. It follows `int.link_state`:
- **While LOST** it holds every message to the ground, in memory and in
  `event_buffer.file` on disk, so a vehicle restart does not lose them.
  Status groups (`payload.status`, `nav.state`, `power.status`) keep only the
  newest one. Everything else (faults, acks, deliveries) is kept in order.
- **The first seconds of an outage:** the link is declared LOST only after
  `link.lost_after_s`, and the link drops what is sent meanwhile. So a rolling
  copy of the last `lost_after_s` of non-status messages goes to the front of
  the backlog. The ground de-duplicates by `msg_id`.
- **Cap:** at `max_events`, drop the oldest status first, then the oldest
  CAUTION faults, then the oldest message. Every drop is logged.
- **On RESTORED** it sends the backlog as `backlog.batch` messages of up to
  `batch_size` events, in order, each with `buffered = true` and its original
  `sent_at`, then resumes live sending.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from aegis.common.clock import Clock
from aegis.common.config import Settings
from aegis.common.envelope import make, parse
from aegis.common.models import FAULT_CATALOG, BacklogBatch, Envelope

if TYPE_CHECKING:
    from aegis.ground.mission_log import MissionLog

ENDPOINT = "vehicle.event_buffer"
STATUS_TYPES = frozenset({"payload.status", "nav.state", "power.status"})
NEVER_BUFFERED = frozenset({"hb.ground", "backlog.batch"})


def _is_caution_fault(env: Envelope) -> bool:
    if env.type not in ("fault.raised", "fault.cleared"):
        return False
    return FAULT_CATALOG[env.body.code].severity == "CAUTION"


class EventBuffer:
    def __init__(self, bus, clock: Clock, cfg: Settings, log: MissionLog):
        self.bus = bus
        self.clock = clock
        self.cfg = cfg
        self.log = log
        self.path: Path = cfg.resolve(cfg.event_buffer.file)
        self.max_events = cfg.event_buffer.max_events
        self.batch_size = cfg.event_buffer.batch_size
        # One heartbeat period of margin: the outage can start just before the
        # last heartbeat arrives.
        self.window = timedelta(
            seconds=cfg.link.lost_after_s + 1.0 / cfg.timing.heartbeat_rate_hz
        )
        self.link_lost = False
        self.backlog: list[Envelope] = []
        self._recent: deque[Envelope] = deque()  # non-status, last lost_after_s

    # -- lifecycle -------------------------------------------------------------

    async def start(self) -> None:
        self._load()
        if self.backlog:
            # Saved before a restart: hold until the link is known to be up.
            self.link_lost = True
            self.log.record("buffer.restored_from_disk", events=len(self.backlog))
        self.bus.add_outbound_filter(self.filter)
        self.bus.subscribe(ENDPOINT, self._on_link_state, types={"int.link_state"})

    async def stop(self) -> None:
        pass  # everything held is already on disk

    # -- outbound filter -------------------------------------------------------

    async def filter(self, env: Envelope) -> Envelope | None:
        if env.type in NEVER_BUFFERED:
            return env
        if not self.link_lost:
            self._remember(env)
            return env
        self._hold(env)
        return None

    def _remember(self, env: Envelope) -> None:
        if env.type in STATUS_TYPES:
            return
        self._recent.append(env)
        cutoff = self.clock.now() - self.window
        while self._recent and self._recent[0].sent_at < cutoff:
            self._recent.popleft()

    def _hold(self, env: Envelope, persist: bool = True) -> None:
        if env.type in STATUS_TYPES:
            self.backlog = [e for e in self.backlog if e.type != env.type]
        if any(e.msg_id == env.msg_id for e in self.backlog):
            return
        self.backlog.append(env)
        if persist:
            self._append_to_disk(env)
        while len(self.backlog) > self.max_events:
            self._drop_one()

    def _drop_one(self) -> None:
        for test in (
            lambda e: e.type in STATUS_TYPES,
            _is_caution_fault,
            lambda e: True,
        ):
            victim = next((e for e in self.backlog if test(e)), None)
            if victim is not None:
                self.backlog.remove(victim)
                self.log.record(
                    "buffer.drop",
                    msg_id=str(victim.msg_id),
                    type=victim.type,
                    reason="cap",
                )
                return

    # -- link state ------------------------------------------------------------

    async def _on_link_state(self, env: Envelope) -> None:
        if env.body.state == "LOST":
            if self.link_lost:
                return
            self.link_lost = True
            # Messages sent while the link was failing but not yet declared LOST.
            cutoff = self.clock.now() - self.window
            early = [e for e in self._recent if e.sent_at >= cutoff]
            self._recent.clear()
            held, self.backlog = self.backlog, []
            for e in [*early, *held]:
                self._hold(e, persist=False)
            self._rewrite_disk()
            self.log.record("buffer.holding", replayed_from_window=len(early))
        elif self.link_lost:
            await self._flush()

    async def _flush(self) -> None:
        """Send the backlog in order, then resume live sending. Anything held
        while flushing goes out in a later batch."""
        sent = 0
        while self.backlog:
            chunk, self.backlog = (
                self.backlog[: self.batch_size],
                self.backlog[self.batch_size :],
            )
            events = [e.model_copy(update={"buffered": True}) for e in chunk]
            batch = make(
                "backlog.batch", ENDPOINT, BacklogBatch(events=events), self.clock
            )
            await self.bus.publish(batch)
            sent += len(events)
        self.link_lost = False
        self._rewrite_disk()
        self.log.record("buffer.flushed", events=sent)

    # -- disk ----------------------------------------------------------------

    def _append_to_disk(self, env: Envelope) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(env.model_dump_json() + "\n")
            f.flush()

    def _rewrite_disk(self) -> None:
        if not self.backlog:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            "".join(e.model_dump_json() + "\n" for e in self.backlog), encoding="utf-8"
        )
        tmp.replace(self.path)

    def _load(self) -> None:
        if not self.path.is_file():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                self._hold(parse(line), persist=False)
            except (ValidationError, json.JSONDecodeError) as exc:
                self.log.record(
                    "bus.invalid", raw=line, error=str(exc), source=str(self.path)
                )
        self._rewrite_disk()
