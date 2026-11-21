# Team 5 Risk Register

**Updated for CDR:** 2026-11-20 · **Reviewed by:** Tolu · **Maintained by:** Mercy (weekly)

Likelihood and impact are scored 1 (low) to 5 (high). Rating is likelihood × impact. Sorted by rating.

## Open risks

| # | Risk | L | I | Rating | Owner | Warning sign | What we do about it | Status |
|---|---|---|---|---|---|---|---|---|
| R1 | Team 1's integration environment is still undefined, so our software may not fit it | 4 | 5 | 20 | Zizwe | Team 1 has not said where software runs or how messages are exchanged by CDR | Clear message contracts and stand-ins for every team, so only the connection layer (`adapters/`) changes. Offer Team 1 our message format | Open |
| R2 | Other teams don't give us the information we need in time | 4 | 4 | 16 | Emmanuel | No reply to a question by its due date | Every assumption is a setting in `config.yaml`; stand-ins for Teams 1 to 4 are built and the full IRON HAWK scenario passes with them | Open (mitigated) |
| R3 | Team 2 does not honor our departure interlock, so the vehicle could leave with an unsecured payload | 3 | 5 | 15 | Zizwe | Team 2 does not agree to `payload.interlock` | The Payload Controller still detects a bad departure and raises a fault; get Team 2's agreement in writing (AEG-511) | Open (new) |
| R4 | Payload weight and box size are inconsistent: 1,000 kg in a 60 × 40 × 40 cm box is denser than steel | 4 | 3 | 12 | Solomon | Team 4 or a reviewer rejects the values; Team 4's bay is smaller than the box we choose | Choose a realistic box size (D-17) and confirm it with Team 4. Values are settings, so the change is in config only | Open (raised) |
| R5 | All code depends on two builders | 3 | 4 | 12 | Tolu | A task slips by more than 2 days | Handoff files, decisions log, CI on every PR, small tasks with clear Done-when lists | Open (new) |
| R6 | The operator is overwhelmed when several problems happen at once | 3 | 4 | 12 | Mercy | Usability test success below 90% (OI-014) | Alerts ranked by severity with a recommended action are built; usability test with 3+ outside participants to be scheduled | Open |
| R7 | A delayed command runs late and causes the wrong action | 2 | 5 | 10 | Zizwe | Command confirmations taking close to 5 s | Built: commands fail after 5 s without a `RECEIVED` ack and are never resent; the vehicle rejects commands older than 5 s. Proven in IRON HAWK steps S11 to S14 | Open (mitigated) |
| R8 | Release energy (3.2 Wh nominal, 5.0 Wh max) is too low for a heavier payload; it was set for 15 to 25 kg | 3 | 3 | 9 | Solomon | Team 4's answer or our analysis shows a higher figure | Recheck the figure for the 500 lb to 1,000 kg range; values are settings | Open (new) |
| R9 | Team 3's link limits differ from our assumption | 3 | 3 | 9 | Emmanuel | Team 3's answer differs from our working values | Limits are settings; update when Team 3 answers | Open |
| R10 | The contracts are not formally frozen, so a builder could change a shared message alone | 2 | 4 | 8 | Tolu | A contract file changes without a `CONTRACT CHANGE` PR | Sign-off pending (D-16). CI already checks that the screen and backend schemas match | Open (new) |
| R11 | The payload is released by accident | 1 | 5 | 5 | Solomon | Any release during a test where it should be refused | Built: safety checks on the vehicle, operator confirmation dialog, tests for every refusal (AEG-506, AEG-507, AEG-511). IRON HAWK passes | Open (mitigated) |

## Closed risks

| Risk | Closed | Why |
|---|---|---|
| Work that slipped from Sprint 1 delays Sprint 3 | 2026-11-20 | Sprint 3 delivered; no longer applies |

## Changes since Sprint 3

- **Lowered:** R7 (delayed command) from 15 to 10 and R11 (accidental release) from 10 to 5, because both safeguards are now built and tested.
- **Raised:** R4 (payload size) from 9 to 12, because the size and weight conflict is now confirmed.
- **New:** R3 (departure interlock), R5 (two builders), R8 (release energy), R10 (contract freeze).
- **Updated warning sign:** R1 no longer uses the October 16 date.
- **Closed:** the Sprint 1 slip risk.
