# backend/tools/gemini_client.py
# FINAL — Smart retry, quota management, reduced API calls

import os
import re
import json
import time
import base64
from pathlib import Path
from typing import Optional, Type, TypeVar
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "secret.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found in secret.env")

genai.configure(api_key=GEMINI_API_KEY)

T = TypeVar("T", bound=BaseModel)

# ── Global call counter (tracks usage in this session) ──────────────────────
_call_count = 0
_call_log: list[str] = []


def _log_call(fn_name: str):
    global _call_count
    _call_count += 1
    _call_log.append(f"[{_call_count}] {fn_name}")
    print(f"[Gemini] API call #{_call_count}: {fn_name}")


def get_call_count() -> int:
    return _call_count


def _wait_on_quota(error_str: str, attempt: int) -> bool:
    """
    If 429/quota error: extract retry delay, wait, return True.
    For other errors: return False immediately.
    """
    if "429" not in error_str and "RESOURCE_EXHAUSTED" not in error_str:
        return False

    delay_match = re.search(r'seconds:\s*(\d+)', error_str)
    wait_secs = int(delay_match.group(1)) + 10 if delay_match else 70
    wait_secs = min(wait_secs, 120)  # cap at 2 minutes
    print(f"[Gemini] ⏳ Quota hit — waiting {wait_secs}s (attempt {attempt+1}/3)...")
    time.sleep(wait_secs)
    return True


def _load_image_part(image_path: str) -> dict:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp"
    }
    with open(path, "rb") as f:
        data = f.read()
    return {
        "inline_data": {
            "mime_type": mime_map.get(suffix, "image/jpeg"),
            "data": base64.b64encode(data).decode("utf-8")
        }
    }


def _load_image_bytes_part(image_bytes: bytes, mime_type: str = "image/png") -> dict:
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }
    }


def text_prompt(prompt: str, temperature: float = 0.7) -> str:
    """Text-only Gemini call with auto quota retry."""
    _log_call("text_prompt")
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(temperature=temperature)
    )
    for attempt in range(3):
        try:
            return model.generate_content(prompt).text
        except Exception as e:
            if not _wait_on_quota(str(e), attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def json_prompt(prompt: str, temperature: float = 0.2) -> dict:
    """Text prompt forcing JSON output, with auto retry."""
    _log_call("json_prompt")
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json"
        )
    )
    for attempt in range(3):
        try:
            raw = model.generate_content(prompt).text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )
            return json.loads(raw)
        except Exception as e:
            if not _wait_on_quota(str(e), attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def vision_prompt(
    prompt: str,
    image_paths: Optional[list[str]] = None,
    image_bytes_list: Optional[list[bytes]] = None,
    temperature: float = 0.3
) -> str:
    """Vision prompt with images, auto retry."""
    _log_call("vision_prompt")
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(temperature=temperature)
    )
    parts = []
    if image_paths:
        for p in image_paths:
            parts.append(_load_image_part(p))
    if image_bytes_list:
        for b in image_bytes_list:
            parts.append(_load_image_bytes_part(b))
    parts.append({"text": prompt})

    for attempt in range(3):
        try:
            return model.generate_content(parts).text
        except Exception as e:
            if not _wait_on_quota(str(e), attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def vision_json_prompt(
    prompt: str,
    image_paths: Optional[list[str]] = None,
    image_bytes_list: Optional[list[bytes]] = None,
    temperature: float = 0.2
) -> dict:
    """Vision prompt forcing JSON, auto retry."""
    _log_call("vision_json_prompt")
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json"
        )
    )
    parts = []
    if image_paths:
        for p in image_paths:
            parts.append(_load_image_part(p))
    if image_bytes_list:
        for b in image_bytes_list:
            parts.append(_load_image_bytes_part(b))
    parts.append({"text": prompt})

    for attempt in range(3):
        try:
            raw = model.generate_content(parts).text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )
            return json.loads(raw)
        except Exception as e:
            if not _wait_on_quota(str(e), attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def parse_to_schema(data: dict, schema_class: Type[T]) -> T:
    try:
        return schema_class.model_validate(data)
    except Exception as e:
        raise ValueError(
            f"Failed to parse into {schema_class.__name__}.\n"
            f"Error: {e}\nData: {json.dumps(data, indent=2)[:500]}"
        )