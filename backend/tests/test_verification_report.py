"""Evidence is attributed by requirement and never manufactures human approval."""

import importlib.util
import json
from collections import defaultdict
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "tools" / "verification_report.py"
spec = importlib.util.spec_from_file_location("verification_report", MODULE)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def test_GEN_002_collects_scenario_pytest_and_browser_evidence(tmp_path):
    evidence = defaultdict(list)
    pytest = tmp_path / "pytest.xml"
    pytest.write_text(
        '<testsuite><testcase name="test_AEG_506_motion"/><testcase name="test_OI_009_timeout"><failure/></testcase><testcase name="test_GEN_002_skipped"><skipped/></testcase></testsuite>'
    )
    browser = tmp_path / "playwright.json"
    browser.write_text(
        json.dumps(
            {
                "suites": [
                    {
                        "specs": [
                            {
                                "title": "OI_018_grayscale_idle",
                                "tests": [{"results": [{"status": "passed"}]}],
                            }
                        ]
                    }
                ]
            }
        )
    )
    scenario = tmp_path / "scenario.json"
    scenario.write_text(
        json.dumps(
            {
                "name": "mission",
                "steps": [
                    {
                        "id": "S1",
                        "iteration": 1,
                        "requirements": ["AEG-506"],
                        "passed": True,
                        "measured_s": 0.9,
                        "logs": ["mission.jsonl"],
                    }
                ],
            }
        )
    )
    report.pytest_evidence(pytest, evidence)
    report.playwright_evidence(browser, evidence)
    report.scenario_evidence([scenario], evidence)
    assert len(evidence["AEG-506"]) == 2
    assert evidence["AEG-506"][1][2:4] == ("0.9 s", "mission.jsonl")
    assert not evidence["OI-009"][0][1]
    assert "GEN-002" not in evidence


def test_OI_018_screenshot_does_not_substitute_for_human_review(tmp_path):
    requirements = tmp_path / "requirements.csv"
    requirements.write_text(
        "ID,short text,method\nOI-018,Severity,Inspection\nOI-014,Usability,Test\n"
    )
    evidence = defaultdict(list)
    report.add(evidence, ["OI-018"], "Playwright: OI_018_grayscale_idle", True)
    assert [row["Result"] for row in report.make_report(requirements, evidence)] == [
        "NO EVIDENCE",
        "NO EVIDENCE",
    ]
    manual = tmp_path / "manual.csv"
    manual.write_text(
        "requirement,evidence file,checked by,date,result\nOI-018,images.zip,Mercy,2026-11-20,PASS\nOI-014,trial.csv,,,PASS\n"
    )
    report.manual_evidence(manual, evidence)
    rows = report.make_report(requirements, evidence)
    assert [row["Result"] for row in rows] == ["PASS", "NO EVIDENCE"]
    assert "Mercy" in rows[0]["Evidence"]
    report.add(evidence, ["OI-018"], "failed test", False)
    assert report.make_report(requirements, evidence)[0]["Result"] == "FAIL"
