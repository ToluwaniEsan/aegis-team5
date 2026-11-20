"""Task A3: the Payload Simulator."""

import random

import pytest

from aegis.common.config import load_settings
from aegis.common.envelope import make
from aegis.vehicle.simulator import PayloadSimulator
from tests.fakes import FakeBus, advance, settle

PC = "vehicle.payload_controller"


@pytest.fixture
def cfg():
    return load_settings()


@pytest.fixture
def bus():
    return FakeBus("vehicle")


@pytest.fixture
async def sim(bus, cfg):
    s = PayloadSimulator(bus, bus.clock, cfg, bus.log, rng=random.Random(1))
    await s.start()
    await settle()
    yield s
    await s.stop()


async def command(bus, action, mass_kg=None):
    body = {"action": action} | ({"mass_kg": mass_kg} if mass_kg is not None else {})
    await bus.publish(make("sim.command", PC, body, bus.clock))
    await settle()


def last(bus):
    return bus.last("sim.reading").body


async def loaded(bus, cfg, mass=742.0):
    await command(bus, "LOAD", mass)
    await advance(bus.clock, cfg.payload.load_time_s)


async def test_AEG_504_twenty_readings_within_accuracy(bus, sim, cfg):
    await loaded(bus, cfg)
    bus.clear()
    await advance(bus.clock, 20.0, step=1.0)  # 1 Hz: 20 readings
    readings = bus.sent("sim.reading")
    assert len(readings) >= 20
    for env in readings[:20]:
        assert env.body.settled
        assert abs(env.body.mass_kg - 742.0) <= cfg.payload.weight_accuracy_kg


async def test_load_settles_after_load_time(bus, sim, cfg):
    await command(bus, "LOAD", 600.0)
    assert last(bus).settled is False
    await advance(bus.clock, cfg.payload.load_time_s - 0.1)
    assert last(bus).settled is False
    await advance(bus.clock, 0.2)
    assert last(bus).settled is True
    assert abs(last(bus).mass_kg - 600.0) <= cfg.payload.weight_accuracy_kg


async def test_AEG_512_update_keeps_lock_closed_and_reweighs(bus, sim, cfg):
    await loaded(bus, cfg)
    await command(bus, "LOCK")
    await advance(bus.clock, cfg.payload.secure_time_s)
    assert last(bus).locked is True

    await command(bus, "LOAD", 800.0)  # payload update
    assert last(bus).settled is False and last(bus).locked is True
    await advance(bus.clock, cfg.payload.reweigh_time_s)
    assert last(bus).settled is True and last(bus).locked is True
    assert abs(last(bus).mass_kg - 800.0) <= cfg.payload.weight_accuracy_kg


async def test_lock_closes_after_secure_time(bus, sim, cfg):
    await loaded(bus, cfg)
    await command(bus, "LOCK")
    await advance(bus.clock, cfg.payload.secure_time_s - 0.1)
    assert last(bus).locked is False
    await advance(bus.clock, 0.2)
    assert last(bus).locked is True


async def test_release_empties_the_bay_after_release_time(bus, sim, cfg):
    await loaded(bus, cfg)
    await command(bus, "LOCK")
    await advance(bus.clock, cfg.payload.secure_time_s)
    await command(bus, "RELEASE")
    assert last(bus).locked is False and last(bus).release_done is False
    await advance(bus.clock, cfg.payload.release_time_s - 0.1)
    assert last(bus).release_done is False
    await advance(bus.clock, 0.2)
    assert last(bus).release_done is True
    assert last(bus).mass_kg == 0.0
    assert sim.release_energy_wh == cfg.payload.release_energy_wh_nominal  # AEG-509


async def test_unload_empties_the_bay(bus, sim, cfg):
    await loaded(bus, cfg)
    await command(bus, "LOCK")
    await advance(bus.clock, cfg.payload.secure_time_s)
    await command(bus, "UNLOAD")
    assert last(bus).locked is False
    assert last(bus).mass_kg == 0.0


async def test_GEN_005_each_failure_can_be_triggered(bus, sim, cfg):
    await loaded(bus, cfg)

    await sim.inject_shift(3.1)
    assert last(bus).shift_cm == 3.1

    for name in ("load_cell", "lock", "shift"):
        await sim.set_sensor(name, "FAULT")
        assert getattr(last(bus).sensors, name) == "FAULT"
    assert last(bus).mass_kg is None  # a FAULT load cell reports no mass
    assert last(bus).shift_cm is None
    for name in ("load_cell", "lock", "shift"):
        await sim.set_sensor(name, "OK")

    await sim.override_mass(1180.0)
    assert abs(last(bus).mass_kg - 1180.0) <= cfg.payload.weight_accuracy_kg

    # A jammed release never finishes.
    await sim.set_release_jam(True)
    await command(bus, "RELEASE")
    await advance(bus.clock, 60.0, step=1.0)
    assert last(bus).release_done is False


async def test_GEN_004_lock_holds_without_controller(bus, sim, cfg):
    await loaded(bus, cfg)
    await command(bus, "LOCK")
    await advance(bus.clock, cfg.payload.secure_time_s)
    # The controller is gone: no more commands. Faults and time do not open it.
    await sim.inject_shift(5.0)
    await sim.set_sensor("load_cell", "FAULT")
    await advance(bus.clock, 600.0, step=10.0)
    assert sim.locked is True
    assert last(bus).locked is True


async def test_readings_at_1_hz(bus, sim, cfg):
    bus.clear()
    await advance(bus.clock, 5.0, step=0.5)
    assert len(bus.sent("sim.reading")) == 5 * cfg.timing.status_rate_hz


async def test_unknown_sensor_fails(sim):
    with pytest.raises(ValueError):
        await sim.set_sensor("gyro", "FAULT")


def test_startup_fails_if_noise_not_below_accuracy(cfg):
    bad = cfg.model_copy(
        update={"payload": cfg.payload.model_copy(update={"sim_noise_kg": 0.5})}
    )
    bus = FakeBus("vehicle")
    with pytest.raises(ValueError, match="sim_noise_kg"):
        PayloadSimulator(bus, bus.clock, bad, bus.log)
