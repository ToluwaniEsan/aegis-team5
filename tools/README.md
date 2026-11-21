# Verification evidence

`verification_report.py` reads the authoritative Traceability export; it does not
invent a requirements list. Supply `tools/requirements.csv` with columns `ID`,
`short text`, and `method`. Optionally supply `tools/manual_evidence.csv` with
columns `requirement`, `evidence file`, `checked by`, `date`, and `result`.
Only complete manual rows with PASS or FAIL are counted. AEG-509, OI-014,
OI-018, GEN-003 and ENV-001 require human-attributed evidence before a PASS;
automated tests and screenshot generation alone cannot establish those results.

From the repository root, run:

```sh
backend/.venv/bin/python tools/verification_report.py
```

The defaults read `backend/reports/pytest.xml`, all
`backend/reports/scenario-*.json`, and `frontend/reports/playwright.json`, then
write `reports/verification.csv` and `.md`. Use `--help` to select specific
inputs, especially when historic scenario reports should not be combined.
A failed item takes precedence over passing items; skipped tests do not count.
CI uploads pytest, Playwright and grayscale inputs as artifacts. Human reviews,
external-team demonstrations, the official requirements export and usability
trial remain separate inputs and are not inferred by this tool.
