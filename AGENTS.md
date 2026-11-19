# AGENTS.md: rules for coding agents on the Team 5 repo

Claude Code reads `CLAUDE.md`, which contains one line, `@AGENTS.md`. Other agents read this file directly.

## Who you work for

Two people build this repo. Each has a handoff file at the root that lists their tasks, in order:
- **Zizwe:** `HANDOFF-ZIZWE.md` (vehicle software and message plumbing)
- **Emmanuel:** `HANDOFF-EMMANUEL.md` (ground application and Operator Screen)

If you were not told which builder you work for, ask before doing anything else. Only do tasks from your builder's handoff file.

## Rule zero: ask first, then build

1. **Start of every session.** Open `docs/decisions.md`. Find every row owned by your builder (or by "Both") whose **Answer** cell is empty. Check its **Blocks** column:
   - `start` always blocks.
   - `Phase 1` blocks once you reach the first Phase 1 task.
   - `no` never blocks.
2. **If any of those rows block now, stop and ask your builder.** Put all of them in one message, numbered. For each one, give the question, the options and the recommended answer. List the non-blocking open rows at the end of the same message. Do not write code, create files or run installs until your builder has answered the blocking ones.
3. **Record the answers** in `docs/decisions.md`: fill in the Answer and Date cells, word for word.
   - If an answer changes a contract, do not edit the contract. Stop, write the proposed change in your summary, and tell your builder it needs a `CONTRACT CHANGE` pull request (hard rule 1).
   - If an answer only changes a value in `config/config.yaml`, tell your builder. They approve the edit.
4. **Questions during a task.** If the docs leave something open, ask your builder. Don't guess. Give a recommendation with each question, then wait for the answer. Add the question and its answer to `docs/decisions.md` so the other builder's agent sees it too.

## Read before you write code

0. Your builder's handoff file (`HANDOFF-ZIZWE.md` or `HANDOFF-EMMANUEL.md`) and `docs/decisions.md`.
1. `docs/01-system-overview.md`: what the system is, how it runs, who owns what.
2. `docs/02-contracts.md`: every message, state, command and screen field. **This is the source of truth.**
3. The workstream file for the task you were given:
   - `docs/03-workstream-A-vehicle.md`
   - `docs/04-workstream-B-ground-integration.md`
   - `docs/05-workstream-C-operator-screen.md`
4. `docs/06-integration-and-test.md` when the task touches another team, the scenario runner or evidence.

Each task in a workstream file has an ID (A3, B5, C7...), the files to create, the requirements it satisfies and a "Done when" list. Work on one task at a time and stop when its Done-when list is met. Where a handoff file changes a task, the handoff wins. Where anything disagrees with `docs/02-contracts.md`, the contracts win; tell your builder.

The older files in `docs/` (`architecture.md`, `process.md`, `design-decisions.md`, `requirements.md`, `interfaces.md`) are background from Sprint 3. Where they disagree with docs 00 to 06, docs 00 to 06 win.

## Hard rules

1. **Never change a contract on your own.** That means `docs/02-contracts.md`, `backend/aegis/common/models.py`, `backend/aegis/common/ui_models.py`, `frontend/src/contracts/ui.ts` and the keys in `config/config.yaml`. (Before the end-of-day-2 freeze, the owner of the file writes it from the contract text; after that, it changes only through a `CONTRACT CHANGE` pull request.) If your task seems to need a change, stop. Write the proposed change in your summary. The humans will open a `CONTRACT CHANGE` pull request.
2. **Stay in your builder's folders** (see the layout in doc 01 and the "You own" list in the handoff file). If you need something from another workstream that does not exist yet, use the mock or stand-in named in your task. Do not build their part.
3. **No hard-coded limits.** Every weight, size, threshold, timeout and rate comes from `config.yaml` through `aegis.common.config`. A literal like `5.0` for a timeout in code is a bug. In the frontend, the few screen-only constants live in `src/config.ts`; everything else comes from `snapshot.limits`.
4. **No wall clock.** Take a `Clock` (`aegis.common.clock`) and call `clock.now()`. Never call `time.time()`, `datetime.now()` or `asyncio.sleep()` for logic that a test needs to control. Use `clock.sleep()`.
5. **Safety logic lives on the vehicle.** The ground and the screen may refuse a command early to help the operator. The Payload Controller must still enforce every guard on its own as if the ground were wrong.
6. **Every message is an `Envelope`** built with `aegis.common.envelope.make(...)` and validated by pydantic on receipt. An invalid message is logged as `bus.invalid` and dropped, never half-processed.
7. **Every message sent or received, every state change and every alert is logged** through the Mission Log (OI-013). If it is not in the log, it did not happen for test purposes.
8. **Tests are named by requirement:** `test_<REQ_ID>_<what>`, for example `test_AEG_506_release_refused_while_moving` or `test_OI_009_command_fails_after_timeout_and_is_not_resent`. One requirement can have several tests. A test with no requirement ID is allowed only for plumbing.
9. **Time-based tests use `ManualClock`.** Never use real sleeps in tests.
10. **Frontend:**
    - Use only the design tokens in `frontend/src/styles/tokens.css`. No hex colors in components.
    - No UI component libraries and no Tailwind.
    - No decorative gradients. The only allowed pattern is the `--stale-pattern` hatch token.
    - No glow, blur or drop-shadow effects, no dark theme, and no purple or violet anywhere.
    - Severity is always shape plus label plus color, never color alone (OI-018).
    - **Use the professional palette in `tokens.css` exactly.** It is an ISA-101 high-performance HMI palette with measured contrast ratios (doc 05). Don't invent colors, don't add "accent" or "brand" colors, and don't use Tailwind, Material, Bootstrap or generic AI-style palettes. Gray and dark blue when normal; red, amber and yellow only for abnormal states; green only for "delivered".
    - **No blur of any kind.** No `backdrop-filter`, no `filter: blur()`, no frosted glass or glassmorphism panels, no soft glowing edges. Edges are 1 px solid borders.
    - **No filler text.** No lorem ipsum, marketing blurbs, taglines, welcome messages or decorative descriptions. Every word on screen is a real label, value, reason or action taken from the contracts or the snapshot.
    - Match `design/operator-screen-reference.png`. If your component looks different from the reference, the reference is right.
11. **No new dependencies** beyond those listed in doc 01 without saying why in the PR description.
12. **Keep it boring.** Plain functions and small classes. No metaclasses, no plugin frameworks, no abstract base classes with one implementation.

## Commands

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
pytest                                   # all backend tests
ruff check . && ruff format --check .
python -m aegis.run_all                  # ground + link + vehicle, screen on http://localhost:8080
python -m aegis.run_all --single-process
python -m aegis.testing.scenario_runner scenarios/iron_hawk.yaml

# frontend
cd frontend && npm install
npm run dev                              # uses the mock feed when VITE_MOCK=1
npm run test && npm run lint && npm run build
npx playwright test                      # layout checks at 1366 x 768
```

## When you finish a task

Report:
- The builder you work for and the task ID.
- The files changed.
- The tests added, with their requirement IDs.
- How you checked the Done-when list.
- Anything you could not do, and why.

- Any new question you asked, and confirmation it's in `docs/decisions.md`.
- The next task in your handoff file. Don't start it until your builder says so.

Do not mark a task done if a Done-when item is unchecked. Tick the task's box in your handoff file when it's merged.
