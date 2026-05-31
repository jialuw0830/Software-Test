"""Target application context for generated artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TargetContext:
    target_name: str = "Target Application"
    base_url: str = ""
    known_selectors: dict[str, str] = field(default_factory=dict)
    known_test_data: dict[str, object] = field(default_factory=dict)

    @property
    def is_saucedemo(self) -> bool:
        name = self.target_name.lower()
        url = self.base_url.lower()
        return "saucedemo" in name or "swag labs" in name or "saucedemo.com" in url


SAUCEDEMO_CONTEXT = TargetContext(
    target_name="SauceDemo / Swag Labs",
    base_url="https://www.saucedemo.com/",
    known_test_data={
        "valid_username": "standard_user",
        "locked_username": "locked_out_user",
        "password": "secret_sauce",
        "product": "Sauce Labs Backpack",
    },
    known_selectors={
        "username": "[data-test='username']",
        "password": "[data-test='password']",
        "login_button": "[data-test='login-button']",
        "error": "[data-test='error']",
        "cart_link": "[data-test='shopping-cart-link']",
        "checkout": "[data-test='checkout']",
        "first_name": "[data-test='firstName']",
        "last_name": "[data-test='lastName']",
        "postal_code": "[data-test='postalCode']",
        "continue": "[data-test='continue']",
        "finish": "[data-test='finish']",
        "title": "[data-test='title']",
    },
)


def context_from_values(target_name: str = "", base_url: str = "") -> TargetContext:
    if "saucedemo" in target_name.lower() or "swag labs" in target_name.lower() or "saucedemo.com" in base_url.lower():
        return SAUCEDEMO_CONTEXT
    return TargetContext(target_name=target_name.strip() or "Target Application", base_url=base_url.strip())
