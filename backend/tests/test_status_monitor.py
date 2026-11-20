from datetime import timedelta

import pytest

from aegis.common.clock import ManualClock
from aegis.common.config import load_settings
from aegis.common.envelope import make, make_ack
from aegis.common.ui_models import Place
from aegis.ground.status_monitor import StatusMonitor
from tests.fakes import FAKE_START, FakeBus, FakeLog

POWER = {"battery_pct": 80, "est_range_km": 40, "drivetrain_health": "OK"}
LINK = {"state": "CONNECTED", "latency_ms": 80, "loss_pct": 0}
PAYLOAD = {
    "state": "SECURED",
    "held_from": None,
    "secured": True,
    "locked": True,
    "mass_kg": 742,
    "shift_cm": 0,
    "release_energy_wh": None,
    "sensors": {"load_cell": "OK", "lock": "OK", "shift": "OK"},
    "prerelease_authorized": False,
    "departure_permitted": True,
    "departure_reason": None,
    "mission_id": "MSN-1",
}
NAV = {
    "moving": True,
    "speed_mps": 8,
    "position": {"lat": 34, "lon": -86},
    "at_destination": False,
    "at_origin": False,
    "eta_s": 100,
    "progress_pct": 20,
    "route": [{"lat": 34, "lon": -86}, {"lat": 35, "lon": -85}],
    "health": "OK",
}
DEST = Place(id="OP_BRAVO", name="Outpost Bravo", lat=35, lon=-85)


@pytest.fixture
def harness():
    clock = ManualClock(FAKE_START)
    log = FakeLog(clock=clock)
    bus = FakeBus(side="ground", clock=clock, log=log)
    cfg = load_settings()
    destinations = {"MSN-1": DEST}
    monitor = StatusMonitor(bus, clock, cfg, log, destinations.get)
    return monitor, bus, clock, cfg, log, destinations


@pytest.mark.asyncio
async def test_OI_008_last_known_status_and_age_shown_when_link_lost(harness):
    monitor, bus, clock, cfg, _, _ = harness
    await bus.inject(make("power.status", "team4.power", POWER, clock))
    await bus.inject(make("link.health", "team3.link", LINK, clock))
    clock.advance(cfg.link.lost_after_s + 1)
    assert monitor.link_view().state == "LOST"
    assert monitor.latest["power.status"].body.battery_pct == 80
    assert monitor.freshness("power.status").age_s == cfg.link.lost_after_s + 1
    assert monitor.freshness("power.status").stale


@pytest.mark.asyncio
async def test_OI_017_values_older_than_5s_marked_stale(harness):
    monitor, bus, clock, cfg, _, _ = harness
    assert monitor.freshness("payload.status").stale
    old = make(
        "payload.status",
        "vehicle.payload_controller",
        PAYLOAD,
        clock,
        payload_id="PAY-1",
    )
    clock.advance(2)
    await bus.inject(old)
    assert monitor.freshness("payload.status").age_s == 2
    clock.advance(cfg.timing.stale_after_s - 2)
    assert not monitor.freshness("payload.status").stale
    clock.advance(0.001)
    assert monitor.freshness("payload.status").stale
    assert monitor.latest["payload.status"].body.mass_kg == 742


@pytest.mark.asyncio
async def test_OI_007_link_state_follows_link_health(harness):
    monitor, bus, clock, _, _, _ = harness
    for state in ("CONNECTED", "DEGRADED", "LOST"):
        clock.advance(1)
        await bus.inject(
            make("link.health", "team3.link", {**LINK, "state": state}, clock)
        )
        assert monitor.link_view().state == state


@pytest.mark.asyncio
async def test_OI_007_link_lost_when_health_messages_stop(harness):
    monitor, bus, clock, cfg, _, _ = harness
    await bus.inject(make("link.health", "team3.link", LINK, clock))
    clock.advance(cfg.link.lost_after_s - 0.001)
    assert monitor.link_view().state == "CONNECTED"
    clock.advance(0.001)
    assert monitor.link_view().state == "LOST"
    assert monitor.link_view().latency_ms == 80


@pytest.mark.asyncio
async def test_AEG_508_confirm_latency_recorded(harness):
    monitor, bus, clock, _, _, _ = harness
    released = clock.now()
    clock.advance(3)
    body = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": released,
        "position": {"lat": 35, "lon": -85},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    await bus.inject(
        make("payload.delivered", "vehicle.payload_controller", body, clock)
    )
    assert monitor.delivery.confirm_latency_s == 3
    assert monitor.delivery.destination == DEST
    assert bus.last("t1.delivery_confirmation").body.model_dump() == body


@pytest.mark.asyncio
async def test_OI_016_delivery_waits_for_destination_but_forwards_immediately(harness):
    monitor, bus, clock, _, _, destinations = harness
    destinations.clear()
    body = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": clock.now(),
        "position": {"lat": 35, "lon": -85},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    clock.advance(2)
    await bus.inject(
        make("payload.delivered", "vehicle.payload_controller", body, clock)
    )
    assert monitor.delivery is None
    assert len(bus.sent("t1.delivery_confirmation")) == 1
    clock.advance(5)
    destinations["MSN-1"] = DEST
    monitor.resolve_deliveries()
    assert monitor.delivery.confirm_latency_s == 2


@pytest.mark.asyncio
async def test_OI_012_blocked_route_preserves_old_route_and_expires(harness):
    monitor, bus, clock, cfg, _, _ = harness
    await bus.inject(make("nav.state", "team2.nav", NAV, clock))
    clock.advance(1)
    new_route = [{"lat": 34.5, "lon": -85.5}, {"lat": 35, "lon": -85}]
    await bus.inject(
        make(
            "nav.route_blocked",
            "team2.nav",
            {
                "reason": "Bridge closed",
                "blocked_at": {"lat": 34, "lon": -86},
                "new_route": new_route,
                "new_eta_s": 150,
            },
            clock,
        )
    )
    assert [p.model_dump() for p in monitor.blocked().old_route] == NAV["route"]
    assert [p.model_dump() for p in monitor.route()] == new_route
    clock.advance(cfg.timing.route_blocked_clear_s)
    assert monitor.blocked() is None
    assert [p.model_dump() for p in monitor.route()] == new_route
    assert (
        monitor.latest["nav.state"].body.route
        == make("nav.state", "team2.nav", NAV, clock).body.route
    )
    assert bus.published == []


@pytest.mark.asyncio
async def test_OI_005_vehicle_health_rollup(harness):
    monitor, bus, clock, cfg, _, _ = harness
    assert monitor.vehicle_health().overall == "DEGRADED"
    for kind, src, body in [
        ("power.status", "team4.power", POWER),
        ("link.health", "team3.link", LINK),
        ("payload.status", "vehicle.payload_controller", PAYLOAD),
        ("nav.state", "team2.nav", NAV),
    ]:
        await bus.inject(make(kind, src, body, clock))
    assert monitor.vehicle_health().overall == "NOMINAL"
    clock.advance(1)
    await bus.inject(
        make(
            "power.status",
            "team4.power",
            {**POWER, "battery_pct": cfg.alerts.power_low_pct - 1},
            clock,
        )
    )
    assert monitor.vehicle_health().overall == "DEGRADED"
    clock.advance(1)
    await bus.inject(
        make(
            "power.status",
            "team4.power",
            {**POWER, "battery_pct": cfg.alerts.power_fault_pct},
            clock,
        )
    )
    assert monitor.vehicle_health().overall == "FAULT"


@pytest.mark.asyncio
async def test_OI_013_backlog_deduplicates_and_preserves_newer_status(harness):
    monitor, bus, clock, _, log, _ = harness
    old = make("power.status", "team4.power", {**POWER, "battery_pct": 20}, clock)
    command = make("cmd.release", "ground.command_manager", {}, clock)
    ack = make_ack(command, "vehicle.payload_controller", "COMPLETED", clock)
    clock.advance(2)
    new = make("power.status", "team4.power", POWER, clock)
    await bus.inject(new)
    batch = make(
        "backlog.batch", "vehicle.event_buffer", {"events": [new, old, ack, ack]}, clock
    )
    await bus.inject(batch)
    assert monitor.latest["power.status"].msg_id == new.msg_id
    assert len(monitor.acks) == 1
    events = log.of("backlog.event")
    assert [e["env"]["msg_id"] for e in events] == [str(old.msg_id), str(ack.msg_id)]
    assert events[0]["original_time"] == old.model_dump(mode="json")["sent_at"]


@pytest.mark.asyncio
async def test_OI_017_older_direct_status_cannot_replace_newer(harness):
    monitor, bus, clock, _, _, _ = harness
    old = make("power.status", "team4.power", {**POWER, "battery_pct": 10}, clock)
    clock.advance(1)
    new = make("power.status", "team4.power", POWER, clock)
    await bus.inject(new)
    await bus.inject(old)
    assert monitor.latest["power.status"].msg_id == new.msg_id
    assert clock.now() == FAKE_START + timedelta(seconds=1)


@pytest.mark.asyncio
async def test_OI_005_payload_and_navigation_views_preserve_status(harness):
    monitor, bus, clock, _, _, _ = harness
    assert monitor.payload_view() is None
    await bus.inject(
        make(
            "payload.status",
            "vehicle.payload_controller",
            PAYLOAD,
            clock,
            payload_id="PAY-1",
        )
    )
    await bus.inject(make("nav.state", "team2.nav", NAV, clock))
    clock.advance(1)
    assert monitor.payload_view().payload_id == "PAY-1"
    assert monitor.payload_view().sensor_health == "OK"
    assert monitor.payload_view().age_s == 1
    assert monitor.nav_view(destination=DEST).destination == DEST
    assert monitor.nav_view().position.lat == 34


@pytest.mark.asyncio
async def test_OI_013_backlog_faults_and_acks_are_forwarded_once(harness):
    monitor, bus, clock, _, _, _ = harness
    delivered = []

    async def on_fault(env):
        delivered.append(env)

    monitor.on_fault = on_fault
    fault = make(
        "fault.raised",
        "vehicle.payload_controller",
        {
            "fault_id": "de117211-9930-4fe2-9a6f-b6e96b75ead0",
            "code": "PAYLOAD_SHIFT",
            "severity": "WARNING",
            "source": "Payload",
            "message": "Payload shifted",
            "recommended_action": "Inspect payload",
            "holds_payload": False,
        },
        clock,
    )
    command = make("cmd.release", "ground.command_manager", {}, clock)
    ack = make_ack(command, "vehicle.payload_controller", "COMPLETED", clock)
    await bus.inject(
        make(
            "backlog.batch",
            "vehicle.event_buffer",
            {"events": [fault, ack, fault]},
            clock,
        )
    )
    assert [event.msg_id for event in delivered] == [fault.msg_id]
    assert [event.msg_id for event in monitor.acks] == [ack.msg_id]
    await bus.inject(ack)
    assert len(monitor.acks) == 1


@pytest.mark.asyncio
async def test_AEG_508_replayed_delivery_is_forwarded_only_once(harness):
    monitor, bus, clock, _, _, _ = harness
    released = clock.now()
    body = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": released,
        "position": {"lat": 35, "lon": -85},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    event = make("payload.delivered", "vehicle.payload_controller", body, clock)
    clock.advance(4)
    batch = make(
        "backlog.batch", "vehicle.event_buffer", {"events": [event, event]}, clock
    )
    await bus.inject(batch)
    await bus.inject(event)
    assert monitor.delivery.confirm_latency_s == 4
    assert len(bus.sent("t1.delivery_confirmation")) == 1


@pytest.mark.asyncio
async def test_OI_012_new_nav_replaces_route_after_notice_expires(harness):
    monitor, bus, clock, cfg, _, _ = harness
    await bus.inject(make("nav.state", "team2.nav", NAV, clock))
    clock.advance(1)
    detour = [{"lat": 34.5, "lon": -85.5}]
    await bus.inject(
        make(
            "nav.route_blocked",
            "team2.nav",
            {
                "reason": "Blocked",
                "blocked_at": {"lat": 34, "lon": -86},
                "new_route": detour,
                "new_eta_s": 150,
            },
            clock,
        )
    )
    clock.advance(cfg.timing.route_blocked_clear_s)
    assert monitor.blocked() is None
    assert [p.model_dump() for p in monitor.route()] == detour
    later = [{"lat": 34.7, "lon": -85.7}, {"lat": 35, "lon": -85}]
    await bus.inject(make("nav.state", "team2.nav", {**NAV, "route": later}, clock))
    assert [p.model_dump() for p in monitor.route()] == later
    assert monitor.blocked() is None


@pytest.mark.asyncio
async def test_OI_016_older_pending_delivery_cannot_replace_newer(harness):
    monitor, bus, clock, _, _, destinations = harness
    destinations.clear()
    body = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": clock.now(),
        "position": {"lat": 35, "lon": -85},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    old = make("payload.delivered", "vehicle.payload_controller", body, clock)
    clock.advance(1)
    await bus.inject(old)
    clock.advance(2)
    destinations["MSN-2"] = DEST
    newer = make(
        "payload.delivered",
        "vehicle.payload_controller",
        {
            **body,
            "mission_id": "MSN-2",
            "payload_id": "PAY-2",
            "released_at": clock.now(),
        },
        clock,
    )
    await bus.inject(newer)
    saved = monitor.delivery.model_dump()
    destinations["MSN-1"] = DEST
    clock.advance(2)
    monitor.resolve_deliveries()
    assert monitor.delivery.model_dump() == saved
    assert monitor.delivery.mission_id == "MSN-2"
    assert old.body.released_at == FAKE_START


def fault_message(clock, fault_id):
    return make(
        "fault.raised",
        "vehicle.payload_controller",
        {
            "fault_id": fault_id,
            "code": "PAYLOAD_SHIFT",
            "severity": "WARNING",
            "source": "Payload",
            "message": "Payload shifted",
            "recommended_action": "Inspect payload",
            "holds_payload": False,
        },
        clock,
    )


@pytest.mark.asyncio
async def test_OI_013_failed_batch_retries_remaining_events_without_repeating_success(
    harness,
):
    monitor, bus, clock, _, log, _ = harness
    seen = []
    attempts = []
    first = fault_message(clock, "de117211-9930-4fe2-9a6f-b6e96b75ead0")
    second = fault_message(clock, "de117211-9930-4fe2-9a6f-b6e96b75ead1")
    third = fault_message(clock, "de117211-9930-4fe2-9a6f-b6e96b75ead2")

    async def callback(env):
        attempts.append(env.msg_id)
        if env.msg_id == second.msg_id and attempts.count(second.msg_id) == 1:
            raise RuntimeError("temporary failure")
        seen.append(env.msg_id)

    monitor.on_fault = callback
    batch = make(
        "backlog.batch",
        "vehicle.event_buffer",
        {"events": [first, second, third]},
        clock,
    )
    with pytest.raises(RuntimeError, match="temporary failure"):
        await bus.inject(batch)
    assert seen == [first.msg_id]
    assert batch.msg_id not in monitor.seen
    await bus.inject(batch)
    assert seen == [first.msg_id, second.msg_id, third.msg_id]
    await bus.inject(batch)
    assert attempts == [first.msg_id, second.msg_id, second.msg_id, third.msg_id]
    assert len(log.of("backlog.event")) == 3
    assert [event.msg_id for event in monitor.replayed_faults] == seen


@pytest.mark.asyncio
async def test_AEG_508_publish_retry_reuses_confirmation_id_and_receipt_time(harness):
    monitor, bus, clock, _, log, _ = harness
    body = {
        "mission_id": "MSN-1",
        "payload_id": "PAY-1",
        "released_at": clock.now(),
        "position": {"lat": 35, "lon": -85},
        "mass_kg": 742,
        "energy_used_wh": 3.2,
    }
    event = make("payload.delivered", "vehicle.payload_controller", body, clock)
    batch = make("backlog.batch", "vehicle.event_buffer", {"events": [event]}, clock)
    clock.advance(3)
    attempted = []
    publish = bus.publish

    async def flaky_publish(outgoing):
        attempted.append(outgoing.msg_id)
        if len(attempted) == 1:
            raise RuntimeError("publish failed")
        await publish(outgoing)

    bus.publish = flaky_publish
    with pytest.raises(RuntimeError, match="publish failed"):
        await bus.inject(batch)
    clock.advance(4)
    await bus.inject(batch)
    await bus.inject(batch)
    assert len(attempted) == 2 and attempted[0] == attempted[1]
    assert len(bus.sent("t1.delivery_confirmation")) == 1
    assert monitor.delivery.confirm_latency_s == 3
    assert monitor.delivery.confirmed_at == "2026-11-19T12:00:03.000Z"
    assert len([r for r in log.of("state.change") if r.get("group") == "delivery"]) == 1


@pytest.mark.asyncio
async def test_OI_012_replayed_older_route_event_does_not_replace_new_navigation(
    harness,
):
    monitor, bus, clock, _, _, _ = harness
    old_block = make(
        "nav.route_blocked",
        "team2.nav",
        {
            "reason": "Blocked",
            "blocked_at": {"lat": 34, "lon": -86},
            "new_route": [{"lat": 34.5, "lon": -85.5}],
            "new_eta_s": 150,
        },
        clock,
    )
    clock.advance(1)
    await bus.inject(make("nav.state", "team2.nav", NAV, clock))
    await bus.inject(
        make("backlog.batch", "vehicle.event_buffer", {"events": [old_block]}, clock)
    )
    assert [p.model_dump() for p in monitor.route()] == NAV["route"]
