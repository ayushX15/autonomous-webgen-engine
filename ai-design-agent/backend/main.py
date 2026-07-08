# backend/main.py
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application — complete working version
# ─────────────────────────────────────────────────────────────────────────────

import sys

# Windows' legacy console codepage (cp1252) can't encode the emoji used in log/
# progress messages throughout this codebase — printing one crashes the whole
# background task. Force UTF-8 on stdout/stderr before anything else prints.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import os
import json
import asyncio
import concurrent.futures
import uuid
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load env first — before any backend imports
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "secret.env")

from backend.graph.workflow import run_workflow

UPLOAD_DIR = Path(os.getenv("GENERATED_OUTPUT_DIR", "./generated-output")).resolve() / "_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Design Agent",
    description="Agentic system that generates Next.js websites from references",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory run storage (resets on server restart)
runs: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    user_requirement: str
    reference_urls: list[str] = []
    reference_image_paths: list[str] = []
    pages_requested: list[str] = ["index", "about", "contact"]
    max_iterations: int = 2


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 1 — Health check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "AI Design Agent",
        "version": "1.0.0"
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 2 — Gemini quota status
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: this used to make a real Gemini API call on every poll, which alone could
# exhaust the free-tier daily quota just from the UI's periodic status checks.
# Instead we report the local call counter and the last real 429 seen (if any) —
# no network call, no quota spent.
@app.get("/api/quota")
def get_quota():
    from backend.tools.gemini_client import get_quota_state

    state = get_quota_state()
    daily_estimate = int(os.getenv("GEMINI_DAILY_QUOTA_ESTIMATE", "1500"))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if state["exhausted"]:
        return {
            "status": "exhausted",
            "model": model,
            "message": state["message"],
            "calls_used": state["calls_used"],
            "calls_limit": daily_estimate,
            "percent_used": 100,
        }

    percent_used = min(100, round((state["calls_used"] / daily_estimate) * 100)) if daily_estimate else 0
    return {
        "status": "available",
        "model": model,
        "message": "Gemini Ready",
        "calls_used": state["calls_used"],
        "calls_limit": daily_estimate,
        "percent_used": percent_used,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 3 — Upload a reference image
# POST /api/upload  →  { "path": "<absolute path usable as reference_image_paths>" }
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_reference_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Use PNG, JPEG, or WebP.")

    suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[file.content_type]
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"

    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(400, "File too large (max 8MB).")
            out.write(chunk)

    return {"path": str(dest)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 4 — Start a new run
# POST /api/run
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/run", response_model=RunResponse)
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Starts the agentic workflow in a background task.
    Returns immediately with a run_id to poll.
    """
    temp_id = "pending_" + uuid.uuid4().hex[:8]

    runs[temp_id] = {
        "status": "running",
        "current_iteration": 0,
        "max_iterations": request.max_iterations,
        "is_complete": False,
        "final_output_path": None,
        "error_message": None,
        "iteration_results": [],
        "pages": [],
        "progress_messages": []
    }

    background_tasks.add_task(_run_workflow_background, temp_id, request)

    return RunResponse(
        run_id=temp_id,
        status="running",
        message="Workflow started. Poll /api/status/" + temp_id
    )


async def _run_workflow_background(run_id: str, request: RunRequest):
    """Runs the full LangGraph workflow in a thread pool executor."""
    try:
        def sync_progress(message: str):
            if run_id in runs:
                runs[run_id]["progress_messages"].append(message)
            print("[Progress] " + message)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                pool,
                lambda: run_workflow(
                    user_requirement=request.user_requirement,
                    reference_urls=request.reference_urls,
                    reference_image_paths=request.reference_image_paths,
                    pages_requested=request.pages_requested,
                    max_iterations=request.max_iterations,
                    progress_callback=sync_progress
                )
            )

        actual_run_id = final_state.output_run_id or run_id

        result_data = {
            "status": "complete",
            "current_iteration": final_state.current_iteration,
            "max_iterations": final_state.max_iterations,
            "is_complete": final_state.is_complete,
            "final_output_path": final_state.final_output_path,
            "error_message": final_state.error_message,
            "iteration_results": [
                r.model_dump() for r in final_state.iteration_results
            ],
            "pages": [
                {"name": p.page_name, "route": p.route_path}
                for p in final_state.generated_pages
            ],
            "progress_messages": runs[run_id].get("progress_messages", [])
        }

        runs[run_id] = result_data
        if actual_run_id != run_id:
            runs[actual_run_id] = result_data

    except Exception as e:
        print("[Main] Workflow error: " + str(e))
        import traceback
        traceback.print_exc()
        if run_id in runs:
            runs[run_id]["status"] = "error"
            runs[run_id]["error_message"] = str(e)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 5 — Get run status
# GET /api/status/{run_id}
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/status/{run_id}")
def get_status(run_id: str):
    """Poll this endpoint to get current workflow status."""
    if run_id not in runs:
        return {"error": "Run '" + run_id + "' not found"}

    run = runs[run_id]
    return {
        "run_id": run_id,
        "status": run.get("status", "unknown"),
        "current_iteration": run.get("current_iteration", 0),
        "max_iterations": run.get("max_iterations", 3),
        "is_complete": run.get("is_complete", False),
        "final_output_path": run.get("final_output_path"),
        "error_message": run.get("error_message"),
        "iteration_results": run.get("iteration_results", []),
        "pages": run.get("pages", []),
        "progress_messages": run.get("progress_messages", [])
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 6 — List all runs
# GET /api/runs
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/runs")
def list_runs():
    """Lists all runs from this server session."""
    return {
        "total": len(runs),
        "runs": [
            {
                "run_id": rid,
                "status": data.get("status"),
                "is_complete": data.get("is_complete"),
                "current_iteration": data.get("current_iteration", 0),
                "final_output_path": data.get("final_output_path"),
            }
            for rid, data in runs.items()
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 7 — WebSocket real-time updates
# WS /ws/run
# ─────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """
    WebSocket for real-time workflow updates.

    Client sends:
        { "user_requirement": "...", "reference_urls": [...],
          "pages_requested": [...], "max_iterations": 2 }

    Server streams:
        { "type": "progress",  "message": "..." }
        { "type": "iteration", "data": { IterationResult } }
        { "type": "complete",  "data": { final_state } }
        { "type": "error",     "message": "..." }
    """
    await websocket.accept()
    print("[WebSocket] Client connected")

    try:
        raw  = await websocket.receive_text()
        data = json.loads(raw)

        await websocket.send_json({
            "type": "progress",
            "message": "Request received — starting workflow..."
        })

        progress_messages: list[str] = []

        def sync_progress(msg: str):
            progress_messages.append(msg)

        loop = asyncio.get_event_loop()

        final_state = await loop.run_in_executor(
            None,
            lambda: run_workflow(
                user_requirement=data.get("user_requirement", ""),
                reference_urls=data.get("reference_urls", []),
                reference_image_paths=data.get("reference_image_paths", []),
                pages_requested=data.get("pages_requested", ["index", "about", "contact"]),
                max_iterations=data.get("max_iterations", 2),
                progress_callback=sync_progress
            )
        )

        # Flush progress messages
        for msg in progress_messages:
            await websocket.send_json({"type": "progress", "message": msg})

        # Send each iteration result
        for result in final_state.iteration_results:
            await websocket.send_json({
                "type": "iteration",
                "data": result.model_dump()
            })

        # Final complete event
        await websocket.send_json({
            "type": "complete",
            "data": {
                "run_id": final_state.output_run_id,
                "output_path": final_state.final_output_path,
                "iterations": final_state.current_iteration,
                "is_complete": final_state.is_complete,
                "iteration_results": [
                    r.model_dump() for r in final_state.iteration_results
                ]
            }
        })

    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected")

    except Exception as e:
        print("[WebSocket] Error: " + str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

    finally:
        print("[WebSocket] Connection closed")


# ─────────────────────────────────────────────────────────────────────────────
# Direct run
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)