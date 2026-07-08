# backend/tools/scrape_worker.py
# Standalone subprocess worker — called by site_scraper.py via argv (no code injection).
# Sets WindowsProactorEventLoopPolicy FIRST before any Playwright imports, mirroring
# screenshot_worker.py's known-working pattern for launching Chromium on Windows.

import sys
import json
import base64

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import asyncio


async def _scrape(url: str) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
            except Exception as e:
                await browser.close()
                return {"error": str(e), "url": url}

        screenshot = await page.screenshot(full_page=True)
        title = await page.title()

        colors = await page.evaluate("""
            () => {
                const colors = new Set();
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules) {
                            if (rule.style) {
                                const m = rule.style.cssText.match(/#[0-9a-fA-F]{3,8}/g) || [];
                                m.forEach(c => colors.add(c.toLowerCase()));
                            }
                        }
                    } catch (e) {}
                }
                return [...colors].slice(0, 20);
            }
        """)
        fonts = await page.evaluate("""
            () => {
                const fonts = new Set();
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules) {
                            if (rule.style && rule.style.fontFamily)
                                fonts.add(rule.style.fontFamily.replace(/['\\"]/g, "").trim());
                        }
                    } catch (e) {}
                }
                return [...fonts].slice(0, 10);
            }
        """)
        structure = await page.evaluate("""
            () => {
                const tags = ["header","nav","main","section","footer"];
                const found = [];
                for (const t of tags) {
                    const n = document.querySelectorAll(t).length;
                    if (n > 0) found.push(t + "(" + n + ")");
                }
                return found.join(", ");
            }
        """)

        await browser.close()
        return {
            "screenshot_b64": base64.b64encode(screenshot).decode("ascii"),
            "colors": colors,
            "fonts": fonts,
            "html_structure": structure,
            "page_title": title,
            "url": url,
        }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"error": "Usage: python scrape_worker.py <url> <output_json_path>"}))
        sys.exit(1)

    target_url = sys.argv[1]
    output_path = sys.argv[2]

    try:
        result = asyncio.run(_scrape(target_url))
    except Exception as e:
        result = {"error": str(e), "url": target_url}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f)

    print("SCRAPE_OK" if "error" not in result else "SCRAPE_ERR", flush=True)
