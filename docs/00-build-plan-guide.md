# 00. Build plan guide (Project AEGIS, Team 5, Payload & Operator Interface)

> **Builders:** Zizwe (`HANDOFF-ZIZWE.md`) and Emmanuel (`HANDOFF-EMMANUEL.md`). Start from your handoff file. This guide explains how the pack fits together.

This pack turns the team doc into work that two or three builders and their coding agents can execute in parallel. Values and decisions come from the team doc; where a later tab changed an earlier one, the later tab wins (see doc 01).

## What is in it

| File | For | What it holds |
|---|---|---|
| `AGENTS.md` | every coding agent | The rules: what to read, what never to change, naming, testing |
| `docs/01-system-overview.md` | everyone | What we build, how it runs, tech, repo layout, who does what, phases, cut list |
| `docs/02-contracts.md` | everyone | Messages I1 to I9, payload state machine, command rules, fault catalog, screen data format. **The source of truth.** |
| `docs/03-workstream-A-vehicle.md` | vehicle builder | Tasks A0 to A9: Payload Controller, simulator, Event Buffer, safety property test |
| `docs/04-workstream-B-ground-integration.md` | ground and integration builder | Tasks B0 to B16: bus, link, stand-ins, Command Manager, Status Monitor, alerts, UI server, scenario runner, adapters |
| `docs/05-workstream-C-operator-screen.md` | screen builder | Design tokens, layout, tasks C0 to C12 |
| `docs/06-integration-and-test.md` | B leads, everyone uses | Connecting Teams 1 to 4, scenario format, IRON HAWK, verification evidence, CDR, TRR and demo checklists |
| `config/config.yaml` | everyone | Every limit and timing value |
| `scenarios/iron_hawk.yaml` | B, reviewed by all | Full IRON HAWK scenario, 25 steps, each tied to requirement IDs |
| `design/operator-screen-reference.png` and `.html` | screen builder | What the screen should look like, with the exact tokens |

## Day 1, before any agent writes code

1. **The repo layout is in place.**
   - `AGENTS.md` and `CLAUDE.md` are at the root.
   - The plan is in `docs/`, with `config/` and `design/` beside it.
   - The IRON HAWK draft is in `backend/scenarios/`.
2. **Owners are agreed:** Zizwe (vehicle and plumbing) and Emmanuel (ground app and screen). See doc 01, "Who builds what".
3. **Each builder starts their agent** with the kickoff prompt in their handoff file. The agent asks the open questions in `docs/decisions.md` first and waits for answers.
4. **Read `docs/02-contracts.md` together** (about 45 minutes). Change anything you disagree with now. After day 2 it is frozen (decision D-16).
5. **Send the interface sheets** to Teams 1 to 4 (doc 06 section 1). Their answers take days, so start now (D-08, D-15).

## How to point an agent at a task

Use the kickoff prompt in your handoff file once. After that, give your agent one task at a time, by ID:

```
Do task A4 from HANDOFF-ZIZWE.md. Stop when its Done-when list is met and report as AGENTS.md describes.
```

```
Do task C4 from HANDOFF-EMMANUEL.md. Look at design/operator-screen-reference.png first.
Use only the tokens in tokens.css.
```

Review every pull request before merging. The agent's report says which requirement tests it added; check they exist and actually assert the requirement.

## What this plan adds to the team doc

These are decisions the plan had to make to be buildable. They are flagged in doc 01. The team should confirm or change them on day 1:

- **Behaviour:**
  - The `RETURNING` payload state.
  - The `payload.interlock` message to Team 2 (AEG-511 needs it).
  - Assumption A-17, shared UTC clock.
- **New definitions:**
  - The fault catalog with recommended actions.
  - The test injection API.
  - The scenario format.
- **Small values:**
  - Named places.
  - Mission priorities.
  - Simulated load, lock and release times.
  - A 10 s wait before a pre-authorized release when the link is lost.
