from __future__ import annotations
import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:30b-instruct"

def base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

def model_name() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

def ollama_status(timeout: float = 0.8):
    try:
        req = urllib.request.Request(f"{base_url()}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        names = [m.get("name", "") for m in data.get("models", [])]
        wanted = model_name()
        installed = any(n == wanted or n.startswith(wanted + ":") for n in names)
        return {
            "running": True,
            "model_installed": installed,
            "models": names,
            "wanted": wanted,
        }
    except Exception:
        return {
            "running": False,
            "model_installed": False,
            "models": [],
            "wanted": model_name(),
        }

def chat(system: str, user: str, *, temperature: float = 0.2, json_mode: bool = False, timeout: int = 120) -> str:
    payload = {
        "model": model_name(),
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": temperature,
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
        },
    }
    if json_mode:
        payload["format"] = "json"

    req = urllib.request.Request(
        f"{base_url()}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["message"]["content"].strip()
