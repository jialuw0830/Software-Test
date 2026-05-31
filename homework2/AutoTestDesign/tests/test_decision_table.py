from __future__ import annotations

from core.decision_table import generate_decision_table_rules
from core.schemas import TestCase


def test_generate_decision_table_rules_from_rule_list() -> None:
    test = TestCase(
        test_case_id="TC-001",
        requirement_id="REQ-LOGIN-001",
        coverage_id="COV-REQ-LOGIN-001-01",
        module="Login",
        technique="Decision Table Testing",
        priority="High",
        test_data={
            "decision_table": [
                {"username": "standard_user", "password": "secret_sauce", "expected": "allow"},
                {"username": "locked_out_user", "password": "secret_sauce", "expected": "reject"},
            ]
        },
        steps=["Execute each rule."],
        expected_result="Only valid credentials are allowed.",
    )

    rules = generate_decision_table_rules([test])

    assert len(rules) == 2
    assert rules[0].decision_table_id == "DT-001"
    assert rules[0].generated_test_case_id == "TC-001"
    assert rules[0].action == "allow"
    assert rules[1].action == "reject"


def test_checkout_required_field_cases_share_one_decision_table() -> None:
    tests = [
        TestCase(
            test_case_id="TC-014",
            requirement_id="REQ-CHECKOUT-001",
            coverage_id="COV-REQ-CHECKOUT-001-01",
            module="Checkout",
            technique="Decision Table Testing",
            priority="High",
            test_data={"first_name": "Ada", "last_name": "Lovelace", "postal_code": "10001"},
            steps=["Submit complete checkout information."],
            expected_result="The checkout overview page is displayed.",
        ),
        TestCase(
            test_case_id="TC-015",
            requirement_id="REQ-CHECKOUT-001",
            coverage_id="COV-REQ-CHECKOUT-001-02",
            module="Checkout",
            technique="Decision Table Testing",
            priority="High",
            test_data={"first_name": "", "last_name": "Lovelace", "postal_code": "10001"},
            steps=["Submit checkout information with first name empty."],
            expected_result="Checkout is blocked with a First Name is required error.",
        ),
        TestCase(
            test_case_id="TC-016",
            requirement_id="REQ-CHECKOUT-001",
            coverage_id="COV-REQ-CHECKOUT-001-03",
            module="Checkout",
            technique="Decision Table Testing",
            priority="High",
            test_data={"first_name": "Ada", "last_name": "", "postal_code": "10001"},
            steps=["Submit checkout information with last name empty."],
            expected_result="Checkout is blocked with a Last Name is required error.",
        ),
        TestCase(
            test_case_id="TC-017",
            requirement_id="REQ-CHECKOUT-001",
            coverage_id="COV-REQ-CHECKOUT-001-04",
            module="Checkout",
            technique="Decision Table Testing",
            priority="High",
            test_data={"first_name": "Ada", "last_name": "Lovelace", "postal_code": ""},
            steps=["Submit checkout information with postal code empty."],
            expected_result="Checkout is blocked with a Postal Code is required error.",
        ),
    ]

    rules = generate_decision_table_rules(tests)

    assert len(rules) == 4
    assert {rule.decision_table_id for rule in rules} == {"DT-001"}
    assert [rule.rule_id for rule in rules] == ["DT-001-R01", "DT-001-R02", "DT-001-R03", "DT-001-R04"]
    assert {rule.generated_test_case_id for rule in rules} == {"TC-014", "TC-015", "TC-016", "TC-017"}
