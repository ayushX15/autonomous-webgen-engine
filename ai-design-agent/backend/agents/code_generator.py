# backend/agents/code_generator.py
# Builds a generation prompt FROM the actual captured/analyzed reference features
# (theme, colors, tone, layout, section order, components, animation level) instead
# of a fixed hardcoded template. Brand name and copy are always derived from the
# user's own requirement text. When a reference image is available it is fed
# DIRECTLY into the generation call (vision-grounded), so Gemini writes the page
# while looking at the reference — not just a text description of it.

import base64

from backend.models.schemas import AgentState, GeneratedPage
from backend.tools.gemini_client import text_prompt, vision_prompt, vision_json_prompt
from backend.tools.file_writer import write_all_pages


# ─────────────────────────────────────────────────────────────────────────────
# COLOR HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _hex_ok(h) -> bool:
    if not isinstance(h, str) or not h.startswith("#"):
        return False
    body = h.lstrip("#")
    return len(body) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in body)


def _brightness(h: str) -> float:
    try:
        v = h.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        return 0.299 * r + 0.587 * g + 0.114 * b
    except Exception:
        return 128.0


def _saturation(h: str) -> float:
    try:
        v = h.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        r, g, b = int(v[0:2], 16) / 255, int(v[2:4], 16) / 255, int(v[4:6], 16) / 255
        mx, mn = max(r, g, b), min(r, g, b)
        return (mx - mn) / mx if mx > 0 else 0.0
    except Exception:
        return 0.0


THEME_KEYWORDS_LIGHT = ["light theme", "light mode", "light-themed", "white background", "bright and clean"]
THEME_KEYWORDS_DARK = ["dark theme", "dark mode", "dark-themed"]


def _pick_theme(features, va: dict, requirement: str) -> str:
    """Decide 'dark' or 'light'. Priority: explicit user wording > real reference
    analysis > extracted palette average brightness > tone > default."""
    req_lower = requirement.lower()
    if any(k in req_lower for k in THEME_KEYWORDS_LIGHT):
        return "light"
    if any(k in req_lower for k in THEME_KEYWORDS_DARK):
        return "dark"

    ds = (va or {}).get("design_system", {})
    bg = ds.get("primary_bg")
    if _hex_ok(bg):
        return "dark" if _brightness(bg) < 128 else "light"

    valid = [c for c in (features.color_palette or []) if _hex_ok(c)]
    if valid:
        avg = sum(_brightness(c) for c in valid) / len(valid)
        return "dark" if avg < 140 else "light"

    if features.tone in ("elegant", "corporate", "minimal"):
        return "light"
    return "dark"


def _assign_colors(features, va: dict, theme: str):
    """Returns (accent, bg, card, text, muted, border) — prefers real screenshot
    analysis, then the extracted palette, then theme-appropriate neutral defaults.
    Never forces a specific brand color (no hardcoded orange)."""
    ds = (va or {}).get("design_system", {}) if va else {}
    valid_cp = [c for c in (features.color_palette or []) if _hex_ok(c)]

    if theme == "dark":
        d_bg, d_card, d_text, d_muted, d_border = "#0a0a0a", "#131313", "#ffffff", "#9a9a9a", "rgba(255,255,255,0.10)"
        neutral_accent = "#6C5CE7"
    else:
        d_bg, d_card, d_text, d_muted, d_border = "#ffffff", "#f6f6f8", "#0f0f14", "#5b5b66", "rgba(0,0,0,0.10)"
        neutral_accent = "#4F46E5"

    bg = ds.get("primary_bg") if _hex_ok(ds.get("primary_bg")) else d_bg
    card = ds.get("secondary_bg") if _hex_ok(ds.get("secondary_bg")) else d_card
    text = ds.get("text_primary") if _hex_ok(ds.get("text_primary")) else d_text
    muted = ds.get("text_secondary") if _hex_ok(ds.get("text_secondary")) else d_muted
    border = ds.get("border_color") or d_border

    accent = ds.get("primary_accent") if _hex_ok(ds.get("primary_accent")) else None
    if not accent:
        candidates = [c for c in valid_cp if abs(_brightness(c) - _brightness(bg)) > 55]
        if candidates:
            accent = max(candidates, key=_saturation)
        elif valid_cp:
            accent = max(valid_cp, key=_saturation)
        else:
            accent = neutral_accent

    if accent.lower() == bg.lower() or abs(_brightness(accent) - _brightness(bg)) < 25:
        accent = neutral_accent

    return accent, bg, card, text, muted, border


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL ANALYSIS (real reference screenshot → design system JSON)
# ─────────────────────────────────────────────────────────────────────────────
VISUAL_ANALYSIS_PROMPT = """
You are an expert frontend developer and UI/UX analyst.
Analyze this website screenshot in technical detail and return ONLY this exact
JSON (no markdown, no explanation) describing what you actually observe:
{
    "design_system": {
        "primary_bg": "<exact hex of the main page background>",
        "secondary_bg": "<exact hex of card/section backgrounds>",
        "primary_accent": "<exact hex of the main brand/accent color>",
        "text_primary": "<exact hex of main text color>",
        "text_secondary": "<exact hex of muted/secondary text>",
        "border_color": "<hex or rgba of borders/dividers>"
    },
    "typography": {
        "heading_weight": "<font-black/font-bold/font-semibold>",
        "heading_size": "<text-5xl/6xl/7xl/8xl for hero>",
        "body_font": "<closest Google Font: Inter/Poppins/Manrope/Sora/etc>",
        "letter_spacing": "<tracking-tight/tracking-normal/tracking-wide>"
    },
    "visual_effects": {
        "card_style": "<glassmorphism/solid/outlined/elevated>",
        "border_radius": "<rounded-md/lg/xl/2xl/3xl/full>",
        "shadow_style": "<none/subtle/colored-glow/hard>"
    },
    "layout": {
        "hero_style": "<centered/left-aligned/split/full-bleed>",
        "section_padding": "<py-16/py-20/py-24/py-32>",
        "content_width": "<max-w-5xl/6xl/7xl>",
        "grid_columns": "<2/3/4 columns for feature grids>"
    },
    "background": {
        "hero_background": "<describe the hero's backdrop in detail: solid, radial glow, gradient mesh, star/dot field, grid lines, floating blurred orbs, imagery, etc.>",
        "depth_effects": "<layering/parallax/floating cards/blur/vignette/none>",
        "texture": "<noise/grid/dots/none>",
        "glow_color": "<hex of any glow/aura color, or none>"
    },
    "animations": {
        "hero_motion": "<what moves in the hero: floating cards, carousel, orbiting elements, pulsing glow, typing text, none>",
        "scroll_effects": "<fade-in-up/slide-in/reveal-on-scroll/parallax/none>",
        "hover_effects": "<scale/glow/lift/color-shift/underline/none>",
        "intensity": "<none/subtle/moderate/heavy>"
    },
    "media": {
        "has_imagery": "<true/false — does the reference show photos, screenshots, illustrations, or product mockups?>",
        "imagery_description": "<what the imagery depicts, e.g. floating app-preview cards, product screenshots, illustrations>"
    },
    "unique_features": ["<specific distinguishing design element observed>"]
}
"""


def _run_visual_analysis(ref_bytes: bytes) -> dict:
    """Analyzes the cached reference screenshot into a design-system JSON.
    ref_bytes is the screenshot captured earlier by the feature extractor — no
    re-scraping here."""
    if not ref_bytes:
        return {}
    try:
        result = vision_json_prompt(prompt=VISUAL_ANALYSIS_PROMPT, image_bytes_list=[ref_bytes])
        accent = result.get("design_system", {}).get("primary_accent", "?")
        style = result.get("visual_effects", {}).get("card_style", "?")
        print(f"[Code Generator] Reference analysis ✅ accent={accent} style={style}")
        return result
    except Exception as e:
        print(f"[Code Generator] Visual analysis failed (continuing without it): {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION PLANNING — driven by CapturedFeatures.page_sections, not a fixed template
# ─────────────────────────────────────────────────────────────────────────────
SECTION_GUIDANCE = {
    "navbar": "Fixed/sticky nav: brand name, nav links, one CTA button.",
    "nav": "Fixed/sticky nav: brand name, nav links, one CTA button.",
    "hero": "Full-viewport hero: headline, subheadline, primary + secondary CTA.",
    "features": "Grid of 3-6 feature cards, each with an icon, title, short description.",
    "stats": "Stats bar with 3-4 large numbers and short labels.",
    "how-it-works": "3-4 numbered steps explaining the process.",
    "how it works": "3-4 numbered steps explaining the process.",
    "testimonials": "2-3 quote cards with name, role, and star rating.",
    "pricing": "2-3 pricing tiers; one visually highlighted as most popular.",
    "faq": "4-6 question/answer items.",
    "cta": "Full-width closing call-to-action with heading, subtext, button.",
    "footer": "Multi-column footer: brand blurb, link columns, copyright line.",
    "gallery": "Image/content gallery grid.",
    "team": "Team member grid: photo placeholder, name, role.",
    "integrations": "Grid of tool/integration names or icons.",
    "contact-form": "Form: name, email, subject, message fields, submit button.",
    "contact form": "Form: name, email, subject, message fields, submit button.",
}

DEFAULT_LANDING_SECTIONS = ["navbar", "hero", "features", "testimonials", "pricing", "cta", "footer"]

PAGE_CONTENT_HINTS = {
    "about": ["navbar", "hero", "mission", "team", "timeline", "cta", "footer"],
    "contact": ["navbar", "hero", "contact-form", "footer"],
    "pricing": ["navbar", "hero", "pricing", "faq", "cta", "footer"],
    "products": ["navbar", "hero", "gallery", "footer"],
}


def _section_plan(page_name: str, is_landing: bool, features) -> list[str]:
    if is_landing and features.page_sections:
        return features.page_sections
    if is_landing:
        return DEFAULT_LANDING_SECTIONS
    return PAGE_CONTENT_HINTS.get(page_name.lower().strip(), ["navbar", "hero", "features", "cta", "footer"])


def _section_lines(sections: list[str]) -> str:
    lines = []
    for i, s in enumerate(sections, 1):
        guidance = SECTION_GUIDANCE.get(s.strip().lower(), f"A '{s}' section appropriate to the site's purpose.")
        lines.append(f"{i}. {s.upper()} — {guidance}")
    return "\n".join(lines)


ANIMATION_GUIDANCE = {
    "none": "Keep motion minimal, but still add gentle hover states on buttons/cards and a soft fade-in on the hero.",
    "subtle": "Hero elements fade/slide in on load (staggered). Cards and buttons have smooth hover transitions (scale/lift/glow). Reveal sections on scroll.",
    "moderate": "Staggered fade/slide-in entrance on the hero; reveal-on-scroll for every section; hover scale+glow on cards and buttons; one or two continuously floating/pulsing accent elements in the background.",
    "heavy": "Cinematic motion: staggered hero entrance, reveal-on-scroll for all sections, floating/orbiting background elements, pulsing glows, an animated gradient or shimmer somewhere prominent, and rich hover states (scale, glow, color-shift) everywhere.",
}

LAYOUT_GUIDANCE = {
    "centered": "Center-align hero and section headings; content in a constrained max-width column.",
    "full-width": "Let sections span the full viewport width with edge-to-edge backgrounds.",
    "sidebar": "Use a persistent side navigation/sidebar alongside the main content area.",
    "grid": "Favor dense grid layouts for content sections.",
    "asymmetric": "Use off-center, asymmetric composition (split hero, staggered cards).",
}


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PROMPT — fully parametrized from extracted features, no fixed brand/style
# ─────────────────────────────────────────────────────────────────────────────
def _build_prompt(page_label: str, fn: str, accent, bg, card, text, muted, border,
                   typo: dict, fx: dict, layout_type: str, animation_style: str,
                   ui_components: list, unique_features: list,
                   sections: list[str], requirement: str, feedback: str,
                   has_reference_image: bool = False,
                   motion: dict = None, background: dict = None,
                   media: dict = None, allow_placeholder_images: bool = False) -> str:

    motion = motion or {}
    background = background or {}
    media = media or {}

    hw = typo.get("heading_weight", "font-bold")
    hs = typo.get("heading_size", "text-6xl")
    ls = typo.get("letter_spacing", "tracking-tight")
    font = typo.get("body_font", "Inter")
    card_style = fx.get("card_style", "solid")
    radius = fx.get("border_radius", "rounded-xl")
    shadow = fx.get("shadow_style", "subtle")

    card_style_line = {
        "glassmorphism": f"background: rgba(255,255,255,0.04); border: 1px solid {border}; backdrop-filter: blur(16px);",
        "outlined": f"background: transparent; border: 1px solid {border};",
        "elevated": f"background: {card}; box-shadow: 0 8px 30px rgba(0,0,0,0.12);",
        "solid": f"background: {card}; border: 1px solid {border};",
    }.get(card_style, f"background: {card}; border: 1px solid {border};")

    components_line = ", ".join(ui_components) if ui_components else "navbar, hero, cards, CTA, footer"
    unique_line = "\n".join(f"  - {u}" for u in unique_features) if unique_features else "  - (none specified — use good design judgment)"

    # ── Motion & background block (vision-driven, so it only asks for what the
    #    reference actually shows — never a hardcoded look) ────────────────────
    hero_bg = background.get("hero_background", "").strip()
    depth = background.get("depth_effects", "").strip()
    texture = background.get("texture", "").strip()
    glow = background.get("glow_color", "").strip()
    hero_motion = motion.get("hero_motion", "").strip()
    scroll_fx = motion.get("scroll_effects", "").strip()
    hover_fx = motion.get("hover_effects", "").strip()

    bg_lines = []
    if hero_bg and hero_bg.lower() not in ("none", "solid"):
        bg_lines.append(f"  - Hero backdrop: {hero_bg} — recreate this with CSS (radial-gradient / conic-gradient / layered absolutely-positioned blurred divs).")
    if glow and glow.lower() != "none":
        bg_lines.append(f"  - Glow/aura color {glow}: place one or two large blurred radial-glow orbs behind the hero (filter: blur(120px); opacity ~0.2).")
    if texture and texture.lower() != "none":
        bg_lines.append(f"  - {texture} texture overlay: a fixed absolutely-positioned layer (e.g. dot grid via radial-gradient background-image, or faint grid lines).")
    if depth and depth.lower() != "none":
        bg_lines.append(f"  - Depth: {depth} — layer elements with z-index, blur, and scale to create foreground/background separation.")
    bg_block = ("\n".join(bg_lines)) if bg_lines else "  - Add a tasteful backdrop (soft radial glow in the accent color behind the hero) so it isn't a flat solid color."

    motion_lines = []
    if hero_motion and hero_motion.lower() != "none":
        motion_lines.append(f"  - Hero motion: {hero_motion} — implement with CSS @keyframes (float/orbit/pulse) on absolutely-positioned decorative elements.")
    if scroll_fx and scroll_fx.lower() != "none":
        motion_lines.append(f"  - Scroll effects: {scroll_fx} — reveal sections as they enter the viewport using a small IntersectionObserver hook (see rules).")
    if hover_fx and hover_fx.lower() != "none":
        motion_lines.append(f"  - Hover: {hover_fx} on cards, buttons, and links via CSS transitions.")
    motion_block = ("\n".join(motion_lines)) if motion_lines else "  - Staggered hero entrance (fadeInUp), reveal-on-scroll for sections, and smooth hover states on cards/buttons."

    media = media or {}
    has_imagery = str(media.get("has_imagery", "")).lower() in ("true", "yes", "1")
    imagery_desc = media.get("imagery_description", "").strip()
    if has_imagery and allow_placeholder_images:
        media_block = (
            f"The reference features imagery ({imagery_desc or 'photos/screenshots/illustrations'}). "
            "You MAY use real placeholder images via plain <img> tags from "
            "https://picsum.photos/seed/<uniqueword>/<w>/<h> (e.g. "
            "https://picsum.photos/seed/hero1/600/400). Give each a distinct seed. "
            "Wrap them in styled cards/frames matching the reference. Use loading=\"lazy\"."
        )
    elif has_imagery:
        media_block = (
            f"The reference features imagery ({imagery_desc or 'photos/screenshots/illustrations'}), but you cannot load "
            "external images. Represent each media item as a styled 'mock' card built with CSS: a gradient/solid fill in "
            "the palette, a mock browser/app chrome bar, a title, and a few shapes — arranged the way the reference "
            "arranges its imagery (e.g. a floating/overlapping cluster behind the hero). Make them look intentional, not empty."
        )
    else:
        media_block = "No significant imagery in the reference — rely on typography, color, and CSS shapes."

    reference_image_note = (
        """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFERENCE IMAGE (attached above)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
An image of the reference website is attached. STUDY IT CLOSELY and reproduce its
look and feel: match its exact background color and overall theme (dark vs light),
its accent/brand colors, its typography scale and weight, the hero composition,
section rhythm, spacing, and any signature visual treatment (gradients, glows,
3D/graphic hero elements, imagery style). The values below were extracted from
this same image — if the image and the values ever disagree, TRUST THE IMAGE.
Recreate distinctive hero visuals with CSS (gradients, layered shapes, glows,
grid/dot textures) since you cannot use external images.
"""
        if has_reference_image else ""
    )

    return f"""
You are a world-class frontend engineer building a real, production-quality {page_label} page.
{reference_image_note}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRAND & COPY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Derive the brand/product name, headline, subheadline, and all body copy directly
from the requirement below. Do NOT reuse any example or placeholder brand name —
invent one that fits the requirement, or use none if not applicable.

REQUIREMENT: {requirement}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM (use these exact values — do not substitute other colors)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Background:     {bg}
Card background:{card}
Accent color:   {accent}   (buttons, links, highlights, icons — do not use as full-page background)
Text:           {text}
Muted text:     {muted}
Border:         {border}
Font:           {font}
Heading style:  {hs} {hw} {ls}
Card style:     {card_style} → style={{{{ {card_style_line} borderRadius: '{ '12px' if 'xl' not in radius else '16px' }' }}}}
Shadow style:   {shadow}

LAYOUT: {LAYOUT_GUIDANCE.get(layout_type, LAYOUT_GUIDANCE["centered"])}
Required UI components: {components_line}
Notable reference details to reproduce:
{unique_line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BACKGROUND & DEPTH (make it rich — not a flat solid color)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bg_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOTION & ANIMATION  (level: {animation_style})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{ANIMATION_GUIDANCE.get(animation_style, ANIMATION_GUIDANCE["moderate"])}
{motion_block}
Define ALL @keyframes in the single <style suppressHydrationWarning> tag. Suggested
keyframes to include and use where appropriate: fadeInUp, float, glowPulse,
gradientShift, shimmer. Stagger hero children with animation-delay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMAGERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{media_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTIONS (build in this exact order, top to bottom)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_section_lines(sections)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEEDBACK FROM PREVIOUS ATTEMPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{feedback}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. "use client" — the VERY FIRST line of the file.
2. Import ONLY from: react, next/link, next/font/google. No other packages exist —
   do NOT import framer-motion, lucide-react, GSAP, or any icon/animation library.
   You MAY use React hooks (useState, useEffect, useRef) from 'react' for scroll
   reveals and simple interactivity. All motion is CSS/JS you write by hand.
3. Load the font: const fontInst = {font}({{ subsets: ['latin'] }}) then
   <main className={{fontInst.className}}>.
4. For reveal-on-scroll, define ONE small hook and reuse it, e.g.:
   function useReveal() {{
     const ref = useRef(null); const [shown, setShown] = useState(false);
     useEffect(() => {{
       const el = ref.current; if (!el) return;
       const io = new IntersectionObserver(([e]) => {{ if (e.isIntersecting) {{ setShown(true); io.disconnect(); }} }}, {{ threshold: 0.15 }});
       io.observe(el); return () => io.disconnect();
     }}, []);
     return {{ ref, style: {{ opacity: shown ? 1 : 0, transform: shown ? 'none' : 'translateY(30px)', transition: 'opacity 0.7s ease, transform 0.7s ease' }} }};
   }}
   Then per section: const r = useReveal(); <section ref={{r.ref}} style={{r.style}}>…</section>
5. All @keyframes live in a single <style suppressHydrationWarning> tag, the FIRST
   child inside <main>. Decorative floating/glow elements must be
   position:absolute, pointerEvents:'none', and behind content (low z-index).
6. Use Tailwind utility classes for layout/spacing and inline style={{{{...}}}} for
   exact colors/gradients/animations.
7. export default function {fn}() — one CamelCase function name, no arguments.
8. Fully responsive: use sm:/md:/lg: breakpoints; decorative background elements
   must not cause horizontal scroll (keep overflow-x hidden on the outer wrapper).
9. Real, specific copy — no "Lorem ipsum", no "TODO", no bracket placeholders.
10. Minimum 200 lines of JSX. Return ONLY raw TypeScript/TSX — zero markdown fences,
    zero explanation before or after the code.

GENERATE THE COMPLETE {page_label.upper()} PAGE NOW:
"""


def _build_feedback(latest_feedback: list, iteration: int) -> str:
    if not latest_feedback or iteration == 0:
        return (
            "This is the first attempt. Follow the design system and section plan "
            "above precisely and produce a complete, polished, production-ready page."
        )
    lines = ["The previous attempt scored below the similarity threshold. Fix all of the following:", ""]
    for i, item in enumerate(latest_feedback, 1):
        lines.append(f"  {i}. {item}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION — LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
def generate_code(state: AgentState) -> AgentState:
    print(f"\n[Code Generator] Iteration {state.current_iteration + 1}...")

    features = state.captured_features
    user_input = state.user_input
    if not features or not user_input:
        state.error_message = "Missing features or user_input"
        return state

    feedback = _build_feedback(state.latest_feedback, state.current_iteration)

    # Decode the cached reference screenshot (captured by the feature extractor).
    ref_bytes = None
    if state.reference_image_b64:
        try:
            ref_bytes = base64.b64decode(state.reference_image_b64)
        except Exception as e:
            print(f"[Code Generator] Could not decode cached reference image: {e}")

    # Reference design-system analysis — only needed once, cached across iterations.
    va = state.reference_analysis if state.reference_analysis else {}
    if state.current_iteration == 0 and not va and ref_bytes:
        va = _run_visual_analysis(ref_bytes)
        state.reference_analysis = va

    theme = _pick_theme(features, va, user_input.user_requirement)
    accent, bg, card, text, muted, border = _assign_colors(features, va, theme)
    print(f"[Code Generator] theme={theme} accent={accent} bg={bg} card={card} "
          f"reference_image={'yes' if ref_bytes else 'no'}")

    typo = (va or {}).get("typography", {})
    fx = (va or {}).get("visual_effects", {})
    motion = (va or {}).get("animations", {})
    background = (va or {}).get("background", {})
    media = (va or {}).get("media", {})
    unique_features = (va or {}).get("unique_features", [])

    # Allow real placeholder images (picsum) only when the user opted in via env —
    # keeps generated sites hermetic by default, richer when desired.
    import os
    allow_images = os.getenv("ALLOW_PLACEHOLDER_IMAGES", "false").lower() in ("1", "true", "yes")

    generated_pages = []
    for page_name in (user_input.pages_requested or ["index", "about", "contact"]):
        is_landing = page_name.lower().strip() in ["index", "home", "landing", "landing page", "landing-page"]
        print(f"[Code Generator] Generating: '{page_name}'...")
        try:
            sections = _section_plan(page_name, is_landing, features)
            fn = "HomePage" if is_landing else "".join(w.capitalize() for w in page_name.strip().split()) + "Page"
            page_label = "landing" if is_landing else page_name

            # Only the landing page is grounded on the reference image — inner
            # pages (about/contact/...) inherit the same design system via the
            # extracted values but shouldn't literally copy the reference layout.
            use_ref_image = ref_bytes if is_landing else None

            prompt = _build_prompt(
                page_label, fn, accent, bg, card, text, muted, border,
                typo, fx, features.layout_type, features.animation_style,
                features.ui_components, unique_features, sections,
                user_input.user_requirement, feedback,
                has_reference_image=bool(use_ref_image),
                motion=motion, background=background, media=media,
                allow_placeholder_images=allow_images,
            )
            if use_ref_image:
                tsx = _clean(vision_prompt(prompt, image_bytes_list=[use_ref_image], temperature=0.6))
            else:
                tsx = _clean(text_prompt(prompt, temperature=0.6))

            page = (
                _rich_fallback(page_name, is_landing, accent, bg, card, text, muted, border, user_input.user_requirement)
                if len(tsx.strip()) < 400 else
                GeneratedPage(
                    page_name=page_name, tsx_code=tsx, is_landing=is_landing,
                    route_path="/" if is_landing else f"/{page_name.lower().replace(' ', '-').replace('_', '-')}",
                )
            )
            generated_pages.append(page)
            print(f"[Code Generator] ✅ '{page_name}' ({len(page.tsx_code):,} chars)")
        except Exception as e:
            print(f"[Code Generator] ❌ '{page_name}': {e}")
            generated_pages.append(_rich_fallback(page_name, is_landing, accent, bg, card, text, muted, border, user_input.user_requirement))

    run_id, run_dir = write_all_pages(generated_pages, [accent, bg, card])
    state.generated_pages = generated_pages
    state.output_run_id = run_id
    state.final_output_path = str(run_dir)
    state.current_iteration += 1
    print(f"[Code Generator] ✅ Run:{run_id}")
    return state


def _clean(code: str) -> str:
    import re
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    code = code.strip()

    def fix_fn(m):
        return "export default function " + "".join(w.capitalize() for w in m.group(1).strip().split()) + "("
    code = re.sub(r"export default function ([A-Za-z][A-Za-z0-9 ]*)\(", fix_fn, code)
    code = (code.replace("&#x27;", "'").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&amp;", "&"))
    return code.strip()


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK — only used if Gemini fails/returns near-empty output.
# Dynamic: reflects the real assigned colors + the actual requirement text,
# so two different requirements never render an identical fallback page.
# ─────────────────────────────────────────────────────────────────────────────
def _rich_fallback(page_name: str, is_landing: bool, accent: str, bg: str, card: str,
                    text: str, muted: str, border: str, requirement: str) -> GeneratedPage:
    fn = "HomePage" if is_landing else "".join(w.capitalize() for w in page_name.strip().split()) + "Page"
    headline = (requirement.strip().split(".")[0] or page_name.title())[:90]
    title = page_name.strip().title()

    tsx = f'''"use client"
import {{ Inter }} from 'next/font/google'
const inter = Inter({{ subsets: ['latin'] }})

export default function {fn}() {{
  return (
    <main className={{inter.className}} style={{{{ background: '{bg}', color: '{text}', minHeight: '100vh' }}}}>
      <nav style={{{{
        position: 'fixed', top: 0, width: '100%', zIndex: 50,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '16px 40px', background: '{bg}ee', borderBottom: '1px solid {border}'
      }}}}>
        <span style={{{{ fontWeight: 800, fontSize: 20, color: '{accent}' }}}}>{title}</span>
        <a href="#cta" style={{{{
          background: '{accent}', color: '#fff', padding: '10px 20px',
          borderRadius: 8, fontWeight: 700, fontSize: 14, textDecoration: 'none'
        }}}}>Get Started</a>
      </nav>

      <section style={{{{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', textAlign: 'center',
        padding: '0 24px'
      }}}}>
        <h1 style={{{{ fontSize: 'clamp(36px,6vw,64px)', fontWeight: 800, maxWidth: 800, marginBottom: 20 }}}}>
          {headline}
        </h1>
        <p style={{{{ fontSize: 18, color: '{muted}', maxWidth: 560, marginBottom: 32, lineHeight: 1.6 }}}}>
          {requirement[:220] if requirement else "A page generated from your requirement."}
        </p>
        <a id="cta" href="#" style={{{{
          background: '{accent}', color: '#fff', padding: '14px 32px',
          borderRadius: 10, fontWeight: 700, fontSize: 16, textDecoration: 'none'
        }}}}>Get Started</a>
      </section>

      <section style={{{{ padding: '80px 24px', background: '{card}' }}}}>
        <div style={{{{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px,1fr))', gap: 24 }}}}>
          {{[1, 2, 3].map(i => (
            <div key={{i}} style={{{{ background: '{bg}', border: '1px solid {border}', borderRadius: 14, padding: 28 }}}}>
              <h3 style={{{{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}}}>Feature {{i}}</h3>
              <p style={{{{ fontSize: 14, color: '{muted}', lineHeight: 1.6 }}}}>
                Generation of this page's real content failed this attempt — this is a
                placeholder section pending the next iteration.
              </p>
            </div>
          ))}}
        </div>
      </section>

      <footer style={{{{ padding: '40px 24px', textAlign: 'center', color: '{muted}', fontSize: 13, borderTop: '1px solid {border}' }}}}>
        © 2026 {title}. All rights reserved.
      </footer>
    </main>
  )
}}
'''
    return GeneratedPage(
        page_name=page_name, tsx_code=tsx, is_landing=is_landing,
        route_path="/" if is_landing else f"/{page_name.lower().replace(' ', '-')}",
    )
