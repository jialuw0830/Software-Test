"""Requirement parsing and structuring."""

from __future__ import annotations

import re

import pandas as pd

from .llm_client import LLMClient
from .schemas import InputField, StructuredRequirement


def parse_requirements_from_dataframe(df: pd.DataFrame) -> list[StructuredRequirement]:
    normalized = {column.lower().strip(): column for column in df.columns}
    id_col = normalized.get("requirement_id") or normalized.get("id")
    module_col = normalized.get("module")
    feature_col = normalized.get("feature")
    text_col = normalized.get("requirement_text") or normalized.get("text") or normalized.get("requirement")
    if text_col is None:
        raise ValueError("CSV must contain requirement_text, text, or requirement column.")

    requirements: list[StructuredRequirement] = []
    for index, row in df.iterrows():
        req_id = str(row[id_col]).strip() if id_col else f"REQ-GEN-{index + 1:03d}"
        raw_text = str(row[text_col]).strip()
        module_hint = str(row[module_col]).strip() if module_col else ""
        feature_hint = str(row[feature_col]).strip() if feature_col else ""
        requirements.append(_structure_requirement(req_id, raw_text, module_hint, feature_hint))
    return requirements


def parse_requirements_from_text(raw_text: str, llm_client: LLMClient) -> list[StructuredRequirement]:
    llm_result = _try_llm_parse(raw_text, llm_client)
    if llm_result:
        return llm_result

    pairs = _extract_requirement_pairs(raw_text)
    return [_structure_requirement(req_id, text) for req_id, text in pairs]


def parse_uploaded_file(file_name: str, content: bytes, llm_client: LLMClient) -> list[StructuredRequirement]:
    lower_name = file_name.lower()
    if lower_name.endswith(".csv"):
        from io import BytesIO

        return parse_requirements_from_dataframe(pd.read_csv(BytesIO(content)))
    return parse_requirements_from_text(content.decode("utf-8"), llm_client)


def _try_llm_parse(raw_text: str, llm_client: LLMClient) -> list[StructuredRequirement]:
    prompt = (
        "Parse these software requirements into a JSON array. Each object must include "
        "requirement_id, module, feature, actor, preconditions, input_fields, data_ranges, "
        "conditions, expected_action, requirement_type, ambiguity_notes, raw_text.\n\n"
        f"{raw_text}"
    )
    data = llm_client.generate_json(prompt, "You are a software testing requirement parser. Return JSON only.")
    if not isinstance(data, list):
        return []
    parsed: list[StructuredRequirement] = []
    for item in data:
        try:
            parsed.append(StructuredRequirement(**item))
        except Exception:
            continue
    return parsed


def _extract_requirement_pairs(raw_text: str) -> list[tuple[str, str]]:
    text = raw_text.strip()
    if not text:
        return []

    pattern = re.compile(r"(REQ-[A-Z0-9-]+)\s*:?\s*(.*?)(?=\n\s*(?:##\s*)?REQ-[A-Z0-9-]+\s*:|\Z)", re.S)
    matches = pattern.findall(text)
    pairs = []
    for req_id, body in matches:
        cleaned = re.sub(r"^#+\s*", "", body.strip())
        cleaned = re.sub(r"^[^\n]*\n", "", cleaned).strip() if "\n" in cleaned and len(cleaned.splitlines()[0]) < 80 else cleaned
        if cleaned:
            pairs.append((req_id, cleaned))
    if pairs:
        return pairs

    lines = [line.strip("-* \t") for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return [(f"REQ-GEN-{index + 1:03d}", line) for index, line in enumerate(lines)]


def _structure_requirement(req_id: str, raw_text: str, module_hint: str = "", feature_hint: str = "") -> StructuredRequirement:
    lower = raw_text.lower()
    module = module_hint or _infer_module(req_id, lower)
    feature = feature_hint or _infer_feature(lower)
    input_fields = _infer_input_fields(lower)
    data_ranges = _infer_data_ranges(lower)
    conditions = _infer_conditions(lower)
    preconditions = _infer_preconditions(module, lower)
    expected_action = _infer_expected_action(raw_text)
    notes = _infer_ambiguity_notes(lower)
    req_type = "Business Rule" if "price" in lower or "tax" in lower or "badge" in lower else "Functional"
    return StructuredRequirement(
        requirement_id=req_id,
        module=module,
        feature=feature,
        actor="Shopper / Tester",
        preconditions=preconditions,
        input_fields=input_fields,
        data_ranges=data_ranges,
        conditions=conditions,
        expected_action=expected_action,
        requirement_type=req_type,
        ambiguity_notes=notes,
        raw_text=raw_text,
    )


def _infer_module(req_id: str, lower: str) -> str:
    if "LOGIN" in req_id or "log in" in lower or "locked_out_user" in lower or "username" in lower:
        return "Login"
    if "INVENTORY" in req_id or "inventory" in lower or "sort" in lower or "product" in lower:
        return "Inventory"
    if "CART" in req_id or "cart" in lower:
        return "Cart"
    if "CHECKOUT" in req_id or "checkout" in lower or "order" in lower or "postal" in lower or "tax" in lower:
        return "Checkout"
    if "LOGOUT" in req_id or "log out" in lower:
        return "Navigation"
    return "General"


def _infer_feature(lower: str) -> str:
    candidates = [
        ("locked_out_user", "Locked-out login rejection"),
        ("valid standard user", "Valid login"),
        ("inventory page", "Inventory page display"),
        ("sort", "Product sorting"),
        ("add one or more", "Add product to cart"),
        ("badge", "Cart badge count"),
        ("remove", "Remove product from cart"),
        ("first name", "Checkout information validation"),
        ("item total", "Checkout price calculation"),
        ("complete the order", "Order completion"),
        ("log out", "Logout"),
    ]
    for needle, feature in candidates:
        if needle in lower:
            return feature
    return "Requirement behavior"


def _infer_input_fields(lower: str) -> list[InputField]:
    fields: list[InputField] = []
    if "username" in lower or "log in" in lower or "locked_out_user" in lower:
        fields.append(InputField(name="username", examples=["standard_user", "locked_out_user", ""]))
    if "password" in lower or "log in" in lower:
        fields.append(InputField(name="password", examples=["secret_sauce", ""]))
    if "first name" in lower:
        fields.append(InputField(name="first_name", examples=["Ada", ""]))
    if "last name" in lower:
        fields.append(InputField(name="last_name", examples=["Lovelace", ""]))
    if "postal code" in lower:
        fields.append(InputField(name="postal_code", examples=["10001", ""]))
    if "sort" in lower:
        fields.append(InputField(name="sort_option", field_type="select", examples=["az", "za", "lohi", "hilo"]))
    if "product" in lower or "cart" in lower:
        fields.append(InputField(name="product_id", field_type="inventory_item", examples=["sauce-labs-backpack"]))
    return fields


def _infer_data_ranges(lower: str) -> dict[str, str]:
    ranges: dict[str, str] = {}
    if "username" in lower or "log in" in lower:
        ranges["username"] = "valid user, locked_out_user, empty, unknown user"
    if "password" in lower or "log in" in lower:
        ranges["password"] = "secret_sauce, empty, invalid password"
    if "first name" in lower:
        ranges["first_name"] = "non-empty text; empty value invalid"
    if "last name" in lower:
        ranges["last_name"] = "non-empty text; empty value invalid"
    if "postal code" in lower:
        ranges["postal_code"] = "non-empty postal code; empty value invalid"
    if "price" in lower or "tax" in lower or "total" in lower:
        ranges["price_values"] = "item subtotal >= 0, tax >= 0, total = subtotal + tax"
    if "sort" in lower:
        ranges["sort_option"] = "Name A-Z, Name Z-A, Price low-high, Price high-low"
    if "cart" in lower:
        ranges["cart_quantity"] = "0, 1, multiple selected products"
    return ranges


def _infer_conditions(lower: str) -> list[str]:
    conditions: list[str] = []
    if "valid" in lower:
        conditions.append("Valid credentials are submitted.")
    if "locked_out_user" in lower:
        conditions.append("Locked-out username is submitted.")
    if "logged-in" in lower or "successful login" in lower:
        conditions.append("User has an authenticated session.")
    if "require" in lower:
        conditions.append("Required fields must be present before continuing.")
    if "confirms checkout" in lower:
        conditions.append("Checkout overview has been reached.")
    if "sort" in lower:
        conditions.append("A sort option is selected from the product sort dropdown.")
    return conditions


def _infer_preconditions(module: str, lower: str) -> list[str]:
    if module in {"Inventory", "Cart", "Checkout", "Navigation"}:
        return ["User is on SauceDemo and can access the application.", "User is logged in unless validating login behavior."]
    return ["SauceDemo login page is available."]


def _infer_expected_action(raw_text: str) -> str:
    sentence = raw_text.strip()
    if sentence.lower().startswith("the system shall "):
        sentence = sentence[len("The system shall ") :]
    return sentence[:1].upper() + sentence[1:].rstrip(".")


def _infer_ambiguity_notes(lower: str) -> list[str]:
    notes: list[str] = []
    if "correctly" in lower:
        notes.append("Exact calculation precision and tax rule should be verified against the application oracle.")
    if "one or more" in lower:
        notes.append("Upper bound for selected products is not explicitly specified.")
    if "error message" in lower:
        notes.append("Exact error text should be confirmed during test design review.")
    return notes
