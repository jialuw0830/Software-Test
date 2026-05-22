"""Minimal Gemini client used by the AutoTestDesign pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _redact_api_key_from_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    query_parts = []
    for part in parts.query.split("&"):
        if part.startswith("key="):
            query_parts.append("key=<redacted>")
        else:
            query_parts.append(part)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query and "&".join(query_parts), parts.fragment))


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
        data, _ = self.generate_json_with_raw(prompt, system_prompt)
        return data

    def generate_json_with_raw(self, prompt: str, system_prompt: str = "") -> tuple[object | None, str]:
        try:
            text = self.generate_text(prompt, system_prompt)
        except requests.HTTPError as exc:
            response = exc.response
            status = response.status_code if response is not None else "unknown"
            url = _redact_api_key_from_url(response.url) if response is not None else ""
            body = response.text if response is not None else ""
            return None, f"[HTTP_ERROR] {status} for url: {url}\n{body}"
        except requests.RequestException as exc:
            return None, f"[REQUEST_EXCEPTION] {exc}"

        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned), text
        except json.JSONDecodeError:
            for start_token, end_token in [("[", "]"), ("{", "}")]:
                start = cleaned.find(start_token)
                end = cleaned.rfind(end_token)
                if start >= 0 and end > start:
                    try:
                        return json.loads(cleaned[start : end + 1]), text
                    except json.JSONDecodeError:
                        pass
        return None, text

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
            timeout=600,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
