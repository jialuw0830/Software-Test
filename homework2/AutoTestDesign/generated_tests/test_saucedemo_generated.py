"""Generated Playwright tests for SauceDemo.

Run with:
    pytest generated_tests/
"""

from __future__ import annotations

import os
import re

from playwright.sync_api import Page, expect


BASE_URL = os.getenv("SAUCEDEMO_URL", "https://www.saucedemo.com/")


def login(page: Page, username: str = "standard_user", password: str = "secret_sauce") -> None:
    page.goto(BASE_URL)
    page.locator('[data-test="username"]').fill(username)
    page.locator('[data-test="password"]').fill(password)
    page.locator('[data-test="login-button"]').click()


def add_backpack_to_cart(page: Page) -> None:
    page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click()
    expect(page.locator('[data-test="remove-sauce-labs-backpack"]')).to_be_visible()


def go_to_checkout(page: Page) -> None:
    page.locator('[data-test="shopping-cart-link"]').click()
    page.locator('[data-test="checkout"]').click()


def fill_checkout_info(page: Page, first_name: str, last_name: str, postal_code: str) -> None:
    page.locator('[data-test="firstName"]').fill(first_name)
    page.locator('[data-test="lastName"]').fill(last_name)
    page.locator('[data-test="postalCode"]').fill(postal_code)
    page.locator('[data-test="continue"]').click()


def start_checkout_with_backpack(page: Page) -> None:
    login(page)
    expect(page.locator('[data-test="title"]')).to_have_text("Products")
    add_backpack_to_cart(page)
    go_to_checkout(page)


def currency_value(text: str) -> float:
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", text)
    assert match, f"No numeric currency value found in {text!r}"
    return float(match.group(0))


def test_valid_login_with_standard_user(page: Page) -> None:
    login(page, "standard_user", "secret_sauce")
    expect(page.locator('[data-test="title"]')).to_have_text("Products")
    expect(page.locator(".inventory_item")).to_have_count(6)


def test_locked_out_user_rejected(page: Page) -> None:
    login(page, "locked_out_user", "secret_sauce")
    expect(page.locator('[data-test="error"]')).to_be_visible()
    expect(page.locator('[data-test="error"]')).to_contain_text("locked out")


def test_add_item_to_cart(page: Page) -> None:
    login(page)
    add_backpack_to_cart(page)
    expect(page.locator('[data-test="shopping-cart-badge"]')).to_have_text("1")
    page.locator('[data-test="shopping-cart-link"]').click()
    expect(page.get_by_text("Sauce Labs Backpack")).to_be_visible()


def test_remove_item_from_cart(page: Page) -> None:
    login(page)
    add_backpack_to_cart(page)
    page.locator('[data-test="remove-sauce-labs-backpack"]').click()
    expect(page.locator('[data-test="add-to-cart-sauce-labs-backpack"]')).to_be_visible()
    expect(page.locator('[data-test="shopping-cart-badge"]')).to_have_count(0)


def test_checkout_missing_first_name(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "", "Lovelace", "10001")
    expect(page.locator('[data-test="error"]')).to_contain_text("First Name is required")


def test_checkout_missing_last_name(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "Ada", "", "10001")
    expect(page.locator('[data-test="error"]')).to_contain_text("Last Name is required")


def test_checkout_missing_postal_code(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "Ada", "Lovelace", "")
    expect(page.locator('[data-test="error"]')).to_contain_text("Postal Code is required")


def test_successful_checkout(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "Ada", "Lovelace", "10001")
    expect(page.locator('[data-test="title"]')).to_have_text("Checkout: Overview")
    page.locator('[data-test="finish"]').click()
    expect(page.locator('[data-test="complete-header"]')).to_contain_text("Thank you for your order")


def test_price_total_oracle(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "Ada", "Lovelace", "10001")
    item_total = currency_value(page.locator('[data-test="subtotal-label"]').inner_text())
    tax = currency_value(page.locator('[data-test="tax-label"]').inner_text())
    total = currency_value(page.locator('[data-test="total-label"]').inner_text())
    assert round(item_total + tax, 2) == round(total, 2)


def test_order_completion(page: Page) -> None:
    start_checkout_with_backpack(page)
    fill_checkout_info(page, "Ada", "Lovelace", "10001")
    page.locator('[data-test="finish"]').click()
    expect(page.locator('[data-test="complete-header"]')).to_have_text("Thank you for your order!")
    expect(page.locator('[data-test="back-to-products"]')).to_be_visible()
