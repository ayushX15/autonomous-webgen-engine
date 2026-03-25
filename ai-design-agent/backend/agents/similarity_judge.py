# backend/agents/similarity_judge.py
# ─────────────────────────────────────────────────────────────────────────────
# Agent 4: Similarity Judge
#
# This is the decision node in the LangGraph loop.
# It reads the latest IterationResult and decides:
#   → PASS: similarity score >= threshold OR max iterations reached
#   → FAIL: score too low, send back for another iteration
#
# This is NOT an LLM call — pure Python logic.
# Fast, deterministic, no API quota used.
# ─────────────────────────────────────────────────────────────────────────────

import os
from pathlib import Path
from dotenv import load_dotenv
from backend.models.schemas import AgentState

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "secret.env")


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION: similarity_judge
# LangGraph node — pure logic, no LLM call
# ─────────────────────────────────────────────────────────────────────────────
def similarity_judge(state: AgentState) -> AgentState:
    """
    LangGraph decision node.

    Reads:  state.iteration_results (last entry)
            state.current_iteration
            state.max_iterations
    Writes: state.is_complete (True/False)

    Does NOT call Gemini — this is pure Python logic.
    """
    print(f"\n[Similarity Judge] Evaluating iteration {state.current_iteration}...")

    threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
    max_iter  = state.max_iterations or 5

    # ── Get latest result ─────────────────────────────────────────────────────
    if not state.iteration_results:
        print("[Similarity Judge] No iteration results found — marking incomplete")
        state.is_complete = False
        return state

    latest = state.iteration_results[-1]
    score  = latest.similarity_score

    print(f"[Similarity Judge] Score: {score:.2f} | Threshold: {threshold}")
    print(f"[Similarity Judge] Iteration: {state.current_iteration}/{max_iter}")

    # ── Decision logic ────────────────────────────────────────────────────────
    if latest.passed:
        # Score meets threshold → DONE
        print(f"[Similarity Judge] ✅ PASSED — Score {score:.2f} >= {threshold}")
        print(f"[Similarity Judge] Final output: {state.final_output_path}")
        state.is_complete = True

    elif state.current_iteration >= max_iter:
        # Hit max iterations → stop anyway, take best result
        best = _get_best_iteration(state)
        print(f"[Similarity Judge] ⚠️ Max iterations reached.")
        print(f"[Similarity Judge] Best score was: {best:.2f} (iteration {_get_best_index(state)+1})")
        print(f"[Similarity Judge] Accepting best result and finishing.")
        state.is_complete = True

    else:
        # Score too low, iterations remaining → loop back
        remaining = max_iter - state.current_iteration
        print(f"[Similarity Judge] ❌ Score {score:.2f} < {threshold}")
        print(f"[Similarity Judge] Sending back for improvement. {remaining} iterations left.")
        print(f"[Similarity Judge] Feedback for next iteration:")
        for i, suggestion in enumerate(latest.suggestions, 1):
            print(f"  {i}. {suggestion}")
        state.is_complete = False

    return state


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTION: should_continue
# Used by LangGraph conditional edge to decide next node
# ─────────────────────────────────────────────────────────────────────────────
def should_continue(state: AgentState) -> str:
    """
    LangGraph conditional edge function.
    Returns the name of the next node to execute.

    Returns:
        "generate_code" → loop back for another iteration
        "END"           → finish the graph
    """
    if state.is_complete:
        return "END"
    return "generate_code"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_best_iteration(state: AgentState) -> float:
    """Returns the highest similarity score across all iterations."""
    if not state.iteration_results:
        return 0.0
    return max(r.similarity_score for r in state.iteration_results)


def _get_best_index(state: AgentState) -> int:
    """Returns the index of the iteration with highest score."""
    if not state.iteration_results:
        return 0
    scores = [r.similarity_score for r in state.iteration_results]
    return scores.index(max(scores))