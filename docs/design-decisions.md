# Design decisions (Sprint 3)

Source: [Team 5 design document (Senior Problems FA25)](https://docs.google.com/document/d/1AkvFVlgxawBSdeIX2vr46VWBIyyHWSFhRqhPwL4LBxo/edit), Sprint 3 section (trade studies pp. 42–46, readiness checklist p. 53).

## Trade studies

| Decision | We chose | Over | Why |
|---|---|---|---|
| Operator screen | **Web-based UI** | Python desktop app (PyQt / Tkinter) | Locks the 1366 × 768 no-scroll layout, cleaner visual and audio alerts, avoids display issues in Team 1's integration environment |
| Programming language | **Python** | C++ or Java | Faster to build; 1-second updates and no hardware mean we don't need compiled speed |
| Payload simulator | **Interactive state simulator** | Pre-recorded scenario files | Testers trigger faults live with no code changes; it reacts to E-Stop and Abort |
| Vehicle health display | **Summary card with status badges** | Raw graphs and gauges | Fits the screen, avoids overload, never shows severity by color alone |

**Trade-off we accept:** the web screen needs a local WebSocket connection to the Python backend.

## Key decisions

- **Safety checks run on the vehicle.** Release needs: stopped, at destination, payload secured, no critical fault, release authorized. This holds even if the link drops.
- **5-second timeout on both sides.** The ground station marks an unconfirmed command FAILED at 5 s. The vehicle rejects any command older than 5 s. Commands are never queued or resent automatically.
- **One-click Emergency Stop.** No confirmation, sent ahead of all traffic (priority 0), payload set to HELD. Abort, Return to Origin, Change Destination and Release need a second confirmation.
- **Data age on every value.** Anything older than 5 s is marked OUT OF DATE with text and an icon.
- **Payload ID** is auto-generated as `PAY-YYYY-NNN` and pre-filled for the operator to verify.
- **Queued missions never auto-start.** The operator confirms them.
- **Vehicle event buffer.** Events are logged on board while the link is down and sent when it returns.
- **Limits live in a config file, not in code.**
- **Requirement IDs:** the old PL-001 to PL-014 are now AEG-501 to AEG-514.

## Finalized values (all TBRs resolved)

| ID | Setting | Value |
|---|---|---|
| AEG-501 / AEG-503 | Payload weight and size | At least 227 kg (500 lb), up to 1,000 kg ¹; 60 × 40 × 40 cm |
| AEG-502 | Unsecured shift threshold | 2.0 cm |
| AEG-504 | Weight sensor accuracy | ±0.5 kg |
| AEG-509 | Release energy | 3.2 Wh nominal, 5.0 Wh max |
| OI-005 | Screen update rate | 1 per second |
| OI-009 | Command timeout | 5.0 s |
| OI-017 | Out-of-date threshold | 5.0 s |
| — | Fault report to Team 1 | within 2 s |
| AEG-508 | Delivery confirmation | within 10 s |
| ENV-002 | Screen size | 1366 × 768, no scrolling |

¹ Corrected from 15–25 kg to a 500 lb minimum (D-18) to match Operation IRON HAWK. **Open:** confirm the size limit and release energy with Team 4 for this weight.

## Open issues

- Confirm the 500 lb payload and release energy with Team 4's power budget.
- Keep E-Stop and vehicle health in sync across Teams 2, 4 and 5.
- Build the WebSocket link between the screen and the backend.
