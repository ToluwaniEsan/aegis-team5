import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MOCK_INTERVAL_MS } from '../config';
import { fixtures, startMockFeed } from './mock';

describe('C1 mock playback', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it('emits immediately, advances every interval, and loops in order', () => {
    const receive = vi.fn();
    const feed = startMockFeed(receive);
    expect(receive).toHaveBeenCalledTimes(1);
    expect(receive).toHaveBeenLastCalledWith(fixtures.idle, 'idle');
    vi.advanceTimersByTime(MOCK_INTERVAL_MS - 1);
    expect(receive).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1);
    expect(receive).toHaveBeenLastCalledWith(fixtures.travelling, 'travelling');
    vi.advanceTimersByTime(MOCK_INTERVAL_MS);
    expect(receive).toHaveBeenLastCalledWith(fixtures.fault_shift, 'fault_shift');
    vi.advanceTimersByTime(MOCK_INTERVAL_MS);
    expect(receive).toHaveBeenLastCalledWith(fixtures.idle, 'idle');
    feed.stop();
  });
  it('selects immediately, continues from that fixture, and stops cleanly', () => {
    const receive = vi.fn();
    const feed = startMockFeed(receive);
    feed.select('fault_shift');
    expect(receive).toHaveBeenLastCalledWith(fixtures.fault_shift, 'fault_shift');
    vi.advanceTimersByTime(MOCK_INTERVAL_MS);
    expect(receive).toHaveBeenLastCalledWith(fixtures.idle, 'idle');
    feed.stop();
    const count = receive.mock.calls.length;
    vi.advanceTimersByTime(MOCK_INTERVAL_MS * 4);
    expect(receive).toHaveBeenCalledTimes(count);
    expect(vi.getTimerCount()).toBe(0);
  });
});
