import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { MockFeed, useMockSnapshot } from './MockFeed';

function SnapshotProbe() {
  const snapshot = useMockSnapshot();
  return <output>{snapshot?.payload.state}:{snapshot?.payload.shift_cm}</output>;
}

afterEach(() => { cleanup(); vi.useRealTimers(); });

it('C1 selects the requested fixture and cleans up on unmount', () => {
  vi.useFakeTimers();
  const view = render(<MockFeed><SnapshotProbe /></MockFeed>);
  expect(screen.getByText('EMPTY:')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Fixture'), { target: { value: 'fault_shift' } });
  expect(screen.getByText('TRAVELLING:3.1')).toBeTruthy();
  view.unmount();
  expect(vi.getTimerCount()).toBe(0);
});
