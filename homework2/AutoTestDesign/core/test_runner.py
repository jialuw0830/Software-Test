"""Run generated pytest tests and export execution results."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .schemas import ExecutionResult


RESULTS_CSV = "execution_results.csv"
JUNIT_XML = "pytest_results.xml"


@dataclass(frozen=True)
class TestRunResult:
    command: list[str]
    return_code: int
    junit_xml: Path
    execution_results_csv: Path
    execution_results: list[ExecutionResult]
    stdout: str
    stderr: str


def run_generated_tests(test_file: Path | str, output_dir: Path | str) -> TestRunResult:
    """Run a generated pytest file and export parsed execution results."""

    test_path = Path(test_file)
    if not test_path.exists():
        raise FileNotFoundError(f"Generated test file does not exist: {test_path}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    junit_path = out / JUNIT_XML
    csv_path = out / RESULTS_CSV

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(test_path),
        "--junitxml",
        str(junit_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)

    if junit_path.exists():
        execution_results = parse_junit_results(junit_path)
    else:
        execution_results = [
            ExecutionResult(
                test_case_id="",
                result="Blocked",
                actual_result="pytest did not produce a JUnit XML report.",
                notes=(completed.stderr or completed.stdout).strip()[:1000],
            )
        ]
    write_execution_results_csv(execution_results, csv_path)

    return TestRunResult(
        command=command,
        return_code=completed.returncode,
        junit_xml=junit_path,
        execution_results_csv=csv_path,
        execution_results=execution_results,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def parse_junit_results(junit_xml: Path | str) -> list[ExecutionResult]:
    """Parse pytest JUnit XML into AutoTestDesign execution results."""

    root = ET.parse(junit_xml).getroot()
    results: list[ExecutionResult] = []
    for case in root.iter("testcase"):
        name = case.attrib.get("name", "")
        test_case_id = _extract_test_case_id(name)
        if not test_case_id:
            continue

        skipped = case.find("skipped")
        failure = case.find("failure")
        error = case.find("error")
        duration = case.attrib.get("time", "")
        duration_note = f"duration={duration}s" if duration else ""

        if failure is not None:
            results.append(
                ExecutionResult(
                    test_case_id=test_case_id,
                    result="Fail",
                    actual_result=_message(failure, "Generated Playwright test failed."),
                    notes=duration_note,
                )
            )
        elif error is not None:
            results.append(
                ExecutionResult(
                    test_case_id=test_case_id,
                    result="Blocked",
                    actual_result=_message(error, "Generated Playwright test errored before completion."),
                    notes=duration_note,
                )
            )
        elif skipped is not None:
            results.append(
                ExecutionResult(
                    test_case_id=test_case_id,
                    result="Blocked",
                    actual_result="Generated test was skipped.",
                    notes=_message(skipped, duration_note or "pytest skipped this generated test."),
                )
            )
        else:
            results.append(
                ExecutionResult(
                    test_case_id=test_case_id,
                    result="Pass",
                    actual_result="Generated Playwright test passed.",
                    notes=duration_note,
                )
            )
    return results


def write_execution_results_csv(results: list[ExecutionResult], csv_path: Path | str) -> Path:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_case_id", "result", "actual_result", "notes"])
        writer.writeheader()
        for result in results:
            writer.writerow(result.model_dump())
    return path


def _extract_test_case_id(pytest_name: str) -> str:
    match = re.search(r"test_tc_(\d+)", pytest_name.lower())
    if not match:
        return ""
    return f"TC-{int(match.group(1)):03d}"


def _message(element: ET.Element, default: str) -> str:
    return (element.attrib.get("message") or (element.text or "").strip() or default).strip()[:1000]
