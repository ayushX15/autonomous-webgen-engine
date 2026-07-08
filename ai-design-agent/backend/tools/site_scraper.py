# backend/tools/site_scraper.py
# Scrapes reference URLs by delegating to scrape_worker.py in a subprocess (so Windows
# gets a clean ProactorEventLoopPolicy for Playwright's subprocess-based browser launch).
# The URL is passed as an argv value, never interpolated into generated source code.

import sys
import json
import tempfile
import subprocess
from pathlib import Path

WORKER_SCRIPT = Path(__file__).resolve().parent / "scrape_worker.py"


def scrape_site(url: str) -> dict:
    """Scrapes a single URL: screenshot + colors + fonts + structure."""
    if not WORKER_SCRIPT.exists():
        raise FileNotFoundError(f"scrape_worker.py not found at {WORKER_SCRIPT}")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT), url, tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if not Path(tmp_path).exists():
            raise RuntimeError(
                f"Scraper produced no output. stdout={result.stdout[:200]!r} "
                f"stderr={result.stderr[:200]!r}"
            )

        data = json.loads(Path(tmp_path).read_text(encoding="utf-8"))

        if "error" in data:
            raise RuntimeError(data["error"])

        import base64
        data["screenshot_bytes"] = base64.b64decode(data.pop("screenshot_b64"))
        return data

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Scraping {url} timed out after 60s")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def scrape_multiple_sites(urls: list[str]) -> list[dict]:
    """Scrape multiple URLs sequentially, isolating failures per-URL."""
    results = []
    for url in urls:
        try:
            results.append(scrape_site(url))
        except Exception as e:
            print(f"[Site Scraper] Failed to scrape {url}: {e}")
            results.append({
                "screenshot_bytes": None,
                "colors": [], "fonts": [],
                "html_structure": "", "page_title": "",
                "url": url, "error": str(e),
            })
    return results
