# backend/tools/screenshot_worker.py
# Standalone subprocess — called by playwright_tool.py
# Sets WindowsProactorEventLoopPolicy FIRST before any imports

import sys
import os

# MUST be first — before any playwright imports
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import asyncio
from pathlib import Path


async def take_screenshot_async(port: int, route: str, output_path: str):
    from playwright.async_api import async_playwright

    url = f"http://localhost:{port}{route}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page(
            viewport={"width": 1440, "height": 900}
        )

        # Try multiple wait strategies
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            try:
                await page.goto(url, wait_until="load", timeout=20000)
                await asyncio.sleep(3)
            except Exception:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(4)

        # Extra wait for JS hydration
        await asyncio.sleep(2)

        screenshot = await page.screenshot(full_page=True, type="png")
        await browser.close()

    Path(output_path).write_bytes(screenshot)
    print(f"SCREENSHOT_OK:{len(screenshot)}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("ERROR: Usage: python screenshot_worker.py <port> <route> <output_path>")
        sys.exit(1)

    port = int(sys.argv[1])
    route = sys.argv[2]
    output_path = sys.argv[3]

    asyncio.run(take_screenshot_async(port, route, output_path))