# 05. Workstream C: Operator Screen

**Owns:** everything in `frontend/`. Builder: Emmanuel (`HANDOFF-EMMANUEL.md`).
**Goal:** a screen a new operator can use after 30 minutes of training (OI-014). The operator must always see:
- what is current and what is out of date
- which commands are possible right now, and why the others are not
- every fault, with what to do about it

It fits 1366 × 768 with no page scrolling (ENV-002). The reference picture is `design/operator-screen-reference.png`, and its source `design/operator-screen-reference.html` holds every token below. Match it.

Read `02-contracts.md` section 9 (your data) and section 5 (commands) first.

## Design direction

The look follows the high-performance HMI approach used in industrial control rooms (ISA-101):

- **The background is calm, neutral gray.** Normal conditions have no color at all.
- **Color is reserved for abnormal states,** so a red or amber element on screen always means "look here".
- **Severity is always shape, then label, then color:** ▲ CRITICAL, ◆ WARNING, ● CAUTION. The screen must still make sense in a black-and-white screenshot (OI-018).
- **Numbers are monospaced and right-aligned** so changing values do not jitter.
- **Out-of-date values stay visible** with a hatch pattern, muted text and their age. They are never blanked out (OI-008).
- **Flat look:** square-ish corners (4 px), 1 px borders, no shadows, no gradients, no glow.
- **No dark theme, and no purple or violet anywhere.** One light theme, tuned for a laptop in daylight.
- **No blur and no filler text.** No `backdrop-filter`, no `filter: blur()`, no frosted glass. No lorem ipsum, taglines or marketing blurbs: every word is a real label, value, reason or action.
- **Only the palette below.** Don't add colors, and don't use Tailwind, Material or other library palettes.

This is also why the screen will not look AI-generated. Those screens get their look from dark backgrounds, violet accents, gradients and glowing cards, and this design uses none of them.

### Design tokens (`src/styles/tokens.css`)

```css
:root {
  /* surfaces */
  --canvas: #DCE0E5;          /* screen background */
  --panel: #F3F4F6;           /* panels */
  --panel-raised: #FAFAFB;    /* cards inside panels, inputs */
  --line: #B8BFC8;            /* panel and card borders */
  --line-strong: #8A939E;     /* dividers that must be seen */

  /* text */
  --text: #17202B;
  --text-muted: #4D5764;      /* secondary values */
  --text-label: #5F6874;      /* small uppercase labels */

  /* the only interactive color */
  --action: #1D4E89;
  --action-hover: #163E6E;
  --action-text: #FFFFFF;
  --focus-ring: 0 0 0 2px #FFFFFF, 0 0 0 4px #1D4E89;

  /* abnormal states */
  --critical: #B42318;  --critical-bg: #FCE9E7;
  --warning: #A6480C;   --warning-bg: #FDEEE3;
  --caution-fill: #F0C33C; --caution-text: #5C4500; --caution-bg: #FFF6D6;

  /* the only "good news" color, used for delivery confirmed and nothing else */
  --done: #2E6B45;  --done-bg: #E6F2EA;

  /* emergency stop */
  --estop: #C4161C;  --estop-border: #8C0F14;  --estop-text: #FFFFFF;

  /* out of date */
  --stale-text: #525A64;
  --stale-pattern: repeating-linear-gradient(135deg, #ECEEF1 0 6px, #E2E5E9 6px 12px);

  /* type */
  --font-ui: "IBM Plex Sans", Arial, sans-serif;
  --font-num: "IBM Plex Mono", "Courier New", monospace;
  --fs-label: 11px;   /* uppercase, letter-spacing 0.06em, weight 600 */
  --fs-body: 13px;
  --fs-value: 15px;   /* mono, tabular */
  --fs-big: 22px;     /* payload state, ETA */
  --fs-title: 14px;   /* panel titles, weight 600 */

  /* space and shape */
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px;
  --radius: 4px;
  --row-h: 26px;      /* list and table rows; alert rows are 32px */
}
```

**Severity shapes are drawn, not typed.** The IBM Plex latin files do not contain ▲ ◆ ●, so a typed glyph falls back to a system font and looks different on every laptop. Build one `SeverityGlyph` component with three small inline SVGs (triangle, diamond, circle), as the reference HTML does.

**Contrast, measured:** `--text` on `--panel` 14.9:1, `--text-muted` 6.7:1, `--text-label` 5.1:1, white on `--action` 8.4:1, `--warning` on `--warning-bg` 5.2:1, `--critical` on `--critical-bg` 5.6:1, `--caution-text` on `--caution-fill` 5.5:1, `--stale-text` on the darker hatch stripe 5.5:1. All are at or above 4.5:1. Disabled buttons are lower on purpose; their reason text below them is `--text-muted`.

Rules:
- **Tokens only.** No hex value appears outside `tokens.css`.
- **Body text:** do not put body text in `--text-label`; it is for the small uppercase labels only.
- **Caution text:** caution is the only severity whose text is dark on its fill (`--caution-text` on `--caution-fill`). Yellow with white text fails contrast.
- **Buttons:**
  - Primary: `--action` with white text.
  - Secondary: `--panel-raised` with a `--line-strong` border.
  - Release and Abort use the primary style. The confirmation dialog carries the weight.
  - Only the emergency stop is red.

## Layout (from the PRD tab, exact)

```
+--------------------------------------------------------------------------------+  64 px
| TOP BAR  mission · payload ID | UTC clock · LINK badge · VEHICLE badge | E-STOP  |
+--------------------------+------------------------------+----------------------+
| LEFT 420                 | CENTER 526                   | RIGHT 420            |
| Payload Status card      | Route & Navigation           | Mission controls     |
|  state, stepper, lock,   |  schematic route (SVG)       |  New / Queue mission |
|  weight, shift, energy,  |  progress bar, ETA           |  5 command buttons   |
|  sensors, data age       |  origin → destination        |   with reasons       |
| Vehicle Health card      |  moving/stopped, speed       | Command tracker      |
|  overall + 5 rows        |  reroute notice              | Mission queue        |
+--------------------------+------------------------------+----------------------+  544 px
| ALERTS & RECOMMENDED ACTIONS  (CRITICAL first)                 | Last delivery |  160 px
+--------------------------------------------------------------------------------+
  total 1366 × 768. Body overflow hidden. Inner lists may scroll; the page never does.
```

- **Grid:** CSS Grid on `#app`, `grid-template-columns: 420px 526px 420px; grid-template-rows: 64px 544px 160px`. Panels have 1 px borders and `--s3` padding.
- **Small screens:** below 1366 × 768 the screen shows a message asking for a bigger window. It does not reflow.
- **The emergency stop is never covered.**
  - Dialogs and drawers place their backdrop from `top: 64px` down, so the top bar stays clickable (OI-019: one click from every screen).
  - The E-STOP button is 152 × 44 px, solid `--estop`, white bold label "E-STOP", with the subtitle "Stops vehicle · holds payload".
  - One click sends the command. It has no confirmation dialog and no keyboard shortcut.

## Source layout

```
frontend/src/
  contracts/ui.ts            frozen copy of contracts section 9
  styles/tokens.css, base.css
  net/socket.ts              WebSocket client with reconnect
  net/mock.ts                plays fixtures when VITE_MOCK=1
  state/store.ts             zustand: snapshot, connection, pending requests, open dialogs
  lib/format.ts              UTC times, ages, numbers with units
  audio/alarm.ts             Web Audio alarm for unacknowledged CRITICAL alerts
  components/                one folder per component, each with a .module.css and a test
  pages/OperatorScreen.tsx
  pages/TestPanel.tsx        /test, only when snapshot.test_mode
  mock/fixtures/*.json       from B13 (hand-written placeholders until then)
```

## Tasks

### Phase 0 (days 1 to 2)

**C0. Scaffold**
- **Build:** Vite, React 18 and TypeScript with strict mode, eslint and prettier, Vitest with React Testing Library, and Playwright.
  - Install `zustand`, `@fontsource/ibm-plex-sans` (weights 400, 600) and `@fontsource/ibm-plex-mono` (400, 600).
  - Add `tokens.css` and `base.css`. Base CSS sets `html, body { margin: 0; overflow: hidden }`, the canvas color and the font.
  - Copy `ui.ts` from contracts section 9 unchanged.
- **Done when:** `npm run build` passes, and the page shows the empty five-panel grid at exactly 1366 × 768.

**C1. Mock feed**
- **Build:** with `VITE_MOCK=1`, `net/mock.ts` plays `mock/fixtures/*.json` in IRON HAWK order, one per 3 s, looping. A small dev-only dropdown in the corner jumps to any fixture by name. It is not rendered in production builds.
- **Schema export:** add `npm run schema`. It runs `ts-json-schema-generator` on `ui.ts` and writes `contracts/ui.from-ts.schema.json`, which B13's test compares with the backend's schema.
  - Until B13 delivers real fixtures, write three by hand (idle, travelling, fault_shift) that type-check against `ui.ts`.
- **Done when:** a type test (`tsc --noEmit` over `fixtures.test.ts`) fails if any fixture does not match `Snapshot`.

### Phase 1 (days 3 to 7)

**C2. WebSocket client and store**
- **Requirements:** OI-005, OI-006
- **`socket.ts`:** connect to `/ws` and reconnect with backoff (0.5 s doubling to 5 s). Every `Snapshot` replaces the store's snapshot whole.
- **`sendCommand(command, args, confirmed)`:**
  - Creates `client_req_id`, sends the command and resolves with the `CommandResult`.
  - If no result comes within 3 s, it resolves as `{accepted: false, command_id: null, reason: "No answer from the ground station. The command may have been sent: check the command tracker."}`. Never tell the operator a command was not sent when the screen cannot know.
- **Constants:** the 3 s and the 2 s below live in `src/config.ts`, never inline (AGENTS rule 3 applies to the frontend too).
- **Screen disconnected:** if the socket is closed for more than 2 s, show a full-width red bar under the top bar: "SCREEN DISCONNECTED FROM GROUND STATION · data frozen at 14:02:11Z". Grey out every panel with the stale pattern.
  - This is a different failure from the Team 3 link being LOST. The screen must never confuse the two.
- **Done when:**
  - Unit tests cover snapshot replacement, the command timeout and the disconnected bar.
  - It works against the real backend once B12 lands.

**C3. Top bar**
- **Requirements:** OI-007, OI-019, AEG-510, GEN-002
- **Left:** mission name ("MSN-2026-007 · FOB Alpha → Outpost Bravo") and the payload ID in mono.
- **Center:**
  - A UTC clock, `HH:MM:SS Z` from `server_time`, so it is the ground's clock and not the laptop's.
  - The link badge:
    - CONNECTED: neutral, with the latency in ms.
    - DEGRADED: ◆, amber outline and background.
    - LOST: ▲, red, with the time lost.
  - The vehicle badge: NOMINAL is neutral, DEGRADED is ◆ amber, FAULT is ▲ red.
- **Right:** the E-STOP button. While `estop_active` is true it shows "E-STOP ACTIVE · acknowledge in alerts" and still sends `estop` if clicked again.
- **Done when:**
  - A component test covers each badge state.
  - A Playwright check clicks E-STOP while a dialog is open and sees the command sent.

**C4. Payload Status card (left, top)**
- **Requirements:** AEG-502, 504, 505, 509, 510, GEN-005, OI-008, OI-017
- **Header:** "PAYLOAD" label, with the data age on the right ("1 s ago"; "OUT OF DATE · 12 s" when stale).
- **State:**
  - The state name in `--fs-big`.
  - Below it, a 7-step stepper labelled EMPTY, LOADED, SECURED, TRAVEL, AT DEST, RELEASED, DELIVERED, with the current step in `--action`. These short labels are used only in the stepper.
  - RETURNING shows a "Returning to origin" tag instead of the stepper position.
  - HELD shows a red bar across the stepper: "▲ HELD (was TRAVELLING) · release blocked".
- **Rows**, label left and mono value right. Thresholds come from `limits`, never typed in:
  - Lock: "Closed" or "▲ OPEN", from `payload.locked`
  - Weight: "742.3 kg", with ◆ if out of range
  - Shift: "0.2 cm", with ◆ over `limits.unsecured_shift_cm`
  - Release energy: "3.2 Wh / 5.0 max", using `limits.release_energy_wh_max`
  - Sensors: load cell, lock and shift, each as text, from `payload.sensors`
  - Pre-authorized release: Yes or No
  - Departure: "Permitted", or "Blocked: " plus `payload.departure_reason`
- **Stale:** the whole card body gets `--stale-pattern` and `--stale-text`. Values stay visible.
- **Done when:** component tests use the fixtures. A stale fixture shows the pattern and the age, and a HELD fixture shows the bar.

**C5. Vehicle Health card (left, bottom)**
- **Requirements:** OI-005, OI-010, OI-018
- **Content:** the overall status, then five rows (Power & Battery, Mobility & Drivetrain, Navigation Sensors, Comms Link, Payload Bay Sensors), each with:
  - the status (text plus shape)
  - the `detail` string
  - its age
  - the owning team in small label text ("Team 4")
- **Done when:** each status renders with its shape and word, and stale rows show their age.

**C6. Route and Navigation panel (center)**
- **Requirements:** OI-005, OI-012
- **Schematic route:** an SVG, not a map. There are no map tiles because the screen must work offline.
  - Project the route's lat/lon into the panel box with an equal-scale fit and 24 px margin.
  - Draw the route as a 2 px `--line-strong` line, with the travelled part in `--action`.
  - Origin is a hollow circle with its label. Destination is a filled square with its label.
  - The vehicle is a 10 px `--text` triangle pointing along the route.
- **Below the schematic:**
  - A progress bar with the percentage.
  - ETA in `--fs-big` mono as `MM:SS`.
  - "Moving · 8.0 m/s" or "Stopped".
- **Reroute:** when `nav.blocked` is set, show a caution banner: "● ROUTE BLOCKED · [reason] · new ETA 07:40". Draw `nav.blocked.old_route` dashed, with a red cross at `nav.blocked.at`, under the new `route`.
- **Stale:** the same pattern as C4.
- **Done when:** fixtures render for idle (no route: "No active mission"), travelling and route blocked.

**C7. Command panel (right)**
- **Requirements:** OI-002, OI-003, OI-004, OI-006, OI-009
- **Primary button:** "New mission", or "Queue mission" when a mission is active. It opens the C8 drawer.
- **Command buttons:** Abort, Return to origin, Change destination, Update payload, Release payload, in a 2-column grid.
  - Disabled buttons show the `allowed[x].reason` underneath in `--text-muted`, never only in a tooltip (OI-004).
  - A click on a command with `needs_confirmation` opens C9. Otherwise it sends at once.
  - **Change destination** first opens a small picker over the right panel (a dropdown of `places`, excluding the current destination), then C9.
  - **Update payload** opens the C8 drawer in update mode: weight and dimensions only, pre-filled with the current values.
- **Command tracker:** the last 4 `commands`, each as a row with label, state and time.
  - States: SENT, RECEIVED, COMPLETED, or ▲ FAILED with the reason, for example "No confirmation in 5 s. Not resent.".
  - The tracker updates from snapshots only. It never guesses a state.
- **Mission queue:** the count plus up to 3 rows. Each row has "Start" (opens C9 with "Start queued mission MSN-...?") and "Remove". "Start" is disabled with a reason while a mission is active (OI-015).
- **Done when:** component tests show every button's disabled reason from fixtures, and a FAILED command shows its reason.

**C8. Mission form drawer**
- **Requirements:** OI-001, OI-014, OI-015, AEG-501, AEG-507, AEG-510
- **Placement:** slides over the right panel only; the backdrop leaves the top bar clear.
- **Fields in order:**
  - Origin and Destination: dropdowns from `places`, which must differ.
  - Priority: three buttons (ROUTINE, PRIORITY, URGENT).
  - Declared weight in kg: number input, with a live check against `limits` ("Must be 226.8 to 1000 kg").
  - Dimensions in cm: three inputs, with a live check.
  - "Pre-authorize release if the link is lost at the destination": a checkbox, off by default.
- **Payload ID:** read-only, from `mission.next_ids`.
- **Submit:** labelled "Assign mission" or "Add to queue", disabled until valid. Show which field is missing.
- **Done when:** a Vitest test fills the form and sends the right `args`. A stopwatch run by someone outside the team takes under 2 minutes, which is a rehearsal for OI-014.

**C9. Confirmation dialog**
- **Requirement:** OI-003
- **Size:** 480 px wide, centered in the area below the top bar.
- **Title:** names the action and the object: "Release payload PAY-2026-007 at Outpost Bravo?". The body says the consequence in one sentence ("This cannot be undone.").
- **Buttons:** "Cancel" has the initial focus. The confirm button carries the verb ("Release payload").
- **Keys:** Esc cancels. Enter does not confirm. The operator must click it, or Tab to it and press Space. That stops a double Enter from releasing a payload.
- **Done when:** tests prove initial focus on Cancel, Enter does nothing, and Esc closes. Sending sets `confirmed: true`.

### Phase 2 (days 8 to 13)

**C10. Alerts feed and alarm (bottom)**
- **Requirements:** OI-010, OI-011, OI-016, OI-018
- **Rows:** 32 px each.
  - A severity tag: shape, word and color. CRITICAL has `--critical-bg` and a 4 px left bar in `--critical`.
  - Then the title, the source, and the time as UTC with its age ("14:02:11Z · 9 s").
  - Then the recommended action in `--text-muted`, and an "Acknowledge" button.
  - Acknowledged but still active alerts stay, with the button replaced by "Acknowledged".
- **Overflow:** at most 3 rows visible; beyond that, "+N more" opens the full list over the bottom panel. CRITICAL rows always sort first, so they are never hidden.
- **Unacknowledged CRITICAL:** the row border pulses between 1 px and 3 px once per second. Use a CSS animation of `outline-width` only, with no glow.
- **Alarm (`audio/alarm.ts`):** while any CRITICAL alert is unacknowledged, play a Web Audio tone pair (880 Hz then 660 Hz, 200 ms each) every 1.5 s. Stop when none remain.
- **Start overlay:** browsers block sound until the user clicks. On load, show a "Start operator console" overlay; that one click unlocks audio.
  - The overlay covers only the area below the top bar (`top: 64px`). The E-STOP stays clickable even before the console is started.
  - If audio is blocked, show "▲ Alarm sound is off. Click to enable" in the top bar.
- **Last delivery:** the right 300 px of the bottom panel holds the `delivery` summary in `--done-bg`. It shows ✓ "Delivered", the payload ID, the destination, the release time, "Confirmed in 3.4 s" and the mass (OI-016).
- **Done when:**
  - Tests cover ordering, the "+N more" behaviour and acknowledge.
  - The alarm is on only while unacknowledged CRITICAL alerts exist, tested with a mocked AudioContext.

**C11. Test panel (`/test`)**
- **Requirement:** GEN-001
- **Build:** a plain page outside the 1366 grid, reachable only when `test_mode` is true.
  - It has its own E-STOP button at the top, so the emergency stop is one click away here too (OI-019).
  - One section per target in contracts section 10, with a button or small form per action, posting to `/api/test/inject`.
  - Show the last 10 results.
- **Demo setup:** this page goes on a second monitor during demos, so the instructor can trigger faults live.
- **Done when:** every row of section 10 can be triggered from the page.

**C12. Layout and accessibility checks (Playwright)**
- **Requirements:** ENV-002, OI-018, OI-019
- **Name the Playwright tests by requirement** so the verification report counts them: `ENV_002_no_scroll_*`, `OI_019_estop_visible_*`, `OI_018_grayscale_*`.
- **Load each fixture at 1366 × 768 and check:**
  - `document.scrollingElement.scrollHeight <= 768` and `scrollWidth <= 1366` (ENV-002).
  - The E-STOP button is visible and enabled (OI-019).
- **Grayscale screenshots:** take a screenshot of each fixture with `filter: grayscale(1)` applied and save it to `reports/grayscale/`. A person checks that severities can be told apart. This is the OI-018 evidence; commit the images with the verification report.
- **Done when:** the Playwright suite runs in CI and the screenshots exist.

## What Workstream C hands to others

| Day | To | What |
|---|---|---|
| 2 | all | Grid and tokens in place, matching the reference image |
| 7 | all | A happy path driven from the real screen |
| 13 | Test Lead (Mercy) | A screen ready for the usability test (OI-014), and the grayscale screenshots |

## Things that make this screen look professional

- **Alignment:** every number is right-aligned in mono; every label is left-aligned, 11 px uppercase.
- **Spacing:** one 4 px spacing scale, used everywhere.
- **Consistent words:** each state name is spelled the same everywhere. The stepper's short labels (TRAVEL, AT DEST) appear nowhere else.
- **No decoration:** no icons except the severity shapes, the lock word and the route glyphs. Text beats icons for a new operator.
- **Calm when normal:** a screen with no problems is almost entirely gray and dark blue. That calm is the point. Color then means something.
