import { describe, expect, it } from 'vitest';
import type { Snapshot } from '../contracts/ui';
import idleJson from './fixtures/idle.json';
import travellingJson from './fixtures/travelling.json';
import faultShiftJson from './fixtures/fault_shift.json';
import { idle, travelling, fault_shift } from './fixtures.generated';

// Generated literal values are checked against Snapshot by tsc, without casts.
const checkedFixtures: Snapshot[] = [idle, travelling, fault_shift];

describe('C1 fixtures', () => {
  it('uses the current JSON files as the type-checked fixtures', () => {
    expect(checkedFixtures).toEqual([idleJson, travellingJson, faultShiftJson]);
  });
  it('represents idle, travel, and the payload shift fault in order', () => {
    expect(idle.payload.state).toBe('EMPTY');
    expect(idle.mission.active).toBeNull();
    expect(travelling.payload.state).toBe('TRAVELLING');
    expect(travelling.nav.moving).toBe(true);
    expect(fault_shift.payload.secured).toBe(false);
    expect(fault_shift.payload.shift_cm).toBeGreaterThan(fault_shift.limits.unsecured_shift_cm);
    expect(fault_shift.alerts.some((alert) => alert.code === 'PAYLOAD_SHIFT' && alert.active)).toBe(true);
  });
});
