// Generated from fixtures/*.json by scripts/generate-fixtures.mjs.
import type { Snapshot } from '../contracts/ui';

export const idle: Snapshot = {
  "kind": "snapshot",
  "seq": 3,
  "server_time": "2026-11-19T15:04:05.100Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "EMPTY",
    "held_from": null,
    "payload_id": null,
    "secured": false,
    "locked": false,
    "mass_kg": 0,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "No mission assigned"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "origin": null,
    "destination": null,
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [],
    "progress_pct": 0,
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
      "reason": "No mission in the queue",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Not at the destination",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No alert to acknowledge",
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
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const assigned: Snapshot = {
  "kind": "snapshot",
  "seq": 5,
  "server_time": "2026-11-19T15:04:05.100Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:05.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "EMPTY",
    "held_from": null,
    "payload_id": null,
    "secured": false,
    "locked": false,
    "mass_kg": 0,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "No mission assigned"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:05.000Z",
    "age_s": 0.1,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [],
    "progress_pct": 0,
    "moving": false,
    "speed_mps": 0,
    "eta_s": null,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ASSIGNED",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 742,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "SENT",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:05.100Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Not possible while the payload is EMPTY",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Not at the destination",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No alert to acknowledge",
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
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const secured: Snapshot = {
  "kind": "snapshot",
  "seq": 61,
  "server_time": "2026-11-19T15:04:10.400Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:10.000Z",
    "age_s": 0.4,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:10.300Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:10.300Z",
    "age_s": 0.1,
    "stale": false,
    "state": "SECURED",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 741.9535385765766,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": true,
    "departure_reason": null
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:10.000Z",
    "age_s": 0.4,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.723836363636366,
        "lon": -86.63481818181818
      },
      {
        "lat": 34.72757272727273,
        "lon": -86.62943636363636
      },
      {
        "lat": 34.73130909090909,
        "lon": -86.62405454545454
      },
      {
        "lat": 34.73504545454546,
        "lon": -86.61867272727272
      },
      {
        "lat": 34.73878181818182,
        "lon": -86.6132909090909
      },
      {
        "lat": 34.742518181818184,
        "lon": -86.60790909090909
      },
      {
        "lat": 34.74625454545455,
        "lon": -86.60252727272727
      },
      {
        "lat": 34.74999090909091,
        "lon": -86.59714545454545
      },
      {
        "lat": 34.753727272727275,
        "lon": -86.59176363636364
      },
      {
        "lat": 34.75746363636364,
        "lon": -86.58638181818182
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 0,
    "moving": false,
    "speed_mps": 0,
    "eta_s": 88.51769394477881,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ASSIGNED",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 742,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": false,
      "reason": "Not possible while the payload is SECURED",
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Not at the destination",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No alert to acknowledge",
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
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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
  "seq": 80,
  "server_time": "2026-11-19T15:04:11.900Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:11.000Z",
    "age_s": 0.9,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:11.700Z",
        "age_s": 0.2,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:11.800Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:11.800Z",
    "age_s": 0.1,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 809.9728962443943,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:11.700Z",
    "age_s": 0.2,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.723836363636366,
        "lon": -86.63481818181818
      },
      {
        "lat": 34.72757272727273,
        "lon": -86.62943636363636
      },
      {
        "lat": 34.73130909090909,
        "lon": -86.62405454545454
      },
      {
        "lat": 34.73504545454546,
        "lon": -86.61867272727272
      },
      {
        "lat": 34.73878181818182,
        "lon": -86.6132909090909
      },
      {
        "lat": 34.742518181818184,
        "lon": -86.60790909090909
      },
      {
        "lat": 34.74625454545455,
        "lon": -86.60252727272727
      },
      {
        "lat": 34.74999090909091,
        "lon": -86.59714545454545
      },
      {
        "lat": 34.753727272727275,
        "lon": -86.59176363636364
      },
      {
        "lat": 34.75746363636364,
        "lon": -86.58638181818182
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 0,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 88.51769394477881,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
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
      "reason": "Not possible while the payload is TRAVELLING",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Vehicle is moving",
      "needs_confirmation": true
    },
    "ack_fault": {
      "allowed": false,
      "reason": "No alert to acknowledge",
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
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const degraded: Snapshot = {
  "kind": "snapshot",
  "seq": 83,
  "server_time": "2026-11-19T15:04:11.900Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:11.900Z",
    "age_s": 0,
    "stale": false,
    "state": "DEGRADED",
    "latency_ms": 1500,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "DEGRADED",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:11.700Z",
        "age_s": 0.2,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:11.900Z",
        "age_s": 0,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "WARN",
        "detail": "1500 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:11.800Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:11.800Z",
    "age_s": 0.1,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 809.9728962443943,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:11.700Z",
    "age_s": 0.2,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.723836363636366,
        "lon": -86.63481818181818
      },
      {
        "lat": 34.72757272727273,
        "lon": -86.62943636363636
      },
      {
        "lat": 34.73130909090909,
        "lon": -86.62405454545454
      },
      {
        "lat": 34.73504545454546,
        "lon": -86.61867272727272
      },
      {
        "lat": 34.73878181818182,
        "lon": -86.6132909090909
      },
      {
        "lat": 34.742518181818184,
        "lon": -86.60790909090909
      },
      {
        "lat": 34.74625454545455,
        "lon": -86.60252727272727
      },
      {
        "lat": 34.74999090909091,
        "lon": -86.59714545454545
      },
      {
        "lat": 34.753727272727275,
        "lon": -86.59176363636364
      },
      {
        "lat": 34.75746363636364,
        "lon": -86.58638181818182
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 0,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 88.51769394477881,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
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
      "reason": "Not possible while the payload is TRAVELLING",
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
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": true
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const link_lost: Snapshot = {
  "kind": "snapshot",
  "seq": 149,
  "server_time": "2026-11-19T15:04:18.000Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:18.000Z",
    "age_s": 0,
    "stale": false,
    "state": "LOST",
    "latency_ms": 1500,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "FAULT",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 7,
        "stale": true,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:11.000Z",
        "age_s": 7,
        "stale": true,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:11.700Z",
        "age_s": 6.3,
        "stale": true,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:18.000Z",
        "age_s": 0,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "FAULT",
        "detail": "1500 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:11.800Z",
        "age_s": 6.2,
        "stale": true,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:11.800Z",
    "age_s": 6.2,
    "stale": true,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 809.9728962443943,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:11.700Z",
    "age_s": 6.3,
    "stale": true,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.723836363636366,
        "lon": -86.63481818181818
      },
      {
        "lat": 34.72757272727273,
        "lon": -86.62943636363636
      },
      {
        "lat": 34.73130909090909,
        "lon": -86.62405454545454
      },
      {
        "lat": 34.73504545454546,
        "lon": -86.61867272727272
      },
      {
        "lat": 34.73878181818182,
        "lon": -86.6132909090909
      },
      {
        "lat": 34.742518181818184,
        "lon": -86.60790909090909
      },
      {
        "lat": 34.74625454545455,
        "lon": -86.60252727272727
      },
      {
        "lat": 34.74999090909091,
        "lon": -86.59714545454545
      },
      {
        "lat": 34.753727272727275,
        "lon": -86.59176363636364
      },
      {
        "lat": 34.75746363636364,
        "lon": -86.58638181818182
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 0,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 88.51769394477881,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
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
      "reason": "Not possible while the payload is TRAVELLING",
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
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status, nav.state, power.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const route_blocked: Snapshot = {
  "kind": "snapshot",
  "seq": 255,
  "server_time": "2026-11-19T15:04:28.300Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:28.000Z",
    "age_s": 0.3,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "89.7 % · 53.8 km"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:28.100Z",
        "age_s": 0.2,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:28.000Z",
    "age_s": 0.3,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 809.7427882371663,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:28.100Z",
    "age_s": 0.2,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.727992416628176,
      "lon": -86.6288318475818
    },
    "route": [
      {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      {
        "lat": 34.72892158258627,
        "lon": -86.62238828365503
      },
      {
        "lat": 34.729850748544365,
        "lon": -86.61594471972825
      },
      {
        "lat": 34.730779914502456,
        "lon": -86.60950115580148
      },
      {
        "lat": 34.731709080460554,
        "lon": -86.6030575918747
      },
      {
        "lat": 34.732638246418645,
        "lon": -86.59661402794794
      },
      {
        "lat": 34.73835059713492,
        "lon": -86.59349122235835
      },
      {
        "lat": 34.74406294785119,
        "lon": -86.59036841676877
      },
      {
        "lat": 34.74977529856746,
        "lon": -86.58724561117917
      },
      {
        "lat": 34.75548764928373,
        "lon": -86.58412280558959
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 17.36729262639167,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 80.88514747639177,
    "blocked": {
      "reason": "Bridge out at grid 4471",
      "at": {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      "old_route": [
        {
          "lat": 34.7201,
          "lon": -86.6402
        },
        {
          "lat": 34.723836363636366,
          "lon": -86.63481818181818
        },
        {
          "lat": 34.72757272727273,
          "lon": -86.62943636363636
        },
        {
          "lat": 34.73130909090909,
          "lon": -86.62405454545454
        },
        {
          "lat": 34.73504545454546,
          "lon": -86.61867272727272
        },
        {
          "lat": 34.73878181818182,
          "lon": -86.6132909090909
        },
        {
          "lat": 34.742518181818184,
          "lon": -86.60790909090909
        },
        {
          "lat": 34.74625454545455,
          "lon": -86.60252727272727
        },
        {
          "lat": 34.74999090909091,
          "lon": -86.59714545454545
        },
        {
          "lat": 34.753727272727275,
          "lon": -86.59176363636364
        },
        {
          "lat": 34.75746363636364,
          "lon": -86.58638181818182
        },
        {
          "lat": 34.7612,
          "lon": -86.581
        }
      ],
      "new_eta_s": 80.88514747639177,
      "since": "2026-11-19T15:04:28.100Z"
    }
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-002",
      "payload_id": "PAY-2026-002"
    }
  },
  "commands": [
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
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
      "reason": "Not possible while the payload is TRAVELLING",
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
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "5a8c612d-67b4-44f0-a5db-5e8c011c1788",
      "code": "ROUTE_BLOCKED",
      "severity": "CAUTION",
      "title": "Route blocked: Bridge out at grid 4471",
      "source": "Team 2 Navigation",
      "recommended_action": "Review the new route and arrival time",
      "raised_at": "2026-11-19T15:04:28.300Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const queued: Snapshot = {
  "kind": "snapshot",
  "seq": 258,
  "server_time": "2026-11-19T15:04:28.300Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:28.000Z",
    "age_s": 0.3,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "89.7 % · 53.8 km"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:28.100Z",
        "age_s": 0.2,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.3,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:28.000Z",
    "age_s": 0.3,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 809.7427882371663,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:28.100Z",
    "age_s": 0.2,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.727992416628176,
      "lon": -86.6288318475818
    },
    "route": [
      {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      {
        "lat": 34.72892158258627,
        "lon": -86.62238828365503
      },
      {
        "lat": 34.729850748544365,
        "lon": -86.61594471972825
      },
      {
        "lat": 34.730779914502456,
        "lon": -86.60950115580148
      },
      {
        "lat": 34.731709080460554,
        "lon": -86.6030575918747
      },
      {
        "lat": 34.732638246418645,
        "lon": -86.59661402794794
      },
      {
        "lat": 34.73835059713492,
        "lon": -86.59349122235835
      },
      {
        "lat": 34.74406294785119,
        "lon": -86.59036841676877
      },
      {
        "lat": 34.74977529856746,
        "lon": -86.58724561117917
      },
      {
        "lat": 34.75548764928373,
        "lon": -86.58412280558959
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 17.36729262639167,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 80.88514747639177,
    "blocked": {
      "reason": "Bridge out at grid 4471",
      "at": {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      "old_route": [
        {
          "lat": 34.7201,
          "lon": -86.6402
        },
        {
          "lat": 34.723836363636366,
          "lon": -86.63481818181818
        },
        {
          "lat": 34.72757272727273,
          "lon": -86.62943636363636
        },
        {
          "lat": 34.73130909090909,
          "lon": -86.62405454545454
        },
        {
          "lat": 34.73504545454546,
          "lon": -86.61867272727272
        },
        {
          "lat": 34.73878181818182,
          "lon": -86.6132909090909
        },
        {
          "lat": 34.742518181818184,
          "lon": -86.60790909090909
        },
        {
          "lat": 34.74625454545455,
          "lon": -86.60252727272727
        },
        {
          "lat": 34.74999090909091,
          "lon": -86.59714545454545
        },
        {
          "lat": 34.753727272727275,
          "lon": -86.59176363636364
        },
        {
          "lat": 34.75746363636364,
          "lon": -86.58638181818182
        },
        {
          "lat": 34.7612,
          "lon": -86.581
        }
      ],
      "new_eta_s": 80.88514747639177,
      "since": "2026-11-19T15:04:28.100Z"
    }
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [
      {
        "mission_id": "MSN-2026-002",
        "payload_id": "PAY-2026-002",
        "status": "QUEUED",
        "origin": {
          "lat": 34.7201,
          "lon": -86.6402,
          "id": "FOB_ALPHA",
          "name": "FOB Alpha"
        },
        "destination": {
          "lat": 34.742,
          "lon": -86.695,
          "id": "LZ_DELTA",
          "name": "Landing Zone Delta"
        },
        "priority": "ROUTINE",
        "declared_mass_kg": 600,
        "dims_cm": {
          "length": 50,
          "width": 30,
          "height": 30
        },
        "prerelease_authorized": false,
        "created_at": "2026-11-19T15:04:28.300Z"
      }
    ],
    "next_ids": {
      "mission_id": "MSN-2026-003",
      "payload_id": "PAY-2026-003"
    }
  },
  "commands": [
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": true,
      "reason": null,
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
      "reason": "Not possible while the payload is TRAVELLING",
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
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "5a8c612d-67b4-44f0-a5db-5e8c011c1788",
      "code": "ROUTE_BLOCKED",
      "severity": "CAUTION",
      "title": "Route blocked: Bridge out at grid 4471",
      "source": "Team 2 Navigation",
      "recommended_action": "Review the new route and arrival time",
      "raised_at": "2026-11-19T15:04:28.300Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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
  "seq": 262,
  "server_time": "2026-11-19T15:04:28.500Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:28.000Z",
    "age_s": 0.5,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.5,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "89.7 % · 53.8 km"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.5,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:28.100Z",
        "age_s": 0.4,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "80 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:28.000Z",
        "age_s": 0.5,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:28.400Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:28.400Z",
    "age_s": 0.1,
    "stale": false,
    "state": "TRAVELLING",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": false,
    "locked": true,
    "mass_kg": 809.9707521254335,
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
    "departure_reason": "Payload is TRAVELLING"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:28.100Z",
    "age_s": 0.4,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.727992416628176,
      "lon": -86.6288318475818
    },
    "route": [
      {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      {
        "lat": 34.72892158258627,
        "lon": -86.62238828365503
      },
      {
        "lat": 34.729850748544365,
        "lon": -86.61594471972825
      },
      {
        "lat": 34.730779914502456,
        "lon": -86.60950115580148
      },
      {
        "lat": 34.731709080460554,
        "lon": -86.6030575918747
      },
      {
        "lat": 34.732638246418645,
        "lon": -86.59661402794794
      },
      {
        "lat": 34.73835059713492,
        "lon": -86.59349122235835
      },
      {
        "lat": 34.74406294785119,
        "lon": -86.59036841676877
      },
      {
        "lat": 34.74977529856746,
        "lon": -86.58724561117917
      },
      {
        "lat": 34.75548764928373,
        "lon": -86.58412280558959
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 17.36729262639167,
    "moving": true,
    "speed_mps": 80,
    "eta_s": 80.88514747639177,
    "blocked": {
      "reason": "Bridge out at grid 4471",
      "at": {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      "old_route": [
        {
          "lat": 34.7201,
          "lon": -86.6402
        },
        {
          "lat": 34.723836363636366,
          "lon": -86.63481818181818
        },
        {
          "lat": 34.72757272727273,
          "lon": -86.62943636363636
        },
        {
          "lat": 34.73130909090909,
          "lon": -86.62405454545454
        },
        {
          "lat": 34.73504545454546,
          "lon": -86.61867272727272
        },
        {
          "lat": 34.73878181818182,
          "lon": -86.6132909090909
        },
        {
          "lat": 34.742518181818184,
          "lon": -86.60790909090909
        },
        {
          "lat": 34.74625454545455,
          "lon": -86.60252727272727
        },
        {
          "lat": 34.74999090909091,
          "lon": -86.59714545454545
        },
        {
          "lat": 34.753727272727275,
          "lon": -86.59176363636364
        },
        {
          "lat": 34.75746363636364,
          "lon": -86.58638181818182
        },
        {
          "lat": 34.7612,
          "lon": -86.581
        }
      ],
      "new_eta_s": 80.88514747639177,
      "since": "2026-11-19T15:04:28.100Z"
    }
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [
      {
        "mission_id": "MSN-2026-002",
        "payload_id": "PAY-2026-002",
        "status": "QUEUED",
        "origin": {
          "lat": 34.7201,
          "lon": -86.6402,
          "id": "FOB_ALPHA",
          "name": "FOB Alpha"
        },
        "destination": {
          "lat": 34.742,
          "lon": -86.695,
          "id": "LZ_DELTA",
          "name": "Landing Zone Delta"
        },
        "priority": "ROUTINE",
        "declared_mass_kg": 600,
        "dims_cm": {
          "length": 50,
          "width": 30,
          "height": 30
        },
        "prerelease_authorized": false,
        "created_at": "2026-11-19T15:04:28.300Z"
      }
    ],
    "next_ids": {
      "mission_id": "MSN-2026-003",
      "payload_id": "PAY-2026-003"
    }
  },
  "commands": [
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": true,
      "reason": null,
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
      "reason": "Not possible while the payload is TRAVELLING",
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
      "alert_id": "7e9af2f7-3b0d-458b-bd3b-1d7a13a8cdcf",
      "code": "PAYLOAD_SHIFT",
      "severity": "WARNING",
      "title": "Payload shifted 3.1 cm",
      "source": "Payload",
      "recommended_action": "Reduce speed and inspect the payload at the next stop",
      "raised_at": "2026-11-19T15:04:28.400Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "5a8c612d-67b4-44f0-a5db-5e8c011c1788",
      "code": "ROUTE_BLOCKED",
      "severity": "CAUTION",
      "title": "Route blocked: Bridge out at grid 4471",
      "source": "Team 2 Navigation",
      "recommended_action": "Review the new route and arrival time",
      "raised_at": "2026-11-19T15:04:28.300Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const estop_held: Snapshot = {
  "kind": "snapshot",
  "seq": 65,
  "server_time": "2026-11-19T15:04:10.900Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:10.000Z",
    "age_s": 0.9,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "92 % · 55.2 km"
      },
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:10.800Z",
        "age_s": 0.1,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:10.000Z",
        "age_s": 0.9,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:10.800Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:10.800Z",
    "age_s": 0.1,
    "stale": false,
    "state": "HELD",
    "held_from": "TRAVELLING",
    "payload_id": "PAY-2026-003",
    "secured": true,
    "locked": true,
    "mass_kg": 741.923331720751,
    "shift_cm": 0,
    "release_energy_wh": null,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Payload is held: acknowledge the fault first"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:10.800Z",
    "age_s": 0.1,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7201,
      "lon": -86.6402
    },
    "route": [
      {
        "lat": 34.7201,
        "lon": -86.6402
      },
      {
        "lat": 34.723836363636366,
        "lon": -86.63481818181818
      },
      {
        "lat": 34.72757272727273,
        "lon": -86.62943636363636
      },
      {
        "lat": 34.73130909090909,
        "lon": -86.62405454545454
      },
      {
        "lat": 34.73504545454546,
        "lon": -86.61867272727272
      },
      {
        "lat": 34.73878181818182,
        "lon": -86.6132909090909
      },
      {
        "lat": 34.742518181818184,
        "lon": -86.60790909090909
      },
      {
        "lat": 34.74625454545455,
        "lon": -86.60252727272727
      },
      {
        "lat": 34.74999090909091,
        "lon": -86.59714545454545
      },
      {
        "lat": 34.753727272727275,
        "lon": -86.59176363636364
      },
      {
        "lat": 34.75746363636364,
        "lon": -86.58638181818182
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 0,
    "moving": false,
    "speed_mps": 0,
    "eta_s": 88.51769394477881,
    "blocked": null
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-003",
      "payload_id": "PAY-2026-003",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 742,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [],
    "next_ids": {
      "mission_id": "MSN-2026-004",
      "payload_id": "PAY-2026-004"
    }
  },
  "commands": [
    {
      "command_id": "26a1032b-4c12-4bdc-a132-87f0f8ba4c88",
      "command": "estop",
      "label": "Estop",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.600Z",
      "updated_at": "2026-11-19T15:04:10.900Z"
    },
    {
      "command_id": "c0f6bffe-4e30-4a49-b725-63cb5850232a",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": false,
      "reason": "No mission in the queue",
      "needs_confirmation": false
    },
    "abort": {
      "allowed": false,
      "reason": "Payload is held: acknowledge the fault first",
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": false,
      "reason": "Payload is held: acknowledge the fault first",
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": false,
      "reason": "Payload is held: acknowledge the fault first",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Payload is held: acknowledge the fault first",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Payload is held: acknowledge the fault first",
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
      "alert_id": "de32d4a2-3a81-48ae-afc0-a7fadf20ab8a",
      "code": "ESTOP_ACTIVE",
      "severity": "CRITICAL",
      "title": "Emergency stop pressed",
      "source": "Payload",
      "recommended_action": "Check the vehicle is safe, then acknowledge to clear the stop",
      "raised_at": "2026-11-19T15:04:10.800Z",
      "acknowledged": false,
      "active": true
    }
  ],
  "estop_active": true,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const at_destination: Snapshot = {
  "kind": "snapshot",
  "seq": 284,
  "server_time": "2026-11-19T15:04:30.100Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:30.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:30.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "89.6 % · 53.8 km"
      },
      {
        "updated_at": "2026-11-19T15:04:30.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:30.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:30.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:30.000Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:30.000Z",
    "age_s": 0.1,
    "stale": false,
    "state": "AT_DESTINATION",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": true,
    "locked": true,
    "mass_kg": 810.0926517840074,
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
    "departure_reason": "Payload is AT_DESTINATION"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:30.000Z",
    "age_s": 0.1,
    "stale": false,
    "origin": {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "position": {
      "lat": 34.7612,
      "lon": -86.581
    },
    "route": [
      {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      {
        "lat": 34.72892158258627,
        "lon": -86.62238828365503
      },
      {
        "lat": 34.729850748544365,
        "lon": -86.61594471972825
      },
      {
        "lat": 34.730779914502456,
        "lon": -86.60950115580148
      },
      {
        "lat": 34.731709080460554,
        "lon": -86.6030575918747
      },
      {
        "lat": 34.732638246418645,
        "lon": -86.59661402794794
      },
      {
        "lat": 34.73835059713492,
        "lon": -86.59349122235835
      },
      {
        "lat": 34.74406294785119,
        "lon": -86.59036841676877
      },
      {
        "lat": 34.74977529856746,
        "lon": -86.58724561117917
      },
      {
        "lat": 34.75548764928373,
        "lon": -86.58412280558959
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 100,
    "moving": false,
    "speed_mps": 0,
    "eta_s": 0,
    "blocked": {
      "reason": "Bridge out at grid 4471",
      "at": {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      "old_route": [
        {
          "lat": 34.7201,
          "lon": -86.6402
        },
        {
          "lat": 34.723836363636366,
          "lon": -86.63481818181818
        },
        {
          "lat": 34.72757272727273,
          "lon": -86.62943636363636
        },
        {
          "lat": 34.73130909090909,
          "lon": -86.62405454545454
        },
        {
          "lat": 34.73504545454546,
          "lon": -86.61867272727272
        },
        {
          "lat": 34.73878181818182,
          "lon": -86.6132909090909
        },
        {
          "lat": 34.742518181818184,
          "lon": -86.60790909090909
        },
        {
          "lat": 34.74625454545455,
          "lon": -86.60252727272727
        },
        {
          "lat": 34.74999090909091,
          "lon": -86.59714545454545
        },
        {
          "lat": 34.753727272727275,
          "lon": -86.59176363636364
        },
        {
          "lat": 34.75746363636364,
          "lon": -86.58638181818182
        },
        {
          "lat": 34.7612,
          "lon": -86.581
        }
      ],
      "new_eta_s": 80.88514747639177,
      "since": "2026-11-19T15:04:28.100Z"
    }
  },
  "mission": {
    "active": {
      "mission_id": "MSN-2026-001",
      "payload_id": "PAY-2026-001",
      "status": "ACTIVE",
      "origin": {
        "lat": 34.7201,
        "lon": -86.6402,
        "id": "FOB_ALPHA",
        "name": "FOB Alpha"
      },
      "destination": {
        "lat": 34.7612,
        "lon": -86.581,
        "id": "OP_BRAVO",
        "name": "Outpost Bravo"
      },
      "priority": "PRIORITY",
      "declared_mass_kg": 810,
      "dims_cm": {
        "length": 58,
        "width": 38,
        "height": 36
      },
      "prerelease_authorized": false,
      "created_at": "2026-11-19T15:04:05.100Z"
    },
    "queue": [
      {
        "mission_id": "MSN-2026-002",
        "payload_id": "PAY-2026-002",
        "status": "QUEUED",
        "origin": {
          "lat": 34.7201,
          "lon": -86.6402,
          "id": "FOB_ALPHA",
          "name": "FOB Alpha"
        },
        "destination": {
          "lat": 34.742,
          "lon": -86.695,
          "id": "LZ_DELTA",
          "name": "Landing Zone Delta"
        },
        "priority": "ROUTINE",
        "declared_mass_kg": 600,
        "dims_cm": {
          "length": 50,
          "width": 30,
          "height": 30
        },
        "prerelease_authorized": false,
        "created_at": "2026-11-19T15:04:28.300Z"
      }
    ],
    "next_ids": {
      "mission_id": "MSN-2026-003",
      "payload_id": "PAY-2026-003"
    }
  },
  "commands": [
    {
      "command_id": "107c832d-fef1-45f7-bbbd-b995e461c3da",
      "command": "ack_fault",
      "label": "Ack fault",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:28.500Z",
      "updated_at": "2026-11-19T15:04:28.800Z"
    },
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": false,
      "reason": "Finish or abort the active mission first",
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": true,
      "reason": null,
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
      "allowed": false,
      "reason": "Not possible while the payload is AT_DESTINATION",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Not possible while the payload is AT_DESTINATION",
      "needs_confirmation": false
    },
    "release": {
      "allowed": true,
      "reason": null,
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
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "5a8c612d-67b4-44f0-a5db-5e8c011c1788",
      "code": "ROUTE_BLOCKED",
      "severity": "CAUTION",
      "title": "Route blocked: Bridge out at grid 4471",
      "source": "Team 2 Navigation",
      "recommended_action": "Review the new route and arrival time",
      "raised_at": "2026-11-19T15:04:28.300Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": null,
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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

export const delivered: Snapshot = {
  "kind": "snapshot",
  "seq": 330,
  "server_time": "2026-11-19T15:04:34.400Z",
  "test_mode": true,
  "link": {
    "updated_at": "2026-11-19T15:04:34.000Z",
    "age_s": 0.4,
    "stale": false,
    "state": "CONNECTED",
    "latency_ms": 80,
    "loss_pct": 0
  },
  "vehicle_health": {
    "overall": "NOMINAL",
    "subsystems": [
      {
        "updated_at": "2026-11-19T15:04:34.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "power",
        "label": "Power & Battery",
        "team": 4,
        "status": "OK",
        "detail": "89.6 % · 53.8 km"
      },
      {
        "updated_at": "2026-11-19T15:04:34.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "mobility",
        "label": "Mobility & Drivetrain",
        "team": 4,
        "status": "OK",
        "detail": "OK"
      },
      {
        "updated_at": "2026-11-19T15:04:34.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "navigation",
        "label": "Navigation Sensors",
        "team": 2,
        "status": "OK",
        "detail": "0 m/s"
      },
      {
        "updated_at": "2026-11-19T15:04:34.000Z",
        "age_s": 0.4,
        "stale": false,
        "key": "comms",
        "label": "Comms Link",
        "team": 3,
        "status": "OK",
        "detail": "80 ms · 0 %"
      },
      {
        "updated_at": "2026-11-19T15:04:34.300Z",
        "age_s": 0.1,
        "stale": false,
        "key": "payload_sensors",
        "label": "Payload Bay Sensors",
        "team": 5,
        "status": "OK",
        "detail": "OK"
      }
    ]
  },
  "payload": {
    "updated_at": "2026-11-19T15:04:34.300Z",
    "age_s": 0.1,
    "stale": false,
    "state": "DELIVERED",
    "held_from": null,
    "payload_id": "PAY-2026-001",
    "secured": false,
    "locked": false,
    "mass_kg": 0,
    "shift_cm": 0,
    "release_energy_wh": 3.2,
    "sensor_health": "OK",
    "sensors": {
      "load_cell": "OK",
      "lock": "OK",
      "shift": "OK"
    },
    "prerelease_authorized": false,
    "departure_permitted": false,
    "departure_reason": "Mission closed: unload the payload and assign a new mission"
  },
  "nav": {
    "updated_at": "2026-11-19T15:04:34.000Z",
    "age_s": 0.4,
    "stale": false,
    "origin": null,
    "destination": null,
    "position": {
      "lat": 34.7612,
      "lon": -86.581
    },
    "route": [
      {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      {
        "lat": 34.72892158258627,
        "lon": -86.62238828365503
      },
      {
        "lat": 34.729850748544365,
        "lon": -86.61594471972825
      },
      {
        "lat": 34.730779914502456,
        "lon": -86.60950115580148
      },
      {
        "lat": 34.731709080460554,
        "lon": -86.6030575918747
      },
      {
        "lat": 34.732638246418645,
        "lon": -86.59661402794794
      },
      {
        "lat": 34.73835059713492,
        "lon": -86.59349122235835
      },
      {
        "lat": 34.74406294785119,
        "lon": -86.59036841676877
      },
      {
        "lat": 34.74977529856746,
        "lon": -86.58724561117917
      },
      {
        "lat": 34.75548764928373,
        "lon": -86.58412280558959
      },
      {
        "lat": 34.7612,
        "lon": -86.581
      }
    ],
    "progress_pct": 100,
    "moving": false,
    "speed_mps": 0,
    "eta_s": 0,
    "blocked": {
      "reason": "Bridge out at grid 4471",
      "at": {
        "lat": 34.727992416628176,
        "lon": -86.6288318475818
      },
      "old_route": [
        {
          "lat": 34.7201,
          "lon": -86.6402
        },
        {
          "lat": 34.723836363636366,
          "lon": -86.63481818181818
        },
        {
          "lat": 34.72757272727273,
          "lon": -86.62943636363636
        },
        {
          "lat": 34.73130909090909,
          "lon": -86.62405454545454
        },
        {
          "lat": 34.73504545454546,
          "lon": -86.61867272727272
        },
        {
          "lat": 34.73878181818182,
          "lon": -86.6132909090909
        },
        {
          "lat": 34.742518181818184,
          "lon": -86.60790909090909
        },
        {
          "lat": 34.74625454545455,
          "lon": -86.60252727272727
        },
        {
          "lat": 34.74999090909091,
          "lon": -86.59714545454545
        },
        {
          "lat": 34.753727272727275,
          "lon": -86.59176363636364
        },
        {
          "lat": 34.75746363636364,
          "lon": -86.58638181818182
        },
        {
          "lat": 34.7612,
          "lon": -86.581
        }
      ],
      "new_eta_s": 80.88514747639177,
      "since": "2026-11-19T15:04:28.100Z"
    }
  },
  "mission": {
    "active": null,
    "queue": [
      {
        "mission_id": "MSN-2026-002",
        "payload_id": "PAY-2026-002",
        "status": "QUEUED",
        "origin": {
          "lat": 34.7201,
          "lon": -86.6402,
          "id": "FOB_ALPHA",
          "name": "FOB Alpha"
        },
        "destination": {
          "lat": 34.742,
          "lon": -86.695,
          "id": "LZ_DELTA",
          "name": "Landing Zone Delta"
        },
        "priority": "ROUTINE",
        "declared_mass_kg": 600,
        "dims_cm": {
          "length": 50,
          "width": 30,
          "height": 30
        },
        "prerelease_authorized": false,
        "created_at": "2026-11-19T15:04:28.300Z"
      }
    ],
    "next_ids": {
      "mission_id": "MSN-2026-003",
      "payload_id": "PAY-2026-003"
    }
  },
  "commands": [
    {
      "command_id": "23a35d74-1033-4b63-b42d-734764471f24",
      "command": "release",
      "label": "Release",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:30.100Z",
      "updated_at": "2026-11-19T15:04:34.400Z"
    },
    {
      "command_id": "107c832d-fef1-45f7-bbbd-b995e461c3da",
      "command": "ack_fault",
      "label": "Ack fault",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:28.500Z",
      "updated_at": "2026-11-19T15:04:28.800Z"
    },
    {
      "command_id": "a5b49c10-8dd5-40d7-8ef0-a157755e0da2",
      "command": "change_destination",
      "label": "Change destination",
      "state": "FAILED",
      "reason": "No confirmation in 5 s. Not resent.",
      "sent_at": "2026-11-19T15:04:12.900Z",
      "updated_at": "2026-11-19T15:04:17.900Z"
    },
    {
      "command_id": "39da74c8-3950-4cdc-9e12-1f8bae32f8a0",
      "command": "update_payload",
      "label": "Update payload",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:10.400Z",
      "updated_at": "2026-11-19T15:04:11.700Z"
    },
    {
      "command_id": "744df2da-63d3-40fb-8367-adadcf902bae",
      "command": "assign_mission",
      "label": "Assign mission",
      "state": "COMPLETED",
      "reason": null,
      "sent_at": "2026-11-19T15:04:05.100Z",
      "updated_at": "2026-11-19T15:04:10.400Z"
    }
  ],
  "allowed": {
    "assign_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "start_queued_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "remove_queued_mission": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": false
    },
    "abort": {
      "allowed": false,
      "reason": "Not possible while the payload is DELIVERED",
      "needs_confirmation": true
    },
    "return_to_origin": {
      "allowed": true,
      "reason": null,
      "needs_confirmation": true
    },
    "change_destination": {
      "allowed": false,
      "reason": "Not possible while the payload is DELIVERED",
      "needs_confirmation": true
    },
    "update_payload": {
      "allowed": false,
      "reason": "Not possible while the payload is DELIVERED",
      "needs_confirmation": false
    },
    "release": {
      "allowed": false,
      "reason": "Payload is not secured",
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
      "alert_id": "5603f66d-c60b-4b09-9469-65a700157d90",
      "code": "LINK_LOST",
      "severity": "WARNING",
      "title": "Link lost",
      "source": "Team 3 Link",
      "recommended_action": "Commands cannot reach the vehicle. Wait for the link; the payload stays secured",
      "raised_at": "2026-11-19T15:04:18.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "5a8c612d-67b4-44f0-a5db-5e8c011c1788",
      "code": "ROUTE_BLOCKED",
      "severity": "CAUTION",
      "title": "Route blocked: Bridge out at grid 4471",
      "source": "Team 2 Navigation",
      "recommended_action": "Review the new route and arrival time",
      "raised_at": "2026-11-19T15:04:28.300Z",
      "acknowledged": false,
      "active": true
    },
    {
      "alert_id": "b75ab0bd-e8ed-4d9f-b08d-123b8184c9f4",
      "code": "COMMAND_FAILED",
      "severity": "CAUTION",
      "title": "Change destination: No confirmation in 5 s. Not resent.",
      "source": "Ground",
      "recommended_action": "Check the reason and send the command again if still needed",
      "raised_at": "2026-11-19T15:04:17.900Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "905629ba-32d8-4918-b3f1-998032a253df",
      "code": "STALE_DATA",
      "severity": "CAUTION",
      "title": "Out of date: payload.status",
      "source": "Ground",
      "recommended_action": "Values marked OUT OF DATE may be wrong",
      "raised_at": "2026-11-19T15:04:17.000Z",
      "acknowledged": false,
      "active": false
    },
    {
      "alert_id": "05775413-f297-4c75-b339-21b8be0e804c",
      "code": "LINK_DEGRADED",
      "severity": "CAUTION",
      "title": "Link degraded: 1500 ms",
      "source": "Team 3 Link",
      "recommended_action": "Check data ages before acting",
      "raised_at": "2026-11-19T15:04:11.900Z",
      "acknowledged": false,
      "active": false
    }
  ],
  "estop_active": false,
  "delivery": {
    "mission_id": "MSN-2026-001",
    "payload_id": "PAY-2026-001",
    "destination": {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    "released_at": "2026-11-19T15:04:34.300Z",
    "confirmed_at": "2026-11-19T15:04:34.400Z",
    "confirm_latency_s": 0.1,
    "mass_kg": 810.0926517840074,
    "energy_used_wh": 3.2
  },
  "places": [
    {
      "lat": 34.7201,
      "lon": -86.6402,
      "id": "FOB_ALPHA",
      "name": "FOB Alpha"
    },
    {
      "lat": 34.7612,
      "lon": -86.581,
      "id": "OP_BRAVO",
      "name": "Outpost Bravo"
    },
    {
      "lat": 34.6905,
      "lon": -86.5521,
      "id": "OP_CHARLIE",
      "name": "Outpost Charlie"
    },
    {
      "lat": 34.742,
      "lon": -86.695,
      "id": "LZ_DELTA",
      "name": "Landing Zone Delta"
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
