"""Sample SauceDemo requirements used for deterministic demos."""

from __future__ import annotations

import pandas as pd


SAMPLE_REQUIREMENTS: list[dict[str, str]] = [
    {
        "requirement_id": "REQ-LOGIN-001",
        "module": "Login",
        "feature": "Valid login",
        "requirement_text": "The system shall allow a valid standard user to log in with username standard_user and password secret_sauce.",
    },
    {
        "requirement_id": "REQ-LOGIN-002",
        "module": "Login",
        "feature": "Locked-out login rejection",
        "requirement_text": "The system shall reject locked_out_user and display an error message.",
    },
    {
        "requirement_id": "REQ-INVENTORY-001",
        "module": "Inventory",
        "feature": "Inventory page display",
        "requirement_text": "The system shall display the product inventory page after successful login.",
    },
    {
        "requirement_id": "REQ-INVENTORY-002",
        "module": "Inventory",
        "feature": "Product sorting",
        "requirement_text": "The system shall allow the user to sort products by name and price.",
    },
    {
        "requirement_id": "REQ-CART-001",
        "module": "Cart",
        "feature": "Add product to cart",
        "requirement_text": "The system shall allow a logged-in user to add one or more products to the cart.",
    },
    {
        "requirement_id": "REQ-CART-002",
        "module": "Cart",
        "feature": "Cart badge count",
        "requirement_text": "The cart badge shall reflect the number of selected products.",
    },
    {
        "requirement_id": "REQ-CART-003",
        "module": "Cart",
        "feature": "Remove product from cart",
        "requirement_text": "The system shall allow the user to remove products from the cart.",
    },
    {
        "requirement_id": "REQ-CHECKOUT-001",
        "module": "Checkout",
        "feature": "Checkout information validation",
        "requirement_text": "The system shall require first name, last name, and postal code before continuing checkout.",
    },
    {
        "requirement_id": "REQ-CHECKOUT-002",
        "module": "Checkout",
        "feature": "Checkout price calculation",
        "requirement_text": "The checkout overview shall display item total, tax, and total price correctly.",
    },
    {
        "requirement_id": "REQ-CHECKOUT-003",
        "module": "Checkout",
        "feature": "Order completion",
        "requirement_text": "The system shall complete the order after the user confirms checkout.",
    },
    {
        "requirement_id": "REQ-LOGOUT-001",
        "module": "Navigation",
        "feature": "Logout",
        "requirement_text": "The system shall allow the user to log out and return to the login page.",
    },
]


def sample_requirements_df() -> pd.DataFrame:
    return pd.DataFrame(SAMPLE_REQUIREMENTS)


def sample_requirements_markdown() -> str:
    lines = ["# SauceDemo Sample Requirements", ""]
    for item in SAMPLE_REQUIREMENTS:
        lines.append(f"## {item['requirement_id']}: {item['feature']}")
        lines.append(item["requirement_text"])
        lines.append("")
    return "\n".join(lines)
