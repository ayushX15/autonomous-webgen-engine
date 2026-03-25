# backend/agents/feature_extractor.py
# ─────────────────────────────────────────────────────────────────────────────
# FIXED: Now fully synchronous — no async/await needed since
# site_scraper and playwright_tool are now sync.
# ─────────────────────────────────────────────────────────────────────────────

from backend.models.schemas import CapturedFeatures, AgentState
from backend.tools.gemini_client import vision_json_prompt, json_prompt, parse_to_schema
from backend.tools.site_scraper import scrape_multiple_sites


FEATURE_EXTRACTION_PROMPT = """
You are an expert UI/UX design analyst.

Analyze the provided reference image(s) and scraped site data,
then extract design features into a structured JSON object.

SCRAPED SITE DATA:
{scraped_data}

USER REQUIREMENT:
{user_requirement}

Return ONLY a valid JSON object with this exact structure:
{{
    "ui_components": ["list of UI components, e.g. navbar, hero, cards, CTA, footer"],
    "color_palette": ["3-6 dominant hex color codes, e.g. #0f172a, #6366f1"],
    "font_style": "font style in 3-5 words, e.g. clean modern sans-serif",
    "font_size_scale": "sizing pattern, e.g. large bold headings with small body text",
    "layout_type": "one of: centered, full-width, sidebar, grid, asymmetric",
    "tone": "one of: minimal, bold, corporate, playful, elegant, technical",
    "page_sections": ["ordered sections top to bottom, e.g. hero, features, pricing, footer"],
    "animation_style": "one of: none, subtle, moderate, heavy"
}}

Rules:
- Return ONLY the JSON object, no explanation
- color_palette must contain actual hex codes only
"""


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION: extract_features  ← NOW SYNC (not async)
# ─────────────────────────────────────────────────────────────────────────────
def extract_features(state: AgentState) -> AgentState:
    """
    LangGraph node — fully synchronous.
    Reads user_input, writes captured_features to state.
    """
    print("\n[Feature Extractor] Starting feature extraction...")

    user_input = state.user_input
    if not user_input:
        state.error_message = "No user input provided"
        return state

    # ── Scrape reference URLs (sync now) ─────────────────────────────────────
    scraped_results = []
    screenshot_bytes_list = []

    if user_input.reference_urls:
        print(f"[Feature Extractor] Scraping {len(user_input.reference_urls)} URL(s)...")
        scraped_results = scrape_multiple_sites(user_input.reference_urls)

        for result in scraped_results:
            if result.get("screenshot_bytes"):
                screenshot_bytes_list.append(result["screenshot_bytes"])
                print(f"[Feature Extractor] Scraped: {result['url']}")
            else:
                print(f"[Feature Extractor] Failed to scrape: {result['url']}")

    # ── Build prompt ──────────────────────────────────────────────────────────
    scraped_summary = _build_scraped_summary(scraped_results)
    prompt = FEATURE_EXTRACTION_PROMPT.format(
        scraped_data=scraped_summary,
        user_requirement=user_input.user_requirement
    )

    # ── Call Gemini ───────────────────────────────────────────────────────────
    print("[Feature Extractor] Sending to Gemini Vision...")
    try:
        if screenshot_bytes_list or user_input.reference_image_paths:
            raw_result = vision_json_prompt(
                prompt=prompt,
                image_paths=user_input.reference_image_paths or None,
                image_bytes_list=screenshot_bytes_list or None
            )
        else:
            raw_result = json_prompt(prompt)
    except Exception as e:
        print(f"[Feature Extractor] Gemini call failed: {e}")
        raw_result = _default_features()

    # ── Parse schema ──────────────────────────────────────────────────────────
    try:
        captured = parse_to_schema(raw_result, CapturedFeatures)
        print(f"[Feature Extractor] Extracted features: {captured.tone} / {captured.layout_type}")
        print(f"[Feature Extractor] Components found: {captured.ui_components}")
        print(f"[Feature Extractor] Colors found: {captured.color_palette}")
    except ValueError as e:
        print(f"[Feature Extractor] Schema parsing failed, using defaults: {e}")
        captured = CapturedFeatures(**_default_features())

    state.captured_features = captured
    return state


def _build_scraped_summary(scraped_results: list) -> str:
    if not scraped_results:
        return "No reference sites scraped."
    lines = []
    for i, result in enumerate(scraped_results):
        if result.get("error"):
            lines.append(f"Site {i+1} ({result['url']}): Failed to scrape")
            continue
        lines.append(f"Site {i+1}: {result.get('page_title','Unknown')} ({result['url']})")
        lines.append(f"  Colors: {', '.join(result.get('colors', []))}")
        lines.append(f"  Fonts: {', '.join(result.get('fonts', []))}")
        lines.append(f"  Structure: {result.get('html_structure','unknown')}")
    return "\n".join(lines)


def _default_features() -> dict:
    return {
        "ui_components": ["navbar", "hero", "features", "cta", "footer"],
        "color_palette": ["#0f172a", "#6366f1", "#ffffff", "#f8fafc"],
        "font_style": "clean modern sans-serif",
        "font_size_scale": "large bold headings with medium body text",
        "layout_type": "centered",
        "tone": "minimal",
        "page_sections": ["hero", "features", "cta", "footer"],
        "animation_style": "subtle"
    }