"""Test suite optimization using risk, coverage gain, automation value, and history."""

from __future__ import annotations

from collections import Counter

from .schemas import ExecutionResult, RiskAssessment, TestCase


def optimize_test_suite(
    test_cases: list[TestCase],
    risks: list[RiskAssessment] | None = None,
    execution_history: list[ExecutionResult] | None = None,
) -> list[TestCase]:
    risk_scores = {risk.requirement_id: risk.risk_score for risk in risks or []}
    technique_counts = Counter(test.technique for test in test_cases)

    failing_case_ids = {
        result.test_case_id
        for result in execution_history or []
        if result.result.lower() in {"fail", "failed", "blocked"}
    }

    optimized: list[TestCase] = []
    for test in test_cases:
        normalized_risk_score = min(risk_scores.get(test.requirement_id, 3.0) / 5.0, 1.0)
        coverage_gain = 1.0 / max(technique_counts.get(test.technique, 1), 1)
        automation_feasibility = test.automation_feasibility
        historical_failure_score = 1.0 if test.test_case_id in failing_case_ids else 0.25 if test.priority == "High" else 0.0
        score = round(
            0.45 * normalized_risk_score
            + 0.25 * coverage_gain
            + 0.20 * automation_feasibility
            + 0.10 * historical_failure_score,
            3,
        )
        data = test.model_dump()
        data["optimization_score"] = score
        optimized.append(TestCase(**data))

    return sorted(
        optimized,
        key=lambda item: (
            item.optimization_score or 0.0,
            {"High": 3, "Medium": 2, "Low": 1}.get(item.priority, 0),
            item.automation_feasibility,
        ),
        reverse=True,
    )
