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
  it('test_AEG_511_blocks_departure_outside_the_secured_state', () => {
    for (const fixture of checkedFixtures) {
      expect(fixture.payload.departure_permitted).toBe(false);
      expect(fixture.payload.departure_reason).toBeTruthy();
    }
    expect(travelling.payload.departure_reason).toBe('Payload is travelling');
  });
  it('test_OI_004_gives_reasons_consistent_with_the_queue_and_alerts', () => {
    for (const fixture of checkedFixtures) {
      expect(fixture.mission.queue).toHaveLength(0);
      expect(fixture.allowed.start_queued_mission).toMatchObject({ allowed: false, reason: 'Mission queue is empty' });
      expect(fixture.allowed.remove_queued_mission).toMatchObject({ allowed: false, reason: 'Mission queue is empty' });
      if (fixture.mission.active) {
        for (const permission of Object.values(fixture.allowed)) {
          expect(permission.reason).not.toBe('No active mission');
        }
      }
      if (!fixture.alerts.some((alert) => !alert.acknowledged)) {
        expect(fixture.allowed.ack_fault).toMatchObject({ allowed: false, reason: 'No unacknowledged alerts' });
      } else {
        expect(fixture.allowed.ack_fault).toMatchObject({ allowed: true, reason: null });
      }
      for (const permission of Object.values(fixture.allowed)) {
        if (!permission.allowed) expect(permission.reason).toBeTruthy();
      }
    }
    expect(idle.allowed.release.reason).toBe('Vehicle is not at the destination');
    expect(travelling.allowed.release.reason).toBe('Vehicle is moving');
    expect(fault_shift.allowed.release.reason).toBe('Vehicle is moving');
  });
});
