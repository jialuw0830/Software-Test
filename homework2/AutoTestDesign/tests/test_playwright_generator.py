from __future__ import annotations

import py_compile

from core.playwright_generator import generate_playwright_tests
from core.schemas import TestCase as SchemaTestCase


def _case(
    test_case_id: str,
    module: str,
    technique: str,
    test_data: dict[str, object],
    expected_result: str,
) -> SchemaTestCase:
    return SchemaTestCase(
        test_case_id=test_case_id,
        requirement_id="REQ-001",
        coverage_id=f"COV-{test_case_id}",
        module=module,
        technique=technique,
        priority="High",
        test_data=test_data,
        steps=["Generated test step"],
        expected_result=expected_result,
    )


def test_generator_writes_file_without_static_template(tmp_path) -> None:
    test_cases = [
        _case(
            "TC-001",
            "Login",
            "Equivalence Partitioning",
            {"username": "standard_user", "password": "secret_sauce"},
            "The inventory page is displayed and the Products title is visible.",
        )
    ]

    path = generate_playwright_tests(test_cases, tmp_path)

    assert path.name == "test_saucedemo_from_artifacts.py"
    assert path.exists()
    assert "def login(page: Page" in path.read_text(encoding="utf-8")


def test_valid_login_case_generates_inventory_assertion(tmp_path) -> None:
    path = generate_playwright_tests(
        [
            _case(
                "TC-001",
                "Login",
                "Equivalence Partitioning",
                {"username": "standard_user", "password": "secret_sauce"},
                "The inventory page is displayed and the Products title is visible.",
            )
        ],
        tmp_path,
    )

    source = path.read_text(encoding="utf-8")
    assert "login(page, 'standard_user', 'secret_sauce')" in source
    assert "to_have_text(\"Products\")" in source
    py_compile.compile(str(path), doraise=True)


def test_error_login_case_generates_error_assertion(tmp_path) -> None:
    path = generate_playwright_tests(
        [
            _case(
                "TC-002",
                "Login",
                "Decision Table Testing",
                {"username": "locked_out_user", "password": "secret_sauce"},
                "Login is rejected and the locked out error is displayed.",
            )
        ],
        tmp_path,
    )

    source = path.read_text(encoding="utf-8")
    assert "locked out" in source
    assert "[data-test='error']" in source
    py_compile.compile(str(path), doraise=True)


def test_checkout_calculation_case_generates_total_assertion(tmp_path) -> None:
    path = generate_playwright_tests(
        [
            _case(
                "TC-003",
                "Checkout",
                "Boundary Value Analysis",
                {"products": [{"name": "Sauce Labs Backpack", "price": 29.99}]},
                "Displayed total equals item subtotal plus tax.",
            )
        ],
        tmp_path,
    )

    source = path.read_text(encoding="utf-8")
    assert "subtotal-label" in source
    assert "tax-label" in source
    assert "total-label" in source
    assert "round(item_total + tax, 2) == round(total, 2)" in source
    py_compile.compile(str(path), doraise=True)


def test_unsupported_case_is_preserved_as_skip(tmp_path) -> None:
    path = generate_playwright_tests(
        [
            _case(
                "TC-004",
                "Visual",
                "Visual Testing",
                {"screenshot": "baseline"},
                "Visual layout matches the approved baseline.",
            )
        ],
        tmp_path,
    )

    source = path.read_text(encoding="utf-8")
    assert "pytest.skip" in source
    assert "unsupported automated mapping" in source
    py_compile.compile(str(path), doraise=True)
