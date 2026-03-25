# backend/agents/visual_reviewer.py
# FIXED: Score improvement, shared node_modules, proper retry

import os
import shutil
import traceback
from pathlib import Path

from backend.models.schemas import AgentState, IterationResult
from backend.tools.gemini_client import vision_json_prompt
from backend.tools.playwright_tool import (
    install_dependencies,
    start_nextjs_server,
    take_screenshot_and_save,
    stop_server
)

SHARED_NM = Path(__file__).resolve().parents[2] / "generated-output" / "_shared_nm"

QUALITY_PROMPT = """
You are a senior UI/UX design expert reviewing a generated website screenshot.

Evaluate this website on these criteria:
1. Visual hierarchy and typography (font sizes, weights, spacing)
2. Color consistency and palette usage
3. Layout composition and whitespace
4. Component completeness (navbar, hero, sections, footer)
5. Overall professional quality and modern aesthetic
6. Animation indicators and interactive element styling
7. Responsive design indicators

Scoring guide (be ACCURATE and STRICT):
- 0.85-1.0: Exceptional design — modern, complete, stunning visuals
- 0.75-0.84: Good design — professional, mostly complete, minor gaps
- 0.60-0.74: Average — functional but missing polish or sections
- 0.40-0.59: Poor — basic or incomplete, major sections missing
- 0.00-0.39: Very poor — broken or nearly empty

Return ONLY this exact JSON (no markdown, no explanation):
{
    "similarity_score": <float 0.0-1.0, be accurate>,
    "visual_diff_notes": "<2-3 specific sentences about what you see>",
    "suggestions": [
        "<specific fix 1 — be very precise>",
        "<specific fix 2 — be very precise>",
        "<specific fix 3 — be very precise>"
    ],
    "color_match": <true/false>,
    "layout_match": <true/false>,
    "components_present": <true/false>
}
"""

DIFF_PROMPT = """
You are a senior UI/UX design expert comparing two website screenshots.

IMAGE 1 = REFERENCE (target design)
IMAGE 2 = GENERATED (what was produced)

Compare them on:
1. Color palette accuracy
2. Layout and spacing similarity
3. Typography style and hierarchy
4. Component presence and placement
5. Overall visual resemblance

Scoring (be accurate):
- 0.85-1.0: Nearly identical — excellent match
- 0.75-0.84: Very similar — minor differences
- 0.60-0.74: Partially similar — noticeable gaps
- 0.40-0.59: Some similarity — major differences
- 0.00-0.39: Very different designs

Return ONLY this exact JSON:
{
    "similarity_score": <float 0.0-1.0>,
    "visual_diff_notes": "<2-3 specific sentences>",
    "suggestions": ["fix 1", "fix 2", "fix 3"],
    "color_match": <true/false>,
    "layout_match": <true/false>,
    "components_present": <true/false>
}
"""


def _setup_node_modules(run_dir: Path) -> bool:
    """Fast node_modules via shared copy."""
    nm = run_dir / "node_modules"
    if nm.exists():
        print("[Visual Reviewer] node_modules exists ✅")
        return True

    if SHARED_NM.exists() and (SHARED_NM / "node_modules").exists():
        print("[Visual Reviewer] ⚡ Copying shared node_modules (~5s)...")
        try:
            shutil.copytree(SHARED_NM / "node_modules", nm, symlinks=True)
            print("[Visual Reviewer] ✅ node_modules copied")
            return True
        except Exception as e:
            print(f"[Visual Reviewer] Copy failed: {e} — running npm install...")

    # Fresh install
    SHARED_NM.mkdir(parents=True, exist_ok=True)
    pkg = run_dir / "package.json"
    if pkg.exists():
        shutil.copy(pkg, SHARED_NM / "package.json")

    success = install_dependencies(run_dir)
    if success and (run_dir / "node_modules").exists():
        try:
            shutil.copytree(run_dir / "node_modules", SHARED_NM / "node_modules", symlinks=True)
            print("[Visual Reviewer] ✅ Shared node_modules cached for next time")
        except Exception:
            pass
    return success


def visual_review(state: AgentState) -> AgentState:
    """LangGraph node — screenshot + Gemini Vision scoring."""
    iteration = state.current_iteration
    print(f"\n[Visual Reviewer] Iteration {iteration}...")

    if not state.final_output_path:
        state.iteration_results.append(_default(iteration))
        return state

    run_dir = Path(state.final_output_path)
    if not run_dir.exists():
        print(f"[Visual Reviewer] ❌ Missing: {run_dir}")
        state.iteration_results.append(_default(iteration))
        return state

    for f in ["package.json", "src/app/page.tsx"]:
        if not (run_dir / f).exists():
            print(f"[Visual Reviewer] ❌ Missing file: {f}")
            state.iteration_results.append(_default(iteration))
            return state

    if not _setup_node_modules(run_dir):
        print("[Visual Reviewer] ❌ node_modules failed")
        state.iteration_results.append(_default(iteration))
        return state

    port = 3010 + iteration
    server = None

    try:
        server = start_nextjs_server(run_dir, port=port)
        print(f"[Visual Reviewer] ✅ Server on :{port}")

        screenshot_bytes, screenshot_path = take_screenshot_and_save(
            port=port,
            run_dir=run_dir,
            iteration=iteration,
            route="/"
        )
        print(f"[Visual Reviewer] ✅ Screenshot: {len(screenshot_bytes):,} bytes")

        ref_images = []
        if state.user_input and state.user_input.reference_image_paths:
            ref_images = state.user_input.reference_image_paths

        print("[Visual Reviewer] Sending to Gemini Vision...")

        # Use diff prompt if reference images available, else quality prompt
        if ref_images:
            raw = vision_json_prompt(
                prompt=DIFF_PROMPT,
                image_paths=ref_images,
                image_bytes_list=[screenshot_bytes]
            )
        else:
            raw = vision_json_prompt(
                prompt=QUALITY_PROMPT,
                image_bytes_list=[screenshot_bytes]
            )

        threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
        score = float(raw.get("similarity_score", 0.5))

        # Clamp to valid range
        score = max(0.0, min(1.0, score))

        result = IterationResult(
            iteration=iteration,
            similarity_score=score,
            visual_diff_notes=raw.get("visual_diff_notes", ""),
            suggestions=raw.get("suggestions", []),
            passed=score >= threshold,
            screenshot_path=screenshot_path
        )

        print(f"[Visual Reviewer] Score: {score:.2f} | "
              f"{'✅ PASSED' if result.passed else '❌ — needs improvement'}")
        print(f"[Visual Reviewer] Notes: {result.visual_diff_notes[:120]}")

        state.iteration_results.append(result)
        state.latest_feedback = result.suggestions

    except Exception as e:
        print(f"[Visual Reviewer] ❌ Exception:")
        traceback.print_exc()
        Path("visual_reviewer_error.txt").write_text(traceback.format_exc())
        state.iteration_results.append(_default(iteration))

    finally:
        if server:
            stop_server(server)

    return state


def _default(iteration: int) -> IterationResult:
    return IterationResult(
        iteration=iteration,
        similarity_score=0.5,
        visual_diff_notes="Visual review could not be completed",
        suggestions=[
            "Ensure the hero section has a bold large headline with gradient text",
            "Add CSS keyframe animations to heading and CTA elements",
            "Use the exact color palette with glassmorphism card effects"
        ],
        passed=False,
        screenshot_path=None
    )