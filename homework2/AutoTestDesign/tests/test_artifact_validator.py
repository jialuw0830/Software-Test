from __future__ import annotations

import csv
import json

from core.artifact_validator import validate_output_artifacts


def _write_csv(path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_validator_reports_missing_decision_table_artifact_and_optimization(tmp_path) -> None:
    (tmp_path / "structured_requirements.json").write_text(
        json.dumps(
            [
                {
                    "requirement_id": "REQ-001",
                    "module": "Login",
                    "feature": "Login",
                    "risk_level": "High",
                    "test_priority": "High",
                    "raw_text": "User login requirement",
                }
            ]
        ),
        encoding="utf-8",
    )
    _write_csv(
        tmp_path / "risk_analysis.csv",
        [
            {
                "requirement_id": "REQ-001",
                "module": "Login",
                "business_impact": "5",
                "failure_probability": "4",
                "user_frequency": "5",
                "implementation_complexity": "3",
                "risk_score": "4.35",
                "priority": "High",
                "rationale": "Login controls access to the main workflow.",
            }
        ],
    )
    _write_csv(
        tmp_path / "coverage_items.csv",
        [
            {
                "coverage_id": "COV-REQ-001-01",
                "requirement_id": "REQ-001",
                "module": "Login",
                "coverage_type": "Decision Table Testing",
                "coverage_item": "Credential combinations decide login outcome",
                "selected_test_design_technique": "Decision Table Testing",
                "rationale": "Multiple conditions decide access.",
                "priority": "High",
            }
        ],
    )
    _write_csv(
        tmp_path / "test_cases.csv",
        [
            {
                "test_case_id": "TC-001",
                "requirement_id": "REQ-001",
                "coverage_id": "COV-REQ-001-01",
                "module": "Login",
                "technique": "Decision Table Testing",
                "priority": "High",
                "steps": "[\"Run rule\"]",
                "test_data": "{\"username\":\"user\"}",
                "expected_result": "Login is evaluated.",
                "assertion_hint": "",
                "optimization_score": "",
            }
        ],
    )
    _write_csv(
        tmp_path / "traceability_matrix.csv",
        [
            {
                "requirement_id": "REQ-001",
                "coverage_id": "COV-REQ-001-01",
                "test_case_id": "TC-001",
                "technique": "Decision Table Testing",
                "priority": "High",
                "automated_or_manual": "Automated",
                "execution_result": "Not Run",
            }
        ],
    )

    issues = validate_output_artifacts(tmp_path, "Example App")
    messages = [issue.message for issue in issues]

    assert any("no rule artifact" in message for message in messages)
    assert any("empty optimization_score" in message for message in messages)
    assert (tmp_path / "artifact_validation_report.md").exists()
    assert (tmp_path / "artifact_validation_report.csv").exists()
