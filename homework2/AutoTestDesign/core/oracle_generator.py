"""Oracle generation and execution-result analysis."""

from __future__ import annotations

from .llm_client import LLMClient
from .schemas import ExecutionResult, ResultAnalysis, RiskAssessment, TestCase


def generate_oracle_notes(test_cases: list[TestCase]) -> dict[str, str]:
    notes: dict[str, str] = {}
    for test in test_cases:
        lowered = test.expected_result.lower()
        if "total" in lowered or "tax" in lowered:
            notes[test.test_case_id] = "Validate numeric fields by parsing currency values and comparing item_total + tax to total."
        elif "error" in lowered:
            notes[test.test_case_id] = "Assert the visible error banner appears and contains the expected required-field or locked-user wording."
        elif "inventory" in lowered or "products" in lowered:
            notes[test.test_case_id] = "Assert the inventory title and at least one inventory item are visible."
        elif "completion" in lowered or "thank you" in lowered:
            notes[test.test_case_id] = "Assert the checkout completion header confirms order completion."
        else:
            notes[test.test_case_id] = "Assert visible UI state and traceable business outcome."
    return notes


def analyze_execution_results(
    test_cases: list[TestCase],
    execution_results: list[ExecutionResult],
    risks: list[RiskAssessment],
    llm_client: LLMClient,
) -> ResultAnalysis:
    base = _deterministic_analysis(test_cases, execution_results, risks)
    llm_suggestions = _try_llm_improvements(base, test_cases, execution_results, llm_client)
    if llm_suggestions:
        data = base.model_dump()
        data["improvement_suggestions"] = llm_suggestions
        return ResultAnalysis(**data)
    return base


def _deterministic_analysis(
    test_cases: list[TestCase],
    execution_results: list[ExecutionResult],
    risks: list[RiskAssessment],
) -> ResultAnalysis:
    result_by_id = {result.test_case_id: result for result in execution_results}
    total_cases = len(test_cases)
    pass_count = 0
    fail_count = 0
    blocked_count = 0
    not_run_count = 0
    failed_high_risk: list[str] = []
    high_risk_requirements = {risk.requirement_id for risk in risks if risk.priority == "High"}
    executed_requirements = set()

    for test in test_cases:
        result = result_by_id.get(test.test_case_id)
        status = result.result if result else "Not Run"
        normalized = status.lower().replace(" ", "")
        if normalized == "pass":
            pass_count += 1
            executed_requirements.add(test.requirement_id)
        elif normalized == "fail":
            fail_count += 1
            executed_requirements.add(test.requirement_id)
            if test.requirement_id in high_risk_requirements:
                failed_high_risk.append(test.requirement_id)
        elif normalized == "blocked":
            blocked_count += 1
            executed_requirements.add(test.requirement_id)
            if test.requirement_id in high_risk_requirements:
                failed_high_risk.append(test.requirement_id)
        else:
            not_run_count += 1

    missing_coverage = []
    for req_id in sorted(high_risk_requirements - executed_requirements):
        missing_coverage.append(f"High-risk requirement {req_id} has no executed result yet.")
    if not any("Boundary Value Analysis" == test.technique for test in test_cases):
        missing_coverage.append("Add boundary value tests for critical numeric or required-field inputs.")
    if not any("Decision Table Testing" == test.technique for test in test_cases):
        missing_coverage.append("Add decision table tests for login and checkout validation rules.")

    suggestions = []
    if failed_high_risk:
        suggestions.append("Prioritize defect triage for failed or blocked high-risk requirements before expanding low-risk coverage.")
    if fail_count:
        suggestions.append("Add regression tests around each failed behavior and capture screenshots/logs during reruns.")
    if blocked_count:
        suggestions.append("Unblock environment or test data issues and rerun affected automated cases.")
    if not_run_count:
        suggestions.append("Schedule remaining Not Run cases by optimized order to maximize risk reduction.")
    if not suggestions:
        suggestions.append("Current result set is healthy; next improvement is broader browser/device coverage.")

    pass_rate = round(pass_count / total_cases * 100, 2) if total_cases else 0.0
    return ResultAnalysis(
        total_cases=total_cases,
        pass_count=pass_count,
        fail_count=fail_count,
        blocked_count=blocked_count,
        not_run_count=not_run_count,
        pass_rate=pass_rate,
        failed_high_risk_requirements=sorted(set(failed_high_risk)),
        missing_coverage_suggestions=missing_coverage,
        improvement_suggestions=suggestions,
    )


def _try_llm_improvements(
    base: ResultAnalysis,
    test_cases: list[TestCase],
    execution_results: list[ExecutionResult],
    llm_client: LLMClient,
) -> list[str]:
    prompt = (
        "Given this execution result analysis, propose concise software testing improvement "
        "suggestions. Return JSON as {\"suggestions\": [\"...\"]}.\n\n"
        f"Analysis: {base.model_dump()}\n"
        f"Test cases: {[case.test_case_id for case in test_cases]}\n"
        f"Results: {[result.model_dump() for result in execution_results]}"
    )
    data = llm_client.generate_json(prompt, "You are a test improvement analyst. Return JSON only.")
    if isinstance(data, dict) and isinstance(data.get("suggestions"), list):
        return [str(item) for item in data["suggestions"] if str(item).strip()]
    return []
