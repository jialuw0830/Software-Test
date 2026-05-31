"""Generated Playwright tests for SauceDemo / Swag Labs from AutoTestDesign artifacts.

Run with:
    pytest generated_tests/test_saucedemo_from_artifacts.py
"""

from __future__ import annotations

import os
import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = os.getenv("TARGET_BASE_URL", os.getenv("SAUCEDEMO_URL", 'https://www.saucedemo.com/'))


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
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", text)
    assert match, f"No numeric currency value found in {text!r}"
    return float(match.group(0))


def test_tc_001_login_equivalence_partitioning(page: Page) -> None:
    'TC-001: requirement=REQ-LOGIN-001; coverage=COV-REQ-LOGIN-001-01; technique=Equivalence Partitioning'
    login(page, 'standard_user', 'secret_sauce')
    expect(page.locator("[data-test='title']")).to_have_text("Products")
    expect(page.locator('.inventory_item')).to_have_count(6)

def test_tc_002_login_boundary_value_analysis(page: Page) -> None:
    'TC-002: requirement=REQ-LOGIN-001; coverage=COV-REQ-LOGIN-001-02; technique=Boundary Value Analysis'
    login(page, '', 'secret_sauce')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('Username is required')
    expect(page.locator("[data-test='title']")).to_have_count(0)

def test_tc_003_login_boundary_value_analysis(page: Page) -> None:
    'TC-003: requirement=REQ-LOGIN-001; coverage=COV-REQ-LOGIN-001-03; technique=Boundary Value Analysis'
    login(page, 'standard_user', '')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('Password is required')
    expect(page.locator("[data-test='title']")).to_have_count(0)

def test_tc_004_login_equivalence_partitioning(page: Page) -> None:
    'TC-004: requirement=REQ-LOGIN-002; coverage=COV-REQ-LOGIN-002-01; technique=Equivalence Partitioning'
    login(page, 'locked_out_user', 'secret_sauce')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('locked out')
    expect(page.locator("[data-test='title']")).to_have_count(0)

def test_tc_005_login_decision_table_testing(page: Page) -> None:
    'TC-005: requirement=REQ-LOGIN-002; coverage=COV-REQ-LOGIN-002-02; technique=Decision Table Testing'
    # decision table rule 1
    login(page, 'standard_user', 'secret_sauce')
    expect(page.locator("[data-test='title']")).to_have_text("Products")
    # decision table rule 2
    login(page, 'standard_user', 'wrong')
    expect(page.locator("[data-test='error']")).to_be_visible()
    # decision table rule 3
    login(page, 'locked_out_user', 'secret_sauce')
    expect(page.locator("[data-test='error']")).to_be_visible()
    # decision table rule 4
    login(page, '', 'secret_sauce')
    expect(page.locator("[data-test='error']")).to_be_visible()

def test_tc_006_inventory_state_transition_testing(page: Page) -> None:
    'TC-006: requirement=REQ-INVENTORY-001; coverage=COV-REQ-INVENTORY-001-01; technique=State Transition Testing'
    login(page, 'standard_user', 'secret_sauce')
    expect(page.locator("[data-test='title']")).to_have_text("Products")
    expect(page.locator('.inventory_item')).to_have_count(6)

def test_tc_007_inventory_equivalence_partitioning(page: Page) -> None:
    'TC-007: requirement=REQ-INVENTORY-002; coverage=COV-REQ-INVENTORY-002-01; technique=Equivalence Partitioning'
    login(page)
    page.locator("[data-test='product-sort-container']").select_option('az')
    expect(page.locator('.inventory_item')).to_have_count(6)
    page.locator("[data-test='product-sort-container']").select_option('za')
    expect(page.locator('.inventory_item')).to_have_count(6)

def test_tc_008_inventory_equivalence_partitioning(page: Page) -> None:
    'TC-008: requirement=REQ-INVENTORY-002; coverage=COV-REQ-INVENTORY-002-02; technique=Equivalence Partitioning'
    login(page)
    page.locator("[data-test='product-sort-container']").select_option('lohi')
    expect(page.locator('.inventory_item')).to_have_count(6)
    page.locator("[data-test='product-sort-container']").select_option('hilo')
    expect(page.locator('.inventory_item')).to_have_count(6)

def test_tc_009_cart_equivalence_partitioning(page: Page) -> None:
    'TC-009: requirement=REQ-CART-001; coverage=COV-REQ-CART-001-01; technique=Equivalence Partitioning'
    login(page)
    add_product_to_cart(page, 'Sauce Labs Backpack')
    page.locator("[data-test='shopping-cart-link']").click()
    expect(page.locator('.cart_item')).to_have_count(1)
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_text('1')

def test_tc_010_cart_boundary_value_analysis(page: Page) -> None:
    'TC-010: requirement=REQ-CART-001; coverage=COV-REQ-CART-001-02; technique=Boundary Value Analysis'
    login(page)
    add_product_to_cart(page, 'Sauce Labs Backpack')
    add_product_to_cart(page, 'Sauce Labs Bike Light')
    page.locator("[data-test='shopping-cart-link']").click()
    expect(page.locator('.cart_item')).to_have_count(2)
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_text('2')

def test_tc_011_cart_boundary_value_analysis(page: Page) -> None:
    'TC-011: requirement=REQ-CART-002; coverage=COV-REQ-CART-002-01; technique=Boundary Value Analysis'
    login(page)
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_count(0)
    add_product_to_cart(page, 'Sauce Labs Backpack')
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_text('1')
    add_product_to_cart(page, 'Sauce Labs Bike Light')
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_text('2')

def test_tc_012_cart_state_transition_testing(page: Page) -> None:
    'TC-012: requirement=REQ-CART-003; coverage=COV-REQ-CART-003-01; technique=State Transition Testing'
    login(page)
    add_product_to_cart(page, 'Sauce Labs Backpack')
    page.locator("[data-test='remove-sauce-labs-backpack']").click()
    page.locator("[data-test='shopping-cart-link']").click()
    expect(page.locator('.cart_item')).to_have_count(0)
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_count(0)

def test_tc_013_cart_boundary_value_analysis(page: Page) -> None:
    'TC-013: requirement=REQ-CART-003; coverage=COV-REQ-CART-003-02; technique=Boundary Value Analysis'
    login(page)
    add_product_to_cart(page, 'Sauce Labs Backpack')
    page.locator("[data-test='remove-sauce-labs-backpack']").click()
    page.locator("[data-test='shopping-cart-link']").click()
    expect(page.locator('.cart_item')).to_have_count(0)
    expect(page.locator("[data-test='shopping-cart-badge']")).to_have_count(0)

def test_tc_014_checkout_decision_table_testing(page: Page) -> None:
    'TC-014: requirement=REQ-CHECKOUT-001; coverage=COV-REQ-CHECKOUT-001-01; technique=Decision Table Testing'
    start_checkout(page)
    fill_checkout_info(page, 'Ada', 'Lovelace', '10001')
    expect(page.locator("[data-test='title']")).to_have_text("Checkout: Overview")

def test_tc_015_checkout_decision_table_testing(page: Page) -> None:
    'TC-015: requirement=REQ-CHECKOUT-001; coverage=COV-REQ-CHECKOUT-001-02; technique=Decision Table Testing'
    start_checkout(page)
    fill_checkout_info(page, '', 'Lovelace', '10001')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('First Name is required')

def test_tc_016_checkout_decision_table_testing(page: Page) -> None:
    'TC-016: requirement=REQ-CHECKOUT-001; coverage=COV-REQ-CHECKOUT-001-03; technique=Decision Table Testing'
    start_checkout(page)
    fill_checkout_info(page, 'Ada', '', '10001')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('Last Name is required')

def test_tc_017_checkout_decision_table_testing(page: Page) -> None:
    'TC-017: requirement=REQ-CHECKOUT-001; coverage=COV-REQ-CHECKOUT-001-04; technique=Decision Table Testing'
    start_checkout(page)
    fill_checkout_info(page, 'Ada', 'Lovelace', '')
    expect(page.locator("[data-test='error']")).to_be_visible()
    expect(page.locator("[data-test='error']")).to_contain_text('Postal Code is required')

def test_tc_018_checkout_boundary_value_analysis(page: Page) -> None:
    'TC-018: requirement=REQ-CHECKOUT-002; coverage=COV-REQ-CHECKOUT-002-01; technique=Boundary Value Analysis'
    start_checkout(page, ['Sauce Labs Backpack'])
    fill_checkout_info(page, 'Ada', 'Lovelace', '10001')
    item_total = currency_value(page.locator("[data-test='subtotal-label']").inner_text())
    tax = currency_value(page.locator("[data-test='tax-label']").inner_text())
    total = currency_value(page.locator("[data-test='total-label']").inner_text())
    assert round(item_total + tax, 2) == round(total, 2)

def test_tc_019_checkout_boundary_value_analysis(page: Page) -> None:
    'TC-019: requirement=REQ-CHECKOUT-002; coverage=COV-REQ-CHECKOUT-002-02; technique=Boundary Value Analysis'
    start_checkout(page, ['Sauce Labs Backpack'])
    fill_checkout_info(page, 'Ada', 'Lovelace', '10001')
    item_total = currency_value(page.locator("[data-test='subtotal-label']").inner_text())
    tax = currency_value(page.locator("[data-test='tax-label']").inner_text())
    total = currency_value(page.locator("[data-test='total-label']").inner_text())
    assert round(item_total + tax, 2) == round(total, 2)

def test_tc_020_checkout_state_transition_testing(page: Page) -> None:
    'TC-020: requirement=REQ-CHECKOUT-003; coverage=COV-REQ-CHECKOUT-003-01; technique=State Transition Testing'
    start_checkout(page)
    fill_checkout_info(page, 'Ada', 'Lovelace', '10001')
    expect(page.locator("[data-test='title']")).to_have_text("Checkout: Overview")

def test_tc_021_checkout_state_transition_testing(page: Page) -> None:
    'TC-021: requirement=REQ-CHECKOUT-003; coverage=COV-REQ-CHECKOUT-003-02; technique=State Transition Testing'
    start_checkout(page, ['Sauce Labs Backpack'])
    fill_checkout_info(page, 'Ada', 'Lovelace', '10001')
    page.locator("[data-test='cancel']").click()
    expect(page.locator("[data-test='title']")).to_have_text("Products")

def test_tc_022_navigation_state_transition_testing(page: Page) -> None:
    'TC-022: requirement=REQ-LOGOUT-001; coverage=COV-REQ-LOGOUT-001-01; technique=State Transition Testing'
    login(page)
    page.locator('#react-burger-menu-btn').click()
    page.locator('#logout_sidebar_link').click()
    expect(page.locator("[data-test='username']")).to_be_visible()
