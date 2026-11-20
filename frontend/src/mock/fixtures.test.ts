import { describe, expect, it } from "vitest";
import type { Snapshot } from "../contracts/ui";
import * as generated from "./fixtures.generated";
import { fixtures, fixtureNames } from "../net/mock";
import idleJson from "./fixtures/idle.json";
import assignedJson from "./fixtures/assigned.json";
import securedJson from "./fixtures/secured.json";
import travellingJson from "./fixtures/travelling.json";
import degradedJson from "./fixtures/degraded.json";
import lostJson from "./fixtures/link_lost.json";
import blockedJson from "./fixtures/route_blocked.json";
import queuedJson from "./fixtures/queued.json";
import shiftJson from "./fixtures/fault_shift.json";
import estopJson from "./fixtures/estop_held.json";
import destinationJson from "./fixtures/at_destination.json";
import deliveredJson from "./fixtures/delivered.json";

// Generated literal values are checked against Snapshot by tsc, without casts.
const checked: Snapshot[] = [
  generated.idle,
  generated.assigned,
  generated.secured,
  generated.travelling,
  generated.degraded,
  generated.link_lost,
  generated.route_blocked,
  generated.queued,
  generated.fault_shift,
  generated.estop_held,
  generated.at_destination,
  generated.delivered,
];

describe("B13 captured snapshots", () => {
  it("test_GEN_002_typechecks_and_replays_all_twelve_json_captures", () => {
    expect(checked).toEqual([
      idleJson,
      assignedJson,
      securedJson,
      travellingJson,
      degradedJson,
      lostJson,
      blockedJson,
      queuedJson,
      shiftJson,
      estopJson,
      destinationJson,
      deliveredJson,
    ]);
    expect(fixtureNames).toHaveLength(12);
    expect(fixtureNames.map((name) => fixtures[name])).toEqual(checked);
  });
  it("test_OI_005_captures_real_named_scenarios", () => {
    expect(generated.idle.payload.updated_at).not.toBeNull();
    expect(generated.idle.mission.active).toBeNull();
    expect(generated.assigned.mission.active).not.toBeNull();
    expect(generated.secured.payload.state).toBe("SECURED");
    expect(generated.travelling.nav.moving).toBe(true);
    expect(generated.degraded.link.state).toBe("DEGRADED");
    expect(generated.link_lost.link.state).toBe("LOST");
    expect(generated.route_blocked.nav.blocked).not.toBeNull();
    expect(generated.queued.mission.queue).toHaveLength(1);
    expect(generated.fault_shift.payload.shift_cm).toBeGreaterThan(
      generated.fault_shift.limits.unsecured_shift_cm,
    );
    expect(
      generated.fault_shift.alerts.some(
        (alert) => alert.code === "PAYLOAD_SHIFT" && alert.active,
      ),
    ).toBe(true);
    expect(generated.estop_held.payload.state).toBe("HELD");
    expect(generated.estop_held.estop_active).toBe(true);
    expect(generated.at_destination.payload.state).toBe("AT_DESTINATION");
    expect(generated.delivered.delivery).not.toBeNull();
  });
  it("test_AEG_511_and_OI_004_permissions_match_the_captured_scenario", () => {
    for (const snapshot of checked) {
      if (snapshot.payload.departure_permitted) {
        expect(snapshot.payload.state).toBe("SECURED");
        expect(snapshot.payload.secured).toBe(true);
      } else expect(snapshot.payload.departure_reason).toBeTruthy();
      for (const permission of Object.values(snapshot.allowed))
        if (!permission.allowed) expect(permission.reason).toBeTruthy();
      if (snapshot.mission.active)
        expect(snapshot.allowed.start_queued_mission.allowed).toBe(false);
      if (snapshot.mission.active)
        for (const permission of Object.values(snapshot.allowed))
          expect(permission.reason).not.toBe("No active mission");
      if (!snapshot.mission.queue.length)
        expect(snapshot.allowed.remove_queued_mission.allowed).toBe(false);
      if (!snapshot.alerts.some((alert) => !alert.acknowledged))
        expect(snapshot.allowed.ack_fault.allowed).toBe(false);
      else expect(snapshot.allowed.ack_fault.allowed).toBe(true);
    }
    expect(generated.travelling.payload.departure_permitted).toBe(false);
    expect(generated.fault_shift.payload.secured).toBe(false);
  });
});
