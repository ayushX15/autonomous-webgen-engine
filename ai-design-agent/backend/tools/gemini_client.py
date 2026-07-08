# backend/tools/gemini_client.py
# Uses the current `google-genai` SDK (the old `google-generativeai` package is
# EOL and no longer receives updates/fixes as of this writing).

import os
import re
import json
import time
import threading
from datetime import date
from pathlib import Path
from typing import Optional, Type, TypeVar
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "secret.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Minimum gap enforced between consecutive Gemini calls. A single generation run
# fires several calls back-to-back (feature extraction, per-page generation,
# visual review, ...) — without pacing them, that burst alone can trip the free
# tier's per-minute rate limit even before the daily cap is a concern.
GEMINI_MIN_INTERVAL_SECONDS = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "6"))

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found in secret.env")

_client = genai.Client(api_key=GEMINI_API_KEY)

T = TypeVar("T", bound=BaseModel)

# ── Quota tracking — persisted to disk so the count survives backend restarts ─
# NOTE: There is no Gemini endpoint that reports real remaining quota — the only
# reliable signal is a 429/RESOURCE_EXHAUSTED response from an actual call. We
# track daily call volume ourselves (reset at UTC midnight) so /api/quota can
# report a used/remaining percentage WITHOUT spending a call itself.
_QUOTA_FILE = (
    Path(os.getenv("GENERATED_OUTPUT_DIR", "./generated-output")).resolve() / "_quota_state.json"
)
_lock = threading.Lock()
_quota_exhausted_until = 0.0
_last_quota_message = ""
_last_call_time = 0.0


def _read_quota_file() -> dict:
    try:
        data = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
        if data.get("date") == str(date.today()):
            return data
    except Exception:
        pass
    return {"date": str(date.today()), "calls_used": 0}


def _write_quota_file(data: dict) -> None:
    try:
        _QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _QUOTA_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        print(f"[Gemini] Could not persist quota state: {e}")


def _log_call(fn_name: str):
    with _lock:
        data = _read_quota_file()
        data["calls_used"] += 1
        _write_quota_file(data)
        print(f"[Gemini] API call #{data['calls_used']} today: {fn_name}")


def _throttle():
    """Sleeps just enough to keep calls spaced at least GEMINI_MIN_INTERVAL_SECONDS
    apart — prevents a burst of calls in one run from tripping the per-minute
    rate limit and getting the whole run blocked."""
    global _last_call_time
    with _lock:
        elapsed = time.time() - _last_call_time
        wait = GEMINI_MIN_INTERVAL_SECONDS - elapsed
        if wait > 0:
            print(f"[Gemini] Pacing — waiting {wait:.1f}s before next call...")
            time.sleep(wait)
        _last_call_time = time.time()


def get_call_count() -> int:
    return _read_quota_file()["calls_used"]


def get_quota_state() -> dict:
    """Returns current quota status derived from the last real 429, if any."""
    now = time.time()
    exhausted = now < _quota_exhausted_until
    return {
        "exhausted": exhausted,
        "message": _last_quota_message if exhausted else "",
        "retry_after_seconds": max(0, int(_quota_exhausted_until - now)) if exhausted else 0,
        "calls_used": get_call_count(),
    }


def _is_quota_error(e: Exception) -> bool:
    code = getattr(e, "code", None)
    return code == 429 or "RESOURCE_EXHAUSTED" in str(e)


def _wait_on_quota(e: Exception, attempt: int) -> bool:
    """If e is a 429/RESOURCE_EXHAUSTED error: extract retry delay, wait, return
    True. For other errors: return False immediately (caller re-raises)."""
    global _quota_exhausted_until, _last_quota_message

    if not _is_quota_error(e):
        return False

    error_str = str(e)
    delay_match = re.search(r'"retryDelay":\s*"(\d+)s"', error_str) or re.search(r'seconds:\s*(\d+)', error_str)
    wait_secs = int(delay_match.group(1)) + 10 if delay_match else 70
    wait_secs = min(wait_secs, 120)  # cap at 2 minutes

    _quota_exhausted_until = time.time() + wait_secs
    _last_quota_message = f"Gemini quota hit — resets in ~{wait_secs}s"

    print(f"[Gemini] ⏳ Quota hit — waiting {wait_secs}s (attempt {attempt + 1}/3)...")
    time.sleep(wait_secs)
    return True


def _image_parts(image_paths, image_bytes_list) -> list:
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    parts = []
    if image_paths:
        for p in image_paths:
            path = Path(p)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {p}")
            mime = mime_map.get(path.suffix.lower(), "image/jpeg")
            parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))
    if image_bytes_list:
        for b in image_bytes_list:
            parts.append(types.Part.from_bytes(data=b, mime_type="image/png"))
    return parts


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return raw.strip()


def text_prompt(prompt: str, temperature: float = 0.7) -> str:
    """Text-only Gemini call with auto quota retry."""
    _throttle()
    _log_call("text_prompt")
    config = types.GenerateContentConfig(temperature=temperature)
    for attempt in range(3):
        try:
            response = _client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
            return response.text
        except Exception as e:
            if not _wait_on_quota(e, attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def json_prompt(prompt: str, temperature: float = 0.2) -> dict:
    """Text prompt forcing JSON output, with auto retry."""
    _throttle()
    _log_call("json_prompt")
    config = types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json")
    for attempt in range(3):
        try:
            response = _client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
            return json.loads(_strip_fences(response.text))
        except Exception as e:
            if not _wait_on_quota(e, attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def vision_prompt(
    prompt: str,
    image_paths: Optional[list[str]] = None,
    image_bytes_list: Optional[list[bytes]] = None,
    temperature: float = 0.3,
) -> str:
    """Vision prompt with images, auto retry."""
    _throttle()
    _log_call("vision_prompt")
    config = types.GenerateContentConfig(temperature=temperature)
    contents = [*_image_parts(image_paths, image_bytes_list), prompt]
    for attempt in range(3):
        try:
            response = _client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
            return response.text
        except Exception as e:
            if not _wait_on_quota(e, attempt):
                raise
    raise RuntimeError("Gemini quota exceeded after 3 retries")


def vision_json_prompt(
    prompt: str,
    image_paths: Optional[list[str]] = None,
    image_bytes_list: Optional[list[bytes]] = None,
    temperature: float = 0.2,
) -> dict:
    """Vision prompt forcing JSON, auto retry."""
    _throttle()
    _log_call("vision_json_prompt")
    config = types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json")
    contents = [*_image_parts(image_paths, image_bytes_list), prompt]
    for attempt in range(3):
        try:
            response = _client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
            return json.loads(_strip_fences(response.text))
        except Exception as e:
            if not _wait_on_quota(e, attempt):
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
