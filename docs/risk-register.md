# Team 5 Risk Register

**Updated for CDR:** 2026-11-20 · **Reviewed by:** Tolu · **Maintained by:** Mercy (weekly)

Likelihood (L) and impact (I) are scored 1 (low) to 5 (high). Rating is likelihood × impact. Sorted by rating. The starting point is the Sprint 3 Risk Updates tab, plus the Sprint 2 risks it did not cover.

## Open risks

| # | Risk | L | I | Rating | Owner | Warning sign | What we do about it | Status |
|---|---|---|---|---|---|---|---|---|
| R1 | Team 1's integration environment is still undefined, so our software may not fit it | 4 | 5 | 20 | Zizwe | Team 1 has not said where software runs or how messages are exchanged by CDR | Clear message contracts and stand-ins for every team, so only the connection layer (`adapters/`) changes. Offer Team 1 our message format | Open |
| R2 | Team 2 does not honor our departure interlock, so the vehicle could leave with an unsecured payload | 3 | 5 | 15 | Zizwe | Team 2 does not agree to `payload.interlock` | The Payload Controller still detects a bad departure and raises `DEPARTED_UNSECURED` (critical). Get Team 2's agreement in writing (AEG-511) | Open (new) |
| R3 | Other teams don't give us the information we need in time | 3 | 4 | 12 | Emmanuel | No reply to a question by its due date | Every assumption is a setting in `config.yaml`; stand-ins for Teams 1 to 4 are built and the full IRON HAWK scenario passes with them | Open (mitigated) |
| R4 | Payload weight and box size are inconsistent: 1,000 kg in a 60 × 40 × 40 cm box is denser than steel | 4 | 3 | 12 | Solomon | Team 4 or a reviewer rejects the values; Team 4's bay is smaller than the box we choose | Choose a realistic box size (D-17) and confirm it with Team 4. Values are settings, so the change is in config only | Open (raised) |
| R5 | Emergency stop or vehicle health faults get out of sync across Teams 2, 4 and 5 | 3 | 4 | 12 | Zizwe | Team 2 or Team 4 does not confirm they act on `cmd.estop`; no agreed restart after a stop | One `cmd.estop` goes to the vehicle, Team 2 and Team 4 at top priority; the payload stays HELD until the operator acknowledges. Our stand-ins follow this. Agree the restart procedure with Team 2 | Open |
| R6 | The operator is overwhelmed when several problems happen at once | 3 | 4 | 12 | Mercy | Usability test success below 90% (OI-014) | Alerts ranked by severity with a recommended action are built; usability test with 3+ outside participants to be scheduled | Open |
| R7 | All code depends on two builders | 3 | 4 | 12 | Tolu | A task slips by more than 2 days | Handoff files, decisions log, CI on every PR, small tasks with clear Done-when lists | Open (new) |
| R8 | A delayed command runs late and causes the wrong action | 2 | 5 | 10 | Zizwe | Command confirmations taking close to 5 s | Built: commands fail after 5 s without a `RECEIVED` ack and are never resent; the vehicle rejects commands older than 5 s. Proven in IRON HAWK steps S11 to S14 | Open (mitigated) |
| R9 | Release energy (3.2 Wh nominal, 5.0 Wh max) is too low for a heavier payload; it was set for 15 to 25 kg | 3 | 3 | 9 | Solomon | Team 4's answer or our analysis shows a higher figure | Recheck the figure for the 500 lb to 1,000 kg range; values are settings | Open (new) |
| R10 | The contracts are not formally frozen, so a builder could change a shared message alone | 2 | 4 | 8 | Tolu | A contract file changes without a `CONTRACT CHANGE` PR | Sign-off pending (D-16). CI already checks that the screen and backend schemas match | Open (new) |
| R11 | Team 3's link limits differ from our assumption | 2 | 3 | 6 | Emmanuel | Team 3's answer differs from our working values | Limits are settings; update when Team 3 answers | Open |
| R12 | The payload is released by accident | 1 | 5 | 5 | Solomon | Any release during a test where it should be refused | Built: safety checks on the vehicle, operator confirmation dialog, tests for every refusal (AEG-506, AEG-507, AEG-511). IRON HAWK passes | Open (mitigated) |

## Closed risks

| Risk | Closed | Why |
|---|---|---|
| Work that slipped from Sprint 1 delays Sprint 3 | 2026-11-20 | Sprint 3 delivered; no longer applies |

## Changes since Sprint 3

- **Raised:** R4 (payload weight and size) from 6 to 12, because the size and weight conflict is now confirmed.
- **New:** R2 (departure interlock), R7 (two builders), R9 (release energy), R10 (contract freeze).
- **Carried from Sprint 2:** R1 (Team 1 environment), which the Sprint 3 update did not list. Its warning sign no longer uses the October 16 date.
- **Unchanged ratings, updated evidence:** R3, R5, R8 and R12 now point to built and tested safeguards.
- **Closed:** the Sprint 1 slip risk.
