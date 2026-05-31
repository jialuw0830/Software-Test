"""Risk scoring for structured requirements."""

from __future__ import annotations

from .llm_client import LLMClient
from .schemas import RiskAssessment, StructuredRequirement
import json

def calculate_risk_score(
    business_impact: int,
    failure_probability: int,
    user_frequency: int,
    implementation_complexity: int,
) -> float:
    return round(
        0.35 * business_impact
        + 0.25 * failure_probability
        + 0.20 * user_frequency
        + 0.20 * implementation_complexity,
        2,
    )


def priority_for_score(score: float) -> str:
    if score >= 4.0:
        return "High"
    if score >= 2.5:
        return "Medium"
    return "Low"


def analyze_risk(
    requirements: list[StructuredRequirement],
    llm_client: LLMClient,
) -> list[RiskAssessment]:
    llm_result = _try_llm_risk(requirements, llm_client)
    if llm_result:
        return llm_result

    return [_risk_for_requirement(req) for req in requirements]


def _try_llm_risk(requirements: list[StructuredRequirement], llm_client: LLMClient) -> list[RiskAssessment]:
    payload = [req.model_dump() for req in requirements]
    with open("prompts/risk_analysis.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()
    payload_json = json.dumps(payload, indent=2, ensure_ascii=False)
    prompt = prompt_template.replace("{structured_requirements}", payload_json)

    data = llm_client.generate_json(prompt, "You are a software testing risk analyst. Return JSON only.")
    if not isinstance(data, list):
        return []
    result: list[RiskAssessment] = []

    # 添加调试输出
    print("=== LLM Returned Data ===")
    print(data)
    print("=========================")

    for item in data:
        try:
            item["risk_score"] = calculate_risk_score(
                int(item["business_impact"]),
                int(item["failure_probability"]),
                int(item["user_frequency"]),
                int(item["implementation_complexity"]),
            )
            item["priority"] = priority_for_score(float(item["risk_score"]))
            result.append(RiskAssessment(**item))
        except Exception:
            continue
    return result


def _risk_for_requirement(req: StructuredRequirement) -> RiskAssessment:
    text = " ".join(
        [
            req.module,
            req.feature,
            " ".join(req.main_actions),
            " ".join(req.conditions),
            " ".join(req.expected_action),
            req.raw_text,
        ]
    ).lower()
    business_impact = 3
    failure_probability = 3
    user_frequency = 3
    implementation_complexity = 2
    rationale_bits = []

    if "checkout" in text or "order" in text or "tax" in text or "total price" in text or "price calculation" in text:
        business_impact = 5
        user_frequency = 4
        implementation_complexity = 4
        rationale_bits.append("Checkout and payment-like calculations have high user and business impact.")
    if "login" in text or "locked" in text:
        business_impact = max(business_impact, 4)
        user_frequency = 5
        failure_probability = max(failure_probability, 3)
        rationale_bits.append("Authentication is used by almost every user journey.")
    if "cart" in text:
        business_impact = max(business_impact, 4)
        user_frequency = max(user_frequency, 4)
        failure_probability = max(failure_probability, 3)
        rationale_bits.append("Cart state affects checkout readiness and user trust.")
    if "sort" in text or "inventory" in text:
        user_frequency = max(user_frequency, 4)
        failure_probability = max(failure_probability, 2)
        rationale_bits.append("Inventory browsing is frequent but usually lower business risk than checkout.")
    if "calculation" in text or "correctly" in text or "total" in text:
        failure_probability = 4
        implementation_complexity = 5
        rationale_bits.append("Price or tax oracle requires precise calculation validation.")
    if "logout" in text:
        business_impact = 3
        failure_probability = 2
        implementation_complexity = 2
        rationale_bits.append("Logout is important but comparatively simple.")

    desired_priority = req.test_priority or req.risk_level
    if desired_priority == "High":
        business_impact = max(business_impact, 4)
        failure_probability = max(failure_probability, 4)
        user_frequency = max(user_frequency, 4)
        implementation_complexity = max(implementation_complexity, 4)

    score = calculate_risk_score(business_impact, failure_probability, user_frequency, implementation_complexity)
    return RiskAssessment(
        requirement_id=req.requirement_id,
        module=req.module,
        business_impact=business_impact,
        failure_probability=failure_probability,
        user_frequency=user_frequency,
        implementation_complexity=implementation_complexity,
        risk_score=score,
        priority=priority_for_score(score),
        rationale=" ".join(rationale_bits) or "Default risk based on module criticality and observed user workflow frequency.",
    )
