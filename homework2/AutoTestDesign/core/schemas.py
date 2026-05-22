"""Pydantic schemas shared across the AutoTestDesign pipeline."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class InputField(BaseModel):
    name: str
    field_type: str = "text"
    required: bool = True
    examples: list[str] = Field(default_factory=list)


class StructuredRequirement(BaseModel):
    requirement_id: str
    module: str
    feature: str
    actor: str = "End user"
    preconditions: list[str] = Field(default_factory=list)
    input_fields: list[object] = Field(default_factory=list)
    main_actions: list[str] = Field(default_factory=list)
    data_ranges: dict[str, object] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)
    expected_action: list[str] = Field(default_factory=list)
    requirement_type: str = "Functional"
    risk_level: str = "Medium"
    test_priority: str = "Medium"
    coverage_items: list[str] = Field(default_factory=list)
    test_techniques: list[str] = Field(default_factory=list)
    acceptance_scenarios: list[str] = Field(default_factory=list)
    ambiguity_notes: list[str] = Field(default_factory=list)
    raw_text: str = ""

    @field_validator(
        "preconditions",
        "main_actions",
        "conditions",
        "expected_action",
        "coverage_items",
        "test_techniques",
        "acceptance_scenarios",
        "ambiguity_notes",
        mode="before",
    )
    @classmethod
    def _coerce_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)]

    @field_validator("input_fields", mode="before")
    @classmethod
    def _coerce_input_fields(cls, value: object) -> list[object]:
        if value is None:
            return []
        if isinstance(value, list):
            fields = []
            for item in value:
                if isinstance(item, dict):
                    fields.append(item)
                elif isinstance(item, str) and item.strip():
                    fields.append({"name": item, "field_type": "text", "required": False, "examples": []})
            return fields
        if isinstance(value, dict):
            return [value]
        if isinstance(value, str) and value.strip():
            return [{"name": value, "field_type": "text", "required": False, "examples": []}]
        return []

    @field_validator("data_ranges", mode="before")
    @classmethod
    def _coerce_data_ranges(cls, value: object) -> dict[str, object]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(key): item for key, item in value.items()}
        if isinstance(value, list):
            return {"values": value}
        if isinstance(value, str) and value.strip():
            return {"description": value}
        return {}


class RiskAssessment(BaseModel):
    requirement_id: str
    module: str
    business_impact: int = Field(ge=1, le=5)
    failure_probability: int = Field(ge=1, le=5)
    user_frequency: int = Field(ge=1, le=5)
    implementation_complexity: int = Field(ge=1, le=5)
    risk_score: float
    priority: str
    rationale: str


class CoverageItem(BaseModel):
    coverage_id: str
    requirement_id: str
    module: str
    coverage_type: str
    coverage_item: str
    selected_test_design_technique: str
    rationale: str
    priority: str


class TestCase(BaseModel):
    test_case_id: str
    requirement_id: str
    coverage_id: str
    module: str
    technique: str
    priority: str
    preconditions: list[str] = Field(default_factory=list)
    test_data: dict[str, object] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    expected_result: str
    automation_feasibility: float = Field(default=0.75, ge=0.0, le=1.0)
    automation_selector_hints: list[str] = Field(default_factory=list)
    traceability_notes: str = ""
    optimization_score: float | None = None


class ReviewLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    artifact_type: str
    action: str
    before_summary: str
    after_summary: str
    reason: str = ""


class TraceabilityRow(BaseModel):
    requirement_id: str
    coverage_id: str
    test_case_id: str
    technique: str
    priority: str
    automated_or_manual: str
    execution_result: str = "Not Run"


class ExecutionResult(BaseModel):
    test_case_id: str
    result: str = "Not Run"
    actual_result: str = ""
    notes: str = ""


class ResultAnalysis(BaseModel):
    total_cases: int
    pass_count: int
    fail_count: int
    blocked_count: int
    not_run_count: int
    pass_rate: float
    failed_high_risk_requirements: list[str] = Field(default_factory=list)
    missing_coverage_suggestions: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


def model_to_dict(model: object) -> dict[str, object]:
    return model.model_dump()
