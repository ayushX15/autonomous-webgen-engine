# backend/graph/workflow.py
# ─────────────────────────────────────────────────────────────────────────────
# FIXED: All agents are now sync — no async wrappers needed.
# Removed _run_async entirely.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from langgraph.graph import StateGraph, END

from backend.models.schemas import AgentState, UserInput
from backend.agents.feature_extractor import extract_features
from backend.agents.code_generator import generate_code
from backend.agents.visual_reviewer import visual_review
from backend.agents.similarity_judge import similarity_judge, should_continue


# ─────────────────────────────────────────────────────────────────────────────
# CONVERTERS
# ─────────────────────────────────────────────────────────────────────────────
def _state_from_dict(data: dict) -> AgentState:
    return AgentState.model_validate(data)

def _state_to_dict(state: AgentState) -> dict:
    return state.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# NODE WRAPPERS — all sync now, no event loop needed
# ─────────────────────────────────────────────────────────────────────────────
def node_extract_features(state: dict) -> dict:
    return _state_to_dict(extract_features(_state_from_dict(state)))

def node_generate_code(state: dict) -> dict:
    return _state_to_dict(generate_code(_state_from_dict(state)))

def node_visual_review(state: dict) -> dict:
    return _state_to_dict(visual_review(_state_from_dict(state)))

def node_similarity_judge(state: dict) -> dict:
    return _state_to_dict(similarity_judge(_state_from_dict(state)))

def edge_should_continue(state: dict) -> str:
    decision = should_continue(_state_from_dict(state))
    print(f"\n[Workflow] Edge decision: → {decision}")
    return decision


# ─────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────────────────────────────
def build_workflow() -> Any:
    graph = StateGraph(dict)

    graph.add_node("extract_features", node_extract_features)
    graph.add_node("generate_code",    node_generate_code)
    graph.add_node("visual_review",    node_visual_review)
    graph.add_node("judge",            node_similarity_judge)

    graph.set_entry_point("extract_features")
    graph.add_edge("extract_features", "generate_code")
    graph.add_edge("generate_code",    "visual_review")
    graph.add_edge("visual_review",    "judge")

    graph.add_conditional_edges(
        "judge",
        edge_should_continue,
        {"generate_code": "generate_code", "END": END}
    )

    compiled = graph.compile()
    print("[Workflow] Graph compiled successfully ✅")
    return compiled


# ─────────────────────────────────────────────────────────────────────────────
# RUN FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def run_workflow(
    user_requirement: str,
    reference_urls: list[str] = None,
    reference_image_paths: list[str] = None,
    pages_requested: list[str] = None,
    max_iterations: int = 5,
    progress_callback=None
) -> AgentState:

    if progress_callback:
        progress_callback("🚀 Starting AI Design Agent workflow...")

    initial_state = AgentState(
        user_input=UserInput(
            user_requirement=user_requirement,
            reference_urls=reference_urls or [],
            reference_image_paths=reference_image_paths or [],
            pages_requested=pages_requested or ["index", "about", "contact"]
        ),
        max_iterations=max_iterations,
        current_iteration=0,
        is_complete=False
    )

    app = build_workflow()

    if progress_callback:
        progress_callback("📊 Extracting design features from references...")

    print("\n" + "="*60)
    print("STARTING WORKFLOW")
    print("="*60)

    final_state_dict = app.invoke(initial_state.model_dump())
    final_state = AgentState.model_validate(final_state_dict)

    print("\n" + "="*60)
    print("WORKFLOW COMPLETE")
    print(f"Run ID:      {final_state.output_run_id}")
    print(f"Iterations:  {final_state.current_iteration}")
    print(f"Output:      {final_state.final_output_path}")
    if final_state.iteration_results:
        best = max(r.similarity_score for r in final_state.iteration_results)
        print(f"Best score:  {best:.2f}")
    print("="*60 + "\n")

    if progress_callback:
        iters = final_state.current_iteration
        score = final_state.iteration_results[-1].similarity_score if final_state.iteration_results else 0
        progress_callback(f"✅ Complete! Iterations: {iters} | Score: {score:.2f}")

    return final_state