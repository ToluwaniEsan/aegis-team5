# Team 5 Interface Sheet: Payload & Operator Interface

**Status:** Draft for CDR · 2026-11-20 · Source of truth: [`02-contracts.md`](02-contracts.md)

This sheet states Team 5's side of every interface: what our software sends, what it expects to receive, and how often. Values marked **ASSUMED** are our working values until the other team confirms them. They live in [`config/config.yaml`](../config/config.yaml), so a confirmed value is a config change, not a code change.

## How we exchange messages

Every message is one JSON object (an *envelope*) with the same outer fields:

```json
{
  "v": 1,
  "msg_id": "6f1c2a9e-1d3b-4c55-9a51-2f2a0f3b7c11",
  "type": "cmd.release",
  "iface": "I2",
  "src": "ground.command_manager",
  "dst": ["vehicle.payload_controller"],
  "sent_at": "2026-11-19T15:04:05.123Z",
  "priority": 2,
  "mission_id": "MSN-2026-007",
  "payload_id": "PAY-2026-007",
  "corr_id": null,
  "buffered": false,
  "body": {}
}
```

- **Priority:** `0` emergency stop, `1` commands and acks, `2` status. Lower numbers go first.
- **Acks:** every command is answered with an `ack` (`RECEIVED`, then `COMPLETED` or `REJECTED` with a reason).
- **Rates:** "1 Hz" means once per second, plus immediately on any change.
- **Other teams** appear in our system as one endpoint each: `team1.integration`, `team2.nav`, `team3.link`, `team4.power`. Today each is a stand-in that behaves like the real team; a real team plugs in behind the same name.

## Interfaces at a glance

| Interface | Between | What crosses it | Status |
|---|---|---|---|
| I1 | Ground station ↔ Operator Screen | Screen snapshot (1 Hz) and operator commands | Internal to Team 5 |
| I2 | Ground → vehicle | Mission, payload and release commands; heartbeat | Internal to Team 5 |
| I3 | Vehicle → ground | Payload status, delivery, faults | Internal to Team 5 |
| I4 | Ground → Team 2 | Mission assignment and route commands | ASSUMED |
| I5 | Ground → vehicle, Team 2, Team 4 | Emergency stop | ASSUMED |
| I6 | Team 2 ↔ vehicle and ground | Navigation state, route blocked, departure interlock | ASSUMED (interlock PROPOSED) |
| I7 | Vehicle ↔ Team 4 | Payload mass and release energy; power status | ASSUMED |
| I8 | Team 3 → ground | Link health | ASSUMED |
| I9 | Ground ↔ Team 1 | Mission, fault and delivery reports; system mode | ASSUMED |

## What Team 5 sends

| Message | To | When | Key fields |
|---|---|---|---|
| `cmd.assign_mission` | Vehicle | Operator assigns | `mission_id`, `payload_id`, `origin`, `destination`, `priority`, `declared_mass_kg`, `dims_cm`, `prerelease_authorized` |
| `cmd.update_payload` | Vehicle | Before departure only | `declared_mass_kg`, `dims_cm` |
| `cmd.release` | Vehicle | Operator confirms release | none |
| `cmd.abort`, `cmd.return_to_origin`, `cmd.change_destination` | Vehicle and Team 2 | Operator command | `destination` (change only) |
| `nav.assign` | Team 2 | Mission starts | `mission_id`, `origin`, `destination`, `priority` |
| `cmd.estop` | Vehicle, Team 2, Team 4 | Operator presses E-STOP (no confirmation) | `reason`, `source: "OPERATOR"` |
| `hb.ground` | Vehicle | 1 Hz | `seq` |
| `payload.status` | Ground | 1 Hz | `state`, `secured`, `locked`, `mass_kg`, `shift_cm`, `sensors`, `departure_permitted` |
| `payload.delivered` | Ground | Once, within 10 s of release | `released_at`, `position`, `mass_kg`, `energy_used_wh` |
| `fault.raised`, `fault.cleared` | Ground | Within 2 s of a fault | `code`, `severity`, `message`, `recommended_action`, `holds_payload` |
| `payload.interlock` | Team 2 | 1 Hz | `departure_permitted`, `reason` (**PROPOSED**) |
| `payload.mass_report` | Team 4 | When the mass changes | `mass_kg`, `release_energy_wh_nominal`, `release_energy_wh_max` |
| `t1.mission_report` | Team 1 | Mission status changes | `mission_id`, `payload_id`, `status` |
| `t1.fault_report` | Team 1 | Within 2 s of a fault | Same as `fault.raised` |
| `t1.delivery_confirmation` | Team 1 | On delivery | Same as `payload.delivered` |

## What Team 5 expects to receive

| Message | From | Rate | Key fields | Status |
|---|---|---|---|---|
| `nav.state` | Team 2 | 1 Hz, on the vehicle (must not depend on the link) | `moving`, `speed_mps`, `position {lat, lon}`, `at_destination`, `at_origin`, `eta_s`, `progress_pct`, `route`, `health` | ASSUMED |
| `nav.route_blocked` | Team 2 | On event | `reason`, `blocked_at`, `new_route`, `new_eta_s` | ASSUMED |
| `ack` | Team 2, Team 4 | Per command | `result`, `reason_code`, `reason` | ASSUMED |
| `power.status` | Team 4 | 1 Hz | `battery_pct`, `est_range_km`, `drivetrain_health` | ASSUMED |
| `link.health` | Team 3 | 1 Hz | `state` (`CONNECTED`, `DEGRADED`, `LOST`), `latency_ms`, `loss_pct` | ASSUMED |
| `t1.system_mode` | Team 1 | On change | `mode` (format unknown) | ASSUMED |

## Working values we assume (from `config.yaml`)

| Value | Working value | Interface |
|---|---|---|
| Payload mass | 226.8 kg (500 lb) to 1,000 kg | I7 |
| Payload box (max) | 60 × 40 × 40 cm (under review, D-17) | I7 |
| Release energy | 3.2 Wh nominal, 5.0 Wh max (under review) | I7 |
| Link degraded | latency over 1,000 ms or loss over 10% | I8 |
| Link lost | nothing received for 5 s | I8 |
| Command timeout | no `RECEIVED` ack within 5 s marks the command failed; never resent | I2, I4 |
| Stale data | values older than 5 s shown as OUT OF DATE | I1 |
| Low battery alert | below 20% | I7 |

## Rules that hold regardless of the other teams

- **Safety lives on the vehicle.** The Payload Controller refuses release while moving, away from the destination, unsecured or under a critical fault, even if the ground or the screen gets it wrong.
- **Departure interlock (AEG-511).** We tell Team 2 whether departure is permitted. The vehicle must not leave while it is false.
- **Emergency stop** has top priority, needs no confirmation, and puts the payload in HELD until the operator acknowledges it.
- **Link loss.** Team 2's moving and arrived signals reach the Payload Controller on the vehicle without crossing the link. Events during an outage are buffered and replayed when the link returns.
