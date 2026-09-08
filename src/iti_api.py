from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "http://apiaccess.iti.net.eg/api/v1"
DEFAULT_MODEL = "deepseek.v3.2"

class ITIAPIError(RuntimeError):
    pass

def base_url() -> str:
    return os.getenv("ITI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

def model_name() -> str:
    return os.getenv("ITI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

def api_key() -> str:
    return os.getenv("SBG_API_KEY", "").strip()

def is_configured() -> bool:
    return bool(api_key())

def _extract_text(data: Any) -> str:
    """
    Be tolerant to slightly different gateway response envelopes.
    """
    if isinstance(data, str):
        return data.strip()

    if isinstance(data, dict):
        # Common simple response shapes
        for key in ("content", "response", "answer", "text", "output", "message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = _extract_text(value)
                if nested:
                    return nested

        # OpenAI-like choices
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            nested = _extract_text(choices[0])
            if nested:
                return nested

        # Sometimes the actual payload is nested under data/result
        for key in ("data", "result"):
            value = data.get(key)
            if value is not None:
                nested = _extract_text(value)
                if nested:
                    return nested

    if isinstance(data, list):
        for item in data:
            nested = _extract_text(item)
            if nested:
                return nested

    return ""

def chat(
    *,
    messages,
    system_prompt: str = "",
    model_id: Optional[str] = None,
    timeout: int = 120,
) -> str:
    key = api_key()
    if not key:
        raise ITIAPIError("SBG_API_KEY is not configured.")

    payload: Dict[str, Any] = {
        "model_id": model_id or model_name(),
        "messages": messages,
    }
    if system_prompt:
        payload["system_prompt"] = system_prompt

    try:
        response = requests.post(
            f"{base_url()}/student/chat",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise ITIAPIError(f"ITI API request failed: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise ITIAPIError("ITI API returned a non-JSON response.") from e

    text = _extract_text(data)
    if not text:
        raise ITIAPIError(f"Could not extract text from ITI API response: {json.dumps(data)[:1000]}")
    return text
