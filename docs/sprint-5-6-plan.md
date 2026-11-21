# Sprint 5 and Sprint 6: Remaining Work

**Status:** Draft for Solomon's approval · 2026-11-20

Sprint 4 code is complete. This lists what each builder still has to do for Sprint 5 (TRR) and Sprint 6 (final demo and SVR). Task IDs refer to the workstream docs (03, 04, 05) and the handoff files.

## Sprint 5: TRR ("Are we ready to conduct meaningful testing?")

### Zizwe: 4 tasks

| # | Task | What it is | Done when |
|---|---|---|---|
| 1 | **A7** | Event Buffer, vehicle side. While the link is lost, keep events (deliveries, faults, acks) and send them as `backlog.batch` when the link returns, in order, with `buffered = true`. The ground side already handles this. | `test_OI_013_delivery_during_outage_reaches_ground_after_restore`, `test_event_buffer_preserves_order` and `test_event_buffer_survives_vehicle_restart` pass |
| 2 | **A8** | Safety property test. `hypothesis` feeds 2,000 random event sequences into the payload rules and checks that a release can never happen when it shouldn't. | Runs in CI with no failure. Any failure it finds becomes a named regression test |
| 3 | **A6** | Fault tests. The fault behavior already works; add the 4 named tests from doc 03. | `test_AEG_502_shift_over_2cm_raises_within_2s`, `test_AEG_513_payload_fault_reported_within_2s`, `test_OI_019_estop_cleared_only_by_ack` and `test_held_exits_only_when_cleared_and_acknowledged` pass |
| 4 | **A9** | Controller crash hook. Test injection `payload/controller_crash` stops only the controller; the payload stays locked. | `test_GEN_004_controller_crash_leaves_payload_secured` passes |

Done: B14 (Fault Injector), most of A9.

### Emmanuel: 4 tasks

All Phase 2 code is done. These are the TRR checklist items.

| # | Task | What it is |
|---|---|---|
| 1 | Defect tracking | GitHub `defect` label and issue template: requirement ID, test or scenario step, log file, severity, owner. TRR needs the open defect list. |
| 2 | Integration status page | `docs/integration-status.md`: for each of Teams 1 to 4, agreed, adapter tested, run together, or still a stand-in. |
| 3 | Verification report in CI | Generate `reports/verification.md` on every merge once Mercy adds `tools/requirements.csv`. |
| 4 | Usability test support (OI-014) | Screen ready for Mercy's usability test. Confirm with her what she needs, and record each participant's time in `reports/usability.csv`. |

Done: B11, B13, B15, C10, C11, C12, all five off-nominal scenarios, the verification report tool.

## Sprint 6: Final demo and SVR

### Zizwe: 3 tasks

| # | Task | What it is |
|---|---|---|
| 1 | **B16**, Team 2 adapter | In `aegis/adapters/`: translate between our envelope and Team 2's real messages, under the same endpoint name the stand-in uses. Build it now against [our interface sheet](team5-interface-sheet.md); adjust when Team 2 shares its format. |
| 2 | **B16**, Team 4 adapter | Same approach. |
| 3 | **B16**, Team 3 adapter | Same approach. |

After each swap, run `iron_hawk.yaml`; it must still pass.

### Emmanuel: 3 tasks

| # | Task | What it is |
|---|---|---|
| 1 | **B16**, Team 1 adapter | Same approach, using whatever Team 1 replies with: transport, message format, `t1.system_mode`. |
| 2 | **GEN-003** | Run our three processes in Team 1's environment as soon as they share it, and keep the run's report. |
| 3 | Demo hardening | Rehearse `iron_hawk.yaml --live` end to end with timing, and document the fallback (`run_all --single-process` on one laptop with stand-ins) in case Team 1's environment fails on the day. |

## Both

- Tick your handoff checkboxes as tasks merge. Most finished tasks are still unticked.
- One task per branch, the PR title starts with the task ID, and every scenario stays green in CI.

## Totals and priority

- **Sprint 5:** 8 tasks (Zizwe 4, Emmanuel 4).
- **Sprint 6:** 6 tasks (Zizwe 3, Emmanuel 3).
- **Priority:** Zizwe's A7 and A8 first. They are the biggest Sprint 5 items and the strongest evidence for TRR.

## Not on the builders

These belong to the rest of the team: the usability test with at least 3 people from outside the team (Mercy), two full demo rehearsals, the TRR and SVR reviews, and the replies from Teams 1 to 4 that the adapters depend on.
