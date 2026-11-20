import httpx
import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.ground.command_manager import CommandManager
from aegis.ground.status_monitor import StatusMonitor
from aegis.ground.ui_server import UiServer
from aegis.testing.fault_injector import FaultInjector
from tests.fakes import FAKE_START, FakeBus, FakeLog


def components(tmp_path, *, test_mode=True):
    cfg = load_settings()
    cfg = cfg.model_copy(
        update={
            "test_mode": test_mode,
            "logging": cfg.logging.model_copy(update={"dir": str(tmp_path)}),
        }
    )
    clock = ManualClock(FAKE_START)
    log = FakeLog(clock=clock)
    bus = FakeBus("ground", clock, log)
    status = StatusMonitor(bus, clock, cfg, log, lambda _: None)
    commands = CommandManager(bus, clock, cfg, log, status)
    injector = FaultInjector(bus, clock, cfg, log)
    return cfg, clock, log, bus, status, commands, injector


@pytest.mark.asyncio
async def test_GEN_001_injection_endpoint_routes_real_validated_injection(tmp_path):
    cfg, clock, log, bus, _, commands, injector = components(tmp_path)
    server = UiServer(cfg, clock, None, commands, injector)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/test/inject",
            json={"target": "payload", "action": "shift", "params": {"cm": 3.1}},
        )
        assert response.status_code == 200
        assert response.json()["dst"] == "vehicle.test_agent"
        assert bus.last("test.inject").body.params == {"cm": 3.1}
        assert len(log.of("test.inject")) == 1
        invalid = await client.post(
            "/api/test/inject",
            json={"target": "payload", "action": "shift", "params": {"cm": "bad"}},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"]
        assert len(bus.sent("test.inject")) == 1
    commands.close()


@pytest.mark.asyncio
async def test_GEN_001_test_inject_endpoint_absent_when_disabled(tmp_path):
    cfg, clock, _, bus, _, commands, injector = components(tmp_path, test_mode=False)
    server = UiServer(cfg, clock, None, commands, injector)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/test/inject",
            json={"target": "payload", "action": "shift", "params": {"cm": 3.1}},
        )
        assert response.status_code == 404
        assert not bus.sent("test.inject")
    commands.close()


@pytest.mark.asyncio
async def test_OI_006_websocket_returns_command_result_to_requesting_client(tmp_path):
    import asyncio
    import json

    from aegis.common.envelope import make, make_ack
    from aegis.ground.snapshot import SnapshotBuilder
    from tests.test_status_monitor import PAYLOAD

    cfg, clock, _, bus, status, commands, injector = components(tmp_path)
    builder = SnapshotBuilder(cfg, clock, status, commands)
    server = UiServer(cfg, clock, builder, commands, injector)
    inbound, outbound = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "scheme": "ws",
        "path": "/ws",
        "raw_path": b"/ws",
        "query_string": b"",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
        "subprotocols": [],
        "root_path": "",
    }
    await inbound.put({"type": "websocket.connect"})
    other_inbound, other_outbound = asyncio.Queue(), asyncio.Queue()
    await other_inbound.put({"type": "websocket.connect"})
    async with server.app.router.lifespan_context(server.app):
        task = asyncio.create_task(server.app(scope, inbound.get, outbound.put))
        assert (await outbound.get())["type"] == "websocket.accept"
        initial = json.loads((await outbound.get())["text"])
        other_task = asyncio.create_task(
            server.app(scope, other_inbound.get, other_outbound.put)
        )
        assert (await other_outbound.get())["type"] == "websocket.accept"
        assert json.loads((await other_outbound.get())["text"])["kind"] == "snapshot"
        assert initial["kind"] == "snapshot"
        assert initial["payload"]["updated_at"] is None
        assert initial["payload"]["stale"] is True
        assert initial["payload"]["departure_reason"] == "Awaiting payload status"
        assert status.payload_view() is None
        assert not initial["allowed"]["release"]["allowed"]
        assert initial["allowed"]["estop"]["allowed"]
        assert initial["limits"]["mass_min_kg"] == cfg.payload.mass_min_kg
        msg = {
            "kind": "command",
            "client_req_id": "req-1",
            "command": "estop",
            "args": {},
            "confirmed": False,
        }
        await inbound.put({"type": "websocket.receive", "text": json.dumps(msg)})
        result = json.loads((await outbound.get())["text"])
        assert result["kind"] == "command_result" and result["accepted"]
        assert result["client_req_id"] == "req-1"
        assert bus.last("cmd.estop").priority == 0
        assert other_outbound.empty()
        for _ in range(3):
            await asyncio.sleep(0)
        clock.advance(cfg.ui.snapshot_debounce_ms / 1000)
        changed = json.loads((await outbound.get())["text"])
        assert changed["kind"] == "snapshot" and changed["seq"] > initial["seq"]
        assert json.loads((await other_outbound.get())["text"])["kind"] == "snapshot"
        clock.advance(1 / cfg.timing.status_rate_hz)
        periodic = json.loads((await outbound.get())["text"])
        assert periodic["kind"] == "snapshot" and periodic["seq"] > changed["seq"]
        await bus.inject(
            make_ack(bus.last("cmd.estop"), "team2.nav", "RECEIVED", clock)
        )
        for _ in range(3):
            await asyncio.sleep(0)
        clock.advance(cfg.ui.snapshot_debounce_ms / 1000)
        lifecycle = json.loads((await outbound.get())["text"])
        assert lifecycle["commands"][0]["state"] == "RECEIVED"
        await bus.inject(
            make(
                "payload.status",
                "vehicle.payload_controller",
                PAYLOAD,
                clock,
                payload_id="PAY-1",
            )
        )
        for _ in range(3):
            await asyncio.sleep(0)
        clock.advance(cfg.ui.snapshot_debounce_ms / 1000)
        real_status = json.loads((await outbound.get())["text"])
        assert real_status["payload"]["state"] == "SECURED"
        assert real_status["payload"]["updated_at"] is not None
        assert real_status["payload"]["payload_id"] == "PAY-1"
        await inbound.put({"type": "websocket.disconnect", "code": 1000})
        await other_inbound.put({"type": "websocket.disconnect", "code": 1000})
        await task
        await other_task
    commands.close()


@pytest.mark.asyncio
async def test_OI_017_startup_snapshot_waits_for_real_payload_and_commands_fail_closed(
    tmp_path,
):
    from aegis.common.envelope import make
    from aegis.common.ui_models import UiCommand
    from aegis.ground.snapshot import SnapshotBuilder
    from tests.test_status_monitor import PAYLOAD

    cfg, clock, _, bus, status, commands, _ = components(tmp_path)
    builder = SnapshotBuilder(cfg, clock, status, commands)
    first = builder.build()
    assert first.payload.state == "EMPTY" and first.payload.stale
    assert first.payload.departure_reason == "Awaiting payload status"
    assert first.payload.updated_at is None and first.payload.age_s is None
    assert (
        first.payload.sensors.load_cell == "UNKNOWN" and first.payload.mass_kg is None
    )
    assert status.payload_view() is None
    assert all(not p.allowed for name, p in first.allowed if name != "estop")
    release = UiCommand(
        kind="command", client_req_id="1", command="release", args={}, confirmed=True
    )
    assert not (await commands.handle(release)).accepted
    estop = UiCommand(
        kind="command", client_req_id="2", command="estop", args={}, confirmed=False
    )
    assert (await commands.handle(estop)).accepted
    await bus.inject(
        make(
            "payload.status",
            "vehicle.payload_controller",
            PAYLOAD,
            clock,
            payload_id="PAY-1",
        )
    )
    second = builder.build()
    assert second.payload.state == "SECURED" and not second.payload.stale
    assert second.payload.payload_id == "PAY-1"
    assert second.seq > first.seq
    commands.close()


@pytest.mark.asyncio
async def test_OI_019_estop_snapshot_uses_alert_source_not_held(tmp_path):
    from aegis.common.envelope import make
    from aegis.common.ui_models import AlertView
    from aegis.ground.snapshot import SnapshotBuilder
    from tests.test_status_monitor import PAYLOAD

    cfg, clock, _, bus, status, commands, _ = components(tmp_path)
    builder = SnapshotBuilder(cfg, clock, status, commands)
    assert not builder.build().estop_active  # D-22 placeholder, not proof of safety.
    held = {
        **PAYLOAD,
        "state": "HELD",
        "held_from": "SECURED",
        "departure_permitted": False,
        "departure_reason": "Held",
    }
    await bus.inject(make("payload.status", "vehicle.payload_controller", held, clock))
    assert builder.build().payload.state == "HELD"
    assert not builder.build().estop_active
    alert = AlertView(
        alert_id="id",
        code="ESTOP_ACTIVE",
        severity="CRITICAL",
        title="Stop",
        source="Payload",
        recommended_action="Check",
        raised_at="2026-11-19T12:00:00.000Z",
        acknowledged=False,
        active=True,
    )
    commands.alerts_for = lambda: [alert]
    assert builder.build().estop_active
    commands.alerts_for = lambda: [alert.model_copy(update={"active": False})]
    assert builder.build().estop_active
    commands.alerts_for = lambda: [
        alert.model_copy(update={"active": False, "acknowledged": True})
    ]
    assert not builder.build().estop_active
    assert builder.build().alerts == []
    warning = alert.model_copy(
        update={
            "alert_id": "warning",
            "severity": "WARNING",
            "code": "PAYLOAD_SHIFT",
            "raised_at": "2026-11-19T12:00:10.000Z",
        }
    )
    commands.alerts_for = lambda: [warning, alert]
    assert [item.alert_id for item in builder.build().alerts] == ["id", "warning"]
    commands.close()
