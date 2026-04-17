PROMPT_TEMPLATE = """You are an expert software testing analyst for black-box dynamic testing.

Your task is to analyze a requirement document and extract a structured requirement model that will later be used to generate:
1. equivalence partitions
2. boundary values
3. decision tables
4. concrete black-box test cases

Important rules:
- Use only information explicitly stated in the requirement text.
- Do not invent hidden implementation details.
- Do not generate test cases yet.
- Do not perform EP or BVA yet.
- Keep all numeric thresholds exactly as written.
- Preserve explicit error messages and success conditions.
- Separate user inputs, derived values, validation rules, rejection rules, and final confirmation rules.
- If something is unclear or unspecified, put it in "ambiguities".

Return STRICT JSON only.

JSON schema:
{
  "system_name": "",
  "system_overview": "",
  "inputs": [
    {
      "name": "",
      "description": "",
      "type": "enum|integer|float|boolean|string",
      "required": true,
      "allowed_values": [],
      "range": {
        "min": null,
        "min_inclusive": true,
        "max": null,
        "max_inclusive": true
      },
      "unit": "",
      "notes": ""
    }
  ],
  "derived_values": [
    {
      "name": "",
      "description": "",
      "formula": "",
      "depends_on": []
    }
  ],
  "validation_rules": [
    {
      "id": "",
      "condition": "",
      "result_if_true": "",
      "result_if_false": ""
    }
  ],
  "rejection_rules": [
    {
      "id": "",
      "trigger_condition": "",
      "system_response": ""
    }
  ],
  "success_conditions": [
    ""
  ],
  "observable_outputs": [
    {
      "condition": "",
      "output_or_message": ""
    }
  ],
  "boundary_candidates": [
    {
      "variable_or_expression": "",
      "reason": "",
      "candidate_values": []
    }
  ],
  "ambiguities": [
    ""
  ]
}

Requirement text:
{{requirement_text}}
"""