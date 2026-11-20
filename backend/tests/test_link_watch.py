"""Task A5: link loss on the vehicle."""

from datetime import timedelta

import pytest

from aegis.common.envelope import make
from aegis.ground.heartbeat import Heartbeat
from aegis.vehicle.link_watch import LinkWatch
from tests.fakes import FakeBus, advance, settle
from tests.test_payload_controller import Vehicle


def link_states(bus):
    return [e.body.state for e in bus.sent("int.link_state")]


@pytest.fixture
async def watched():
    v = Vehicle()
    v.watch = LinkWatch(v.bus, v.clock, v.cfg, v.bus.log)
    v.hb = Heartbeat(v.bus, v.clock, v.cfg)
    await v.start()
    await v.watch.start()
    await v.hb.start()
    await settle()
    yield v
    await v.hb.stop()
    await v.watch.stop()
    await v.stop()


async def test_lost_after_silence_and_restored_on_next_heartbeat():
    bus = FakeBus("vehicle")
    from aegis.common.config import load_settings

    cfg = load_settings()
    watch = LinkWatch(bus, bus.clock, cfg, bus.log)
    hb = Heartbeat(bus, bus.clock, cfg)
    await watch.start()
    await hb.start()
    await advance(bus.clock, 30.0, step=0.5)
    assert link_states(bus) == []  # heartbeats flowing: never LOST

    await hb.stop()
    silent_from = bus.clock.now()
    await advance(bus.clock, cfg.link.lost_after_s - 1.5, step=0.5)
    assert link_states(bus) == []
    await advance(bus.clock, 2.0, step=0.5)
    assert link_states(bus) == ["LOST"]
    lost = bus.last("int.link_state")
    assert lost.dst == ["vehicle.payload_controller", "vehicle.event_buffer"]
    assert lost.body.since <= silent_from

    await advance(bus.clock, 60.0, step=1.0)
    assert link_states(bus) == ["LOST"]  # once, not every second

    hb.seq = 99
    await hb.beat()
    assert link_states(bus) == ["LOST", "RESTORED"]
    await watch.stop()


async def test_lost_if_no_heartbeat_ever_arrives():
    from aegis.common.config import load_settings

    cfg = load_settings()
    bus = FakeBus("vehicle")
    watch = LinkWatch(bus, bus.clock, cfg, bus.log)
    await watch.start()
    await advance(bus.clock, cfg.link.lost_after_s + 0.5, step=0.5)
    assert link_states(bus) == ["LOST"]
    await watch.stop()


async def to_destination(v, prerelease):
    p = v.cfg.payload
    await v.assign(prerelease=prerelease)
    await v.wait(p.load_time_s + p.secure_time_s + 1.0)
    await v.nav.depart()
    await v.wait(1.0)
    await v.nav.arrive()
    await v.wait(1.0)
    assert v.status().state == "AT_DESTINATION"


async def test_AEG_514_link_lost_at_destination_without_preauth_stays_secured(watched):
    v = watched
    await to_destination(v, prerelease=False)
    await v.hb.stop()  # the link goes down
    await v.wait(v.cfg.link.lost_after_s + 1.0)
    assert link_states(v.bus) == ["LOST"]

    await v.wait(600.0, step=5.0)  # ten minutes
    s = v.status()
    assert s.state == "AT_DESTINATION"
    assert s.secured and s.locked
    assert v.bus.sent("payload.delivered") == []
    assert "RELEASE" not in [e.body.action for e in v.bus.sent("sim.command")]


async def test_AEG_507_link_lost_with_preauth_releases_after_wait(watched):
    v = watched
    await to_destination(v, prerelease=True)
    await v.hb.stop()
    await v.wait(v.cfg.link.lost_after_s + 1.0)
    assert link_states(v.bus) == ["LOST"]
    lost_at = v.bus.last("int.link_state").sent_at

    wait = v.cfg.link.prerelease_wait_s
    await v.wait(wait - 1.5)
    assert v.status().state == "AT_DESTINATION"  # not before the wait

    await v.wait(2.0)
    assert v.status().state == "RELEASED"
    started = v.bus.last("sim.command")
    assert started.body.action == "RELEASE"
    assert (started.sent_at - lost_at) >= timedelta(seconds=wait)
    assert v.bus.log.of("release.preauthorized")

    await v.wait(v.cfg.payload.release_time_s + 1.0)
    assert v.status().state == "DELIVERED"
    assert len(v.bus.sent("payload.delivered")) == 1


async def test_AEG_507_preauth_release_still_checks_guards(watched):
    v = watched
    await to_destination(v, prerelease=True)
    await v.sim.inject_shift(v.cfg.payload.unsecured_shift_cm + 1.0)  # now unsecured
    await v.hb.stop()
    await v.wait(v.cfg.link.lost_after_s + v.cfg.link.prerelease_wait_s + 30.0)
    assert v.status().state == "AT_DESTINATION"
    assert v.bus.sent("payload.delivered") == []


async def test_AEG_514_old_release_command_rejected_after_link_returns(watched):
    v = watched
    await to_destination(v, prerelease=False)
    await v.hb.stop()
    await v.wait(v.cfg.link.lost_after_s + 1.0)

    # The operator pressed release during the outage; the command arrives late.
    old = make("cmd.release", "ground.command_manager", {}, v.clock)
    await v.wait(30.0)
    await v.hb.start()  # the link returns
    await v.wait(1.0)
    assert link_states(v.bus)[-1] == "RESTORED"

    await v.bus.publish(old)
    await settle()
    await v.ctrl.drain()
    await settle()
    [rej] = [
        a
        for a in v.bus.sent("ack")
        if a.corr_id == old.msg_id and a.body.result == "REJECTED"
    ]
    assert rej.body.reason_code == "STALE_COMMAND"
    assert v.status().state == "AT_DESTINATION"

    # A fresh command after the link returns is accepted.
    await v.send("cmd.release")
    assert v.status().state == "RELEASED"


def test_AEG_507_prerelease_wait_restarts_after_held_exit():
    from dataclasses import replace

    from aegis.vehicle import rules
    from tests.test_rules import CFG, NOW, cmd, in_state, run

    wait = CFG.link.prerelease_wait_s
    s = replace(in_state("AT_DESTINATION"), prerelease_authorized=True)
    s, _ = run(s, rules.LinkLost(), now=NOW)

    # An emergency stop just before the wait ends, acknowledged later.
    stop_at = NOW + timedelta(seconds=wait - 1)
    s, _ = run(
        s,
        rules.Command(cmd("cmd.estop", {"reason": "t", "source": "OPERATOR"}, stop_at)),
        now=stop_at,
    )
    fault = next(f for f in s.faults if f.code == "ESTOP_ACTIVE")
    ack_at = NOW + timedelta(seconds=wait + 20)
    s, _ = run(
        s,
        rules.Command(cmd("cmd.ack_fault", {"fault_id": fault.fault_id}, ack_at)),
        now=ack_at,
    )
    assert s.state == "AT_DESTINATION" and s.prerelease_from == ack_at

    # The full wait counts again from the HELD exit.
    s, _ = run(s, rules.Tick(), now=ack_at + timedelta(seconds=wait - 1))
    assert s.state == "AT_DESTINATION"
    s, _ = run(s, rules.Tick(), now=ack_at + timedelta(seconds=wait))
    assert s.state == "RELEASED"
