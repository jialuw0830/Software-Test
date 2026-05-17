"""Traceability matrix generation."""

from __future__ import annotations

from .schemas import CoverageItem, ExecutionResult, StructuredRequirement, TestCase, TraceabilityRow


def generate_traceability_matrix(
    requirements: list[StructuredRequirement],
    coverage_items: list[CoverageItem],
    test_cases: list[TestCase],
    execution_results: list[ExecutionResult] | None = None,
) -> list[TraceabilityRow]:
    known_requirements = {req.requirement_id for req in requirements}
    known_coverage = {item.coverage_id for item in coverage_items}
    result_by_id = {result.test_case_id: result.result for result in execution_results or []}
    rows: list[TraceabilityRow] = []
    for test in test_cases:
        if test.requirement_id not in known_requirements or test.coverage_id not in known_coverage:
            continue
        rows.append(
            TraceabilityRow(
                requirement_id=test.requirement_id,
                coverage_id=test.coverage_id,
                test_case_id=test.test_case_id,
                technique=test.technique,
                priority=test.priority,
                automated_or_manual="Automated" if test.automation_feasibility >= 0.75 else "Manual / Assisted",
                execution_result=result_by_id.get(test.test_case_id, "Not Run"),
            )
        )
    return rows
