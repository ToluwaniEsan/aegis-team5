# Requirements Traceability Matrix (RTM)

Source: Team 5 design document (Senior Problems FA25), Traceability section and Sprint 3 updates.
Handbook rule: every requirement must answer *why it exists, where it is implemented, which work item produced it, how we verify it, and what evidence proves it.*

**Code**, **Test** and **Status** were updated on 2026-11-22 from the verification report (`tools/verification_report.py`). **Done (verified)** means the automated evidence passed in CI. **Status:** Not started → In progress → Review → Test → Done.

Check methods: **Test** = we measure it. **Demo** = we show it working. **Analysis** = we calculate it. **Inspection** = we look at the screen, code or log.

## Payload (AEG)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| AEG-501 | Payload size and weight limit (60 × 40 × 40 cm) | Payload Controller | Team 4 | Test | `aegis/vehicle/rules.py` | 2 pytest (e.g. `test_AEG_501_assign_rejected_over_mass_limit`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| AEG-502 | Report payload shift (> 2.0 cm = unsecured) | Payload Simulator | Team 4 | Analysis, Test | `aegis/vehicle/rules.py` | 2 pytest (e.g. `test_AEG_502_shift_over_2cm_raises_within_2s`); scenarios: faults, iron_hawk, repeatability | Done (verified 2026-11-22) |
| AEG-503 | Accept payloads of at least 227 kg (500 lb), up to 1,000 kg ¹ | Payload Controller | | Test | `aegis/vehicle/rules.py` | 3 pytest (e.g. `test_AEG_503_accepts_500_750_1000_kg`); scenarios: estop, iron_hawk, iron_hawk_short | Done (verified 2026-11-22) |
| AEG-504 | Weight accurate to ±0.5 kg | Payload Simulator | | Test | `aegis/vehicle/simulator.py` | 1 pytest (e.g. `test_AEG_504_twenty_readings_within_accuracy`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| AEG-505 | Show secured status | Payload Simulator, Operator Screen | | Test | `aegis/vehicle/payload_controller.py` | 1 pytest (e.g. `test_AEG_505_status_at_1_hz_and_on_change`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| AEG-506 | No release while moving | Payload Controller | Team 2 | Test | `aegis/vehicle/rules.py` | 3 pytest (e.g. `test_AEG_506_release_refused_while_moving`); scenarios: iron_hawk, repeatability | Done (verified 2026-11-22) |
| AEG-507 | Release only at destination with authorization | Payload Controller | Team 2 | Demo | `aegis/vehicle/link_watch.py`, `aegis/vehicle/rules.py` | 5 pytest (e.g. `test_AEG_507_link_lost_with_preauth_releases_after_wait`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| AEG-508 | Delivery confirmation within 10 s | Payload Controller | Team 1 | Test | `aegis/vehicle/payload_controller.py`, `aegis/vehicle/rules.py` | 7 pytest (e.g. `test_AEG_508_delivered_sent_within_10_s_of_release`); scenarios: estop, iron_hawk, iron_hawk_short, repeatability | Done (verified 2026-11-22) |
| AEG-509 | Release energy 5 Wh or less (3.2 Wh nominal) | Payload Simulator | Team 4 | Analysis | `config/config.yaml` (release energy) | Analysis by Solomon (pending) | In progress: waiting on Solomon's release energy analysis |
| AEG-510 | Payload ID in every message (`PAY-YYYY-NNN`) | Mission Log, Payload Controller | | Inspection, Test | `aegis/ground/command_manager.py`, `aegis/ground/mission_log.py` | 2 pytest (e.g. `test_AEG_510_ids_unique_across_restarts`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| AEG-511 | No departure unless secured | Payload Controller | Team 2 | Test | `aegis/standins/nav.py`, `aegis/vehicle/rules.py` | 2 pytest (e.g. `test_AEG_511_standin_waits_for_interlock`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| AEG-512 | Update payload details | Command Manager, Payload Controller | Team 4 | Test, Demo | `aegis/ground/command_manager.py`, `aegis/vehicle/rules.py` | 4 pytest (e.g. `test_AEG_512_payload_limits_rejected_without_send`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| AEG-513 | Report payload faults | Alert Manager, Payload Controller | Team 1 | Test | `aegis/ground/alert_manager.py`, `aegis/vehicle/rules.py` | 3 pytest (e.g. `test_AEG_513_fault_forwarded_once_with_original_body`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| AEG-514 | Hold payload if link lost at destination | Payload Controller | Team 3 | Test | `aegis/vehicle/link_watch.py` | 2 pytest (e.g. `test_AEG_514_link_lost_at_destination_without_preauth_stays_secured`); scenarios: link_loss_at_destination | Done (verified 2026-11-22) |

¹ Changed from 15–25 kg to a 500 lb (227 kg) minimum to match Operation IRON HAWK (D-18). Size limit and release energy still need confirming with Team 4 for this weight.

## Operator Interface (OI)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| OI-001 | Assign a mission | Operator Screen | | Demo | `frontend/src` | scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| OI-002 | Full command set | Operator Screen, Command Manager | Team 2 | Demo | `frontend/src`, `aegis/ground/command_manager.py` | scenarios: abort_return, iron_hawk | Done (verified 2026-11-22) |
| OI-003 | Confirm risky commands (two-step) | Command Manager | | Demo | `aegis/ground/command_manager.py`, `aegis/ground/permissions.py` | 5 pytest (e.g. `test_OI_003_risky_command_refused_without_confirmation`); scenarios: abort_return, estop, iron_hawk, iron_hawk_short, repeatability; 1 browser checks | Done (verified 2026-11-22) |
| OI-004 | Refuse invalid commands with a reason | Command Manager | | Test | `aegis/ground/command_manager.py`, `aegis/ground/permissions.py` | 5 pytest (e.g. `test_OI_004_real_permissions_refuse_moving_release_without_publish`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| OI-005 | Live status display, 1 update per second | Status Monitor, Operator Screen | Teams 2, 3, 4 | Test | `aegis/ground/status_monitor.py`, `aegis/ground/ui_server.py` | 3 pytest (e.g. `test_OI_005_vehicle_health_rollup`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| OI-006 | Show command status (SENT, RECEIVED, COMPLETED, FAILED) | Command Manager | Team 3 | Test | `aegis/ground/command_manager.py`, `aegis/ground/ui_server.py` | 4 pytest (e.g. `test_OI_006_status_change_visible_within_2s`); scenarios: faults, iron_hawk, repeatability | Done (verified 2026-11-22) |
| OI-007 | Show link state | Status Monitor | Team 3 | Test | `aegis/standins/link.py`, `aegis/ground/status_monitor.py` | 4 pytest (e.g. `test_OI_007_link_health_follows_injected_conditions_within_1s`); scenarios: abort_return, estop, faults, iron_hawk, iron_hawk_short, link_loss_at_destination, repeatability | Done (verified 2026-11-22) |
| OI-008 | Last known status on link loss | Status Monitor | Team 3 | Test | `aegis/ground/status_monitor.py` | 1 pytest (e.g. `test_OI_008_last_known_status_and_age_shown_when_link_lost`); scenarios: faults, iron_hawk; 1 browser checks | Done (verified 2026-11-22) |
| OI-009 | Failed commands never resent (5 s timeout) | Command Manager | Team 3 | Test | `aegis/ground/command_manager.py`, `aegis/standins/link.py` | 5 pytest (e.g. `test_OI_009_command_fails_after_timeout_and_is_not_resent`); scenarios: faults, iron_hawk | Done (verified 2026-11-22) |
| OI-010 | Show faults with severity | Alert Manager | Team 1 | Test | `aegis/ground/alert_manager.py` | 3 pytest (e.g. `test_OI_010_replayed_fault_is_deduplicated_and_sorted`); scenarios: faults, iron_hawk | Done (verified 2026-11-22) |
| OI-011 | Critical alerts can't be missed | Alert Manager | | Demo, Inspection | `aegis/ground/alert_manager.py` | 3 pytest (e.g. `test_OI_011_critical_stays_until_acknowledged`) | Done (verified 2026-11-22) |
| OI-012 | Show blocked route | Status Monitor | Team 2 | Demo | `aegis/ground/status_monitor.py` | 5 pytest (e.g. `test_OI_012_blocked_route_preserves_old_route_and_expires`); scenarios: iron_hawk; 1 browser checks | Done (verified 2026-11-22) |
| OI-013 | Record everything | Mission Log | | Test, Inspection | `aegis/ground/command_manager.py`, `aegis/vehicle/event_buffer.py` | 16 pytest (e.g. `test_OI_013_failed_alert_callback_retries_without_duplicate_transition`) | Done (verified 2026-11-22) |
| OI-014 | Easy to learn (assign a mission in under 2 min) | Operator Screen | | Test | `frontend/src` | Usability trial protocol (`docs/evidence/OI-014-usability-protocol.md`) | Test: usability trial to run in Sprint 5 |
| OI-015 | New mission mid-mission (queued, never auto-starts) | Operator Screen, Command Manager | Team 2 | Demo | `aegis/ground/command_manager.py` | 2 pytest (e.g. `test_OI_015_queued_mission_never_starts_on_its_own`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| OI-016 | Show delivery summary | Operator Screen | | Demo | `aegis/ground/status_monitor.py` | 2 pytest (e.g. `test_OI_016_delivery_waits_for_destination_but_forwards_immediately`); scenarios: estop, iron_hawk, iron_hawk_short, repeatability | Done (verified 2026-11-22) |
| OI-017 | Mark out-of-date values (older than 5 s) | Status Monitor | Team 3 | Test | `aegis/ground/alert_manager.py`, `aegis/ground/status_monitor.py` | 8 pytest (e.g. `test_OI_017_stale_data_tracks_observed_groups`); scenarios: iron_hawk | Done (verified 2026-11-22) |
| OI-018 | Not color alone | Alert Manager | | Inspection | `frontend/src` | Grayscale captures (`docs/evidence/OI-018-grayscale/`) | Test: evidence ready, awaiting human sign-off |
| OI-019 | Emergency stop (one click, priority 0) | Command Manager, Payload Controller | Teams 2, 4 | Demo, Test | `aegis/ground/command_manager.py`, `aegis/vehicle/rules.py` | 6 pytest (e.g. `test_OI_019_estop_sent_with_priority_0_to_all_three`); scenarios: estop; 16 browser checks | Done (verified 2026-11-22) |

## General and environment (GEN, ENV)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| GEN-001 | Trigger faults for testing | Fault Injector | | Test | `aegis/standins/team1.py`, `aegis/ground/ui_server.py` | 6 pytest (e.g. `test_GEN_001_every_fault_triggerable_without_code_change`); 1 browser checks | Done (verified 2026-11-22) |
| GEN-002 | Metric units and UTC time | All parts | All teams | Inspection | `aegis/common/ui_models.py`, `aegis/common/envelope.py` | 14 pytest (e.g. `test_GEN_002_pydantic_schema_matches_checked_in_contract`) | Done (verified 2026-11-22) |
| GEN-003 | Runs in Team 1's environment | All parts | Team 1 | Demo | `aegis/run_all.py` | Run in Team 1's environment (pending) | Blocked: waiting on Team 1's environment |
| GEN-004 | Fail safe | Payload Controller | | Test | `aegis/vehicle/test_agent.py`, `aegis/vehicle/simulator.py` | 2 pytest (e.g. `test_GEN_004_controller_crash_leaves_payload_secured`) | Done (verified 2026-11-22) |
| GEN-005 | Payload simulator with failures | Payload Simulator | | Inspection, Test | `aegis/vehicle/simulator.py` | 1 pytest (e.g. `test_GEN_005_each_failure_can_be_triggered`) | Done (verified 2026-11-22) |
| ENV-001 | Runs on a standard laptop | Ground station | Team 1 | Demo | `aegis/run_all.py` | Laptop run (`docs/evidence/ENV-001-laptop-demo.md`) | Test: evidence ready, awaiting human sign-off |
| ENV-002 | Fits a 1366 × 768 screen | Operator Screen | | Inspection | `frontend/src` | 14 browser checks | Done (verified 2026-11-22) |
