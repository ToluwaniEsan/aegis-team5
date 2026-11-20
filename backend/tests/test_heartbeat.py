"""Task B4: the ground heartbeat."""

import itertools
from datetime import timedelta

import pytest

from aegis.common.config import load_settings
from aegis.ground.heartbeat import Heartbeat
from tests.fakes import FakeBus
from tests.test_link_standin import settle


@pytest.mark.asyncio
async def test_heartbeat_at_configured_rate_with_rising_seq():
    cfg = load_settings()
    bus = FakeBus("ground")
    hb = Heartbeat(bus, bus.clock, cfg)
    await hb.start()
    await settle()
    period = 1.0 / cfg.timing.heartbeat_rate_hz
    for _ in range(3):
        bus.clock.advance(period)
        await settle()
    await hb.stop()

    sent = bus.sent("hb.ground")
    assert [e.body.seq for e in sent] == [0, 1, 2, 3]
    assert all(e.src == "ground.command_manager" for e in sent)
    assert all(e.dst == ["vehicle.link_watch"] for e in sent)
    gaps = {b.sent_at - a.sent_at for a, b in itertools.pairwise(sent)}
    assert gaps == {timedelta(seconds=period)}
