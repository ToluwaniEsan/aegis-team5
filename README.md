# Project AEGIS · Team 5: Payload & Operator Interface

Team 5's subsystem for **Project AEGIS** (Autonomous Expeditionary Ground Support System), the AAMU Senior Problem class project. We own payload delivery, the operator screen, and the operator's command and alert flow.

**Team:** Olasubomi Awodipe, Toluwani Esan, Mercy Akinyemi, Solomon Agyire, Emmanuel Aina, Zizwe Mtonga

**Sprint 4 builders:** Zizwe Mtonga (vehicle software and plumbing) and Emmanuel Aina (ground application and Operator Screen).

## Builders: start here

| Builder | Your file | What you build |
|---|---|---|
| Zizwe | [`HANDOFF-ZIZWE.md`](HANDOFF-ZIZWE.md) | Payload Controller and safety interlocks, simulator, Event Buffer, bus and link, Team 2, 3 and 4 stand-ins, permissions, Fault Injector |
| Emmanuel | [`HANDOFF-EMMANUEL.md`](HANDOFF-EMMANUEL.md) | Command Manager, Status Monitor, Alert Manager, Mission Log, UI server, scenario runner, Team 1 stand-in, the Operator Screen, CI |

1. Open your handoff file. Paste its kickoff prompt into your coding agent.
2. The agent asks your open questions from [`docs/decisions.md`](docs/decisions.md) first. Answer them before it writes any code.
3. Give the agent one task at a time. Review every pull request; the other builder approves it.

Every coding agent follows [`AGENTS.md`](AGENTS.md); `CLAUDE.md` points Claude Code at it.

## Run it and demo a mission

You need Python 3.11+ and Node 22. Build the screen once, then start everything with one command:

```bash
cd frontend && npm install && npm run build && cd ..
cd backend && python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m aegis.run_all             # ground + link + vehicle + stand-ins for Teams 1 to 4
```

Open two browser windows (a second monitor works best):

| Window | Address | Who uses it |
|---|---|---|
| Operator Screen | http://localhost:8080 | The operator. Click **Start operator console** (it unlocks the alarm sound). |
| Test panel | http://localhost:8080/test | The presenter or instructor, to trigger events and faults live. Only available while `test_mode: true` in `config/config.yaml`. |

**A full mission (the CDR demo):**
1. Operator Screen: **New mission** → pick origin and destination, weight 226.8 to 1000 kg, dimensions within 60 × 40 × 40 cm → **Assign mission**. The payload goes LOADED → SECURED.
2. Test panel: **Depart**. The Team 2 stand-in waits for this on purpose (`standins.nav.auto_depart: false`), so scenarios and demos control when the trip starts. The payload goes TRAVELLING → AT_DESTINATION.
3. Operator Screen: **Release payload** → confirm in the dialog. The payload goes RELEASED → DELIVERED, and the delivery confirmation appears bottom right.

Faults to show from the test panel: **Inject shift** (payload moves, HELD), **Start outage** (link loss), **Set battery**, **Block route**.

**Automated checks:** `pytest` in `backend/`; `npm run test`, `npm run lint` and `npm run test:layout` in `frontend/`; and the full IRON HAWK scenario: `python -m aegis.testing.scenario_runner scenarios/iron_hawk.yaml --fast` from `backend/`.

## Build plan

| File | What it covers |
|---|---|
| [`docs/00-build-plan-guide.md`](docs/00-build-plan-guide.md) | How the plan pack fits together |
| [`docs/01-system-overview.md`](docs/01-system-overview.md) | What we build, how it runs, tech, repo layout, who builds what, phases, handoffs, cut list |
| [`docs/02-contracts.md`](docs/02-contracts.md) | Messages I1 to I9, payload state machine, command rules, fault catalog, screen data format. **The source of truth.** |
| [`docs/03-workstream-A-vehicle.md`](docs/03-workstream-A-vehicle.md) | Tasks A0 to A9 (Zizwe) |
| [`docs/04-workstream-B-ground-integration.md`](docs/04-workstream-B-ground-integration.md) | Tasks B0 to B16 (split between both builders) |
| [`docs/05-workstream-C-operator-screen.md`](docs/05-workstream-C-operator-screen.md) | Design tokens, layout, tasks C0 to C12 (Emmanuel) |
| [`docs/06-integration-and-test.md`](docs/06-integration-and-test.md) | Connecting Teams 1 to 4, scenario format, IRON HAWK, verification evidence, CDR, TRR and demo checklists |
| [`docs/decisions.md`](docs/decisions.md) | Open questions each builder answers first, and the answers |
| [`docs/team5-interface-sheet.md`](docs/team5-interface-sheet.md) | Team 5's side of every interface: messages we send and expect, rates, assumed values |
| [`docs/risk-register.md`](docs/risk-register.md) | Risk register, updated for CDR |
| [`docs/sprint-5-6-plan.md`](docs/sprint-5-6-plan.md) | Remaining tasks per builder for Sprint 5 (TRR) and Sprint 6 (final demo and SVR) |
| [`config/config.yaml`](config/config.yaml) | Every limit and timing value |
| [`backend/scenarios/iron_hawk.yaml`](backend/scenarios/iron_hawk.yaml) | The full IRON HAWK scenario, tied to requirement IDs |
| [`design/`](design/) | Operator screen reference image, its HTML source and the bundled fonts |

## Sprint 3 background

| File | What it covers |
|---|---|
| [`docs/design-decisions.md`](docs/design-decisions.md) | Sprint 3 trade studies, key decisions, and the finalized values |
| [`docs/requirements.md`](docs/requirements.md) | Requirements Traceability Matrix: every AEG, OI, GEN and ENV requirement |
| [`docs/interfaces.md`](docs/interfaces.md) | Interfaces I1–I9 with the other teams, plus the change-control checklist |
| [`docs/architecture.md`](docs/architecture.md) | The subsystem parts and what each one owns (layout replaced by doc 01) |
| [`docs/process.md`](docs/process.md) | Sprint schedule, Definition of Done, Git conventions |
| [`docs/sprint3-prototype.html`](docs/sprint3-prototype.html) | The Sprint 3 operator screen prototype. Download it and open it in a browser. |

## Sources

- **Team 5 design document:** [Senior Problems FA25 (Google Doc)](https://docs.google.com/document/d/1AkvFVlgxawBSdeIX2vr46VWBIyyHWSFhRqhPwL4LBxo/edit). Access is limited to people the doc is shared with; ask Olasubomi if you can't open it.
- Project AEGIS Student Project Handbook (provided by the instructor)

## Working rules

- Branches: `feature/<TASK-ID>-short-name`, for example `feature/A4-payload-controller`. Merge to `main` at least once a day.
- PR titles: `[A4][AEG-506] Block release while moving`. The other builder reviews.
- Tests are named by requirement: `test_AEG_506_release_refused_while_moving`.
- Update the Code, Test and Status columns in `docs/requirements.md` as work finishes.
