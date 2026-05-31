"""Validate exported AutoTestDesign artifacts for consistency and completeness."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


REPORT_MD = "artifact_validation_report.md"
REPORT_CSV = "artifact_validation_report.csv"


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    artifact: str
    rule: str
    message: str


def validate_output_artifacts(output_dir: Path | str, target_name: str = "Target Application") -> list[ValidationIssue]:
    out = Path(output_dir)
    issues: list[ValidationIssue] = []

    requirements = _read_json_list(out / "structured_requirements.json", issues)
    risks = _read_csv(out / "risk_analysis.csv", issues)
    coverage = _read_csv(out / "coverage_items.csv", issues)
    tests = _read_csv(out / "test_cases.csv", issues)
    traceability = _read_csv(out / "traceability_matrix.csv", issues)
    decision_tables = _read_csv(out / "decision_table_review.csv", issues, required=False)
    execution_results = _read_csv(out / "execution_results.csv", issues, required=False)

    _validate_target_name(target_name, issues)
    _validate_requirements(requirements, issues)
    _validate_risks(requirements, risks, issues)
    _validate_coverage(requirements, coverage, tests, issues)
    _validate_tests(requirements, coverage, tests, issues)
    _validate_decision_tables(tests, decision_tables, issues)
    _validate_optimization(tests, issues)
    _validate_priority_consistency(requirements, risks, coverage, tests, issues)
    _validate_execution_evidence(traceability, execution_results, out, issues)

    write_validation_reports(issues, out)
    return issues


def write_validation_reports(issues: list[ValidationIssue], output_dir: Path | str) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / REPORT_CSV
    md_path = out / REPORT_MD
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["severity", "artifact", "rule", "message"])
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.__dict__)

    lines = ["# Artifact Validation Report", ""]
    if not issues:
        lines.append("No validation issues detected.")
    else:
        for issue in issues:
            lines.append(f"- **{issue.severity}** `{issue.artifact}` `{issue.rule}`: {issue.message}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"md": md_path, "csv": csv_path}


def _read_csv(path: Path, issues: list[ValidationIssue], required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            issues.append(ValidationIssue("Error", path.name, "file_exists", f"Required artifact is missing: {path.name}"))
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_json_list(path: Path, issues: list[ValidationIssue]) -> list[dict[str, object]]:
    if not path.exists():
        issues.append(ValidationIssue("Error", path.name, "file_exists", f"Required artifact is missing: {path.name}"))
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(ValidationIssue("Error", path.name, "valid_json", f"JSON parse failed: {exc}"))
        return []
    if not isinstance(data, list):
        issues.append(ValidationIssue("Error", path.name, "json_array", "Structured requirements must be a JSON array."))
        return []
    return [item for item in data if isinstance(item, dict)]


def _validate_target_name(target_name: str, issues: list[ValidationIssue]) -> None:
    if target_name.strip().lower() == "autotestdesign":
        issues.append(
            ValidationIssue(
                "Error",
                "target_context",
                "target_not_tool",
                "Target application must not be AutoTestDesign itself.",
            )
        )


def _validate_requirements(requirements: list[dict[str, object]], issues: list[ValidationIssue]) -> None:
    seen: set[str] = set()
    for index, requirement in enumerate(requirements, start=1):
        if not any(str(value).strip() for value in requirement.values()):
            issues.append(ValidationIssue("Error", "structured_requirements.json", "no_empty_rows", f"Requirement row {index} is empty."))
            continue
        req_id = str(requirement.get("requirement_id", "")).strip()
        if not req_id:
            issues.append(ValidationIssue("Error", "structured_requirements.json", "requirement_id", f"Requirement row {index} lacks requirement_id."))
        elif req_id in seen:
            issues.append(ValidationIssue("Error", "structured_requirements.json", "unique_requirement_id", f"Duplicate requirement_id: {req_id}"))
        seen.add(req_id)
        if not str(requirement.get("raw_text", "")).strip():
            issues.append(ValidationIssue("Error", "structured_requirements.json", "raw_text", f"{req_id or index} lacks raw_text."))


def _validate_risks(requirements: list[dict[str, object]], risks: list[dict[str, str]], issues: list[ValidationIssue]) -> None:
    req_ids = {str(item.get("requirement_id", "")).strip() for item in requirements}
    risk_ids = {item.get("requirement_id", "").strip() for item in risks}
    for req_id in sorted(req_ids - risk_ids):
        if req_id:
            issues.append(ValidationIssue("Error", "risk_analysis.csv", "requirement_has_risk", f"{req_id} has no risk record."))
    for risk in risks:
        req_id = risk.get("requirement_id", "")
        for field in ["risk_score", "priority", "rationale"]:
            if not risk.get(field, "").strip():
                issues.append(ValidationIssue("Error", "risk_analysis.csv", field, f"{req_id} risk record lacks {field}."))


def _validate_coverage(
    requirements: list[dict[str, object]],
    coverage: list[dict[str, str]],
    tests: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    req_ids = {str(item.get("requirement_id", "")).strip() for item in requirements}
    test_coverage_ids = {test.get("coverage_id", "").strip() for test in tests}
    for item in coverage:
        coverage_id = item.get("coverage_id", "")
        req_id = item.get("requirement_id", "")
        if req_id not in req_ids:
            issues.append(ValidationIssue("Error", "coverage_items.csv", "valid_requirement_id", f"{coverage_id} maps to unknown requirement {req_id}."))
        if coverage_id not in test_coverage_ids:
            issues.append(ValidationIssue("Error", "coverage_items.csv", "coverage_has_test", f"{coverage_id} has no generated test case."))


def _validate_tests(
    requirements: list[dict[str, object]],
    coverage: list[dict[str, str]],
    tests: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    req_ids = {str(item.get("requirement_id", "")).strip() for item in requirements}
    coverage_ids = {item.get("coverage_id", "").strip() for item in coverage}
    required = ["test_case_id", "requirement_id", "coverage_id", "technique", "priority", "steps", "test_data", "expected_result"]
    for test in tests:
        test_id = test.get("test_case_id", "")
        for field in required:
            if not test.get(field, "").strip():
                issues.append(ValidationIssue("Error", "test_cases.csv", field, f"{test_id or '<missing id>'} lacks {field}."))
        if test.get("requirement_id", "") not in req_ids:
            issues.append(ValidationIssue("Error", "test_cases.csv", "valid_requirement_id", f"{test_id} maps to unknown requirement."))
        if test.get("coverage_id", "") not in coverage_ids:
            issues.append(ValidationIssue("Error", "test_cases.csv", "valid_coverage_id", f"{test_id} maps to unknown coverage item."))
        if not test.get("assertion_hint", "").strip():
            issues.append(ValidationIssue("Warning", "test_cases.csv", "assertion_hint", f"{test_id} lacks assertion_hint."))


def _validate_decision_tables(
    tests: list[dict[str, str]],
    decision_tables: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    decision_tests = [test for test in tests if test.get("technique") == "Decision Table Testing"]
    if not decision_tests:
        issues.append(ValidationIssue("Error", "test_cases.csv", "decision_table_testing", "No Decision Table Testing test cases were generated."))
        return
    if not decision_tables:
        issues.append(ValidationIssue("Error", "decision_table_review.csv", "decision_table_artifact", "Decision Table test cases exist but no rule artifact was exported."))
        return
    mapped_ids = {row.get("generated_test_case_id", "") for row in decision_tables}
    for test in decision_tests:
        if test.get("test_case_id", "") not in mapped_ids:
            issues.append(ValidationIssue("Warning", "decision_table_review.csv", "decision_table_mapping", f"{test.get('test_case_id')} has no decision-table rule mapping."))


def _validate_optimization(tests: list[dict[str, str]], issues: list[ValidationIssue]) -> None:
    for test in tests:
        test_id = test.get("test_case_id", "")
        if not test.get("optimization_score", "").strip():
            issues.append(ValidationIssue("Warning", "test_cases.csv", "optimization_score", f"{test_id} has empty optimization_score."))
        for field in ["selected_for_smoke", "selected_for_regression"]:
            if field not in test:
                issues.append(ValidationIssue("Warning", "test_cases.csv", field, f"{field} column is missing."))
                return


def _validate_priority_consistency(
    requirements: list[dict[str, object]],
    risks: list[dict[str, str]],
    coverage: list[dict[str, str]],
    tests: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    risk_priority = {risk.get("requirement_id", ""): risk.get("priority", "") for risk in risks}
    coverage_priority = {item.get("coverage_id", ""): item.get("priority", "") for item in coverage}
    for req in requirements:
        req_id = str(req.get("requirement_id", ""))
        for field in ["risk_level", "test_priority"]:
            value = str(req.get(field, ""))
            if value and risk_priority.get(req_id) and value != risk_priority[req_id]:
                issues.append(ValidationIssue("Warning", "risk_analysis.csv", "priority_consistency", f"{req_id} {field}={value} differs from risk priority={risk_priority[req_id]}."))
    for test in tests:
        test_id = test.get("test_case_id", "")
        coverage_id = test.get("coverage_id", "")
        if coverage_priority.get(coverage_id) and test.get("priority") != coverage_priority[coverage_id]:
            issues.append(ValidationIssue("Warning", "test_cases.csv", "priority_consistency", f"{test_id} priority differs from coverage priority."))


def _validate_execution_evidence(
    traceability: list[dict[str, str]],
    execution_results: list[dict[str, str]],
    output_dir: Path,
    issues: list[ValidationIssue],
) -> None:
    has_non_not_run = any(row.get("execution_result", "Not Run") != "Not Run" for row in traceability)
    if has_non_not_run and not execution_results:
        issues.append(ValidationIssue("Error", "execution_results.csv", "execution_evidence", "Traceability has execution results but execution_results.csv is missing."))
    if execution_results and not (output_dir / "pytest_results.xml").exists():
        issues.append(ValidationIssue("Warning", "pytest_results.xml", "execution_evidence", "execution_results.csv exists but pytest_results.xml is missing."))
