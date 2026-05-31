"""Artifact export helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .schemas import model_to_dict


def to_dataframe(records: list[object]) -> pd.DataFrame:
    dicts = [item if isinstance(item, dict) else model_to_dict(item) for item in records]
    if not dicts:
        return pd.DataFrame()
    return pd.DataFrame([_flatten_for_table(item) for item in dicts])


def export_artifacts(
    output_dir: Path | str,
    structured_requirements: list[object],
    risk_analysis: list[object],
    coverage_items: list[object],
    test_cases: list[object],
    traceability_matrix: list[object],
    review_log: list[object],
    optimized_cases: list[object] | None = None,
    result_analysis: object | None = None,
    decision_table_rules: list[object] | None = None,
    execution_results: list[object] | None = None,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    structured_json = out / "structured_requirements.json"
    structured_json.write_text(
        json.dumps([model_to_dict(item) for item in structured_requirements], indent=2),
        encoding="utf-8",
    )
    paths["structured_requirements"] = str(structured_json)

    review_json = out / "review_log.json"
    review_json.write_text(
        json.dumps([model_to_dict(item) for item in review_log], indent=2),
        encoding="utf-8",
    )
    paths["review_log"] = str(review_json)

    exported_test_cases = _merge_optimization_fields(test_cases, optimized_cases or [])

    sheet_map = {
        "risk_analysis": (to_dataframe(risk_analysis), out / "risk_analysis.xlsx"),
        "coverage_items": (to_dataframe(coverage_items), out / "coverage_items.xlsx"),
        "test_cases": (to_dataframe(exported_test_cases), out / "test_cases.xlsx"),
        "traceability_matrix": (to_dataframe(traceability_matrix), out / "traceability_matrix.xlsx"),
    }
    if decision_table_rules is not None:
        sheet_map["decision_table_review"] = (to_dataframe(decision_table_rules), out / "decision_table_review.xlsx")
    if execution_results is not None:
        sheet_map["execution_results"] = (to_dataframe(execution_results), out / "execution_results.xlsx")
    for key, (df, path) in sheet_map.items():
        df.to_excel(path, index=False)
        paths[key] = str(path)

    full_path = out / "full_autotestdesign_artifacts.xlsx"
    with pd.ExcelWriter(full_path, engine="openpyxl") as writer:
        to_dataframe(structured_requirements).to_excel(writer, sheet_name="Requirements", index=False)
        to_dataframe(risk_analysis).to_excel(writer, sheet_name="Risk", index=False)
        to_dataframe(coverage_items).to_excel(writer, sheet_name="Coverage", index=False)
        to_dataframe(exported_test_cases).to_excel(writer, sheet_name="TestCases", index=False)
        to_dataframe(optimized_cases or []).to_excel(writer, sheet_name="Optimized", index=False)
        to_dataframe(traceability_matrix).to_excel(writer, sheet_name="Traceability", index=False)
        to_dataframe(decision_table_rules or []).to_excel(writer, sheet_name="DecisionTables", index=False)
        to_dataframe(execution_results or []).to_excel(writer, sheet_name="ExecutionResults", index=False)
        to_dataframe(review_log).to_excel(writer, sheet_name="ReviewLog", index=False)
        if result_analysis is not None:
            pd.DataFrame([_flatten_for_table(model_to_dict(result_analysis))]).to_excel(
                writer, sheet_name="ResultAnalysis", index=False
            )
    paths["full_artifacts"] = str(full_path)

    for key, df in {
        "risk_analysis": to_dataframe(risk_analysis),
        "coverage_items": to_dataframe(coverage_items),
        "test_cases": to_dataframe(exported_test_cases),
        "traceability_matrix": to_dataframe(traceability_matrix),
        "decision_table_review": to_dataframe(decision_table_rules or []),
        "execution_results": to_dataframe(execution_results or []),
    }.items():
        if df.empty and key in {"decision_table_review", "execution_results"}:
            continue
        csv_path = out / f"{key}.csv"
        df.to_csv(csv_path, index=False)
        paths[f"{key}_csv"] = str(csv_path)

    return paths


def _merge_optimization_fields(test_cases: list[object], optimized_cases: list[object]) -> list[dict[str, object]]:
    optimized_by_id = {
        _record_to_dict(item)["test_case_id"]: _record_to_dict(item)
        for item in optimized_cases
        if _record_to_dict(item).get("test_case_id")
    }
    exported = []
    for item in test_cases:
        data = _record_to_dict(item)
        optimized = optimized_by_id.get(data.get("test_case_id"), {})
        for key in ["optimization_score", "selected_for_smoke", "selected_for_regression"]:
            if key in optimized:
                data[key] = optimized[key]
        exported.append(data)
    return exported


def _record_to_dict(item: object) -> dict[str, object]:
    return item if isinstance(item, dict) else model_to_dict(item)


def _flatten_for_table(item: dict[str, object]) -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, value in item.items():
        if isinstance(value, (list, dict)):
            flattened[key] = json.dumps(value, ensure_ascii=False)
        else:
            flattened[key] = value
    return flattened
