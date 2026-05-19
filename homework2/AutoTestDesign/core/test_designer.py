"""Black-box test case generation."""

from __future__ import annotations

from .llm_client import LLMClient
from .schemas import CoverageItem, RiskAssessment, TestCase
import json


SELECTORS = {
    "username": '[data-test="username"]',
    "password": '[data-test="password"]',
    "login_button": '[data-test="login-button"]',
    "error": '[data-test="error"]',
    "cart_link": '[data-test="shopping-cart-link"]',
    "checkout": '[data-test="checkout"]',
    "first_name": '[data-test="firstName"]',
    "last_name": '[data-test="lastName"]',
    "postal_code": '[data-test="postalCode"]',
    "continue": '[data-test="continue"]',
    "finish": '[data-test="finish"]',
    "complete_header": '[data-test="complete-header"]',
    "title": '[data-test="title"]',
    "add_backpack": '[data-test="add-to-cart-sauce-labs-backpack"]',
    "remove_backpack": '[data-test="remove-sauce-labs-backpack"]',
}


def generate_test_cases(
    coverage_items: list[CoverageItem],
    risks: list[RiskAssessment],
    llm_client: LLMClient,
) -> list[TestCase]:
    llm_result = _try_llm_test_cases(coverage_items, risks, llm_client)
    if llm_result:
        return llm_result

    return [_case_for_coverage(index, coverage) for index, coverage in enumerate(coverage_items, start=1)]


def _try_llm_test_cases(
    coverage_items: list[CoverageItem],
    risks: list[RiskAssessment],
    llm_client: LLMClient,
) -> list[TestCase]:
    coverage_payload = [item.model_dump() for item in coverage_items]
    risk_payload = [risk.model_dump() for risk in risks]
    with open("prompts/test_case_generation.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()
    coverage_json = json.dumps(coverage_payload, indent=2, ensure_ascii=False)
    risk_json = json.dumps(risk_payload, indent=2, ensure_ascii=False)
    prompt = prompt_template.replace("{coverage_items_json}", coverage_json).replace("{risk_analysis_json}", risk_json)

    data = llm_client.generate_json(prompt, "You are a senior software testing engineer. Return JSON only.")
    if not isinstance(data, list):
        return []
    result: list[TestCase] = []
    for index, item in enumerate(data, start=1):
        try:
            item.setdefault("test_case_id", f"TC-{index:03d}")
            result.append(TestCase(**item))
        except Exception:
            continue
    return result


def _case_for_coverage(index: int, coverage: CoverageItem) -> TestCase:
    name = coverage.coverage_item.lower()
    base = dict(
        test_case_id=f"TC-{index:03d}",
        requirement_id=coverage.requirement_id,
        coverage_id=coverage.coverage_id,
        module=coverage.module,
        technique=coverage.selected_test_design_technique,
        priority=coverage.priority,
        preconditions=["SauceDemo is reachable at https://www.saucedemo.com/."],
        automation_selector_hints=list(SELECTORS.values()),
        traceability_notes=f"Generated from {coverage.coverage_id}: {coverage.coverage_item}",
    )

    def case(test_data, steps, expected_result, automation_feasibility=0.9) -> TestCase:
        return TestCase(
            **base,
            test_data=test_data,
            steps=steps,
            expected_result=expected_result,
            automation_feasibility=automation_feasibility,
        )

    if "valid login" in name or "inventory page visible" in name:
        return case(
            {"username": "standard_user", "password": "secret_sauce"},
            [
                "Open the SauceDemo login page.",
                "Enter username standard_user.",
                "Enter password secret_sauce.",
                "Click Login.",
            ],
            "The inventory page is displayed and the Products title is visible.",
            0.95,
        )
    if "locked-out" in name:
        return case(
            {"username": "locked_out_user", "password": "secret_sauce"},
            [
                "Open the SauceDemo login page.",
                "Enter username locked_out_user.",
                "Enter password secret_sauce.",
                "Click Login.",
            ],
            "Login is rejected and an error message is displayed.",
            0.95,
        )
    if "empty username" in name:
        return case(
            {"username": "", "password": "secret_sauce"},
            ["Open the login page.", "Leave username empty.", "Enter password secret_sauce.", "Click Login."],
            "The system displays a Username is required error.",
            0.95,
        )
    if "empty password" in name:
        return case(
            {"username": "standard_user", "password": ""},
            ["Open the login page.", "Enter username standard_user.", "Leave password empty.", "Click Login."],
            "The system displays a Password is required error.",
            0.95,
        )
    if "invalid user" in name:
        return case(
            {
                "decision_table": [
                    {"username": "standard_user", "password": "secret_sauce", "expected": "allow"},
                    {"username": "standard_user", "password": "wrong", "expected": "reject"},
                    {"username": "locked_out_user", "password": "secret_sauce", "expected": "reject"},
                    {"username": "", "password": "secret_sauce", "expected": "reject"},
                ]
            },
            ["Execute each credential combination in the decision table.", "Record whether login is allowed or rejected."],
            "Only the valid standard_user and secret_sauce combination is allowed.",
        )
    if "name ascending" in name:
        return case(
            {"sort_options": ["az", "za"]},
            ["Log in as standard_user.", "Select Name A to Z.", "Select Name Z to A."],
            "Products are sorted alphabetically ascending and then descending.",
            0.8,
        )
    if "price" in name and "sort" in name:
        return case(
            {"sort_options": ["lohi", "hilo"]},
            ["Log in as standard_user.", "Select Price low to high.", "Select Price high to low."],
            "Products are sorted by numeric price ascending and then descending.",
            0.8,
        )
    if "add one item" in name:
        return case(
            {"product": "Sauce Labs Backpack"},
            ["Log in as standard_user.", "Click Add to cart for Sauce Labs Backpack.", "Open the cart."],
            "The backpack appears in the cart and the cart badge shows 1.",
            0.95,
        )
    if "add multiple" in name:
        return case(
            {"products": ["Sauce Labs Backpack", "Sauce Labs Bike Light"]},
            ["Log in as standard_user.", "Add two products to the cart.", "Open the cart."],
            "Both selected products appear in the cart and the cart badge shows 2.",
            0.85,
        )
    if "badge" in name:
        return case(
            {"cart_quantities": [0, 1, 2]},
            ["Log in as standard_user.", "Observe empty cart state.", "Add one item.", "Add a second item."],
            "Badge is hidden for 0 items, shows 1 for one item, and shows 2 for two items.",
            0.85,
        )
    if "remove item" in name:
        return case(
            {"product": "Sauce Labs Backpack"},
            ["Log in as standard_user.", "Add Sauce Labs Backpack to cart.", "Click Remove.", "Open the cart."],
            "The backpack is removed and the cart badge is cleared.",
            0.95,
        )
    if "cart empty" in name:
        return case(
            {"initial_cart_quantity": 1},
            ["Log in as standard_user.", "Add one product.", "Remove the selected product.", "Open cart."],
            "The cart contains no inventory items after removal.",
            0.85,
        )
    if "all valid fields" in name:
        return case(
            {"first_name": "Ada", "last_name": "Lovelace", "postal_code": "10001"},
            [
                "Log in as standard_user.",
                "Add Sauce Labs Backpack to cart.",
                "Open checkout.",
                "Enter first name, last name, and postal code.",
                "Click Continue.",
            ],
            "The checkout overview page is displayed.",
            0.95,
        )
    if "missing first name" in name:
        return case(
            {"first_name": "", "last_name": "Lovelace", "postal_code": "10001"},
            ["Log in and add an item.", "Start checkout.", "Leave first name empty.", "Click Continue."],
            "Checkout is blocked with a First Name is required error.",
            0.95,
        )
    if "missing last name" in name:
        return case(
            {"first_name": "Ada", "last_name": "", "postal_code": "10001"},
            ["Log in and add an item.", "Start checkout.", "Leave last name empty.", "Click Continue."],
            "Checkout is blocked with a Last Name is required error.",
            0.95,
        )
    if "missing postal" in name:
        return case(
            {"first_name": "Ada", "last_name": "Lovelace", "postal_code": ""},
            ["Log in and add an item.", "Start checkout.", "Leave postal code empty.", "Click Continue."],
            "Checkout is blocked with a Postal Code is required error.",
            0.95,
        )
    if "item total" in name:
        return case(
            {"products": [{"name": "Sauce Labs Backpack", "price": 29.99}]},
            ["Log in and add backpack.", "Proceed to checkout overview.", "Read item total."],
            "Item total equals the sum of selected item prices.",
            0.8,
        )
    if "tax and total" in name:
        return case(
            {"expected_formula": "total = item_total + tax"},
            ["Log in and add backpack.", "Proceed to checkout overview.", "Read item total, tax, and total."],
            "Displayed total equals item total plus tax within cent-level rounding.",
            0.8,
        )
    if "finish order" in name:
        return case(
            {"first_name": "Ada", "last_name": "Lovelace", "postal_code": "10001"},
            ["Log in and add an item.", "Complete checkout information.", "Click Finish."],
            "The order completion page displays Thank you for your order.",
            0.95,
        )
    if "cancel checkout" in name:
        return case(
            {"action": "cancel from checkout overview"},
            ["Log in and add an item.", "Proceed to checkout overview.", "Click Cancel."],
            "The user returns to the inventory page without completing an order.",
            0.8,
        )
    if "logout" in name:
        return case(
            {"username": "standard_user", "password": "secret_sauce"},
            ["Log in as standard_user.", "Open the application menu.", "Click Logout."],
            "The login page is displayed and the username field is visible.",
            0.75,
        )

    return case(
        {},
        ["Execute the requirement behavior under representative valid and invalid inputs."],
        "The observed behavior matches the structured requirement.",
        0.55,
    )
