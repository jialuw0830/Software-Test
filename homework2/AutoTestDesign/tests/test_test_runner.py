from __future__ import annotations

import csv

from core.schemas import ExecutionResult
from core.test_runner import parse_junit_results, write_execution_results_csv


def test_parse_junit_results_maps_pytest_outcomes(tmp_path) -> None:
    xml_path = tmp_path / "pytest_results.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4" failures="1" errors="1" skipped="1">
    <testcase classname="generated" name="test_tc_001_login[chromium]" time="1.23" />
    <testcase classname="generated" name="test_tc_002_login_error[chromium]" time="0.20">
      <failure message="expected error text">trace</failure>
    </testcase>
    <testcase classname="generated" name="test_tc_003_cart[chromium]" time="0.01">
      <skipped message="manual case" />
    </testcase>
    <testcase classname="generated" name="test_tc_004_checkout[chromium]" time="0.02">
      <error message="browser setup failed">trace</error>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )

    results = parse_junit_results(xml_path)

    assert [(result.test_case_id, result.result) for result in results] == [
        ("TC-001", "Pass"),
        ("TC-002", "Fail"),
        ("TC-003", "Blocked"),
        ("TC-004", "Blocked"),
    ]
    assert results[1].actual_result == "expected error text"
    assert results[2].actual_result == "Generated test was skipped."
    assert results[3].actual_result == "browser setup failed"


def test_write_execution_results_csv(tmp_path) -> None:
    csv_path = tmp_path / "execution_results.csv"
    write_execution_results_csv(
        [
            ExecutionResult(
                test_case_id="TC-001",
                result="Pass",
                actual_result="Generated Playwright test passed.",
                notes="duration=1.0s",
            )
        ],
        csv_path,
    )

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "test_case_id": "TC-001",
            "result": "Pass",
            "actual_result": "Generated Playwright test passed.",
            "notes": "duration=1.0s",
        }
    ]
