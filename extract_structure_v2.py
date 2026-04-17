import argparse
import json
import os
import re
from pathlib import Path

from openai import AzureOpenAI


DEFAULT_ENDPOINT = "https://azure-api-jialu.openai.azure.com/"
DEFAULT_API_VERSION = "2024-12-01-preview"
DEFAULT_DEPLOYMENT = "gpt-4o"


def load_prompt_template(prompt_path: Path) -> str:
    text = prompt_path.read_text(encoding="utf-8").strip()
    if "{{requirement_text}}" not in text:
        raise ValueError("Prompt template must contain '{{requirement_text}}' placeholder.")
    return text


def split_system_blocks(requirements_text: str):
    lines = requirements_text.splitlines()
    blocks = []
    current_name = None
    current_lines = []

    for line in lines:
        match = re.match(r"^SYSTEM\s+\d+:\s+.+$", line.strip())
        if match:
            if current_name and current_lines:
                blocks.append((current_name, "\n".join(current_lines).strip()))
            current_name = line.strip()
            current_lines = [line]
            continue

        if current_name:
            current_lines.append(line)

    if current_name and current_lines:
        blocks.append((current_name, "\n".join(current_lines).strip()))

    return blocks


def extract_functional_requirements(system_block: str) -> str:
    start_marker = "[Functional Requirements]"
    start = system_block.find(start_marker)
    if start == -1:
        raise ValueError("Selected system block does not contain [Functional Requirements].")

    functional_text = system_block[start:].strip()
    if not functional_text:
        raise ValueError("Functional requirements section is empty.")
    return functional_text


def pick_requirement_block(requirements_path: Path, selector: str) -> str:
    requirements_text = requirements_path.read_text(encoding="utf-8")
    blocks = split_system_blocks(requirements_text)
    if not blocks:
        raise ValueError("No SYSTEM block found in requirements file.")

    if selector.isdigit():
        idx = int(selector)
        if idx < 1 or idx > len(blocks):
            raise ValueError(f"System index out of range: {idx}. Valid range: 1-{len(blocks)}.")
        return extract_functional_requirements(blocks[idx - 1][1])

    selector_lower = selector.lower()
    for name, block in blocks:
        if selector_lower in name.lower():
            return extract_functional_requirements(block)

    valid = ", ".join(f"{i + 1}:{name}" for i, (name, _) in enumerate(blocks))
    raise ValueError(f"No matched system for '{selector}'. Available systems: {valid}")


def build_client(endpoint: str, api_version: str, api_key: str) -> AzureOpenAI:
    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )


def call_model(client: AzureOpenAI, deployment: str, prompt_text: str) -> str:
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a software testing assistant. "
                    "Return only valid JSON with no markdown fences."
                ),
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ],
        max_tokens=4096,
        temperature=0,
        top_p=1.0,
        model=deployment,
    )
    return response.choices[0].message.content or ""


def validate_output_schema(parsed: dict):
    required_top_keys = ["input_variables", "equivalence_partitions", "boundary_value_analysis", "test_cases"]
    for key in required_top_keys:
        if key not in parsed:
            raise ValueError(f"Missing required top-level key in model output: '{key}'")

    if not isinstance(parsed["input_variables"], list):
        raise ValueError("'input_variables' must be a list")
    if not isinstance(parsed["equivalence_partitions"], list):
        raise ValueError("'equivalence_partitions' must be a list")
    if not isinstance(parsed["boundary_value_analysis"], list):
        raise ValueError("'boundary_value_analysis' must be a list")
    if not isinstance(parsed["test_cases"], list):
        raise ValueError("'test_cases' must be a list")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate EP, BVA, and test cases from requirements text via Azure OpenAI."
    )
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to requirements input file.",
    )
    parser.add_argument(
        "--prompt",
        default="prompt/structure_v2.py",
        help="Path to prompt template file that contains {{requirement_text}}.",
    )
    parser.add_argument(
        "--system",
        default="1",
        help="System selector. Supports index (1,2,3...) or keyword match in SYSTEM title.",
    )
    parser.add_argument(
        "--output",
        default="output/ep_bva_testcases.json",
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("AZURE_OPENAI_ENDPOINT", DEFAULT_ENDPOINT),
        help="Azure OpenAI endpoint.",
    )
    parser.add_argument(
        "--deployment",
        default=os.getenv("AZURE_OPENAI_DEPLOYMENT", DEFAULT_DEPLOYMENT),
        help="Azure OpenAI deployment name.",
    )
    parser.add_argument(
        "--api-version",
        dest="api_version",
        default=os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION),
        help="Azure OpenAI API version.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("AZURE_OPENAI_API_KEY"),
        help="Azure OpenAI API key. If omitted, reads AZURE_OPENAI_API_KEY env.",
    )
    return parser.parse_args()


def main():
    dotenv = Path(".env")
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    args = parse_args()

    api_key = args.api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing API key. Please set AZURE_OPENAI_API_KEY (or AZURE_API_KEY) "
            "in environment/.env, or pass --api-key."
        )

    requirements_path = Path(args.requirements)
    prompt_path = Path(args.prompt)

    selected_requirement = pick_requirement_block(requirements_path, args.system)
    prompt_template = load_prompt_template(prompt_path)
    final_prompt = prompt_template.replace("{{requirement_text}}", selected_requirement)

    client = build_client(args.endpoint, args.api_version, api_key)
    content = call_model(client, args.deployment, final_prompt).strip()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        output_path.write_text(content, encoding="utf-8")
        raise ValueError(
            f"Model output is not valid JSON. Raw content has been saved to: {output_path}"
        )

    validate_output_schema(parsed)

    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"EP/BVA/Test cases saved to: {output_path}")


if __name__ == "__main__":
    main()