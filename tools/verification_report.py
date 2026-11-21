"""Combine named automated and human evidence without inventing missing evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

MANUAL_REQUIRED = {"AEG-509", "OI-014", "OI-018", "GEN-003", "ENV-001"}

REQ = re.compile(r"(?<![A-Za-z0-9])(AEG|OI|ENV|GEN)[_-](\d{3})(?!\d)")


def ids(text):
    return {f"{prefix}-{number}" for prefix, number in REQ.findall(text)}


def add(evidence, names, description, passed, measured="", logs="", source="automated"):
    for name in names:
        evidence[name].append((description, passed, measured, logs, source))


def pytest_evidence(path, evidence):
    if not path.exists():
        return
    for case in ET.parse(path).iter("testcase"):
        if case.find("skipped") is not None:
            continue
        name = case.get("name", "")
        passed = case.find("failure") is None and case.find("error") is None
        add(evidence, ids(name), f"pytest: {name}", passed)


def playwright_evidence(path, evidence):
    if not path.exists():
        return

    def walk(suite):
        for spec in suite.get("specs", []):
            name = spec.get("title", "")
            for test in spec.get("tests", []):
                results = test.get("results", [])
                if not results or results[-1].get("status") in (
                    "skipped",
                    "interrupted",
                ):
                    continue
                add(
                    evidence,
                    ids(name),
                    f"Playwright: {name}",
                    results[-1].get("status") == "passed",
                )
        for child in suite.get("suites", []):
            walk(child)

    for suite in json.loads(path.read_text(encoding="utf-8")).get("suites", []):
        walk(suite)


def scenario_evidence(paths, evidence):
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for step in report.get("steps", []):
            elapsed = step.get("measured_s")
            measured = "" if elapsed is None else f"{elapsed:g} s"
            add(
                evidence,
                step.get("requirements", []),
                f"{report.get('name', path.stem)}: {step['id']} (iteration {step.get('iteration', 1)})",
                step.get("passed") is True,
                measured,
                "; ".join(step.get("logs", [])),
            )


def manual_evidence(path, evidence):
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            result = row.get("result", "").strip().upper()
            if result not in {"PASS", "FAIL"} or not all(
                row.get(k, "").strip()
                for k in ("requirement", "evidence file", "checked by", "date")
            ):
                continue
            add(
                evidence,
                [row["requirement"].strip()],
                f"{row['evidence file']} (checked by {row['checked by']}, {row['date']})",
                result == "PASS",
                source="manual",
            )


def make_report(requirements, evidence):
    rows = []
    with requirements.open(newline="", encoding="utf-8-sig") as stream:
        for req in csv.DictReader(stream):
            key = req["ID"].strip()
            entries = evidence.get(key, [])
            eligible = [
                e for e in entries if key not in MANUAL_REQUIRED or e[4] == "manual"
            ]
            result = (
                "FAIL"
                if any(not entry[1] for entry in entries)
                else "PASS"
                if eligible
                else "NO EVIDENCE"
            )
            rows.append(
                {
                    "Requirement": key,
                    "Method": req["method"].strip(),
                    "Evidence": "; ".join(e[0] for e in entries),
                    "Result": result,
                    "Measured value": "; ".join(e[2] for e in entries if e[2]),
                    "Log file": "; ".join(dict.fromkeys(e[3] for e in entries if e[3])),
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--requirements", type=Path, default=Path("tools/requirements.csv")
    )
    parser.add_argument(
        "--manual", type=Path, default=Path("tools/manual_evidence.csv")
    )
    parser.add_argument(
        "--pytest", type=Path, default=Path("backend/reports/pytest.xml")
    )
    parser.add_argument(
        "--playwright", type=Path, default=Path("frontend/reports/playwright.json")
    )
    parser.add_argument("--scenarios", type=Path, default=Path("backend/reports"))
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()
    if not args.requirements.is_file():
        parser.error(
            f"requirements file missing: {args.requirements} (supply the Traceability export)"
        )
    evidence = defaultdict(list)
    pytest_evidence(args.pytest, evidence)
    playwright_evidence(args.playwright, evidence)
    scenario_evidence(sorted(args.scenarios.glob("scenario-*.json")), evidence)
    manual_evidence(args.manual, evidence)
    rows = make_report(args.requirements, evidence)
    fields = [
        "Requirement",
        "Method",
        "Evidence",
        "Result",
        "Measured value",
        "Log file",
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "verification.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with (args.output / "verification.md").open("w", encoding="utf-8") as stream:
        stream.write(
            "| "
            + " | ".join(fields)
            + " |\n| "
            + " | ".join("---" for _ in fields)
            + " |\n"
        )
        for row in rows:
            stream.write(
                "| "
                + " | ".join(
                    str(row[field]).replace("|", "\\|").replace("\n", " ")
                    for field in fields
                )
                + " |\n"
            )


if __name__ == "__main__":
    main()
