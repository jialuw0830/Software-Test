"""Minimal Gemini client used by the AutoTestDesign pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class LLMClient:
    def __init__(self) -> None:
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required in AutoTestDesign/.env")

    @property
    def mode(self) -> str:
        return f"LLM mode: Gemini ({self.model})"

    def generate_json(self, prompt: str, system_prompt: str = "") -> object | None:
        try:
            text = self.generate_text(prompt, system_prompt)
        except requests.RequestException:
            return None

        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            for start_token, end_token in [("[", "]"), ("{", "}")]:
                start = cleaned.find(start_token)
                end = cleaned.rfind(end_token)
                if start >= 0 and end > start:
                    try:
                        return json.loads(cleaned[start : end + 1])
                    except json.JSONDecodeError:
                        pass
        return None

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = requests.post(
            url,
            params={"key": self.api_key},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\n{prompt}".strip()}],
                    }
                ],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            },
            timeout=45,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
