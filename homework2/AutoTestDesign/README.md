# AutoTestDesign

AutoTestDesign is a complete course project for an AI-driven software test design tool. It targets SauceDemo / Swag Labs and implements a full test-design pipeline instead of a single prompt-to-tests shortcut:

Requirement Input -> Requirement Structuring -> Risk Analysis -> Coverage Identification -> Strategy Selection -> Test Case Generation -> Human Review -> Traceability -> Export -> Playwright/PyTest Generation -> Execution Result Analysis -> Improvement Suggestions

## Target Application

- Live site: <https://www.saucedemo.com/>
- Reference repository: <https://github.com/saucelabs/sample-app-web>
- Domain: sample e-commerce application with login, inventory, cart, checkout, price calculation, order completion, sorting, and logout.

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
├── data/                          # SauceDemo sample requirements
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
cd /scratch/jialu/Software-Test/homework2/AutoTestDesign
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
2. Step 1: click **Load SauceDemo Sample Requirements**.
3. Step 2: review the structured requirements table and apply a small edit with a reason.
4. Step 3: click **Run Risk Analysis**, review weighted scores, and apply any calibration.
5. Step 4: click **Generate Coverage Items** and inspect EP, BVA, decision table, and state transition items.
6. Step 5: click **Generate Test Cases**, then **Optimize Test Suite**.
7. Step 6: click **Generate Traceability Matrix**, then **Export Artifacts**.
8. Step 7: click **Generate Playwright Tests**.
9. Step 8: enter sample Pass/Fail/Blocked results and click **Analyze Results**.

## Exported Artifacts

The app writes these files to `outputs/`:

- `structured_requirements.json`
- `risk_analysis.xlsx`
- `coverage_items.xlsx`
- `test_cases.xlsx`
- `traceability_matrix.xlsx`
- `review_log.json`
- `full_autotestdesign_artifacts.xlsx`
- CSV copies of the key tabular artifacts

The full workbook contains separate sheets for requirements, risk, coverage, test cases, optimized order, traceability, review log, and result analysis.

## Playwright/PyTest Tests

Generate tests from the UI or use the included file:

```bash
cd /scratch/jialu/Software-Test/homework2/AutoTestDesign
pytest generated_tests/
```

The generated tests include helper functions:

- `login(page, username="standard_user", password="secret_sauce")`
- `add_backpack_to_cart(page)`
- `go_to_checkout(page)`
- `fill_checkout_info(page, first_name, last_name, postal_code)`

They cover valid login, locked-out rejection, add/remove cart item, checkout required-field validation, successful checkout, total-price oracle, and order completion.

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

- Equivalence Partitioning: valid/invalid credential classes, sort options, cart item classes.
- Boundary Value Analysis: empty username/password, 0/1/many cart quantities, required checkout fields, price totals.
- Decision Table Testing: login acceptance/rejection and checkout required-field rules.

It also includes State Transition Testing for login-to-inventory, cart add/remove, checkout workflow, order completion, cancel checkout, and logout.

## Human-In-The-Loop Review

Each major artifact is displayed as an editable Streamlit data table:

- Structured requirements
- Risk scores
- Coverage items
- Test cases
- Execution results

When the user applies edits, the app records a review log entry with timestamp, artifact type, action, before summary, after summary, and reason. This demonstrates interactive designer participation and traceable human judgment.

## Assignment Requirement Mapping

- FR 1.0: Requirement ingestion from pasted text, CSV upload, and sample SauceDemo loading.
- FR 1.1: Requirement structuring into JSON-like Pydantic objects with fields, ranges, conditions, and ambiguity notes.
- FR 2.0: Risk analysis with a weighted scoring formula and High/Medium/Low priority.
- FR 3.0: Black-box test design using EP, BVA, and Decision Table Testing.
- FR 6.0: Structured export to JSON, CSV, Excel, and a multi-sheet workbook.
- Interactive review: Streamlit editable tables plus review log.
- Optional FR 4.0: State Transition Testing for workflow behavior.
- Optional FR 5.0: Test oracle generation and price-total oracle.
- Optional FR 7.0: Execution result analysis, pass-rate metrics, failed high-risk requirement reporting, and improvement suggestions.

## Presentation Script

Start with the pipeline diagram in the README, then run the app. Load the SauceDemo sample requirements, show the structured requirement table, and explain that the tool preserves traceability from raw requirement to test case. Run risk analysis and point out the weighted formula. Generate coverage and show all required black-box techniques. Generate and optimize test cases, then export the workbook. Finally, generate Playwright tests and show a result-analysis example with one high-risk checkout failure to demonstrate feedback-driven improvement.
