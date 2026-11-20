"""B12 HTTP and WebSocket interface for the ground station."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from aegis.common.ui_models import UiCommand

if TYPE_CHECKING:
    from aegis.common.clock import Clock
    from aegis.common.config import Settings
    from aegis.ground.command_manager import CommandManager
    from aegis.ground.snapshot import SnapshotBuilder
    from aegis.testing.fault_injector import FaultInjector


class _Client:
    """One ordered writer; pending adjacent full snapshots may be coalesced."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.pending: deque[tuple[str, dict]] = deque()
        self.ready = asyncio.Event()
        self.sender: asyncio.Task | None = None
        self.reader: asyncio.Task | None = None
        self.handling = False
        self.deferred_snapshot: dict | None = None

    def snapshot(self, data: dict) -> None:
        if self.handling:
            self.deferred_snapshot = data
            return
        if self.pending and self.pending[-1][0] == "snapshot":
            self.pending[-1] = ("snapshot", data)
        else:
            self.pending.append(("snapshot", data))
        self.ready.set()

    def result(self, data: dict) -> None:
        self.pending.append(("result", data))
        self.ready.set()

    def flush_deferred(self) -> None:
        if self.deferred_snapshot is not None:
            snapshot, self.deferred_snapshot = self.deferred_snapshot, None
            self.snapshot(snapshot)

    async def send(self) -> None:
        while True:
            await self.ready.wait()
            self.ready.clear()
            while self.pending:
                _, data = self.pending.popleft()
                await self.ws.send_json(data)


class UiServer:
    def __init__(
        self,
        cfg: Settings,
        clock: Clock,
        builder: SnapshotBuilder,
        commands: CommandManager,
        injector: FaultInjector,
    ):
        self.cfg, self.clock, self.builder = cfg, clock, builder
        self.commands, self.injector = commands, injector
        self.clients: dict[WebSocket, _Client] = {}
        self._broadcast_lock = asyncio.Lock()
        self._periodic: asyncio.Task | None = None
        self._debounced: asyncio.Task | None = None
        self._dirty = False
        commands.on_change = self.changed
        commands.bus.subscribe("ground.status_monitor", self._on_bus_event)
        commands.bus.subscribe("ground.command_manager", self._on_bus_event, {"ack"})

        @asynccontextmanager
        async def lifespan(_app):
            self._periodic = asyncio.create_task(self._periodic_updates())
            try:
                yield
            finally:
                tasks = [task for task in (self._periodic, self._debounced) if task]
                for client in self.clients.values():
                    tasks.extend(
                        task for task in (client.sender, client.reader) if task
                    )
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                self.clients.clear()
                self._periodic = self._debounced = None

        self.app = FastAPI(lifespan=lifespan)
        self.app.add_api_route("/api/health", self.health, methods=["GET"])
        if cfg.test_mode:
            self.app.add_api_route("/api/test/inject", self.inject, methods=["POST"])
        else:
            # Prevent the frontend static mount from turning this into a 405.
            self.app.add_api_route("/api/test/inject", self.not_found, methods=["POST"])
        self.app.add_api_websocket_route("/ws", self.websocket)
        dist = cfg.root / "frontend" / "dist"
        if cfg.test_mode and (dist / "index.html").is_file():
            self.app.add_api_route(
                "/test", lambda: FileResponse(dist / "index.html"), methods=["GET"]
            )
        else:
            self.app.add_api_route("/test", self.not_found, methods=["GET"])
        if dist.is_dir():
            self.app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
        else:
            self.app.add_api_route("/", self.index, methods=["GET"])

    async def index(self):
        raise HTTPException(status_code=404, detail="Frontend build not found")

    async def health(self):
        return {"status": "ok"}

    async def not_found(self):
        raise HTTPException(status_code=404, detail="Not Found")

    async def inject(self, request: Request):
        try:
            body = await request.json()
            if (
                not isinstance(body, dict)
                or not isinstance(body.get("target"), str)
                or not isinstance(body.get("action"), str)
                or not isinstance(body.get("params", {}), dict)
            ):
                raise ValueError("Expected target, action and params")
            result = await self.injector.inject(
                body["target"], body["action"], body.get("params", {})
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return asdict(result)

    async def websocket(self, ws: WebSocket):
        await ws.accept()
        client = _Client(ws)
        self.clients[ws] = client
        client.snapshot(self.builder.build().model_dump(mode="json"))
        client.sender = asyncio.create_task(client.send())
        client.reader = asyncio.create_task(self._read_commands(client))
        try:
            await asyncio.wait(
                (client.sender, client.reader), return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            self.clients.pop(ws, None)
            for task in (client.sender, client.reader):
                task.cancel()
            await asyncio.gather(client.sender, client.reader, return_exceptions=True)

    async def _read_commands(self, client: _Client):
        ws = client.ws
        try:
            while True:
                data = await ws.receive_json()
                try:
                    request = UiCommand.model_validate(data)
                except ValidationError:
                    await ws.close(code=1008)
                    return
                # Queue this client's result before changes made while handling it.
                client.handling = True
                try:
                    result = await self.commands.handle(request)
                    client.result(result.model_dump(mode="json"))
                finally:
                    client.handling = False
                    client.flush_deferred()
                self.changed()
        except WebSocketDisconnect:
            pass

    async def _broadcast(self):
        async with self._broadcast_lock:
            if not self.clients:
                return
            snapshot = self.builder.build().model_dump(mode="json")
            for client in list(self.clients.values()):
                client.snapshot(snapshot)

    async def _on_bus_event(self, _env):
        self.changed()

    async def _periodic_updates(self):
        while True:
            await self.clock.sleep(1 / self.cfg.timing.status_rate_hz)
            await self._broadcast()

    def changed(self):
        if self.clients:
            self._dirty = True
            if self._debounced is None or self._debounced.done():
                self._debounced = asyncio.create_task(self._debounce())

    async def _debounce(self):
        while self._dirty:
            await self.clock.sleep(self.cfg.ui.snapshot_debounce_ms / 1000)
            self._dirty = False
            await self._broadcast()
