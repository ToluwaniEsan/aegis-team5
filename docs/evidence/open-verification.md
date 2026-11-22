# Open verification evidence

| Requirement | Status and evidence needed |
|---|---|
| AEG-509 | Open pending Solomon's release-energy analysis for the current payload. Attach the calculation and supporting simulator log once available. |
| GEN-003 | Open pending Team 1's environment details and an end-to-end demonstration in that environment. Retain the run report and environment specifications. |
| OI-014 | Open pending Sprint 5 scheduling and execution. See the [usability protocol](OI-014-usability-protocol.md). |

## Traceability discrepancy (resolved 2026-11-22)

AEG-503 in the Traceability table said "Accept 15 to 25 kg", which conflicted with D-18 (minimum 500 lb, 226.8 kg). The Traceability row and `tools/requirements.csv` now read "Accept at least 227 kg (500 lb), up to 1,000 kg", matching D-18, the configuration and the tests. The report's AEG-503 gate only applies to the old wording, so AEG-503 now reports PASS on its evidence.
