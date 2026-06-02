# AutoTestDesign

AutoTestDesign is a complete course project for an AI-driven software test design tool. It keeps the test-design tool separate from the target application under test and implements a full pipeline instead of a single prompt-to-tests shortcut:

Requirement Input -> Requirement Structuring -> Risk Analysis -> Coverage Identification -> Strategy Selection -> Test Case Generation -> Human Review -> Traceability -> Export -> Playwright/PyTest Generation -> Execution Result Analysis -> Improvement Suggestions

## Tool Scope

AutoTestDesign is the supporting tool. The target application is supplied by the user through pasted requirements, a CSV upload, or an optional sample requirement set. Generated artifacts should describe the target application, not AutoTestDesign itself.

The repository includes a sample target only for demonstration and regression evidence. Target-specific details should be documented in a separate test plan or detailed design document.

## Architecture

```text
AutoTestDesign/
├── app.py                         # Streamlit UI and pipeline orchestration
├── core/
│   ├── schemas.py                 # Pydantic data models
│   ├── llm_client.py              # Gemini client
│   ├── parser.py                  # Requirement structuring
│   ├── risk_analyzer.py           # Weighted risk scoring
│   ├── coverage_identifier.py     # Coverage item identification
│   ├── test_designer.py           # Black-box test generation
│   ├── oracle_generator.py        # Oracle notes and result analysis
│   ├── optimizer.py               # Test suite prioritization
│   ├── traceability.py            # Requirement-to-test traceability
│   ├── exporter.py                # JSON, CSV, Excel export
│   └── playwright_generator.py    # Pytest + Playwright test generation
├── data/                          # Optional sample requirements
├── prompts/                       # Prompt templates for documentation/reuse
├── outputs/                       # Exported artifacts
└── generated_tests/               # Executable tests
```

## Installation

Python 3.10+ is recommended.

The project is configured for Gemini:

```bash
GEMINI_MODEL=gemini-3-pro-preview
GEMINI_API_KEY=...
```

This version intentionally requires `GEMINI_API_KEY`; it does not silently switch to a no-key mode.

## Run The Streamlit App

```bash
cd Software-Test/homework2/AutoTestDesign
./run.sh
```

Open the local URL printed by Streamlit, usually <http://localhost:8501>.

Install Playwright browsers before running generated browser tests:

```bash
source .venv/bin/activate
playwright install
```

## Demo Flow

1. Open the app and confirm the sidebar says `LLM mode: Gemini (gemini-3-pro-preview)`.
2. Step 1: enter the target application name and base URL, then paste requirements, upload a CSV, or load the optional sample requirements.
3. Step 2: review the structured requirements table and apply a small edit with a reason.
4. Step 3: click **Run Risk Analysis**, review weighted scores, and apply any calibration.
5. Step 4: click **Generate Coverage Items** and inspect EP, BVA, decision table, and state transition items.
6. Step 5: click **Generate Test Cases**, then **Optimize Test Suite**.
7. Step 6: click **Generate Traceability Matrix**, then **Export Artifacts**.
8. Step 7: click **Generate Playwright Tests**.
9. Step 8: enter sample Pass/Fail/Blocked results and click **Analyze Results**.

## Generated Artifacts

The app can produce artifacts in two locations:

- `outputs/` for reviewable test-design reports, exports, validation reports, and execution evidence.
- `generated_tests/` for generated pytest modules.

When **Export Artifacts** is clicked, the app writes these files to `outputs/`:

- `structured_requirements.json`
- `review_log.json`
- `risk_analysis.xlsx`
- `risk_analysis.csv`
- `coverage_items.xlsx`
- `coverage_items.csv`
- `test_cases.xlsx`
- `test_cases.csv`
- `traceability_matrix.xlsx`
- `traceability_matrix.csv`
- `decision_table_review.xlsx`
- `decision_table_review.csv` when decision-table rules exist
- `execution_results.xlsx`
- `execution_results.csv` when execution results exist during export
- `artifact_validation_report.md`
- `artifact_validation_report.csv`
- `pytest_results.xml` when generated Pytest tests are run from the UI
- `full_autotestdesign_artifacts.xlsx`

The full workbook contains separate sheets for requirements, risk, coverage, test cases, optimized order, traceability, decision tables, execution results, and review log. It also includes a result-analysis sheet when execution results have been analyzed before export.

When **Generate Playwright Tests** is clicked, the app writes one generated pytest module to `generated_tests/`. The generated file is either an adapter-specific browser test module for a configured target, or a generic assisted-placeholder module when no target adapter is available.

When **Run Generated Tests** is clicked from the UI, the app writes:

- `outputs/pytest_results.xml`
- `outputs/execution_results.csv`

When **Analyze Results** is clicked after manual entry or CSV upload, the app writes:

- `outputs/execution_results.csv`

Oracle notes and improvement suggestions are displayed in the UI. Improvement analysis is included in `full_autotestdesign_artifacts.xlsx` if the user exports after analysis.

## Playwright/PyTest Tests

Generate tests from the UI, then run the generated pytest file or directory:

```bash
cd /path/to/Software-Test/homework2/AutoTestDesign
pytest generated_tests/
```

Generated pytest artifacts use a target-specific adapter when one is configured. If no adapter exists for the current target, AutoTestDesign creates assisted pytest placeholders that preserve test case IDs, steps, expected results, and review notes so a tester can complete the browser automation safely.

When the UI runs generated tests, it writes `outputs/pytest_results.xml` and parses it into `outputs/execution_results.csv`.

## Risk Model

Risk score is calculated as:

```text
risk_score = 0.35 * business_impact
           + 0.25 * failure_probability
           + 0.20 * user_frequency
           + 0.20 * implementation_complexity
```

Priority is:

- High: score >= 4.0
- Medium: 2.5 <= score < 4.0
- Low: score < 2.5

## Test Design Techniques

The project uses at least three required black-box techniques:

- Equivalence Partitioning for valid and invalid input or workflow classes.
- Boundary Value Analysis for empty, minimum, maximum, and edge values described by the target requirements.
- Decision Table Testing for multi-condition business rules.

It also supports State Transition Testing when the target requirements describe workflow states and transitions.

## Human-In-The-Loop Review

Each major artifact is displayed as an editable Streamlit data table:

- Structured requirements
- Risk scores
- Coverage items
- Test cases
- Execution results

When the user applies edits, the app records a review log entry with timestamp, artifact type, action, before summary, after summary, and reason. This demonstrates interactive designer participation and traceable human judgment.

## Assignment Requirement Mapping

- FR 1.0: Requirement ingestion from pasted text, CSV upload, and optional sample loading.
- FR 1.1: Requirement structuring into JSON-like Pydantic objects with fields, ranges, conditions, and ambiguity notes.
- FR 2.0: Risk analysis with a weighted scoring formula and High/Medium/Low priority.
- FR 3.0: Black-box test design using EP, BVA, and Decision Table Testing.
- FR 6.0: Structured export to JSON, CSV, Excel, and a multi-sheet workbook.
- Interactive review: Streamlit editable tables plus review log.
- Optional FR 4.0: State Transition Testing for workflow behavior.
- Optional FR 5.0: Test oracle generation and assertion hints.
- Optional FR 7.0: Execution result analysis, pass-rate metrics, failed high-risk requirement reporting, and improvement suggestions.

## Presentation Script

Start with the pipeline diagram in the README, then run the app with a chosen target application's requirements. Show the structured requirement table and explain that the tool preserves traceability from raw requirement to test case. Run risk analysis and point out the weighted formula. Generate coverage and show all required black-box techniques. Generate and optimize test cases, then export the workbook and validation report. Finally, generate Pytest/Playwright artifacts and show a result-analysis example with one high-risk failure to demonstrate feedback-driven improvement.
