from __future__ import annotations

import csv

from core.exporter import export_artifacts
from core.optimizer import optimize_test_suite
from core.schemas import CoverageItem, RiskAssessment, ReviewLogEntry, StructuredRequirement, TestCase


def test_export_merges_optimization_fields_into_test_cases_csv(tmp_path) -> None:
    requirement = StructuredRequirement(
        requirement_id="REQ-001",
        module="Login",
        feature="Login",
        actor="User",
        raw_text="Login requirement",
    )
    risk = RiskAssessment(
        requirement_id="REQ-001",
        module="Login",
        business_impact=5,
        failure_probability=4,
        user_frequency=5,
        implementation_complexity=3,
        risk_score=4.35,
        priority="High",
        rationale="Login controls access.",
    )
    coverage = CoverageItem(
        coverage_id="COV-REQ-001-01",
        requirement_id="REQ-001",
        module="Login",
        coverage_type="Equivalence Partitioning",
        coverage_item="Valid login",
        selected_test_design_technique="Equivalence Partitioning",
        rationale="Valid partition.",
        priority="High",
    )
    test = TestCase(
        test_case_id="TC-001",
        requirement_id="REQ-001",
        coverage_id="COV-REQ-001-01",
        module="Login",
        technique="Equivalence Partitioning",
        priority="High",
        test_data={"username": "user"},
        steps=["Login"],
        expected_result="Dashboard is visible.",
        automation_feasibility=0.95,
    )
    optimized = optimize_test_suite([test], [risk])

    export_artifacts(
        tmp_path,
        [requirement],
        [risk],
        [coverage],
        [test],
        [],
        [ReviewLogEntry(artifact_type="test", action="generate", before_summary="0", after_summary="1")],
        optimized,
    )

    with (tmp_path / "test_cases.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["optimization_score"]
    assert rows[0]["selected_for_smoke"] == "True"
    assert rows[0]["selected_for_regression"] == "True"
