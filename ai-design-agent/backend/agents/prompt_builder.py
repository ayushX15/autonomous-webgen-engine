# backend/agents/prompt_builder.py
# ─────────────────────────────────────────────────────────────────────────────
# Analyzes the reference site screenshot and generates a CUSTOM prompt
# specifically tailored to that site's design system.
# This replaces the fixed template approach.
# ─────────────────────────────────────────────────────────────────────────────

from backend.tools.gemini_client import vision_json_prompt, json_prompt
from backend.models.schemas import CapturedFeatures


ANALYSIS_PROMPT = """
You are an expert frontend developer and UI/UX analyst.

Analyze this website screenshot in extreme technical detail.
Your analysis will be used to generate code that closely mimics this design.

Extract and return ONLY this exact JSON:
{
    "design_system": {
        "primary_bg": "<exact hex of main background>",
        "secondary_bg": "<exact hex of card/section backgrounds>",
        "primary_accent": "<exact hex of main accent/brand color>",
        "secondary_accent": "<exact hex of secondary accent>",
        "text_primary": "<exact hex of main text>",
        "text_secondary": "<exact hex of muted text>",
        "border_color": "<exact hex or rgba of borders>"
    },
    "typography": {
        "heading_weight": "<font-black/font-bold/font-semibold>",
        "heading_size": "<text-6xl/text-7xl/text-8xl for hero>",
        "heading_style": "<describe: italic, uppercase, mixed-case, etc>",
        "body_font": "<closest Google Font: Inter/Geist/Poppins/etc>",
        "letter_spacing": "<tracking-tight/tracking-normal/tracking-wide>"
    },
    "visual_effects": {
        "card_style": "<glassmorphism/solid/outlined/elevated>",
        "blur_amount": "<backdrop-blur-sm/md/lg/xl/2xl>",
        "border_style": "<none/subtle/colored/glowing>",
        "gradient_direction": "<to-br/to-r/radial/none>",
        "gradient_description": "<describe the gradient in detail>",
        "shadow_style": "<none/subtle/colored-glow/hard>",
        "border_radius": "<rounded-lg/xl/2xl/3xl/full>"
    },
    "animations": {
        "hero_animation": "<describe what animates in the hero>",
        "scroll_effects": "<parallax/fade-in/slide-up/none>",
        "hover_effects": "<scale/glow/color-shift/underline>",
        "special_elements": "<any unique animated elements>"
    },
    "layout": {
        "hero_style": "<centered/left-aligned/split/full-bleed>",
        "section_padding": "<py-20/py-24/py-32>",
        "content_width": "<max-w-5xl/max-w-6xl/max-w-7xl>",
        "grid_columns": "<2/3/4 columns for feature grid>"
    },
    "unique_features": [
        "<list specific design elements that make this site unique>",
        "<e.g. keyboard animation, glowing buttons, floating cards>",
        "<e.g. gradient text on headings, noise texture overlay>"
    ],
    "css_techniques": [
        "<list specific CSS techniques to implement>",
        "<e.g. background: radial-gradient(circle at 50% 0%, #ff4500 0%, transparent 60%)>",
        "<e.g. border: 1px solid rgba(255,255,255,0.1)>",
        "<e.g. box-shadow: 0 0 40px rgba(255,69,0,0.3)>"
    ]
}
"""


def build_dynamic_prompt(
    screenshot_bytes: bytes,
    captured_features: CapturedFeatures,
    user_requirement: str
) -> str:
    """
    Analyzes a screenshot and builds a completely custom generation prompt
    tailored to that specific website's design system.
    
    Returns a complete prompt string for the code generator.
    """
    print("[Prompt Builder] Analyzing reference design...")
    
    try:
        # Step 1: Deep visual analysis of the screenshot
        analysis = vision_json_prompt(
            prompt=ANALYSIS_PROMPT,
            image_bytes_list=[screenshot_bytes]
        )
        print(f"[Prompt Builder] Analysis complete: {analysis.get('visual_effects', {}).get('card_style', 'unknown')} style")
        
    except Exception as e:
        print(f"[Prompt Builder] Analysis failed: {e} — using feature data only")
        analysis = {}
    
    # Step 2: Build custom prompt from analysis
    return _build_prompt(analysis, captured_features, user_requirement)


def _build_prompt(analysis: dict, features: CapturedFeatures, requirement: str) -> str:
    """Constructs a custom prompt from the visual analysis."""
    
    ds = analysis.get("design_system", {})
    typo = analysis.get("typography", {})
    fx = analysis.get("visual_effects", {})
    anim = analysis.get("animations", {})
    layout = analysis.get("layout", {})
    unique = analysis.get("unique_features", [])
    css_tech = analysis.get("css_techniques", [])
    
    cp = features.color_palette
    c0 = ds.get("primary_accent") or (cp[0] if cp else "#ff4500")
    c1 = ds.get("primary_bg") or (cp[1] if len(cp) > 1 else "#0a0a0a")
    c2 = ds.get("secondary_bg") or (cp[2] if len(cp) > 2 else "#1a1a1a")
    text_color = ds.get("text_primary", "#ffffff")
    text_muted = ds.get("text_secondary", "#888888")
    border = ds.get("border_color", "rgba(255,255,255,0.1)")

    unique_str = "\n".join(f"  - {u}" for u in unique) if unique else "  - Premium modern aesthetic"
    css_str = "\n".join(f"  {c}" for c in css_tech) if css_tech else "  backdrop-filter: blur(20px)"

    prompt = f"""
You are a world-class frontend engineer creating an award-winning website.
This prompt was dynamically generated by analyzing the reference design.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT DESIGN SYSTEM (extracted from reference)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Background:        {c1}
Card/Section bg:   {c2}  
Primary accent:    {c0}
Text primary:      {text_color}
Text muted:        {text_muted}
Border:            {border}

Typography:
  Heading weight:  {typo.get("heading_weight", "font-black")}
  Heading size:    {typo.get("heading_size", "text-7xl")}
  Heading style:   {typo.get("heading_style", "bold, mixed case")}
  Font family:     {typo.get("body_font", "Inter")}
  Letter spacing:  {typo.get("letter_spacing", "tracking-tight")}

Visual Effects:
  Card style:      {fx.get("card_style", "glassmorphism")}
  Blur:            {fx.get("blur_amount", "backdrop-blur-xl")}
  Borders:         {fx.get("border_style", "subtle rgba borders")}
  Gradients:       {fx.get("gradient_description", "radial dark gradient")}
  Shadows:         {fx.get("shadow_style", "colored glow shadows")}
  Border radius:   {fx.get("border_radius", "rounded-2xl")}

Layout:
  Hero style:      {layout.get("hero_style", "centered")}
  Section padding: {layout.get("section_padding", "py-24")}
  Max width:       {layout.get("content_width", "max-w-7xl")}
  Grid:            {layout.get("grid_columns", "3")} columns

Unique Design Features:
{unique_str}

Exact CSS techniques to use:
{css_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER REQUIREMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{requirement}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY SECTIONS (build ALL of these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. NAVIGATION
   - Fixed, backdrop-blur: style={{{{backdropFilter:'blur(20px)', background:'{c1}cc'}}}}
   - Border bottom: style={{{{borderBottom:'1px solid {border}'}}}}
   - Brand name in {typo.get("heading_weight","font-black")} weight
   - Nav links with hover color: text-[{c0}]
   - CTA button: style={{{{background:'{c0}', borderRadius:'8px'}}}}

2. HERO SECTION
   - Full viewport: min-h-screen flex items-center justify-center
   - Background: style={{{{background:'radial-gradient(circle at 50% 0%, {c0}33 0%, {c1} 60%)'}}}}
   - Floating glow blob: style={{{{background:'{c0}', filter:'blur(100px)', opacity:'0.15', animation:'float 6s ease infinite'}}}}
   - H1: {typo.get("heading_size","text-7xl")} {typo.get("heading_weight","font-black")} {typo.get("letter_spacing","tracking-tight")}
   - Gradient heading: style={{{{background:'linear-gradient(135deg, {text_color}, {c0})', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}}}
   - Subtitle: text-xl style={{{{color:'{text_muted}'}}}}
   - Animated entrance: style={{{{animation:'fadeInUp 0.8s ease both'}}}}

3. FEATURE CARDS (glassmorphism)
   Each card: style={{{{
     background: 'rgba(255,255,255,0.03)',
     border: '1px solid {border}',
     backdropFilter: 'blur(20px)',
     borderRadius: '16px'
   }}}}
   Hover: transition-all duration-300 hover:scale-[1.02]
   Hover shadow: hover:shadow-[0_0_30px_{c0}33]

4. STATS BAR
   Dark section with 3-4 large numbers in {c0}
   Separator lines between stats

5. INTEGRATION/TOOL GRID
   Grid of tool cards with emoji icons
   Same glassmorphism style as feature cards

6. TESTIMONIALS
   Quote cards with glassmorphism
   Star ratings in {c0}
   Name and role in {text_muted}

7. PRICING (3 tiers)
   Middle card highlighted: style={{{{border:'2px solid {c0}', boxShadow:'0 0 40px {c0}33'}}}}
   Feature list with checkmarks in {c0}

8. FINAL CTA
   style={{{{background:'linear-gradient(135deg, {c0}22, {c1})'}}}}
   Email input + button

9. FOOTER
   4-column layout
   style={{{{borderTop:'1px solid {border}'}}}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMATION SYSTEM (implement ALL in <style> tag)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@keyframes fadeInUp {{
  from {{ opacity:0; transform:translateY(40px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes float {{
  0%,100% {{ transform:translateY(0px) scale(1); }}
  50%      {{ transform:translateY(-20px) scale(1.05); }}
}}
@keyframes glow-pulse {{
  0%,100% {{ box-shadow: 0 0 20px {c0}44; }}
  50%      {{ box-shadow: 0 0 60px {c0}88, 0 0 100px {c0}22; }}
}}
@keyframes gradient-shift {{
  0%,100% {{ background-position: 0% 50%; }}
  50%      {{ background-position: 100% 50%; }}
}}
@keyframes shimmer {{
  0%   {{ transform: translateX(-100%); }}
  100% {{ transform: translateX(100%); }}
}}

Apply:
- Hero h1: style={{{{animation:'fadeInUp 0.8s ease 0.2s both'}}}}
- Hero p:  style={{{{animation:'fadeInUp 0.8s ease 0.4s both'}}}}
- Buttons: style={{{{animation:'fadeInUp 0.8s ease 0.6s both'}}}}
- Glow blob: style={{{{animation:'float 6s ease infinite'}}}}
- CTA btn: style={{{{animation:'glow-pulse 2s ease infinite'}}}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. "use client" as ABSOLUTE FIRST LINE
2. Import ONLY: react, next/link, next/font/google
3. Load font: import {{ Inter }} from 'next/font/google' (or {typo.get("body_font","Inter")})
4. NO framer-motion, NO external icon libraries
5. Use Tailwind for layout + inline styles for exact colors/effects
6. Function name: export default function HomePage() — ONE CamelCase word
7. Add <style>{{`...keyframes...`}}</style> inside JSX return
8. Minimum 250 lines of JSX — comprehensive and complete
9. Return ONLY raw TypeScript — no markdown fences, no explanation

GENERATE THE MOST STUNNING, AWARD-WINNING LANDING PAGE NOW:
"""
    return prompt