"""Generate pytest + Playwright scripts from AutoTestDesign test cases."""

from __future__ import annotations

import re
from pathlib import Path

from .schemas import TestCase


GENERATED_FILE_NAME = "test_saucedemo_from_artifacts.py"


def generate_playwright_tests(test_cases: list[TestCase], output_dir: Path | str) -> Path:
    """Generate a pytest file from the current test-case artifacts."""

    if not test_cases:
        raise ValueError("At least one test case is required to generate Playwright tests.")

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / GENERATED_FILE_NAME
    target.write_text(_render_module(test_cases), encoding="utf-8")
    return target


def _render_module(test_cases: list[TestCase]) -> str:
    parts = [_module_header()]
    used_names: set[str] = set()
    for test_case in test_cases:
        function_name = _unique_name(_function_name(test_case), used_names)
        parts.append(_render_test_function(function_name, test_case))
    return "\n\n".join(parts).rstrip() + "\n"


def _module_header() -> str:
    return '''"""Generated Playwright tests for SauceDemo from AutoTestDesign artifacts.

Run with:
    pytest generated_tests/test_saucedemo_from_artifacts.py
"""

from __future__ import annotations

import os
import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = os.getenv("SAUCEDEMO_URL", "https://www.saucedemo.com/")


PRODUCT_SELECTORS = {
    "Sauce Labs Backpack": "[data-test='add-to-cart-sauce-labs-backpack']",
    "Sauce Labs Bike Light": "[data-test='add-to-cart-sauce-labs-bike-light']",
    "Sauce Labs Bolt T-Shirt": "[data-test='add-to-cart-sauce-labs-bolt-t-shirt']",
    "Sauce Labs Fleece Jacket": "[data-test='add-to-cart-sauce-labs-fleece-jacket']",
    "Sauce Labs Onesie": "[data-test='add-to-cart-sauce-labs-onesie']",
    "Test.allTheThings() T-Shirt (Red)": "[data-test='add-to-cart-test.allthethings()-t-shirt-(red)']",
}


def login(page: Page, username: str = "standard_user", password: str = "secret_sauce") -> None:
    page.goto(BASE_URL)
    page.locator("[data-test='username']").fill(username)
    page.locator("[data-test='password']").fill(password)
    page.locator("[data-test='login-button']").click()


def add_product_to_cart(page: Page, product_name: str = "Sauce Labs Backpack") -> None:
    selector = PRODUCT_SELECTORS.get(product_name)
    if selector is None:
        pytest.skip(f"No stable generated selector for product: {product_name}")
    page.locator(selector).click()


def go_to_checkout(page: Page) -> None:
    page.locator("[data-test='shopping-cart-link']").click()
    page.locator("[data-test='checkout']").click()


def fill_checkout_info(page: Page, first_name: str, last_name: str, postal_code: str) -> None:
    page.locator("[data-test='firstName']").fill(first_name)
    page.locator("[data-test='lastName']").fill(last_name)
    page.locator("[data-test='postalCode']").fill(postal_code)
    page.locator("[data-test='continue']").click()


def start_checkout(page: Page, products: list[str] | None = None) -> None:
    login(page)
    expect(page.locator("[data-test='title']")).to_have_text("Products")
    for product in products or ["Sauce Labs Backpack"]:
        add_product_to_cart(page, product)
    go_to_checkout(page)


def currency_value(text: str) -> float:
    match = re.search(r"[-+]?[0-9]*\\.?[0-9]+", text)
    assert match, f"No numeric currency value found in {text!r}"
    return float(match.group(0))
'''


def _render_test_function(function_name: str, test_case: TestCase) -> str:
    body = _automation_body(test_case)
    doc = (
        f"{test_case.test_case_id}: requirement={test_case.requirement_id}; "
        f"coverage={test_case.coverage_id}; technique={test_case.technique}"
    )
    fixture_args = "" if _is_skip_only_body(body) else "page: Page"
    lines = [f"def {function_name}({fixture_args}) -> None:", f"    {doc!r}"]
    lines.extend(f"    {line}" for line in body)
    return "\n".join(lines)


def _automation_body(test_case: TestCase) -> list[str]:
    data = test_case.test_data
    expected = test_case.expected_result.lower()
    module = test_case.module.lower()

    if _is_checkout_calculation(test_case):
        return _checkout_calculation_body(data)
    if _is_checkout_fields(data):
        return _checkout_fields_body(data, expected)
    if "completion" in expected or "thank you" in expected or "order completion" in expected:
        return _order_completion_body(data)
    if "login" in module or "username" in data or "password" in data:
        return _login_body(data, expected)
    if "cart" in module or "product" in data or "products" in data or "cart_quantity" in data:
        return _cart_body(data, expected)

    return [
        f"pytest.skip({_skip_reason(test_case)!r})",
    ]


def _login_body(data: dict[str, object], expected: str) -> list[str]:
    username = str(data.get("username", "standard_user"))
    password = str(data.get("password", "secret_sauce"))
    lines = [f"login(page, {username!r}, {password!r})"]
    if _expects_error(expected):
        lines.append("expect(page.locator(\"[data-test='error']\")).to_be_visible()")
        error_text = _expected_error_text(data, expected)
        if error_text:
            lines.append(f"expect(page.locator(\"[data-test='error']\")).to_contain_text({error_text!r})")
        lines.append("expect(page.locator(\"[data-test='title']\")).to_have_count(0)")
    else:
        lines.append("expect(page.locator(\"[data-test='title']\")).to_have_text(\"Products\")")
        lines.append("expect(page.locator('.inventory_item')).to_have_count(6)")
    return lines


def _checkout_fields_body(data: dict[str, object], expected: str) -> list[str]:
    first_name = str(data.get("first_name", data.get("firstName", "Ada")))
    last_name = str(data.get("last_name", data.get("lastName", "Lovelace")))
    postal_code = str(data.get("postal_code", data.get("postalCode", "10001")))
    lines = [
        "start_checkout(page)",
        f"fill_checkout_info(page, {first_name!r}, {last_name!r}, {postal_code!r})",
    ]
    if _expects_error(expected) or not first_name or not last_name or not postal_code:
        lines.append("expect(page.locator(\"[data-test='error']\")).to_be_visible()")
        error_text = _checkout_error_text(first_name, last_name, postal_code, expected)
        if error_text:
            lines.append(f"expect(page.locator(\"[data-test='error']\")).to_contain_text({error_text!r})")
    else:
        lines.append("expect(page.locator(\"[data-test='title']\")).to_have_text(\"Checkout: Overview\")")
    return lines


def _checkout_calculation_body(data: dict[str, object]) -> list[str]:
    products = _product_names(data) or ["Sauce Labs Backpack"]
    return [
        f"start_checkout(page, {products!r})",
        "fill_checkout_info(page, 'Ada', 'Lovelace', '10001')",
        "item_total = currency_value(page.locator(\"[data-test='subtotal-label']\").inner_text())",
        "tax = currency_value(page.locator(\"[data-test='tax-label']\").inner_text())",
        "total = currency_value(page.locator(\"[data-test='total-label']\").inner_text())",
        "assert round(item_total + tax, 2) == round(total, 2)",
    ]


def _order_completion_body(data: dict[str, object]) -> list[str]:
    products = _product_names(data) or ["Sauce Labs Backpack"]
    return [
        f"start_checkout(page, {products!r})",
        "fill_checkout_info(page, 'Ada', 'Lovelace', '10001')",
        "page.locator(\"[data-test='finish']\").click()",
        "expect(page.locator(\"[data-test='complete-header']\")).to_contain_text('Thank you for your order')",
        "expect(page.locator(\"[data-test='back-to-products']\")).to_be_visible()",
    ]


def _cart_body(data: dict[str, object], expected: str) -> list[str]:
    products = _product_names(data)
    quantity = data.get("cart_quantity") or data.get("cart_item_count")
    if not products and quantity in {1, "1"}:
        products = ["Sauce Labs Backpack"]
    if not products and quantity in {2, "2", "multiple"}:
        products = ["Sauce Labs Backpack", "Sauce Labs Bike Light"]
    if not products and ("empty" in expected or quantity in {0, "0"}):
        return [
            "login(page)",
            "page.locator(\"[data-test='shopping-cart-link']\").click()",
            "expect(page.locator('.cart_item')).to_have_count(0)",
            "expect(page.locator(\"[data-test='shopping-cart-badge']\")).to_have_count(0)",
        ]
    if not products:
        return ["pytest.skip('Cart case lacks concrete product data for generated automation')"]
    lines = ["login(page)"]
    for product in products:
        lines.append(f"add_product_to_cart(page, {product!r})")
    lines.append("page.locator(\"[data-test='shopping-cart-link']\").click()")
    lines.append(f"expect(page.locator('.cart_item')).to_have_count({len(products)})")
    lines.append(f"expect(page.locator(\"[data-test='shopping-cart-badge']\")).to_have_text({str(len(products))!r})")
    return lines


def _is_checkout_fields(data: dict[str, object]) -> bool:
    return any(key in data for key in ["first_name", "firstName", "last_name", "lastName", "postal_code", "postalCode"])


def _is_checkout_calculation(test_case: TestCase) -> bool:
    expected = test_case.expected_result.lower()
    return "subtotal" in expected or "tax" in expected or "total" in expected or "calculation" in expected


def _expects_error(expected: str) -> bool:
    return any(word in expected for word in ["error", "reject", "blocked", "required", "locked", "invalid"])


def _expected_error_text(data: dict[str, object], expected: str) -> str:
    if data.get("username", None) == "":
        return "Username is required"
    if data.get("password", None) == "":
        return "Password is required"
    if "locked" in expected or data.get("username") == "locked_out_user":
        return "locked out"
    if "match" in expected or "invalid" in expected or "reject" in expected:
        return "Username and password do not match"
    return ""


def _checkout_error_text(first_name: str, last_name: str, postal_code: str, expected: str) -> str:
    if not first_name:
        return "First Name is required"
    if not last_name:
        return "Last Name is required"
    if not postal_code:
        return "Postal Code is required"
    if "first name" in expected:
        return "First Name is required"
    if "last name" in expected:
        return "Last Name is required"
    if "postal" in expected or "zip" in expected:
        return "Postal Code is required"
    return ""


def _product_names(data: dict[str, object]) -> list[str]:
    products = data.get("products")
    if isinstance(products, list):
        names = []
        for product in products:
            if isinstance(product, dict) and product.get("name"):
                names.append(str(product["name"]))
            elif isinstance(product, str):
                names.append(product)
        return names
    product = data.get("product")
    if isinstance(product, str) and product:
        return [product]
    return []


def _function_name(test_case: TestCase) -> str:
    raw = f"test_{test_case.test_case_id}_{test_case.module}_{test_case.technique}"
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()


def _unique_name(name: str, used_names: set[str]) -> str:
    candidate = name
    suffix = 2
    while candidate in used_names:
        candidate = f"{name}_{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def _skip_reason(test_case: TestCase) -> str:
    return (
        "Manual or assisted case generated from artifact "
        f"{test_case.test_case_id}; unsupported automated mapping for {test_case.technique}."
    )


def _is_skip_only_body(body: list[str]) -> bool:
    return len(body) == 1 and body[0].startswith("pytest.skip(")
