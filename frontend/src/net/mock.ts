import type { Snapshot } from '../contracts/ui';
import { MOCK_INTERVAL_MS } from '../config';
import { idle, travelling, fault_shift } from '../mock/fixtures.generated';

export const fixtures = { idle, travelling, fault_shift };
export type FixtureName = keyof typeof fixtures;
export const fixtureNames: FixtureName[] = ['idle', 'travelling', 'fault_shift'];

export function startMockFeed(onSnapshot: (snapshot: Snapshot, name: FixtureName) => void) {
  let index = 0;
  const emit = () => onSnapshot(fixtures[fixtureNames[index]], fixtureNames[index]);
  emit();
  const timer = setInterval(() => {
    index = (index + 1) % fixtureNames.length;
    emit();
  }, MOCK_INTERVAL_MS);
  return {
    select(name: FixtureName) {
      index = fixtureNames.indexOf(name);
      emit();
    },
    stop() { clearInterval(timer); },
  };
}
