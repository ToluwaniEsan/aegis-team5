// Generated from fixtures/*.json by scripts/generate-fixtures.mjs.
import type { Snapshot } from '../contracts/ui';

export const idle: Snapshot = {
  "kind": "snapshot",
  "seq": 1,
  "server_time": "2026-11-19T15:04:05.000Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 %",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "3 of 3 OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "EMPTY",
    "held_from": null,
    "payload_id": null,
    "secured": false,
    "locked": false,
    "mass_kg": null,
    "shift_cm": null,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "No payload"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "origin": null,
    "destination": null,
    "position": null,
    "route": [],
    "progress_pct": null,
    "moving": false,
    "speed_mps": 0,
    "eta_s": null,
    "blocked": null
  },
  "mission": {
    "active": null,
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001"
    }
  },
  "commands": [],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": false,
      "reason": "No active mission",
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": false,
      "reason": "No active mission",
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": false,
      "reason": "No active mission",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "No active mission",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Vehicle is not at the destination",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No unacknowledged alerts",
      "needs_confirmation": false
    },
    "estop": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    }
  },
  "alerts": [],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "id": "FOB_ALPHA",
      "name": "FOB Alpha",
      "lat": 34.7201,
      "lon": -86.6402
    },
    {
      "id": "OP_BRAVO",
      "name": "Outpost Bravo",
      "lat": 34.7612,
      "lon": -86.581
    },
    {
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie",
      "lat": 34.6905,
      "lon": -86.5521
    },
    {
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta",
      "lat": 34.742,
      "lon": -86.695
    }
  ],
  "limits": {
    "mass_min_kg": 226.8,
    "mass_max_kg": 1000,
    "dims_max_cm": {
      "length": 60,
      "width": 40,
      "height": 40
    },
    "stale_after_s": 5,
    "unsecured_shift_cm": 2,
    "release_energy_wh_max": 5
  }
};

export const travelling: Snapshot = {
  "kind": "snapshot",
  "seq": 2,
  "server_time": "2026-11-19T15:04:05.000Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 %",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "3 of 3 OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 742,
    "shift_cm": 0.2,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is travelling"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "origin": {
      "id": "FOB_ALPHA",
      "name": "FOB Alpha",
      "lat": 34.7201,
      "lon": -86.6402
    },
    "destination": {
      "id": "OP_BRAVO",
      "name": "Outpost Bravo",
      "lat": 34.7612,
      "lon": -86.581
    },
    "position": {
      "lat": 34.7398,
      "lon": -86.6105
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 46,
    "moving": true,
    "speed_mps": 8,
    "eta_s": 460,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "id": "FOB_ALPHA",
        "name": "FOB Alpha",
        "lat": 34.7201,
        "lon": -86.6402
      },
      "destination": {
        "id": "OP_BRAVO",
        "name": "Outpost Bravo",
        "lat": 34.7612,
        "lon": -86.581
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 742,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.000Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Only before departure",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Vehicle is moving",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No unacknowledged alerts",
      "needs_confirmation": false
    },
    "estop": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    }
  },
  "alerts": [],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "id": "FOB_ALPHA",
      "name": "FOB Alpha",
      "lat": 34.7201,
      "lon": -86.6402
    },
    {
      "id": "OP_BRAVO",
      "name": "Outpost Bravo",
      "lat": 34.7612,
      "lon": -86.581
    },
    {
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie",
      "lat": 34.6905,
      "lon": -86.5521
    },
    {
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta",
      "lat": 34.742,
      "lon": -86.695
    }
  ],
  "limits": {
    "mass_min_kg": 226.8,
    "mass_max_kg": 1000,
    "dims_max_cm": {
      "length": 60,
      "width": 40,
      "height": 40
    },
    "stale_after_s": 5,
    "unsecured_shift_cm": 2,
    "release_energy_wh_max": 5
  }
};

export const fault_shift: Snapshot = {
  "kind": "snapshot",
  "seq": 3,
  "server_time": "2026-11-19T15:04:05.000Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "DEGRADED",
    "subsystems": [
      {
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 %",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "OK",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      },
      {
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "WARN",
        "detail": "Payload shift",
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0,
        "stale": false
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": false,
    "locked": true,
    "mass_kg": 742,
    "shift_cm": 3.1,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Shift over limit"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0,
    "stale": false,
    "origin": {
      "id": "FOB_ALPHA",
      "name": "FOB Alpha",
      "lat": 34.7201,
      "lon": -86.6402
    },
    "destination": {
      "id": "OP_BRAVO",
      "name": "Outpost Bravo",
      "lat": 34.7612,
      "lon": -86.581
    },
    "position": {
      "lat": 34.7398,
      "lon": -86.6105
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 46,
    "moving": true,
    "speed_mps": 8,
    "eta_s": 460,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "id": "FOB_ALPHA",
        "name": "FOB Alpha",
        "lat": 34.7201,
        "lon": -86.6402
      },
      "destination": {
        "id": "OP_BRAVO",
        "name": "Outpost Bravo",
        "lat": 34.7612,
        "lon": -86.581
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 742,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.000Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "Mission queue is empty",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Only before departure",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Vehicle is moving",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "estop": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    }
  },
  "alerts": [
    {
      "alert_id": "3f64ee77-14ba-48ea-b827-18875c8c7e4c",
      "code": "PAYLOAD_SHIFT",
      "severity": "WARNING",
      "title": "Payload shifted 3.1 cm",
      "source": "Payload",
      "recommended_action": "Reduce speed and inspect the payload at the next stop",
      "raised_at": "2026-11-19T15:04:05.000Z",
      "acknowledged": false,
      "active": true
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "id": "FOB_ALPHA",
      "name": "FOB Alpha",
      "lat": 34.7201,
      "lon": -86.6402
    },
    {
      "id": "OP_BRAVO",
      "name": "Outpost Bravo",
      "lat": 34.7612,
      "lon": -86.581
    },
    {
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie",
      "lat": 34.6905,
      "lon": -86.5521
    },
    {
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta",
      "lat": 34.742,
      "lon": -86.695
    }
  ],
  "limits": {
    "mass_min_kg": 226.8,
    "mass_max_kg": 1000,
    "dims_max_cm": {
      "length": 60,
      "width": 40,
      "height": 40
    },
    "stale_after_s": 5,
    "unsecured_shift_cm": 2,
    "release_energy_wh_max": 5
  }
};
