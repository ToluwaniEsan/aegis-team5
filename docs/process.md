# How we work (from the Project AEGIS handbook)

> **Sprint 3 background.** For Sprint 4 onward:
> - The build order and phases are in `docs/01-system-overview.md`.
> - The task lists are in `HANDOFF-ZIZWE.md` and `HANDOFF-EMMANUEL.md`.
> - Branches are named `feature/<TASK-ID>-short-name`, for example `feature/A4-payload-controller`. That replaces `feature/WI-###` below.

## Sprint schedule

| Phase | Focus | Outcome |
|---|---|---|
| Sprint 3 | Preliminary design | Trade studies, design decisions, risk updates, PDR ✅ |
| **Sprint 4** | **Build / model / prototype** | **Working increment, integration, CDR** |
| Sprint 5 | Integration & verification | Integrated capability, test execution, defects, TRR |
| Sprint 6 | Validation | Operational scenario, SVR, final capability |
| Final | Closeout | Operational demonstration, final report, lessons learned |

## Sprint 4 build order (from our PDR exit checklist)

1. Shared message formats, config file and mission log
2. Payload simulator
3. Payload Controller safety checks
4. Stand-ins for Teams 2, 3 and 4

## Backlog workflow

Backlog → Ready → In Progress → Engineering Review → Test → Done

Each work item has: ID (`WI-###`), description, owner, requirement link, acceptance criteria, dependencies, estimate, status. Use GitHub Issues for work items.

## Definition of Done

A work item is Done only when:

- [ ] The requirement or mission need is identified
- [ ] Acceptance criteria are defined
- [ ] Technical work is complete
- [ ] Peer review has occurred (an approved pull request)
- [ ] Interface impacts have been assessed
- [ ] Verification method is identified
- [ ] Required evidence has been produced (test output, screenshot, log)
- [ ] Configuration and documentation are updated (`docs/requirements.md`)
- [ ] Product Owner acceptance obtained when applicable

> "A PowerPoint describing work is not a substitute for a technical increment."

## Git conventions

- Branch per task: `feature/<TASK-ID>-short-name`, for example `feature/A4-payload-controller`
- PR title starts with the task ID and the requirement ID: `[A4][AEG-506] Block release while moving`
- At least one teammate approves before merging to `main`
- Never hard-code a limit; put it in the config file

## Final demonstration: Operation IRON HAWK

The system receives a mission · communications degrade · the primary route becomes unavailable · the payload requirement changes within allowable bounds · the operator issues a new mission command · a simulated subsystem fault occurs · the system recovers, safely responds, or shows an appropriate fallback.
