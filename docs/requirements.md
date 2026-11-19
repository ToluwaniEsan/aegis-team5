# Requirements Traceability Matrix (RTM)

Source: Team 5 design document (Senior Problems FA25), Traceability section and Sprint 3 updates.
Handbook rule: every requirement must answer *why it exists, where it is implemented, which work item produced it, how we verify it, and what evidence proves it.*

Fill in **Code** and **Test** as each item is built. **Status:** Not started → In progress → Review → Test → Done.

Check methods: **Test** = we measure it. **Demo** = we show it working. **Analysis** = we calculate it. **Inspection** = we look at the screen, code or log.

## Payload (AEG)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| AEG-501 | Payload size and weight limit (60 × 40 × 40 cm) | Payload Controller | Team 4 | Test | | | Not started |
| AEG-502 | Report payload shift (> 2.0 cm = unsecured) | Payload Simulator | Team 4 | Analysis, Test | | | Not started |
| AEG-503 | Accept payloads up to 227 kg (500 lb) ¹ | Payload Controller | | Test | | | Not started |
| AEG-504 | Weight accurate to ±0.5 kg | Payload Simulator | | Test | | | Not started |
| AEG-505 | Show secured status | Payload Simulator, Operator Screen | | Test | | | Prototyped (Sprint 3) |
| AEG-506 | No release while moving | Payload Controller | Team 2 | Test | | | Not started |
| AEG-507 | Release only at destination with authorization | Payload Controller | Team 2 | Demo | | | Not started |
| AEG-508 | Delivery confirmation within 10 s | Payload Controller | Team 1 | Test | | | Not started |
| AEG-509 | Release energy 5 Wh or less (3.2 Wh nominal) | Payload Simulator | Team 4 | Analysis | | | Not started |
| AEG-510 | Payload ID in every message (`PAY-YYYY-NNN`) | Mission Log, Payload Controller | | Inspection, Test | | | Not started |
| AEG-511 | No departure unless secured | Payload Controller | Team 2 | Test | | | Not started |
| AEG-512 | Update payload details | Command Manager, Payload Controller | Team 4 | Test, Demo | | | Not started |
| AEG-513 | Report payload faults | Alert Manager, Payload Controller | Team 1 | Test | | | Not started |
| AEG-514 | Hold payload if link lost at destination | Payload Controller | Team 3 | Test | | | Not started |

¹ Changed from 15–25 kg to 500 lb (227 kg) to match Operation IRON HAWK. Size limit and release energy still need confirming with Team 4 for this weight.

## Operator Interface (OI)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| OI-001 | Assign a mission | Operator Screen | | Demo | | | Prototyped (Sprint 3) |
| OI-002 | Full command set | Operator Screen, Command Manager | Team 2 | Demo | | | Not started |
| OI-003 | Confirm risky commands (two-step) | Command Manager | | Demo | | | Not started |
| OI-004 | Refuse invalid commands with a reason | Command Manager | | Test | | | Not started |
| OI-005 | Live status display, 1 update per second | Status Monitor, Operator Screen | Teams 2, 3, 4 | Test | | | Not started |
| OI-006 | Show command status (SENT, RECEIVED, COMPLETED, FAILED) | Command Manager | Team 3 | Test | | | Not started |
| OI-007 | Show link state | Status Monitor | Team 3 | Test | | | Not started |
| OI-008 | Last known status on link loss | Status Monitor | Team 3 | Test | | | Not started |
| OI-009 | Failed commands never resent (5 s timeout) | Command Manager | Team 3 | Test | | | Not started |
| OI-010 | Show faults with severity | Alert Manager | Team 1 | Test | | | Not started |
| OI-011 | Critical alerts can't be missed | Alert Manager | | Demo, Inspection | | | Not started |
| OI-012 | Show blocked route | Status Monitor | Team 2 | Demo | | | Not started |
| OI-013 | Record everything | Mission Log | | Test, Inspection | | | Not started |
| OI-014 | Easy to learn (assign a mission in under 2 min) | Operator Screen | | Test | | | Not started |
| OI-015 | New mission mid-mission (queued, never auto-starts) | Operator Screen, Command Manager | Team 2 | Demo | | | Not started |
| OI-016 | Show delivery summary | Operator Screen | | Demo | | | Not started |
| OI-017 | Mark out-of-date values (older than 5 s) | Status Monitor | Team 3 | Test | | | Not started |
| OI-018 | Not color alone | Alert Manager | | Inspection | | | Not started |
| OI-019 | Emergency stop (one click, priority 0) | Command Manager, Payload Controller | Teams 2, 4 | Demo, Test | | | Not started |

## General and environment (GEN, ENV)

| ID | Requirement | Part | Other team | Check | Code | Test | Status |
|---|---|---|---|---|---|---|---|
| GEN-001 | Trigger faults for testing | Fault Injector | | Test | | | Not started |
| GEN-002 | Metric units and UTC time | All parts | All teams | Inspection | | | Not started |
| GEN-003 | Runs in Team 1's environment | All parts | Team 1 | Demo | | | Not started |
| GEN-004 | Fail safe | Payload Controller | | Test | | | Not started |
| GEN-005 | Payload simulator with failures | Payload Simulator | | Inspection, Test | | | Not started |
| ENV-001 | Runs on a standard laptop | Ground station | Team 1 | Demo | | | Not started |
| ENV-002 | Fits a 1366 × 768 screen | Operator Screen | | Inspection | | | Prototyped (Sprint 3) |
