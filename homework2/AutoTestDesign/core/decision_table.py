"""Decision table artifact generation."""

from __future__ import annotations

from .schemas import DecisionTableRule, TestCase


def generate_decision_table_rules(test_cases: list[TestCase]) -> list[DecisionTableRule]:
    """Generate a reviewable decision-table rule artifact from decision-table test cases."""

    rules: list[DecisionTableRule] = []
    table_sequence = 1
    grouped_single_cases: dict[tuple[str, str, str], str] = {}
    for test in test_cases:
        if test.technique != "Decision Table Testing":
            continue
        data = test.test_data
        rows = data.get("decision_table")
        if isinstance(rows, list):
            table_id = f"DT-{table_sequence:03d}"
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    continue
                rules.append(
                    DecisionTableRule(
                        decision_table_id=table_id,
                        requirement_id=test.requirement_id,
                        module=test.module,
                        rule_id=f"{table_id}-R{index:02d}",
                        condition_name=_condition_name(row),
                        condition_value=_condition_value(row),
                        action=_action(row),
                        expected_result=_expected_result(row, test.expected_result),
                        generated_test_case_id=test.test_case_id,
                    )
                )
            table_sequence += 1
        else:
            group_key = _single_case_group_key(test)
            table_id = grouped_single_cases.get(group_key)
            if table_id is None:
                table_id = f"DT-{table_sequence:03d}"
                grouped_single_cases[group_key] = table_id
                table_sequence += 1
            rule = _rule_from_single_case(table_id, test)
            if rule is not None:
                rule_data = rule.model_dump()
                rule_data["rule_id"] = f"{table_id}-R{_next_rule_number(rules, table_id):02d}"
                rules.append(DecisionTableRule(**rule_data))
    return rules


def _rule_from_single_case(table_id: str, test: TestCase) -> DecisionTableRule | None:
    data = test.test_data
    if not data:
        return None
    return DecisionTableRule(
        decision_table_id=table_id,
        requirement_id=test.requirement_id,
        module=test.module,
        rule_id=f"{table_id}-R01",
        condition_name=", ".join(data.keys()),
        condition_value=", ".join(f"{key}={value!r}" for key, value in data.items()),
        action="allow" if _looks_successful(test.expected_result) else "reject/block",
        expected_result=test.expected_result,
        generated_test_case_id=test.test_case_id,
    )


def _condition_name(row: dict[str, object]) -> str:
    keys = [key for key in row.keys() if key != "expected"]
    return ", ".join(keys)


def _condition_value(row: dict[str, object]) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in row.items() if key != "expected")


def _action(row: dict[str, object]) -> str:
    expected = str(row.get("expected", "")).strip()
    return expected or "evaluate"


def _expected_result(row: dict[str, object], fallback: str) -> str:
    expected = str(row.get("expected", "")).lower()
    if expected == "allow":
        return "Decision outcome allows the workflow to continue."
    if expected == "reject":
        return "Decision outcome rejects or blocks the workflow."
    return fallback


def _looks_successful(expected_result: str) -> bool:
    text = expected_result.lower()
    return not any(word in text for word in ["error", "reject", "blocked", "required", "invalid"])


def _single_case_group_key(test: TestCase) -> tuple[str, str, str]:
    if test.module.lower() == "checkout" and {"first_name", "last_name", "postal_code"} & set(test.test_data.keys()):
        return (test.requirement_id, test.module, "checkout_required_fields")
    return (test.requirement_id, test.module, test.coverage_id)


def _next_rule_number(rules: list[DecisionTableRule], table_id: str) -> int:
    return 1 + sum(1 for rule in rules if rule.decision_table_id == table_id)
