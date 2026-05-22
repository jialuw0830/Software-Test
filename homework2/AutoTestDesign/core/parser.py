"""Requirement parsing and structuring."""

from __future__ import annotations

import re
from pydantic import ValidationError

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
    fallback_reason = ""
    if llm_result:
        if not _is_over_consolidated(raw_text, llm_result):
            return llm_result
        explicit_ids = _explicit_requirement_ids(raw_text)
        fallback_reason = (
            "LLM output appears over-consolidated "
            f"({len(llm_result)} parsed requirement(s), {len(explicit_ids)} explicit requirement ID(s) in source)."
        )
    else:
        fallback_reason = "LLM parsing returned no valid structured requirements."

    pairs = _extract_requirement_pairs(raw_text)
    print(
        "[AutoTestDesign][RequirementParser] Falling back to deterministic parser. "
        f"Reason: {fallback_reason} "
        f"Extracted {len(pairs)} requirement block(s): {[req_id for req_id, _ in pairs]}"
    )
    return [_structure_requirement(req_id, text) for req_id, text in pairs]


def parse_uploaded_file(file_name: str, content: bytes, llm_client: LLMClient) -> list[StructuredRequirement]:
    lower_name = file_name.lower()
    if lower_name.endswith(".csv"):
        from io import BytesIO

        return parse_requirements_from_dataframe(pd.read_csv(BytesIO(content)))
    return parse_requirements_from_text(content.decode("utf-8"), llm_client)


def _try_llm_parse(raw_text: str, llm_client: LLMClient) -> list[StructuredRequirement]:
    with open("prompts/requirement_parser.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()
    prompt = prompt_template.replace("{user_input}", raw_text)
    if hasattr(llm_client, "generate_json_with_raw"):
        data, raw_output = llm_client.generate_json_with_raw(
            prompt,
            "You are a software testing requirement parser. Return JSON only.",
        )
    else:
        data = llm_client.generate_json(prompt, "You are a software testing requirement parser. Return JSON only.")
        raw_output = "[raw output unavailable for this llm_client]"

    print("[AutoTestDesign][RequirementParser] Raw LLM output start")
    print(raw_output)
    print("[AutoTestDesign][RequirementParser] Raw LLM output end")

    if not isinstance(data, list):
        print(
            "[AutoTestDesign][RequirementParser] LLM output was not parsed as a JSON array. "
            f"Parsed type: {type(data).__name__}"
        )
        return []
    parsed: list[StructuredRequirement] = []
    for index, item in enumerate(data, start=1):
        try:
            parsed.append(StructuredRequirement(**item))
        except ValidationError as exc:
            print(
                "[AutoTestDesign][RequirementParser] Dropped LLM requirement item "
                f"#{index} due to schema validation error: {exc}"
            )
            print(f"[AutoTestDesign][RequirementParser] Invalid item #{index}: {item}")
        except Exception as exc:
            print(
                "[AutoTestDesign][RequirementParser] Dropped LLM requirement item "
                f"#{index} due to unexpected error: {exc}"
            )
            print(f"[AutoTestDesign][RequirementParser] Invalid item #{index}: {item}")
            continue
    print(
        "[AutoTestDesign][RequirementParser] Parsed "
        f"{len(parsed)} valid structured requirement(s) from {len(data)} LLM item(s)."
    )
    return parsed


def _is_over_consolidated(raw_text: str, parsed: list[StructuredRequirement]) -> bool:
    explicit_ids = _explicit_requirement_ids(raw_text)
    if len(explicit_ids) < 3:
        return False
    parsed_ids = {req.requirement_id for req in parsed}
    matched_ids = explicit_ids & parsed_ids
    if len(parsed) == 1 and len(explicit_ids) > 1:
        return True
    return len(matched_ids) < max(2, len(explicit_ids) // 2)


def _explicit_requirement_ids(raw_text: str) -> set[str]:
    return set(
        re.findall(
            r"\b((?:FR|NFR|REQ|CTX)-[A-Z0-9-]+)\b",
            raw_text,
            flags=re.I,
        )
    )

def _extract_requirement_pairs(raw_text: str) -> list[tuple[str, str]]:
    text = raw_text.strip()
    if not text:
        return []

    heading_pattern = re.compile(
        r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\d+[.)][ \t]*)?"
        r"((?:FR|NFR|REQ|CTX)-[A-Z0-9-]+)"
        r"[ \t:：-]*([^\n]*)$",
        re.I | re.M,
    )
    matches = list(heading_pattern.finditer(text))
    pairs = []
    for index, match in enumerate(matches):
        req_id = match.group(1).upper()
        title = match.group(2).strip()
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        cleaned = "\n".join(part.strip() for part in [title, body] if part.strip())
        cleaned = re.sub(r"^#+\s*", "", cleaned.strip())
        if cleaned:
            pairs.append((req_id, cleaned))
    if pairs:
        return pairs

    heading_blocks = re.split(r"\n(?=#{1,6}\s+)", text)
    paragraphs = []
    for block in heading_blocks:
        cleaned = block.strip()
        if not cleaned:
            continue
        if _is_supporting_only_block(cleaned):
            continue
        paragraphs.append(cleaned)
    if paragraphs:
        return [(f"REQ-GEN-{index + 1:03d}", paragraph) for index, paragraph in enumerate(paragraphs)]

    return [(f"REQ-GEN-001", text)]


def _is_supporting_only_block(block: str) -> bool:
    lower = block.lower()
    heading = lower.splitlines()[0].strip("# ").strip()
    supporting_headings = {
        "coverage",
        "coverage items",
        "techniques",
        "test techniques",
        "acceptance criteria",
        "acceptance scenarios",
        "risk level",
        "test priority",
    }
    return heading in supporting_headings


def _structure_requirement(req_id: str, raw_text: str, module_hint: str = "", feature_hint: str = "") -> StructuredRequirement:
    lower = raw_text.lower()
    module = module_hint or _infer_module(req_id, lower)
    feature = feature_hint or _infer_feature(lower)
    input_fields = _infer_input_fields(lower)
    main_actions = _infer_main_actions(lower)
    data_ranges = _infer_data_ranges(lower)
    conditions = _infer_conditions(lower)
    preconditions = _infer_preconditions(module, lower)
    expected_action = _infer_expected_action(raw_text)
    notes = _infer_ambiguity_notes(lower)
    req_type = "Non-functional" if req_id.startswith("NFR-") else "Functional"
    priority = _infer_requirement_priority(module, lower)
    return StructuredRequirement(
        requirement_id=req_id,
        module=module,
        feature=feature,
        actor="System" if req_type == "Non-functional" else "Shopper",
        preconditions=preconditions,
        input_fields=input_fields,
        main_actions=main_actions,
        data_ranges=data_ranges,
        conditions=conditions,
        expected_action=expected_action,
        requirement_type=req_type,
        risk_level=priority,
        test_priority=priority,
        ambiguity_notes=notes,
        raw_text=raw_text,
    )


def _infer_module(req_id: str, lower: str) -> str:
    if "LOGIN" in req_id or "log in" in lower or "locked_out_user" in lower or "username" in lower:
        return "Login"
    if "CART" in req_id or "cart" in lower:
        return "Cart"
    if "CHECKOUT" in req_id or "checkout" in lower or "order" in lower or "postal" in lower or "tax" in lower:
        return "Checkout"
    if "LOGOUT" in req_id or "log out" in lower:
        return "Navigation"
    if "INVENTORY" in req_id or "inventory" in lower or "sort" in lower or "product" in lower:
        return "Inventory"
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


def _infer_main_actions(lower: str) -> list[str]:
    actions: list[str] = []
    if "log in" in lower or "login" in lower:
        actions.extend(["Enter username", "Enter password", "Click Login"])
    if "sort" in lower:
        actions.append("Select product sort option")
    if "add" in lower and "cart" in lower:
        actions.append("Add product to cart")
    if "remove" in lower and "cart" in lower:
        actions.append("Remove product from cart")
    if "checkout" in lower:
        actions.append("Proceed through checkout")
    if "log out" in lower or "logout" in lower:
        actions.append("Click Logout")
    return actions


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


def _infer_expected_action(raw_text: str) -> list[str]:
    sentence = raw_text.strip()
    if sentence.lower().startswith("the system shall "):
        sentence = sentence[len("The system shall ") :]
    return [sentence[:1].upper() + sentence[1:].rstrip(".")]


def _infer_requirement_priority(module: str, lower: str) -> str:
    if module in {"Login", "Cart", "Checkout"} or any(word in lower for word in ["security", "access control", "tax", "total price"]):
        return "High"
    if module in {"Inventory", "Product Details", "Navigation", "Performance"}:
        return "Medium"
    return "Low"


def _infer_ambiguity_notes(lower: str) -> list[str]:
    notes: list[str] = []
    if "correctly" in lower:
        notes.append("Exact calculation precision and tax rule should be verified against the application oracle.")
    if "one or more" in lower:
        notes.append("Upper bound for selected products is not explicitly specified.")
    if "error message" in lower:
        notes.append("Exact error text should be confirmed during test design review.")
    return notes
