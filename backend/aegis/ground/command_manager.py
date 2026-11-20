"""Ground command lifecycle, mission queue and durable identifier allocation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError

from aegis.common.envelope import make, parse
from aegis.common.models import AssignMission, Dims, Envelope, format_timestamp
from aegis.common.ui_models import CommandResult, CommandView, Mission, NextIds, Place

if TYPE_CHECKING:
    from aegis.bus.local_bus import LocalBus
    from aegis.common.clock import Clock
    from aegis.common.config import Settings
    from aegis.ground.mission_log import MissionLog
    from aegis.ground.status_monitor import StatusMonitor


CONFIRM = frozenset(
    {
        "start_queued_mission",
        "abort",
        "return_to_origin",
        "change_destination",
        "release",
    }
)


class CommandManager:
    """Own commands and missions; injected hooks connect later ground components.

    With no permission hook, the handoff's temporary allow-all stub is used.
    Failure alerts are retained until an Alert Manager hook is installed.
    """

    def __init__(
        self,
        bus: LocalBus,
        clock: Clock,
        cfg: Settings,
        log: MissionLog,
        status: StatusMonitor,
        *,
        permission_for: Callable | None = None,
        on_failure: Callable[[CommandView], Awaitable[None]] | None = None,
        ack_ground_alert: Callable[[str], Awaitable[bool]] | None = None,
    ) -> None:
        self.bus, self.clock, self.cfg, self.log, self.status = (
            bus,
            clock,
            cfg,
            log,
            status,
        )
        self.permission_for = permission_for
        self.on_failure = on_failure
        self.ack_ground_alert = ack_ground_alert
        self.active: Mission | None = None
        self.queue: list[Mission] = []
        self.missions: dict[str, Mission] = {}
        self.commands: dict[str, CommandView] = {}
        self._maps: dict[UUID, str] = {}
        self._recipients: dict[str, set[tuple[UUID, str]]] = {}
        self._completed: dict[str, set[tuple[UUID, str]]] = {}
        self._effects: dict[str, tuple[str, dict]] = {}
        self._seen_acks: set[UUID] = set()
        self._timers: dict[str, asyncio.Task] = {}
        self.failed_alerts: list[CommandView] = []
        self._ids_path = cfg.resolve(cfg.logging.dir) / "ids.json"
        self._ids_path.parent.mkdir(parents=True, exist_ok=True)
        self._counters = (
            json.loads(self._ids_path.read_text()) if self._ids_path.exists() else {}
        )
        status.destination_for = self.destination_for
        status.on_ack = self.handle_ack
        status.on_mission_event = self._mission_event
        bus.subscribe(
            "ground.status_monitor",
            self._mission_event,
            {"payload.status", "payload.delivered"},
        )

    def next_ids(self) -> NextIds:
        year = str(self.clock.now().year)
        number = self._counters.get(year, 0) + 1
        return NextIds(
            mission_id=f"{self.cfg.payload.mission_id_prefix}-{year}-{number:03d}",
            payload_id=f"{self.cfg.payload.payload_id_prefix}-{year}-{number:03d}",
        )

    def _allocate_ids(self) -> NextIds:
        ids = self.next_ids()
        year = str(self.clock.now().year)
        counters = {**self._counters, year: self._counters.get(year, 0) + 1}
        temporary = self._ids_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(counters) + "\n", encoding="utf-8")
        temporary.replace(self._ids_path)
        self._counters = counters
        return ids

    def destination_for(self, mission_id: str) -> Place | None:
        mission = self.missions.get(mission_id)
        return None if mission is None else mission.destination

    def _place(self, value: object) -> Place:
        for place in self.cfg.places:
            if place.id == value:
                return Place(**place.model_dump())
        raise ValueError(f"Unknown place: {value}")

    def _validate_load(self, args: dict) -> tuple[float, Dims]:
        mass = args.get("declared_mass_kg")
        if isinstance(mass, bool) or not isinstance(mass, (float, int)):
            raise ValueError("Payload mass must be a number")
        if not self.cfg.payload.mass_min_kg <= mass <= self.cfg.payload.mass_max_kg:
            raise ValueError(
                f"Payload {mass:g} kg is outside {self.cfg.payload.mass_min_kg:g}–{self.cfg.payload.mass_max_kg:g} kg"
            )
        dims = Dims.model_validate(args.get("dims_cm"))
        for key in ("length", "width", "height"):
            value, limit = (
                getattr(dims, key),
                getattr(self.cfg.payload.dims_max_cm, key),
            )
            if value > limit:
                raise ValueError(f"Payload {key} {value:g} cm exceeds {limit:g} cm")
        return mass, dims

    async def handle(self, ui_command) -> CommandResult:
        request = ui_command

        def result(
            accepted: bool, command_id: str | None = None, reason: str | None = None
        ) -> CommandResult:
            return CommandResult(
                kind="command_result",
                client_req_id=request.client_req_id,
                accepted=accepted,
                command_id=command_id,
                reason=reason,
            )

        name, args = request.command, request.args
        if self.permission_for is not None and name != "estop":
            permission = self.permission_for(name)
            if not permission.allowed:
                return result(
                    False, reason=permission.reason or "Command not permitted"
                )
            if permission.needs_confirmation and not request.confirmed:
                return result(False, reason="Confirmation required")
        if name in CONFIRM and not request.confirmed:
            return result(False, reason="Confirmation required")
        try:
            if name == "assign_mission":
                mass, dims = self._validate_load(args)
                origin, destination = (
                    self._place(args.get("origin_id")),
                    self._place(args.get("destination_id")),
                )
                # Validate the complete wire body before consuming an identifier.
                draft = {
                    "mission_id": "pending",
                    "payload_id": "pending",
                    "origin": origin.model_dump(),
                    "destination": destination.model_dump(),
                    "priority": args.get("priority"),
                    "declared_mass_kg": mass,
                    "dims_cm": dims.model_dump(),
                    "prerelease_authorized": args.get("prerelease_authorized"),
                }
                AssignMission.model_validate(draft)
                ids = self._allocate_ids()
                mission = Mission(
                    mission_id=ids.mission_id,
                    payload_id=ids.payload_id,
                    status="QUEUED" if self.active else "ASSIGNED",
                    origin=origin,
                    destination=destination,
                    priority=draft["priority"],
                    declared_mass_kg=mass,
                    dims_cm=dims.model_dump(),
                    prerelease_authorized=draft["prerelease_authorized"],
                    created_at=format_timestamp(self.clock.now()),
                )
                self.missions[mission.mission_id] = mission
                if self.active is not None:
                    self.queue.append(mission)
                    self.log.record(
                        "mission.change", mission=mission.model_dump(mode="json")
                    )
                    return result(True)
                self.active = mission
                await self._report_mission(mission)
                return result(True, await self._send_mission(mission, name))
            if name in {"start_queued_mission", "remove_queued_mission"}:
                mission_id = args.get("mission_id")
                queued = next(
                    (m for m in self.queue if m.mission_id == mission_id), None
                )
                if queued is None:
                    return result(False, reason="Mission is not in the queue")
                if name == "remove_queued_mission":
                    self.queue.remove(queued)
                    self.missions.pop(queued.mission_id, None)
                    self.log.record(
                        "mission.change", mission_id=queued.mission_id, status="REMOVED"
                    )
                    return result(True)
                if self.active is not None:
                    return result(False, reason="A mission is active")
                if queued is not self.queue[0]:
                    return result(False, reason="Start the first queued mission")
                self.queue.pop(0)
                self.active = queued.model_copy(update={"status": "ASSIGNED"})
                self.missions[queued.mission_id] = self.active
                await self._report_mission(self.active)
                return result(True, await self._send_mission(self.active, name))
            if name == "ack_fault" and self.ack_ground_alert is not None:
                if await self.ack_ground_alert(str(args.get("alert_id", ""))):
                    return result(True)
            if name == "update_payload":
                mass, dims = self._validate_load(args)
                body = {"declared_mass_kg": mass, "dims_cm": dims.model_dump()}
            elif name == "change_destination":
                body = {
                    "destination": self._place(args.get("destination_id")).model_dump()
                }
            elif name == "ack_fault":
                body = {"fault_id": args.get("alert_id")}
            elif name == "estop":
                body = {"reason": "Operator emergency stop", "source": "OPERATOR"}
            else:
                body = {}
            env = make(
                f"cmd.{name}",
                "ground.command_manager",
                body,
                self.clock,
                mission_id=self.active.mission_id if self.active else None,
                payload_id=self.active.payload_id if self.active else None,
            )
            effect = None
            if self.active and name in {"change_destination", "update_payload"}:
                effect = (self.active.mission_id, body)
            return result(True, await self._send(name, [env], effect))
        except (ValueError, ValidationError, TypeError) as exc:
            return result(False, reason=str(exc))

    async def _send_mission(self, mission: Mission, command: str) -> str:
        body = mission.model_dump(
            include={
                "mission_id",
                "payload_id",
                "origin",
                "destination",
                "priority",
                "declared_mass_kg",
                "dims_cm",
                "prerelease_authorized",
            }
        )
        first = make(
            "cmd.assign_mission",
            "ground.command_manager",
            body,
            self.clock,
            mission_id=mission.mission_id,
            payload_id=mission.payload_id,
        )
        nav = make(
            "nav.assign",
            "ground.command_manager",
            {
                key: body[key]
                for key in ("mission_id", "origin", "destination", "priority")
            },
            self.clock,
            mission_id=mission.mission_id,
            payload_id=mission.payload_id,
        )
        return await self._send(command, [first, nav])

    async def _send(
        self,
        name: str,
        envelopes: list[Envelope],
        effect: tuple[str, dict] | None = None,
    ) -> str:
        command_id = str(envelopes[0].msg_id)
        timestamp = format_timestamp(self.clock.now())
        view = CommandView(
            command_id=command_id,
            command=name,
            label=name.replace("_", " ").capitalize(),
            state="SENT",
            reason=None,
            sent_at=timestamp,
            updated_at=timestamp,
        )
        self.commands[command_id] = view
        self._recipients[command_id] = {
            (env.msg_id, dst) for env in envelopes for dst in env.dst
        }
        self._completed[command_id] = set()
        if effect is not None:
            self._effects[command_id] = effect
        for env in envelopes:
            self._maps[env.msg_id] = command_id
        self._log_command(view)
        self._timers[command_id] = asyncio.create_task(self._timeout(command_id))
        for env in envelopes:
            await self.bus.publish(env)
        return command_id

    def _log_command(self, view: CommandView) -> None:
        self.log.record("cmd.lifecycle", command=view.model_dump(mode="json"))

    async def _transition(
        self, command_id: str, state: str, reason: str | None = None
    ) -> None:
        old = self.commands[command_id]
        if old.state in {"FAILED", "COMPLETED"} or (
            old.state == state and old.reason == reason
        ):
            return
        view = old.model_copy(
            update={
                "state": state,
                "reason": reason,
                "updated_at": format_timestamp(self.clock.now()),
            }
        )
        self.commands[command_id] = view
        self._log_command(view)
        if state == "FAILED":
            self.failed_alerts.append(view)
            if self.on_failure is not None:
                await self.on_failure(view)
        if state in {"FAILED", "COMPLETED"}:
            task = self._timers.pop(command_id, None)
            if task is not None and task is not asyncio.current_task():
                task.cancel()
            if state == "COMPLETED" and old.command == "abort" and self.active:
                await self._set_mission_status("ABORTED")
            effect = self._effects.pop(command_id, None)
            if state == "COMPLETED" and effect:
                mission_id, values = effect
                mission = self.missions.get(mission_id)
                if mission is not None:
                    changes = dict(values)
                    if "destination" in changes:
                        changes["destination"] = Place.model_validate(
                            changes["destination"]
                        )
                    if "dims_cm" in changes:
                        from aegis.common.ui_models import Dims as UiDims

                        changes["dims_cm"] = UiDims.model_validate(changes["dims_cm"])
                    mission = mission.model_copy(update=changes)
                    self.missions[mission_id] = mission
                    if self.active is not None and self.active.mission_id == mission_id:
                        self.active = mission
                    self.log.record(
                        "mission.change", mission=mission.model_dump(mode="json")
                    )

    async def _timeout(self, command_id: str) -> None:
        sent_at = self.commands[command_id].sent_at
        from datetime import datetime

        started = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
        first_deadline = started.timestamp() + self.cfg.timing.command_timeout_s
        await self.clock.sleep(max(0, first_deadline - self.clock.now().timestamp()))
        if self.commands[command_id].state == "SENT":
            await self._transition(
                command_id,
                "FAILED",
                f"No confirmation in {self.cfg.timing.command_timeout_s:g} s. Not resent.",
            )
            return
        deadline = started.timestamp() + self.cfg.timing.command_complete_timeout_s
        await self.clock.sleep(max(0, deadline - self.clock.now().timestamp()))
        if self.commands[command_id].state == "RECEIVED":
            await self._transition(
                command_id,
                "FAILED",
                f"Received but not completed in {self.cfg.timing.command_complete_timeout_s:g} s",
            )

    async def handle_ack(self, incoming: Envelope) -> None:
        try:
            env = parse(incoming.model_dump_json())
        except (ValidationError, ValueError, TypeError) as exc:
            self.log.record("bus.invalid", error=str(exc))
            return
        if env.type != "ack" or env.msg_id in self._seen_acks:
            return
        command_id = self._maps.get(env.corr_id)
        if (
            command_id is None
            or (env.corr_id, env.src) not in self._recipients[command_id]
        ):
            return
        self._seen_acks.add(env.msg_id)
        if env.body.result == "REJECTED":
            await self._transition(command_id, "FAILED", env.body.reason)
        elif env.body.result == "COMPLETED":
            self._completed[command_id].add((env.corr_id, env.src))
            if self._completed[command_id] == self._recipients[command_id]:
                await self._transition(command_id, "COMPLETED")
            else:
                await self._transition(command_id, "RECEIVED")
        else:
            await self._transition(command_id, "RECEIVED")

    async def _report_mission(self, mission: Mission) -> None:
        self.log.record("mission.change", mission=mission.model_dump(mode="json"))
        await self.bus.publish(
            make(
                "t1.mission_report",
                "ground.command_manager",
                {
                    "mission_id": mission.mission_id,
                    "payload_id": mission.payload_id,
                    "status": mission.status,
                },
                self.clock,
                mission_id=mission.mission_id,
                payload_id=mission.payload_id,
            )
        )

    async def _set_mission_status(self, state: str) -> None:
        if self.active is None or self.active.status == state:
            return
        mission = self.active.model_copy(update={"status": state})
        self.missions[mission.mission_id] = mission
        self.active = None if state in {"COMPLETE", "ABORTED"} else mission
        await self._report_mission(mission)

    async def _mission_event(self, incoming: Envelope) -> None:
        try:
            env = parse(incoming.model_dump_json())
        except (ValidationError, ValueError, TypeError):
            return
        if self.active is None:
            return
        mission_id = env.body.mission_id
        if mission_id != self.active.mission_id:
            return
        if env.type == "payload.delivered" or env.body.state == "DELIVERED":
            await self._set_mission_status("COMPLETE")
        elif env.body.state in {"TRAVELLING", "AT_DESTINATION", "RELEASED"}:
            await self._set_mission_status("ACTIVE")

    def close(self) -> None:
        for task in self._timers.values():
            task.cancel()
        self._timers.clear()
