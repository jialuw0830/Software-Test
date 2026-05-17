"""Expose the generated SauceDemo pytest file."""

from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST = PROJECT_ROOT / "generated_tests" / "test_saucedemo_generated.py"


def generate_playwright_tests(output_dir: Path | str) -> Path:
    target = Path(output_dir) / DEFAULT_TEST.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.resolve() != DEFAULT_TEST.resolve():
        shutil.copyfile(DEFAULT_TEST, target)
    return target
