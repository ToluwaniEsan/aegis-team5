"""Task B6: the Team 4 stand-in."""

import pytest

from aegis.bus.local_bus import LocalBus
from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.standins.power import PowerStandin
from tests.fakes import FakeBus, FakeLog, advance, settle

PC = "vehicle.payload_controller"


@pytest.fixture
def cfg():
    return load_settings()


class Flag:
    def __init__(self):
        self.on = False

    def __call__(self):
        return self.on


async def test_mass_reports_logged_and_power_status_reaches_status_monitor(cfg):
    """B6 Done-when, on a real LocalBus: the status goes across the link."""
    bus_log = FakeLog("vehicle")
    bus = LocalBus("vehicle", bus_log.clock, bus_log)

    class Link:
        def __init__(self):
            self.sent = []

        async def send(self, env):
            self.sent.append(env)

    link = Link()
    bus.attach_link(link)
    power = PowerStandin(bus, bus_log.clock, cfg, bus_log)
    await power.start()
    await settle()

    report = make(
        "payload.mass_report",
        PC,
        {
            "mass_kg": 742.1,
            "release_energy_wh_nominal": 3.2,
            "release_energy_wh_max": 5.0,
        },
        bus_log.clock,
    )
    await bus.publish(report)
    [logged] = bus_log.of("power.mass_report")
    assert logged["mass_kg"] == 742.1 and logged["msg_id"] == str(report.msg_id)

    statuses = [e for e in link.sent if e.type == "power.status"]
    assert statuses and statuses[0].dst == [PC, "ground.status_monitor"]
    assert statuses[0].body.battery_pct == cfg.standins.power.start_battery_pct
    await power.stop()


async def test_battery_drains_only_while_moving(cfg):
    bus = FakeBus("vehicle")
    moving = Flag()
    power = PowerStandin(bus, bus.clock, cfg, bus.log, moving=moving)
    await power.start()
    await settle()
    start = cfg.standins.power.start_battery_pct

    await advance(bus.clock, 60.0, step=1.0)
    assert bus.last("power.status").body.battery_pct == start

    moving.on = True
    await advance(bus.clock, 60.0, step=1.0)
    s = cfg.standins
    expected = start - s.power.drain_pct_per_min * s.time_scale  # one minute
    assert bus.last("power.status").body.battery_pct == pytest.approx(expected, abs=0.2)
    await power.stop()


async def test_power_status_at_1_hz(cfg):
    bus = FakeBus("vehicle")
    power = PowerStandin(bus, bus.clock, cfg, bus.log)
    await power.start()
    await settle()
    bus.clear()
    await advance(bus.clock, 5.0, step=0.5)
    assert len(bus.sent("power.status")) == 5 * cfg.timing.status_rate_hz
    await power.stop()


async def test_estop_acked(cfg):
    bus = FakeBus("vehicle")
    power = PowerStandin(bus, bus.clock, cfg, bus.log)
    await power.start()
    stop = make(
        "cmd.estop",
        "ground.command_manager",
        {"reason": "t", "source": "OPERATOR"},
        bus.clock,
    )
    await bus.publish(stop)
    acks = [a for a in bus.sent("ack") if a.corr_id == stop.msg_id]
    assert [a.body.result for a in acks] == ["RECEIVED", "COMPLETED"]
    assert all(a.src == "team4.power" and a.iface == "I5" for a in acks)
    await power.stop()


async def test_battery_and_drivetrain_hooks(cfg):
    bus = FakeBus("vehicle")
    power = PowerStandin(bus, bus.clock, cfg, bus.log)
    await power.start()
    await power.battery(15.0)
    assert bus.last("power.status").body.battery_pct == 15.0
    await power.drivetrain("FAULT")
    assert bus.last("power.status").body.drivetrain_health == "FAULT"
    await power.stop()


def test_range_follows_battery(cfg):
    bus = FakeBus("vehicle")
    power = PowerStandin(bus, bus.clock, cfg, bus.log)
    full = power.est_range_km()
    power.battery_pct /= 2
    assert power.est_range_km() == pytest.approx(full / 2)
