# backend/tools/site_scraper.py
# FIXED: Windows ProactorEventLoop policy set before every Playwright call.

import sys
import time
import asyncio
from playwright.sync_api import sync_playwright


def _fix_windows_event_loop():
    """Force ProactorEventLoop on Windows before Playwright calls."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


def scrape_site(url: str) -> dict:
    """
    Scrapes a URL by spawning a separate subprocess with correct event loop.
    """
    import sys
    import json
    import tempfile
    from pathlib import Path

    # Write a temporary scraper script
    scraper_code = f'''
import sys
import json
import asyncio
import base64

async def scrape():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={{"width": 1440, "height": 900}},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto("{url}", wait_until="networkidle", timeout=30000)
        except:
            try:
                await page.goto("{url}", wait_until="domcontentloaded", timeout=20000)
                import asyncio; await asyncio.sleep(3)
            except Exception as e:
                print(json.dumps({{"error": str(e), "url": "{url}"}}))
                return

        screenshot = await page.screenshot(full_page=True)
        title = await page.title()
        colors = await page.evaluate("""
            () => {{
                const colors = new Set();
                for (const sheet of document.styleSheets) {{
                    try {{
                        for (const rule of sheet.cssRules) {{
                            if (rule.style) {{
                                const m = rule.style.cssText.match(/#[0-9a-fA-F]{{3,8}}/g) || [];
                                m.forEach(c => colors.add(c.toLowerCase()));
                            }}
                        }}
                    }} catch(e) {{}}
                }}
                return [...colors].slice(0, 20);
            }}
        """)
        fonts = await page.evaluate("""
            () => {{
                const fonts = new Set();
                for (const sheet of document.styleSheets) {{
                    try {{
                        for (const rule of sheet.cssRules) {{
                            if (rule.style && rule.style.fontFamily)
                                fonts.add(rule.style.fontFamily.replace(/[\\'"]/g,"").trim());
                        }}
                    }} catch(e) {{}}
                }}
                return [...fonts].slice(0,10);
            }}
        """)
        structure = await page.evaluate("""
            () => {{
                const tags = ["header","nav","main","section","footer"];
                const found = [];
                for (const t of tags) {{
                    const n = document.querySelectorAll(t).length;
                    if (n > 0) found.push(t+"("+n+")");
                }}
                return found.join(", ");
            }}
        """)
        await browser.close()
        result = {{
            "screenshot_b64": base64.b64encode(screenshot).decode(),
            "colors": colors,
            "fonts": fonts,
            "html_structure": structure,
            "page_title": title,
            "url": "{url}"
        }}
        print(json.dumps(result))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.run(scrape())
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(scraper_code)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=60
        )
        Path(script_path).unlink(missing_ok=True)

        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(f"Scraper failed: {result.stderr[:200]}")

        import json
        import base64
        data = json.loads(result.stdout.strip())

        if "error" in data:
            raise RuntimeError(data["error"])

        screenshot_bytes = base64.b64decode(data["screenshot_b64"])
        data["screenshot_bytes"] = screenshot_bytes
        del data["screenshot_b64"]
        return data

    except Exception as e:
        Path(script_path).unlink(missing_ok=True)
        raise RuntimeError(f"Could not scrape {url}: {e}")

        
def scrape_multiple_sites(urls: list[str]) -> list[dict]:
    """Scrape multiple URLs sequentially."""
    results = []
    for url in urls:
        try:
            result = scrape_site(url)
            results.append(result)
        except Exception as e:
            results.append({
                "screenshot_bytes": None,
                "colors": [], "fonts": [],
                "html_structure": "", "page_title": "",
                "url": url, "error": str(e)
            })
    return results