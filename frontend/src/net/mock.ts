import type { Snapshot } from "../contracts/ui";
import { MOCK_INTERVAL_MS } from "../config";
import {
  idle,
  assigned,
  secured,
  travelling,
  degraded,
  link_lost,
  route_blocked,
  queued,
  fault_shift,
  estop_held,
  at_destination,
  delivered,
} from "../mock/fixtures.generated";

export const fixtures = {
  idle,
  assigned,
  secured,
  travelling,
  degraded,
  link_lost,
  route_blocked,
  queued,
  fault_shift,
  estop_held,
  at_destination,
  delivered,
};
export type FixtureName = keyof typeof fixtures;
export const fixtureNames: FixtureName[] = [
  "idle",
  "assigned",
  "secured",
  "travelling",
  "degraded",
  "link_lost",
  "route_blocked",
  "queued",
  "fault_shift",
  "estop_held",
  "at_destination",
  "delivered",
];

export function startMockFeed(
  onSnapshot: (snapshot: Snapshot, name: FixtureName) => void,
) {
  let index = 0;
  const emit = () =>
    onSnapshot(fixtures[fixtureNames[index]], fixtureNames[index]);
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
    stop() {
      clearInterval(timer);
    },
  };
}
