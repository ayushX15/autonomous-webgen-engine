# backend/tools/playwright_tool.py
# FINAL — subprocess-based screenshot, sync everything else

import os
import sys
import time
import signal
import subprocess
import tempfile
from pathlib import Path

NPM_CMD = "npm.cmd" if os.name == "nt" else "npm"
WORKER_SCRIPT = Path(__file__).resolve().parent / "screenshot_worker.py"


def install_dependencies(run_dir: Path) -> bool:
    """Runs npm install inside the generated Next.js project."""
    print(f"[Playwright Tool] Installing npm dependencies in {run_dir.name}...")

    result = subprocess.run(
        [NPM_CMD, "install"],
        cwd=str(run_dir),
        capture_output=True,
        text=True,
        timeout=180
    )

    if result.returncode != 0:
        print(f"[Playwright Tool] npm install failed:\n{result.stderr[:300]}")
        return False

    print("[Playwright Tool] npm install complete ✅")
    return True


def start_nextjs_server(run_dir: Path, port: int = 3001) -> subprocess.Popen:
    """Starts Next.js dev server as a background process."""
    print(f"[Playwright Tool] Starting Next.js server on port {port}...")

    process = subprocess.Popen(
        [NPM_CMD, "run", "dev", "--", "--port", str(port)],
        cwd=str(run_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    )

    start_time = time.time()
    timeout = 120  # increased to 2 minutes

    while time.time() - start_time < timeout:
        if process.poll() is not None:
            out = process.stdout.read().decode("utf-8", errors="ignore")
            err = process.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"Next.js server died.\nstdout: {out[:300]}\nstderr: {err[:300]}"
            )
        if _is_port_open("localhost", port):
            elapsed = int(time.time() - start_time)
            print(f"[Playwright Tool] Server ready at http://localhost:{port} ({elapsed}s) ✅")
            time.sleep(3)  # extra buffer for full hydration
            return process
        time.sleep(2)
        print(f"[Playwright Tool] Waiting... ({int(time.time() - start_time)}s)")

    raise TimeoutError(f"Server did not start within {timeout}s on port {port}")


def take_screenshot(
    port: int,
    route: str = "/",
    viewport_width: int = 1440,
    viewport_height: int = 900,
    full_page: bool = True
) -> bytes:
    """
    Takes screenshot via subprocess worker.
    Worker sets WindowsProactorEventLoopPolicy before Playwright runs.
    """
    url = f"http://localhost:{port}{route}"
    print(f"[Playwright Tool] Taking screenshot of {url}...")

    if not WORKER_SCRIPT.exists():
        raise FileNotFoundError(f"screenshot_worker.py not found at {WORKER_SCRIPT}")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT), str(port), route, tmp_path],
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print(f"[Playwright Tool] Worker failed:")
            print(f"  stdout: {result.stdout[:300]}")
            print(f"  stderr: {result.stderr[:300]}")
            raise RuntimeError(f"Screenshot worker failed: {result.stderr[:200]}")

        if not Path(tmp_path).exists():
            raise RuntimeError("Worker ran but no screenshot file was created")

        screenshot_bytes = Path(tmp_path).read_bytes()
        if len(screenshot_bytes) < 1000:
            raise RuntimeError(f"Screenshot too small ({len(screenshot_bytes)} bytes) — page likely empty")

        print(f"[Playwright Tool] Screenshot taken ({len(screenshot_bytes):,} bytes) ✅")
        return screenshot_bytes

    finally:
        Path(tmp_path).unlink(missing_ok=True)


def take_screenshot_and_save(
    port: int,
    run_dir: Path,
    iteration: int,
    route: str = "/"
) -> tuple[bytes, str]:
    """Takes screenshot and saves to run_dir/screenshots/iter_N_route.png"""
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    screenshot_bytes = take_screenshot(port, route)

    route_name = "landing" if route == "/" else route.strip("/")
    filename = f"iter_{iteration}_{route_name}.png"
    filepath = screenshots_dir / filename
    filepath.write_bytes(screenshot_bytes)

    print(f"[Playwright Tool] Saved: screenshots/{filename}")
    return screenshot_bytes, str(filepath)


def stop_server(process: subprocess.Popen) -> None:
    """Stops the Next.js server cleanly."""
    if process and process.poll() is None:
        print("[Playwright Tool] Stopping server...")
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
            process.wait(timeout=10)
            print("[Playwright Tool] Server stopped ✅")
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            print(f"[Playwright Tool] Stop error: {e}")
            process.kill()


def _is_port_open(host: str, port: int) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False