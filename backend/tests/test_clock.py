"""Task A1: the clock."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone

import pytest

from aegis.common.clock import Clock, ManualClock, RealClock

START = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)


async def _settle() -> None:
    """Let woken tasks run."""
    for _ in range(5):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_five_second_sleep_resolves_on_advance_5_not_4_9():
    clock = ManualClock(START)
    task = asyncio.create_task(clock.sleep(5))
    await _settle()

    clock.advance(4.9)
    await _settle()
    assert not task.done()

    clock.advance(0.1)
    await _settle()
    assert task.done()


@pytest.mark.asyncio
async def test_single_advance_of_exactly_5_resolves():
    clock = ManualClock(START)
    task = asyncio.create_task(clock.sleep(5))
    await _settle()
    clock.advance(5)
    await _settle()
    assert task.done()


@pytest.mark.asyncio
async def test_two_sleeps_resolve_in_deadline_order():
    clock = ManualClock(START)
    order: list[str] = []

    async def sleeper(name: str, seconds: float) -> None:
        await clock.sleep(seconds)
        order.append(name)

    # Started long-first, so start order and deadline order differ.
    asyncio.create_task(sleeper("long", 3))
    asyncio.create_task(sleeper("short", 1))
    await _settle()

    clock.advance(10)
    await _settle()
    assert order == ["short", "long"]


@pytest.mark.asyncio
async def test_equal_deadlines_resolve_in_start_order():
    clock = ManualClock(START)
    order: list[int] = []

    async def sleeper(n: int) -> None:
        await clock.sleep(2)
        order.append(n)

    for n in range(3):
        asyncio.create_task(sleeper(n))
    await _settle()
    clock.advance(2)
    await _settle()
    assert order == [0, 1, 2]


@pytest.mark.asyncio
async def test_only_due_sleeps_resolve():
    clock = ManualClock(START)
    early = asyncio.create_task(clock.sleep(1))
    late = asyncio.create_task(clock.sleep(10))
    await _settle()
    clock.advance(5)
    await _settle()
    assert early.done()
    assert not late.done()
    assert clock.pending == 1


@pytest.mark.asyncio
async def test_cancelled_sleep_is_dropped():
    clock = ManualClock(START)
    task = asyncio.create_task(clock.sleep(1))
    await _settle()
    task.cancel()
    await _settle()
    assert clock.pending == 0
    clock.advance(2)  # must not raise on the cancelled future
    await _settle()
    assert task.cancelled()


@pytest.mark.asyncio
async def test_zero_sleep_returns_immediately():
    clock = ManualClock(START)
    await asyncio.wait_for(clock.sleep(0), timeout=1)
    assert clock.pending == 0


def test_advance_moves_now():
    clock = ManualClock(START)
    clock.advance(2.5)
    assert clock.now() == START + timedelta(seconds=2.5)


def test_advance_backwards_fails():
    with pytest.raises(ValueError):
        ManualClock(START).advance(-1)


def test_naive_start_fails():
    with pytest.raises(ValueError):
        ManualClock(datetime(2026, 11, 19, 12, 0, 0))


def test_manual_clock_now_is_always_utc():
    other_zone = timezone(timedelta(hours=-6))
    clock = ManualClock(datetime(2026, 11, 19, 6, 0, 0, tzinfo=other_zone))
    assert clock.now().utcoffset() == timedelta(0)
    assert clock.now() == START
    clock.advance(1)
    assert clock.now().utcoffset() == timedelta(0)


def test_real_clock_now_is_utc_and_aware():
    now = RealClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


@pytest.mark.asyncio
async def test_real_clock_sleep_zero_returns():
    await asyncio.wait_for(RealClock().sleep(0), timeout=1)


def test_both_clocks_satisfy_the_protocol():
    clocks: list[Clock] = [RealClock(), ManualClock(START)]
    for clock in clocks:
        assert callable(clock.now)
        assert callable(clock.sleep)
