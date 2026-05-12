from __future__ import annotations

import json
import re
from typing import Any

from .env import load_env, require_env


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def openai_chat(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    load_env()
    api_key = require_env("OPENAI_API_KEY")
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=60, max_retries=2)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()
