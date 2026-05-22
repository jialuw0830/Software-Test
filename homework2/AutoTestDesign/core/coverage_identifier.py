"""Coverage item generation from structured requirements and risk."""

from __future__ import annotations

from .llm_client import LLMClient
from .schemas import CoverageItem, RiskAssessment, StructuredRequirement
import json


def identify_coverage_items(
    requirements: list[StructuredRequirement],
    risks: list[RiskAssessment],
    llm_client: LLMClient,
) -> list[CoverageItem]:
    llm_result = _try_llm_coverage(requirements, risks, llm_client)
    if llm_result:
        return llm_result

    risk_priority = {risk.requirement_id: risk.priority for risk in risks}
    return [
        item
        for req in requirements
        for item in _coverage_for_requirement(req, risk_priority.get(req.requirement_id, "Medium"))
    ]


def _try_llm_coverage(
    requirements: list[StructuredRequirement],
    risks: list[RiskAssessment],
    llm_client: LLMClient,
) -> list[CoverageItem]:
    req_payload = [req.model_dump() for req in requirements]
    risk_payload = [risk.model_dump() for risk in risks]

    with open("prompts/coverage_identifier.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()
    req_json = json.dumps(req_payload, indent=2, ensure_ascii=False)
    risk_json = json.dumps(risk_payload, indent=2, ensure_ascii=False)
    prompt = prompt_template.replace("{requirements_json}", req_json).replace("{risks_json}", risk_json)

    data = llm_client.generate_json(prompt, "You are a test design researcher. Return JSON only.")
    if not isinstance(data, list):
        return []
    result: list[CoverageItem] = []
    for item in data:
        try:
            result.append(CoverageItem(**item))
        except Exception:
            continue
    return result


def _coverage_for_requirement(req: StructuredRequirement, priority: str) -> list[CoverageItem]:
    rid = req.requirement_id
    module = req.module
    text = " ".join(
        [
            req.feature,
            " ".join(req.main_actions),
            " ".join(req.conditions),
            " ".join(req.expected_action),
            req.raw_text,
        ]
    ).lower()
    specs: list[tuple[str, str, str, str, str]] = []

    if "REQ-LOGIN-001" in rid or "valid login" in text:
        specs = [
            ("Credential class", "valid login", "Equivalence Partitioning", "Valid user/password pair should authenticate.", priority),
            ("Credential boundary", "empty username", "Boundary Value Analysis", "Empty username is the lower input boundary.", "Medium"),
            ("Credential boundary", "empty password", "Boundary Value Analysis", "Empty password is the lower input boundary.", "Medium"),
        ]
    elif "REQ-LOGIN-002" in rid or "locked_out_user" in text:
        specs = [
            ("Credential class", "locked-out user login", "Equivalence Partitioning", "Locked-out users are a rejected account partition.", priority),
            ("Credential decision", "invalid user/password decision combinations", "Decision Table Testing", "Outcome depends on username state and password validity.", priority),
        ]
    elif "REQ-INVENTORY-001" in rid:
        specs = [
            ("Page state", "inventory page visible after login", "State Transition Testing", "Login success transitions to inventory state.", priority),
        ]
    elif "REQ-INVENTORY-002" in rid or "sort" in text:
        specs = [
            ("Sort options", "sort products by name ascending and descending", "Equivalence Partitioning", "Name sort options form behavior partitions.", priority),
            ("Sort options", "sort products by price low-high and high-low", "Equivalence Partitioning", "Price sort options form behavior partitions.", priority),
        ]
    elif "REQ-CART-001" in rid:
        specs = [
            ("Cart quantity", "add one item to cart", "Equivalence Partitioning", "Single selected product is the base valid partition.", priority),
            ("Cart quantity", "add multiple items to cart", "Boundary Value Analysis", "Multiple products exercises count growth beyond one.", priority),
        ]
    elif "REQ-CART-002" in rid:
        specs = [
            ("Cart badge", "cart badge count for zero, one, and multiple items", "Boundary Value Analysis", "Badge count has important 0/1/many boundaries.", priority),
        ]
    elif "REQ-CART-003" in rid:
        specs = [
            ("Cart quantity", "remove item from cart", "State Transition Testing", "Removing product transitions selected item to unselected.", priority),
            ("Cart quantity", "remove item until cart empty", "Boundary Value Analysis", "Cart empty state is a boundary after removal.", "Medium"),
        ]
    elif "REQ-CHECKOUT-001" in rid:
        specs = [
            ("Checkout decision", "checkout with all valid fields", "Decision Table Testing", "All required fields present allows continuation.", priority),
            ("Checkout decision", "missing first name", "Decision Table Testing", "First name absence must block continuation.", priority),
            ("Checkout decision", "missing last name", "Decision Table Testing", "Last name absence must block continuation.", priority),
            ("Checkout decision", "missing postal code", "Decision Table Testing", "Postal code absence must block continuation.", priority),
        ]
    elif "REQ-CHECKOUT-002" in rid:
        specs = [
            ("Price oracle", "item total calculation", "Boundary Value Analysis", "Subtotal should equal sum of selected item prices.", priority),
            ("Price oracle", "tax and total calculation", "Boundary Value Analysis", "Total should equal subtotal plus tax with displayed precision.", priority),
        ]
    elif "REQ-CHECKOUT-003" in rid:
        specs = [
            ("Checkout workflow", "finish order", "State Transition Testing", "Finish transitions checkout overview to completion.", priority),
            ("Checkout workflow", "cancel checkout", "State Transition Testing", "Cancel should leave checkout without completing an order.", "Medium"),
        ]
    elif "REQ-LOGOUT-001" in rid:
        specs = [
            ("Session state", "logout", "State Transition Testing", "Logout transitions authenticated session back to login page.", priority),
        ]
    else:
        specs = [
            ("Functional behavior", req.feature, "Equivalence Partitioning", "Default behavior partition for stated requirement.", priority),
        ]

    items: list[CoverageItem] = []
    for index, (coverage_type, coverage_item, technique, rationale, item_priority) in enumerate(specs, start=1):
        items.append(
            CoverageItem(
                coverage_id=f"COV-{rid}-{index:02d}",
                requirement_id=rid,
                module=module,
                coverage_type=coverage_type,
                coverage_item=coverage_item,
                selected_test_design_technique=technique,
                rationale=rationale,
                priority=item_priority,
            )
        )
    return items
