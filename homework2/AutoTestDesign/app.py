from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import streamlit as st

from core.coverage_identifier import identify_coverage_items
from core.artifact_validator import validate_output_artifacts
from core.decision_table import generate_decision_table_rules
from core.exporter import export_artifacts, to_dataframe
from core.llm_client import LLMClient
from core.optimizer import optimize_test_suite
from core.oracle_generator import analyze_execution_results, generate_oracle_notes
from core.parser import parse_requirements_from_dataframe, parse_requirements_from_text, parse_uploaded_file
from core.playwright_generator import generate_playwright_tests
from core.risk_analyzer import calculate_risk_score, priority_for_score, analyze_risk
from core.sample_data import sample_requirements_df, sample_requirements_markdown
from core.schemas import (
    CoverageItem,
    ExecutionResult,
    ReviewLogEntry,
    RiskAssessment,
    StructuredRequirement,
    TestCase,
    model_to_dict,
)
from core.test_designer import generate_test_cases
from core.test_runner import run_generated_tests, write_execution_results_csv
from core.target_context import SAUCEDEMO_CONTEXT, context_from_values
from core.traceability import generate_traceability_matrix


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
GENERATED_TESTS_DIR = BASE_DIR / "generated_tests"

JSON_FIELDS = {
    "preconditions",
    "input_fields",
    "main_actions",
    "data_ranges",
    "conditions",
    "expected_action",
    "coverage_items",
    "test_techniques",
    "acceptance_scenarios",
    "ambiguity_notes",
    "test_data",
    "steps",
    "automation_selector_hints",
    "failed_high_risk_requirements",
    "missing_coverage_suggestions",
    "improvement_suggestions",
}


def init_state() -> None:
    defaults = {
        "raw_requirements": "",
        "requirements": [],
        "risks": [],
        "coverage_items": [],
        "test_cases": [],
        "optimized_cases": [],
        "traceability": [],
        "review_log": [],
        "execution_results": [],
        "result_analysis": None,
        "export_paths": {},
        "generated_test_path": "",
        "target_name": "",
        "target_base_url": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def summarize_records(records: Sequence[object]) -> str:
    if not records:
        return "0 records"
    ids = []
    for item in records[:5]:
        data = model_to_dict(item) if not isinstance(item, dict) else item
        ids.append(
            str(
                data.get("requirement_id")
                or data.get("coverage_id")
                or data.get("test_case_id")
                or data.get("timestamp")
                or "record"
            )
        )
    suffix = "..." if len(records) > 5 else ""
    return f"{len(records)} records: {', '.join(ids)}{suffix}"


def add_review_log(artifact_type: str, action: str, before: Sequence[object], after: Sequence[object], reason: str) -> None:
    st.session_state.review_log.append(
        ReviewLogEntry(
            artifact_type=artifact_type,
            action=action,
            before_summary=summarize_records(before),
            after_summary=summarize_records(after),
            reason=reason,
        )
    )


def parse_json_cell(value: object, default: object) -> object:
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if isinstance(default, list):
            return [line.strip() for line in text.splitlines() if line.strip()]
        return default


def clean_record(row: dict[str, object]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, float) and pd.isna(value):
            value = ""
        if key in JSON_FIELDS:
            default = {} if key in {"data_ranges", "test_data"} else []
            value = parse_json_cell(value, default)
        cleaned[key] = value
    return cleaned


def editor_to_models(df: pd.DataFrame, model_cls: type[object]) -> list[object]:
    models = []
    for row in df.to_dict(orient="records"):
        cleaned = clean_record(row)
        if not any(str(value).strip() for value in cleaned.values()):
            continue
        if model_cls is RiskAssessment:
            for field in ["business_impact", "failure_probability", "user_frequency", "implementation_complexity"]:
                cleaned[field] = int(float(cleaned[field]))
            cleaned["risk_score"] = calculate_risk_score(
                cleaned["business_impact"],
                cleaned["failure_probability"],
                cleaned["user_frequency"],
                cleaned["implementation_complexity"],
            )
            cleaned["priority"] = priority_for_score(cleaned["risk_score"])
        if model_cls is TestCase:
            cleaned["automation_feasibility"] = float(cleaned.get("automation_feasibility") or 0.0)
            if cleaned.get("optimization_score") not in {"", None}:
                cleaned["optimization_score"] = float(cleaned["optimization_score"])
            else:
                cleaned["optimization_score"] = None
        models.append(model_cls(**cleaned))
    return models


def can_run_pipeline() -> bool:
    if st.session_state.requirements:
        return True
    st.warning("Parse or load requirements first.")
    return False


def show_metric_row() -> None:
    cols = st.columns(5)
    cols[0].metric("Requirements", len(st.session_state.requirements))
    cols[1].metric("Risk Items", len(st.session_state.risks))
    cols[2].metric("Coverage Items", len(st.session_state.coverage_items))
    cols[3].metric("Test Cases", len(st.session_state.test_cases))
    cols[4].metric("Review Events", len(st.session_state.review_log))


def main() -> None:
    st.set_page_config(page_title="AutoTestDesign", page_icon="AT", layout="wide")
    init_state()

    st.title("AutoTestDesign")
    st.caption("AI-driven test design pipeline for a configured target application")

    with st.sidebar:
        st.subheader("Runtime")
        try:
            llm_client = LLMClient()
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()
        st.success(llm_client.mode)
        st.session_state.target_name = st.text_input(
            "Target application",
            value=st.session_state.target_name,
            placeholder="e.g. SauceDemo / Swag Labs",
        )
        st.session_state.target_base_url = st.text_input(
            "Target base URL",
            value=st.session_state.target_base_url,
            placeholder="https://example.test/",
        )
        st.write(f"Outputs: `{OUTPUT_DIR}`")
        st.write(f"Generated tests: `{GENERATED_TESTS_DIR}`")

    show_metric_row()

    tabs = st.tabs(
        [
            "Step 1: Requirement Input",
            "Step 2: Structured Requirement Review",
            "Step 3: Risk Analysis Review",
            "Step 4: Coverage Item Review",
            "Step 5: Test Case Review",
            "Step 6: Traceability and Export",
            "Step 7: Playwright/PyTest",
            "Step 8: Results and Improvements",
        ]
    )

    with tabs[0]:
        st.header("Step 1: Requirement Input")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.session_state.raw_requirements = st.text_area(
                "Paste raw requirements",
                value=st.session_state.raw_requirements,
                height=320,
                placeholder="Paste plain-text or Markdown requirements here...",
            )
        with col_b:
            uploaded = st.file_uploader("Upload requirements CSV / TXT / MD", type=["csv", "txt", "md"])
            if st.button("Load SauceDemo Sample Requirements", use_container_width=True):
                before = list(st.session_state.requirements)
                st.session_state.target_name = SAUCEDEMO_CONTEXT.target_name
                st.session_state.target_base_url = SAUCEDEMO_CONTEXT.base_url
                st.session_state.raw_requirements = sample_requirements_markdown()
                st.session_state.requirements = parse_requirements_from_dataframe(sample_requirements_df())
                add_review_log("requirements", "load_sample", before, st.session_state.requirements, "Loaded curated SauceDemo sample requirements.")
                st.success("Sample requirements loaded and structured.")
            if st.button("Parse Requirements", type="primary", use_container_width=True):
                before = list(st.session_state.requirements)
                try:
                    if uploaded is not None:
                        st.session_state.requirements = parse_uploaded_file(uploaded.name, uploaded.read(), llm_client)
                    elif st.session_state.raw_requirements.strip():
                        st.session_state.requirements = parse_requirements_from_text(st.session_state.raw_requirements, llm_client)
                    else:
                        st.warning("Paste requirements or upload a file first.")
                        st.stop()
                    add_review_log("requirements", "parse", before, st.session_state.requirements, "Parsed raw input into structured requirements.")
                    st.success(f"Parsed {len(st.session_state.requirements)} structured requirements.")
                except Exception as exc:
                    st.error(f"Parsing failed: {exc}")

        with st.expander("Sample input preview", expanded=False):
            st.dataframe(sample_requirements_df(), use_container_width=True)

    with tabs[1]:
        st.header("Step 2: Structured Requirement Review")
        if st.session_state.requirements:
            reason = st.text_input("Review reason", value="Human review of structured requirements", key="req_reason")
            edited = st.data_editor(to_dataframe(st.session_state.requirements), num_rows="dynamic", use_container_width=True, key="req_editor")
            if st.button("Apply Requirement Edits", use_container_width=True):
                before = list(st.session_state.requirements)
                try:
                    st.session_state.requirements = editor_to_models(edited, StructuredRequirement)
                    add_review_log("requirements", "manual_edit", before, st.session_state.requirements, reason)
                    st.success("Requirement edits applied.")
                except Exception as exc:
                    st.error(f"Could not apply requirement edits: {exc}")
        else:
            st.info("No structured requirements yet.")

    with tabs[2]:
        st.header("Step 3: Risk Analysis Review")
        if st.button("Run Risk Analysis", type="primary", use_container_width=True):
            if can_run_pipeline():
                before = list(st.session_state.risks)
                st.session_state.risks = analyze_risk(st.session_state.requirements, llm_client)
                add_review_log("risk_analysis", "generate", before, st.session_state.risks, "Generated weighted risk scoring.")
                st.success("Risk analysis complete.")
        if st.session_state.risks:
            reason = st.text_input("Risk review reason", value="Human calibration of factor scores", key="risk_reason")
            edited = st.data_editor(to_dataframe(st.session_state.risks), num_rows="dynamic", use_container_width=True, key="risk_editor")
            if st.button("Apply Risk Edits", use_container_width=True):
                before = list(st.session_state.risks)
                try:
                    st.session_state.risks = editor_to_models(edited, RiskAssessment)
                    add_review_log("risk_analysis", "manual_edit", before, st.session_state.risks, reason)
                    st.success("Risk edits applied and weighted scores recalculated.")
                except Exception as exc:
                    st.error(f"Could not apply risk edits: {exc}")

    with tabs[3]:
        st.header("Step 4: Coverage Item Review")
        if st.button("Generate Coverage Items", type="primary", use_container_width=True):
            if can_run_pipeline():
                before = list(st.session_state.coverage_items)
                st.session_state.coverage_items = identify_coverage_items(
                    st.session_state.requirements,
                    st.session_state.risks,
                    llm_client,
                )
                add_review_log("coverage_items", "generate", before, st.session_state.coverage_items, "Generated coverage using EP, BVA, decision tables, and state transitions.")
                st.success("Coverage items generated.")
        if st.session_state.coverage_items:
            reason = st.text_input("Coverage review reason", value="Human adjustment of coverage strategy", key="coverage_reason")
            edited = st.data_editor(to_dataframe(st.session_state.coverage_items), num_rows="dynamic", use_container_width=True, key="coverage_editor")
            if st.button("Apply Coverage Edits", use_container_width=True):
                before = list(st.session_state.coverage_items)
                try:
                    st.session_state.coverage_items = editor_to_models(edited, CoverageItem)
                    add_review_log("coverage_items", "manual_edit", before, st.session_state.coverage_items, reason)
                    st.success("Coverage edits applied.")
                except Exception as exc:
                    st.error(f"Could not apply coverage edits: {exc}")

    with tabs[4]:
        st.header("Step 5: Test Case Review")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Generate Test Cases", type="primary", use_container_width=True):
                if st.session_state.coverage_items:
                    before = list(st.session_state.test_cases)
                    st.session_state.test_cases = generate_test_cases(st.session_state.coverage_items, st.session_state.risks, llm_client)
                    add_review_log("test_cases", "generate", before, st.session_state.test_cases, "Generated black-box test cases from coverage items.")
                    st.success("Test cases generated.")
                else:
                    st.warning("Generate coverage items first.")
        with col_b:
            if st.button("Optimize Test Suite", use_container_width=True):
                if st.session_state.test_cases:
                    before = list(st.session_state.optimized_cases)
                    st.session_state.optimized_cases = optimize_test_suite(
                        st.session_state.test_cases,
                        st.session_state.risks,
                        st.session_state.execution_results,
                    )
                    add_review_log("test_cases", "optimize", before, st.session_state.optimized_cases, "Applied value-based optimization formula.")
                    st.success("Optimized order generated.")
                else:
                    st.warning("Generate test cases first.")
        if st.session_state.test_cases:
            reason = st.text_input("Test case review reason", value="Human review of generated tests", key="test_reason")
            edited = st.data_editor(to_dataframe(st.session_state.test_cases), num_rows="dynamic", use_container_width=True, key="test_editor")
            if st.button("Apply Test Case Edits", use_container_width=True):
                before = list(st.session_state.test_cases)
                try:
                    st.session_state.test_cases = editor_to_models(edited, TestCase)
                    add_review_log("test_cases", "manual_edit", before, st.session_state.test_cases, reason)
                    st.success("Test case edits applied.")
                except Exception as exc:
                    st.error(f"Could not apply test case edits: {exc}")
        if st.session_state.optimized_cases:
            with st.expander("Optimized execution order", expanded=True):
                st.dataframe(to_dataframe(st.session_state.optimized_cases), use_container_width=True)

    with tabs[5]:
        st.header("Step 6: Traceability Matrix and Export")
        if st.button("Generate Traceability Matrix", type="primary", use_container_width=True):
            if st.session_state.test_cases:
                st.session_state.traceability = generate_traceability_matrix(
                    st.session_state.requirements,
                    st.session_state.coverage_items,
                    st.session_state.test_cases,
                    st.session_state.execution_results,
                )
                st.success("Traceability matrix generated.")
            else:
                st.warning("Generate test cases first.")
        if st.session_state.traceability:
            st.dataframe(to_dataframe(st.session_state.traceability), use_container_width=True)
        if st.button("Export Artifacts", use_container_width=True):
            if st.session_state.requirements and st.session_state.test_cases:
                target_context = context_from_values(st.session_state.target_name, st.session_state.target_base_url)
                if not st.session_state.traceability:
                    st.session_state.traceability = generate_traceability_matrix(
                        st.session_state.requirements,
                        st.session_state.coverage_items,
                        st.session_state.test_cases,
                        st.session_state.execution_results,
                    )
                decision_table_rules = generate_decision_table_rules(st.session_state.test_cases)
                st.session_state.export_paths = export_artifacts(
                    OUTPUT_DIR,
                    st.session_state.requirements,
                    st.session_state.risks,
                    st.session_state.coverage_items,
                    st.session_state.test_cases,
                    st.session_state.traceability,
                    st.session_state.review_log,
                    st.session_state.optimized_cases,
                    st.session_state.result_analysis,
                    decision_table_rules,
                    st.session_state.execution_results,
                )
                issues = validate_output_artifacts(OUTPUT_DIR, target_context.target_name)
                st.session_state.export_paths["artifact_validation_report"] = str(OUTPUT_DIR / "artifact_validation_report.md")
                st.session_state.export_paths["artifact_validation_report_csv"] = str(OUTPUT_DIR / "artifact_validation_report.csv")
                st.success(f"Artifacts exported. Validation issues: {len(issues)}")
            else:
                st.warning("Generate requirements and test cases before export.")
        if st.session_state.export_paths:
            st.dataframe(pd.DataFrame(list(st.session_state.export_paths.items()), columns=["artifact", "path"]), use_container_width=True)

    with tabs[6]:
        st.header("Step 7: Generate Playwright/PyTest Scripts")
        st.write("Generated pytest artifacts use a target-specific adapter when one is configured; otherwise assisted placeholders are created.")
        if st.button("Generate Playwright Tests", type="primary", use_container_width=True):
            if st.session_state.test_cases:
                try:
                    target_context = context_from_values(st.session_state.target_name, st.session_state.target_base_url)
                    path = generate_playwright_tests(st.session_state.test_cases, GENERATED_TESTS_DIR, target_context)
                    st.session_state.generated_test_path = str(path)
                    st.success(f"Generated: {path}")
                except Exception as exc:
                    st.error(f"Could not generate Playwright tests: {exc}")
            else:
                st.warning("Generate test cases first.")
        if st.session_state.generated_test_path:
            path = Path(st.session_state.generated_test_path)
            if path.exists():
                st.code(path.read_text(encoding="utf-8")[:6000], language="python")
                if st.button("Run Generated Tests", use_container_width=True):
                    with st.spinner("Running generated pytest tests..."):
                        try:
                            run_result = run_generated_tests(path, OUTPUT_DIR)
                            before = list(st.session_state.execution_results)
                            st.session_state.execution_results = run_result.execution_results
                            add_review_log(
                                "execution_results",
                                "pytest_run",
                                before,
                                st.session_state.execution_results,
                                f"Ran generated Playwright tests with return code {run_result.return_code}.",
                            )
                            st.success(f"Execution results exported: {run_result.execution_results_csv}")
                            st.write(
                                f"pytest return code: {run_result.return_code}; "
                                f"results: {len(run_result.execution_results)} case(s)"
                            )
                            if run_result.stdout:
                                with st.expander("pytest stdout"):
                                    st.code(run_result.stdout[-6000:], language="text")
                            if run_result.stderr:
                                with st.expander("pytest stderr"):
                                    st.code(run_result.stderr[-6000:], language="text")
                        except Exception as exc:
                            st.error(f"Could not run generated tests: {exc}")
            else:
                st.warning(f"Generated test file is missing: {path}")

    with tabs[7]:
        st.header("Step 8: Upload/Enter Test Execution Results and Generate Improvement Suggestions")
        if st.session_state.test_cases:
            template = pd.DataFrame(
                [
                    {
                        "test_case_id": test.test_case_id,
                        "result": "Not Run",
                        "actual_result": "",
                        "notes": "",
                    }
                    for test in st.session_state.test_cases
                ]
            )
            if st.session_state.execution_results:
                template = to_dataframe(st.session_state.execution_results)
            uploaded_results = st.file_uploader("Upload execution results CSV", type=["csv"], key="results_upload")
            if uploaded_results is not None:
                template = pd.read_csv(uploaded_results)
            edited = st.data_editor(
                template,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "result": st.column_config.SelectboxColumn("result", options=["Pass", "Fail", "Blocked", "Not Run"])
                },
                key="results_editor",
            )
            if st.button("Analyze Results", type="primary", use_container_width=True):
                before = list(st.session_state.execution_results)
                st.session_state.execution_results = [ExecutionResult(**clean_record(row)) for row in edited.to_dict(orient="records")]
                st.session_state.result_analysis = analyze_execution_results(
                    st.session_state.test_cases,
                    st.session_state.execution_results,
                    st.session_state.risks,
                    llm_client,
                )
                st.session_state.traceability = generate_traceability_matrix(
                    st.session_state.requirements,
                    st.session_state.coverage_items,
                    st.session_state.test_cases,
                    st.session_state.execution_results,
                )
                add_review_log("execution_results", "analyze", before, st.session_state.execution_results, "Entered or uploaded execution results and generated improvement suggestions.")
                write_execution_results_csv(st.session_state.execution_results, OUTPUT_DIR / "execution_results.csv")
                st.success("Execution results analyzed.")
        else:
            st.info("Generate test cases before entering results.")

        if st.session_state.result_analysis:
            analysis = st.session_state.result_analysis
            cols = st.columns(5)
            cols[0].metric("Total", analysis.total_cases)
            cols[1].metric("Pass", analysis.pass_count)
            cols[2].metric("Fail", analysis.fail_count)
            cols[3].metric("Blocked", analysis.blocked_count)
            cols[4].metric("Pass Rate", f"{analysis.pass_rate}%")
            st.subheader("Improvement Suggestions")
            for suggestion in analysis.improvement_suggestions:
                st.write(f"- {suggestion}")
            with st.expander("Oracle notes for generated tests"):
                st.dataframe(pd.DataFrame(list(generate_oracle_notes(st.session_state.test_cases).items()), columns=["test_case_id", "oracle_note"]), use_container_width=True)


if __name__ == "__main__":
    main()
