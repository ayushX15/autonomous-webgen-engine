# backend/agents/code_generator.py
# FINAL — Dark theme + FF4500 accent + noise texture on cards

import re
from backend.models.schemas import AgentState, GeneratedPage, CapturedFeatures
from backend.tools.gemini_client import text_prompt, vision_json_prompt
from backend.tools.file_writer import write_all_pages

# ─────────────────────────────────────────────────────────────────────────────
# NOISE TEXTURE — SVG fractal noise embedded as data URI
# Applied to cards for the premium sparkle/grain effect
# ─────────────────────────────────────────────────────────────────────────────
NOISE_SVG = "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E\")"

# Card background with noise = noise SVG + transparent base
# Noise sits on top of the rgba background
CARD_BG        = f"{NOISE_SVG}, rgba(255,255,255,0.03)"
CARD_BG_HOVER  = f"{NOISE_SVG}, rgba(255,255,255,0.055)"
CARD_BG_ACCENT = f"{NOISE_SVG}, rgba(255,69,0,0.08)"   # for highlighted/Pro card


# ─────────────────────────────────────────────────────────────────────────────
# COLOR INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────
def _brightness(h: str) -> float:
    try:
        h = h.lstrip('#')
        if len(h) == 3:
            h = ''.join(c*2 for c in h)
        r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return 0.299*r + 0.587*g + 0.114*b
    except Exception:
        return 128.0

def _saturation(h: str) -> float:
    try:
        h = h.lstrip('#')
        if len(h) == 3:
            h = ''.join(c*2 for c in h)
        r,g,b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
        mx,mn = max(r,g,b), min(r,g,b)
        return (mx-mn)/mx if mx>0 else 0.0
    except Exception:
        return 0.0

def _is_navy_or_blue(h: str) -> bool:
    """Returns True if the hex color is a blue/navy tint — must be replaced with pure dark."""
    try:
        h = h.lstrip('#')
        if len(h) == 3:
            h = ''.join(c*2 for c in h)
        r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        # Blue-dominant: b is significantly larger than r, and overall dark
        return b > r + 12 and b > g + 6 and (r+g+b) < 300
    except Exception:
        return False

def _assign_colors(cp: list) -> tuple[str,str,str]:
    if not cp:
        return "#FF4500","#0a0a0a","#111111"
    valid = [c for c in cp if isinstance(c,str) and c.startswith('#') and len(c)>=4]
    if not valid:
        return "#FF4500","#0a0a0a","#111111"
    by_b = sorted(valid, key=_brightness)
    c1   = by_b[0]
    # If darkest color is navy/blue-tinted, force pure black
    if _is_navy_or_blue(c1):
        c1 = "#0a0a0a"
    cands= [c for c in valid if _brightness(c)>40]
    c0   = max(cands, key=_saturation) if cands else by_b[-1]
    if c0==c1: c0="#FF4500"
    rest = [c for c in by_b if c!=c1 and c!=c0]
    if rest:
        c2 = rest[0]
        # If the card bg is also navy/blue-tinted, force #111111
        if _is_navy_or_blue(c2):
            c2 = "#111111"
    else:
        try:
            h=c1.lstrip('#'); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
            c2=f"#{min(255,r+22):02x}{min(255,g+22):02x}{min(255,b+22):02x}"
            if _is_navy_or_blue(c2):
                c2 = "#111111"
        except Exception:
            c2="#111111"
    return c0,c1,c2


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL ANALYSIS PROMPT
# ─────────────────────────────────────────────────────────────────────────────
VISUAL_ANALYSIS_PROMPT = """
You are an expert frontend developer and UI/UX analyst.
Analyze this website screenshot in extreme technical detail.

Return ONLY this exact JSON (no markdown, no explanation):
{
    "design_system": {
        "primary_bg": "<dark hex e.g. #0a0a0a>",
        "secondary_bg": "<slightly lighter dark hex>",
        "primary_accent": "<vibrant brand color>",
        "secondary_accent": "<secondary accent>",
        "text_primary": "<main text hex>",
        "text_secondary": "<muted text hex>",
        "border_color": "<rgba or hex of borders>"
    },
    "typography": {
        "heading_weight": "<font-black or font-bold>",
        "heading_size": "<text-6xl or text-7xl or text-8xl>",
        "heading_style": "<mixed-case or uppercase>",
        "body_font": "<Inter/Geist/Manrope/Poppins>",
        "letter_spacing": "<tracking-tight or tracking-normal>"
    },
    "visual_effects": {
        "card_style": "<glassmorphism or solid or outlined>",
        "blur_amount": "<backdrop-blur-lg or xl or 2xl>",
        "gradient_description": "<describe exact gradient>",
        "shadow_style": "<colored-glow or subtle or none>",
        "border_radius": "<rounded-xl or 2xl or 3xl>"
    },
    "layout": {
        "hero_style": "<centered or left-aligned or split>",
        "section_padding": "<py-20 or py-24 or py-32>",
        "content_width": "<max-w-6xl or max-w-7xl>",
        "grid_columns": "<2 or 3 or 4>"
    },
    "unique_features": [
        "<unique design element 1>",
        "<unique design element 2>",
        "<unique design element 3>"
    ],
    "css_techniques": [
        "<exact CSS technique 1>",
        "<exact CSS technique 2>",
        "<exact CSS technique 3>"
    ]
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PROMPT — dark theme enforced + noise cards + FF4500
# ─────────────────────────────────────────────────────────────────────────────
def _build_prompt(c0,c1,c2,text,muted,border,hw,hs,ls,
                  font,cs,blur,rad,gc,cw,sp,
                  unique_str,css_str,req,feedback,dynamic=False) -> str:

    # Noise SVG string safe for f-string (no curly braces inside)
    noise = NOISE_SVG

    return f"""
You are a world-class frontend engineer creating a STUNNING DARK-THEMED website.
{"Prompt DYNAMICALLY built from visual analysis." if dynamic else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Page bg:   {c1}  ← DARK (near-black, pure #0a0a0a)
Card bg:   {c2}  ← SLIGHTLY LIGHTER DARK (#111111)
Accent:    {c0}  ← WARM RED-ORANGE #FF4500 (buttons, glows, icons ONLY)
Text:      {text}
Muted:     {muted}
Border:    {border}
Font:      {font}
Heading:   {hs} {hw} {ls}
Cards:     {cs} + noise texture + {blur}
Grid:      {gc} columns  Container: {cw}

Detected features: {unique_str}
CSS to use: {css_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL COLOR RULES  (ZERO BLUE/NAVY — PURE BLACK ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{c1} = PAGE/SECTION BACKGROUND → MUST be #0a0a0a pure near-black
       NEVER navy or blue-tinted dark (#1a1f2e #0d1117 #0f172a #161b27 #1e2130 or similar)
       ALL alternating section backgrounds must be #0a0a0a or #111111 — pure dark grey/black
       NO BLUE. NO NAVY. ZERO BLUE CHANNEL DOMINANCE.
{c2} = CARD/SECTION ALT BACKGROUND → MUST be #111111 pure dark (NOT #1e2130 or any navy)
{c0} = ACCENT ONLY → #FF4500 warm orange-red
       Use for: buttons, icon bg, glow, gradient text, badges, nav brand, checkmarks, stars
       NEVER use {c0} as full section or page background
FORBIDDEN colors (never use): #1a1f2e #0d1117 #0f172a #161b27 #1e2130 #1c2333 #13192a
  or ANY hex where blue channel > red channel by more than 10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOISE TEXTURE (apply to ALL cards and highlighted sections)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This SVG noise data URI creates the premium sparkle/grain texture:
NOISE = {noise}

CARD WITH NOISE — GLASSMORPHISM (use this for EVERY feature card, testimonial card, pricing card, step card, integration card):
style={{{{
  background: `${{NOISE}}, rgba(255,255,255,0.04)`,
  border: '1px solid {border}',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: 16,
  padding: 32,
  transition: 'all 0.3s',
  position: 'relative',
  overflow: 'hidden'
}}}}
GLASSMORPHISM IS MANDATORY on ALL cards — never use a solid opaque background like #111111 or #1a1a1a directly on cards.
Cards must be semi-transparent with backdrop-filter blur so the dark page background shows through.

HIGHLIGHTED CARD WITH NOISE (Pro pricing card, featured card):
style={{{{
  background: `${{NOISE}}, rgba(255,69,0,0.06)`,
  border: '2px solid {c0}',
  boxShadow: '0 0 80px {c0}33, inset 0 0 40px {c0}08',
  backdropFilter: 'blur(20px)',
  borderRadius: 16,
  position: 'relative',
  overflow: 'hidden'
}}}}

STAT BAR WITH NOISE:
style={{{{
  background: `${{NOISE}}, {c2}`,
  borderTop: '1px solid {border}',
  borderBottom: '1px solid {border}'
}}}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIREMENT: {req}
FEEDBACK — MUST FIX: {feedback}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1 — NAVIGATION
style={{{{position:'fixed',top:0,width:'100%',zIndex:50,
  display:'flex',justifyContent:'space-between',alignItems:'center',
  padding:'14px 40px',backdropFilter:'blur(24px)',
  background:'{c1}ee',borderBottom:'1px solid {border}'}}}}
Brand: color:{c0} (ORANGE, NOT white) {hw} text-xl tracking-tighter
Links: 14px {muted} hover:{c0} font-medium gap:32px
CTA: bg:{c0} white px:22 py:10 borderRadius:10 font-bold
  boxShadow:'0 0 24px {c0}55'

SECTION 2 — HERO (PREMIUM — most important section)
Outer: minHeight:100vh flex alignItems:center justifyContent:center
  position:relative overflow:hidden paddingTop:80

Background (DARK pure-black with subtle top glow — NOT navy):
style={{{{background:'radial-gradient(ellipse 80% 55% at 50% -15%, {c0}40 0%, transparent 62%), #0a0a0a'}}}}

GLOW ORBS:
Orb1: 700x700px blur:160px opacity:0.14 bg:{c0}
  top:-200px left:-180px animation:float 10s infinite
Orb2: 500x500px blur:130px opacity:0.09 bg:{c0}
  bottom:-150px right:-120px animation:float 8s infinite reverse

GRID TEXTURE:
style={{{{position:'absolute',inset:0,pointerEvents:'none',
  backgroundImage:'radial-gradient(circle,rgba(255,255,255,0.04) 1px,transparent 1px)',
  backgroundSize:'28px 28px',opacity:0.7}}}}

CONTENT (relative z-1 text-center max-w:900px m:0 auto):

① PILL BADGE (animation:fadeInUp 0.7s both):
style={{{{display:'inline-flex',alignItems:'center',gap:8,
  padding:'6px 18px',borderRadius:999,
  background:'{c0}18',border:'1px solid {c0}44',
  color:'{c0}',fontSize:12,fontWeight:800,
  letterSpacing:'0.12em',textTransform:'uppercase',marginBottom:32}}}}
dot (6x6px bg:{c0} rounded boxShadow:0 0 8px {c0}) + "New · AI-Powered Generation"

② HEADLINE ({hs} {hw} {ls} lineHeight:0.95 white, animation:fadeInUp 0.9s 0.1s both):
Line 1: white text
Line 2: gradient text:
  style={{{{background:'linear-gradient(135deg, {text} 0%, {c0} 55%)',
    WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}}}

③ SUBTITLE (20px color:{muted} maxWidth:580px margin:'0 auto 16px' lineHeight:1.7,
   animation:fadeInUp 0.9s 0.25s both)

④ KBD HINT (flex justify-center gap:8 opacity:0.35 fontSize:13):
"Press" + <kbd style={{{{padding:'2px 10px',borderRadius:6,
  background:'rgba(255,255,255,0.08)',border:'1px solid rgba(255,255,255,0.12)',
  fontFamily:'monospace',color:'white'}}}}>⌘ Space</kbd> + "to open"
marginBottom:40

⑤ CTA BUTTONS (flex gap:16 justify-center flexWrap:wrap animation:fadeInUp 0.9s 0.4s both):
Primary: bg:{c0} white py:14 px:34 borderRadius:12 font-bold
  boxShadow:'0 0 40px {c0}66' animation:glow-pulse 3s infinite
Secondary: bg:rgba(255,255,255,0.06) border:1px solid rgba(255,255,255,0.14)
  white py:14 px:34 borderRadius:12 backdropFilter:blur(12px)

⑥ TRUST: "Trusted by 100,000+ developers · Free · No credit card" fontSize:13
  color:rgba(255,255,255,0.25) marginTop:24

SECTION 3 — STATS BAR (with noise texture)
style={{{{
  background: `{NOISE_SVG}, {c2}`,
  borderTop:'1px solid {border}',
  borderBottom:'1px solid {border}',
  padding:'32px 0'
}}}}
3 stats with 1px vertical dividers:
Number: 44px font-black color:{c0} tracking-tight
Label: 13px color:{muted}

SECTION 4 — FEATURES (bg:{c1}, {gc} cols, {sp})
Title: text-4xl {hw} {ls} white centered
Subtitle: 18px color:{muted}

NOISE CARD (every feature card):
const NOISE = "{noise}";
style={{{{
  background: `${{NOISE}}, rgba(255,255,255,0.03)`,
  border: '1px solid {border}',
  backdropFilter: 'blur(20px)',
  borderRadius: 16, padding: 32,
  transition: 'all 0.3s', cursor: 'default',
  position: 'relative', overflow: 'hidden'
}}}}
Hover: scale(1.03) + shadow: 0 8px 40px {c0}22

Icon box (52x52 borderRadius:14 bg:{c0}1a border:{c0}33 fontSize:26)
Ambient corner glow inside each card (position:absolute bottom:-20 right:-20
  width:110 height:110 borderRadius:50% filter:blur(42px) bg:{c0}0e)
6 features in 3x2 grid

SECTION 5 — HOW IT WORKS (bg:#111111 — pure dark, NOT navy; noise on step cards with glassmorphism)
Step cards use same NOISE card style
Step number: text-8xl font-black color:{c0} opacity:0.12 (decorative overlay, position:absolute)
Step badge circle: bg:{c0}22 border:2px solid {c0}55 color:{c0} boxShadow:0 0 28px {c0}33
3 steps with dashed connector line using linear-gradient({c0}55)

SECTION 6 — INTEGRATIONS (bg:{c1})
4-col grid, each card uses NOISE card style
Tools: VS Code, GitHub, Slack, Notion, Linear, Figma, Zoom, Spotify
Hover: border-color:{c0} scale(1.05)
"+ 200 more integrations" pill: bg:{c0}12 border:{c0}30 color:{c0}

SECTION 7 — TESTIMONIALS (bg:#111111 — pure dark, NOT navy; glassmorphism noise cards)
3 cards — NOISE card style
★★★★★ color:{c0}, quote italic color:rgba(255,255,255,0.70)
Author avatar circle: bg:{c0}25 border:{c0}45 color:{c0}
name font-bold white, role color:{muted}
Ambient glow top-left inside each card: bg:{c0}0e

SECTION 8 — PRICING (bg:{c1})
Free + Pro (highlighted) + Enterprise
Free/Enterprise: NOISE card style
Pro card (HIGHLIGHTED with noise):
style={{{{
  background: `{NOISE_SVG}, rgba(255,69,0,0.07)`,
  border: '2px solid {c0}',
  boxShadow: '0 0 80px {c0}33, inset 0 0 40px {c0}08',
  backdropFilter: 'blur(20px)',
  borderRadius: 16,
  position: 'relative', overflow: 'hidden',
  marginTop: -10
}}}}
"Most Popular" badge: bg:{c0} boxShadow:0 0 16px {c0}66
Checkmarks: color:{c0} textShadow:0 0 8px {c0} (on Pro card)
Pro CTA button: animation:glow-pulse 3s infinite

SECTION 9 — CTA (bg:{c1})
Rounded container with noise + gradient:
style={{{{
  background: `{NOISE_SVG}, linear-gradient(135deg, {c0}22 0%, {c1} 50%, {c0}15 100%)`,
  border: '1px solid {c0}30',
  borderRadius: 24, padding: '80px 60px',
  position: 'relative', overflow: 'hidden'
}}}}
Corner glow orbs inside container: top-right + bottom-left
Heading + subtitle + glow CTA button animation:glow-pulse 3s infinite

SECTION 10 — FOOTER (bg:#0a0a0a pure black — NOT navy)
borderTop:1px solid {border} py:60px
4 cols: Brand({c0} color)+social | Product | Resources | Company
Social icons: hover border-color:{c0} hover bg:{c0}18
Bottom: copyright + privacy links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMATIONS (<style suppressHydrationWarning> — FIRST child of <main>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(50px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes float{{0%,100%{{transform:translateY(0)scale(1)}}50%{{transform:translateY(-28px)scale(1.04)}}}}
@keyframes glow-pulse{{0%,100%{{box-shadow:0 0 20px {c0}55,0 0 40px {c0}22}}50%{{box-shadow:0 0 60px {c0}99,0 0 120px {c0}44}}}}
@keyframes shimmer{{0%{{background-position:-200% center}}100%{{background-position:200% center}}}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO USE NOISE IN JSX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Define at top of component (inside function body, before return):
const NOISE = "{noise}";

Then use in style:
background: `${{NOISE}}, rgba(255,255,255,0.03)`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. "use client" — VERY FIRST LINE
2. Import ONLY: react, next/link, next/font/google  (NO lucide-react, NO framer-motion)
3. const fontInst = {font}({{ subsets:['latin'] }}) → <main className={{fontInst.className}}>
4. NO framer-motion, NO lucide-react, NO external libs
5. Tailwind layout + inline style for colors/effects
6. export default function HomePage() — ONE CamelCase word
7. Responsive: sm: md: lg: everywhere
8. <style suppressHydrationWarning> FIRST child of <main>
9. const NOISE = "..." defined inside component function
10. Min 300 lines JSX — no placeholders, no TODOs
11. Return ONLY raw TypeScript — ZERO markdown
12. Background must be pure near-black #0a0a0a — NEVER navy or blue-tinted dark
13. Nav brand name must use color:{c0} (orange), NOT white
14. ALL section alternating backgrounds: use #0a0a0a or #111111 ONLY — no navy, no blue
15. ALL cards MUST use glassmorphism: backdrop-filter:blur(20px) + semi-transparent background rgba(255,255,255,0.04) — NEVER solid opaque card backgrounds

GENERATE THE COMPLETE DARK-THEMED LANDING PAGE WITH NOISE CARDS NOW:
"""


# ─────────────────────────────────────────────────────────────────────────────
# OUTER PAGE PROMPT
# ─────────────────────────────────────────────────────────────────────────────
def _outer_prompt(pu,fn,c0,c1,c2,tx,mu,bo,font,req,content) -> str:
    noise = NOISE_SVG
    return f"""
You are a world-class Next.js 14 developer. Generate complete dark-themed {pu} page.

DESIGN: bg:{c1}(DARK pure-black #0a0a0a — NOT navy) card:{c2}(#111111) accent:{c0}(#FF4500 USE SPARINGLY)
text:{tx} muted:{mu} border:{bo} font:{font}

NOISE TEXTURE (define inside component, apply to ALL cards):
const NOISE = "{noise}";
Card: background:`${{NOISE}}, rgba(255,255,255,0.03)` + border:{bo} + backdropFilter:blur(20px) + borderRadius:16

NAV: fixed backdropFilter:blur(24px) bg:{c1}ee border:{bo}
Brand: color:{c0} (ORANGE — NOT white) + links(color:{mu} hover:{c0}) + CTA(bg:{c0})

REQUIREMENT: {req}
PAGE CONTENT: {content}

ANIMATIONS in <style suppressHydrationWarning>:
fadeInUp | glow-pulse(color:{c0})

RULES:
1. "use client" FIRST LINE
2. Import: react, next/link, next/font/google ONLY
3. export default function {fn}() — ONE CamelCase word
4. <style suppressHydrationWarning> first in <main>
5. const NOISE defined inside component
6. Dark pure-black theme (#0a0a0a bg, #111111 cards), noise on every card, min 140 lines JSX
7. ONLY raw TypeScript — no markdown

GENERATE {pu} NOW:
"""


PAGE_CONTENT = {
    "about": """
HERO: "Our Story" gradient heading + dark radial bg + pill badge
MISSION: glassmorphism+noise card, large quote, left {c0} border
VALUES: 4 noise cards — Speed|Design|Trust|Privacy
TEAM: 4 noise member cards — emoji, name, role, bio
TIMELINE: 4 milestones, {c0} dot connector
CTA: dark gradient+noise container
""",
    "contact": """
HERO: "Get In Touch" gradient heading + dark bg
FORM: noise card container — Name+Email+Subject+Message
  Inputs: dark bg, border:{bo}, white text
  Submit: bg:{c0} glow-pulse
CONTACT CARDS: 3 noise cards — Email|Phone|Location
SOCIAL: 5 pill buttons hover:{c0}
""",
    "extensions": """
HERO: "Extensions Store" dark bg + search bar + count badge
STATS: noise bar — total, downloads, contributors
FILTERS: pill bar (All|Productivity|Engineering|Design|Writing)
FEATURED: 1 large noise glassmorphism card
GRID: 12 noise cards 3-col — icon, name, author, Install btn
""",
    "pricing": """
HERO: "Simple Pricing" dark bg
Free(noise outlined) | Pro(highlighted noise {c0} glow, Most Popular) | Team(noise)
COMPARISON TABLE: checkmarks color:{c0}
FAQ: 5 items in noise cards
CTA: dark gradient+noise container
""",
    "products": """
HERO: collection heading + filter pills — dark bg
GRID: 9 noise product cards 3-col — placeholder, name, price, stars, cart btn
CATEGORIES: scrollable pill bar
FEATURED: 1 large noise card
""",
    "default": """
HERO: heading + gradient text + description + CTA — dark bg
CONTENT: 3 noise glassmorphism cards with icons
HIGHLIGHT: noise callout with {c0}22 gradient
CTA: dark gradient+noise container
"""
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def generate_code(state: AgentState) -> AgentState:
    print(f"\n[Code Generator] Iteration {state.current_iteration + 1}...")

    features   = state.captured_features
    user_input = state.user_input
    if not features or not user_input:
        state.error_message = "Missing features or user_input"
        return state

    feedback = _build_feedback(state.latest_feedback, state.current_iteration)

    # Smart color assignment — prevents accent-as-background bug
    c0, c1, c2 = _assign_colors(features.color_palette or [])
    print(f"[Code Generator] Colors → accent:{c0} bg:{c1} card:{c2}")

    # Visual analysis on iteration 0 only (quota efficient)
    va = {}
    if state.current_iteration == 0 and user_input.reference_urls:
        va = _run_visual_analysis(user_input.reference_urls[0])
        if va:
            ds  = va.get("design_system", {})
            va0 = ds.get("primary_accent", c0)
            va1 = ds.get("primary_bg",     c1)
            # Safety: ensure accent is brighter than background
            if _brightness(va0) < _brightness(va1):
                ds["primary_accent"], ds["primary_bg"] = va1, va0
                print(f"[Code Generator] Color safety swap applied")

    generated_pages = []
    for page_name in (user_input.pages_requested or ["index","about","contact"]):
        is_landing = page_name.lower().strip() in [
            "index","home","landing","landing page","landing-page"
        ]
        print(f"[Code Generator] Generating: '{page_name}'...")
        try:
            tsx = (
                _gen_landing(features, user_input.user_requirement, feedback, c0, c1, c2, va)
                if is_landing else
                _gen_outer(page_name, features, user_input.user_requirement, c0, c1, c2, va)
            )
            page = (
                _rich_fallback(page_name, is_landing, c0, c1, c2)
                if len(tsx.strip()) < 500 else
                GeneratedPage(
                    page_name=page_name, tsx_code=tsx, is_landing=is_landing,
                    route_path="/" if is_landing
                               else f"/{page_name.lower().replace(' ','-').replace('_','-')}"
                )
            )
            generated_pages.append(page)
            print(f"[Code Generator] ✅ '{page_name}' ({len(tsx):,} chars)")
        except Exception as e:
            print(f"[Code Generator] ❌ '{page_name}': {e}")
            generated_pages.append(_rich_fallback(page_name, is_landing, c0, c1, c2))

    run_id, run_dir = write_all_pages(generated_pages, [c0,c1,c2])
    state.generated_pages   = generated_pages
    state.output_run_id     = run_id
    state.final_output_path = str(run_dir)
    state.current_iteration += 1
    print(f"[Code Generator] ✅ Run:{run_id} accent:{c0} bg:{c1}")
    return state


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _run_visual_analysis(url: str) -> dict:
    print("[Code Generator] 🔍 Visual analysis...")
    try:
        from backend.tools.site_scraper import scrape_site
        data = scrape_site(url)
        sb   = data.get("screenshot_bytes")
        if not sb:
            return {}
        result = vision_json_prompt(prompt=VISUAL_ANALYSIS_PROMPT, image_bytes_list=[sb])
        a = result.get("design_system",{}).get("primary_accent","?")
        s = result.get("visual_effects",{}).get("card_style","?")
        print(f"[Code Generator] ✅ Analysis: {s} cards, accent:{a}")
        return result
    except Exception as e:
        print(f"[Code Generator] Analysis failed: {e}")
        return {}


def _gen_landing(features, req, feedback, c0, c1, c2, va) -> str:
    ds   = va.get("design_system",{})   if va else {}
    typo = va.get("typography",{})      if va else {}
    fx   = va.get("visual_effects",{})  if va else {}
    lay  = va.get("layout",{})          if va else {}
    uniq = va.get("unique_features",[]) if va else []
    css  = va.get("css_techniques",[])  if va else []

    ac  = ds.get("primary_accent", c0)
    bg  = ds.get("primary_bg",     c1)
    cd  = ds.get("secondary_bg",   c2)
    tx  = ds.get("text_primary",   "#ffffff")
    mu  = ds.get("text_secondary", "#888888")
    # ── CHANGED: border default was rgba(255,255,255,0.1) → 0.08 (Image 2 is subtler)
    bo  = ds.get("border_color",   "rgba(255,255,255,0.08)")

    # Sanitize: if visual analysis returned navy/blue-tinted bg, override with pure black
    if _is_navy_or_blue(bg):  bg = "#0a0a0a"
    if _is_navy_or_blue(cd):  cd = "#111111"

    if _brightness(ac) < _brightness(bg):
        ac, bg = bg, ac

    hw  = typo.get("heading_weight","font-black")
    hs  = typo.get("heading_size",  "text-7xl")
    ls  = typo.get("letter_spacing","tracking-tight")
    fn  = typo.get("body_font",     "Inter")
    cs  = fx.get("card_style",      "glassmorphism")
    bl  = fx.get("blur_amount",     "backdrop-blur-xl")
    rad = fx.get("border_radius",   "rounded-2xl")
    gc  = lay.get("grid_columns",   "3")
    cw  = lay.get("content_width",  "max-w-7xl")
    sp  = lay.get("section_padding","py-24")

    u_str = "\n".join(f"  - {u}" for u in uniq) if uniq else "  - Dark glassmorphism with noise texture and colored glow"
    c_str = "\n".join(f"  {c}" for c in css) if css else (
        f"  background:radial-gradient(ellipse 80% 55% at 50% -15%, {ac}40 0%, transparent 62%), {bg}\n"
        f"  border:1px solid rgba(255,255,255,0.08)\n"
        f"  box-shadow:0 0 60px {ac}22"
    )

    print(f"[Code Generator] {'DYNAMIC' if va else 'Standard'} prompt")
    prompt = _build_prompt(
        ac,bg,cd,tx,mu,bo,hw,hs,ls,fn,cs,bl,rad,gc,cw,sp,
        u_str,c_str,req,feedback,dynamic=bool(va)
    )
    return _clean(text_prompt(prompt, temperature=0.4))


def _gen_outer(page_name, features, req, c0, c1, c2, va) -> str:
    clean = page_name.lower().strip().replace(' ','-').replace('_','-')
    fn    = ''.join(w.capitalize() for w in page_name.strip().split()) + "Page"
    ctnt  = PAGE_CONTENT.get(clean, PAGE_CONTENT["default"])

    ds  = va.get("design_system",{}) if va else {}
    ac  = ds.get("primary_accent", c0)
    bg  = ds.get("primary_bg",     c1)
    cd  = ds.get("secondary_bg",   c2)
    # ── CHANGED: border default was rgba(255,255,255,0.1) → 0.08
    bo  = ds.get("border_color",   "rgba(255,255,255,0.08)")
    tx  = ds.get("text_primary",   "#ffffff")
    mu  = ds.get("text_secondary", "#888888")
    fnt = va.get("typography",{}).get("body_font","Inter") if va else "Inter"

    # Sanitize: if visual analysis returned navy/blue-tinted bg, override with pure black
    if _is_navy_or_blue(bg):  bg = "#0a0a0a"
    if _is_navy_or_blue(cd):  cd = "#111111"

    if _brightness(ac) < _brightness(bg):
        ac, bg = bg, ac

    content = ctnt.replace("{c0}",ac).replace("{border_color}",bo)
    prompt  = _outer_prompt(clean.upper(),fn,ac,bg,cd,tx,mu,bo,fnt,req,content)
    return _clean(text_prompt(prompt, temperature=0.4))


def _build_feedback(feedback: list, iteration: int) -> str:
    if not feedback or iteration == 0:
        return (
            "FIRST ITERATION — go all out.\n"
            "DARK theme: pure near-black #0a0a0a background (NOT navy/blue), #FF4500 accent for glows/buttons ONLY.\n"
            "Nav brand name must use color:#FF4500 (orange), NOT white.\n"
            "NOISE TEXTURE: define const NOISE inside component, apply to every card.\n"
            "GLASSMORPHISM: ALL cards must use backdrop-filter:blur(20px) + rgba(255,255,255,0.04) — never solid opaque backgrounds on cards.\n"
            "NO NAVY/BLUE: alternating sections must use #111111 not navy (#1a1f2e etc).\n"
            "Premium hero: pill badge + gradient heading + glow orbs + grid texture + kbd hint.\n"
            "Ambient corner glows inside feature/testimonial cards.\n"
            "All 10 sections complete."
        )
    lines = ["PREVIOUS ITERATION BELOW THRESHOLD. Fix ALL:",""]
    for i,item in enumerate(feedback,1):
        lines.append(f"  {i}. {item}")
    lines += [
        "","MANDATORY:",
        "  • DARK pure-black background (#0a0a0a) — NEVER navy or blue-tinted dark (#1a1f2e #0d1117 etc)",
        "  • Alternating section backgrounds: #111111 ONLY — never navy",
        "  • ALL cards must use glassmorphism: backdrop-filter:blur(20px) + rgba(255,255,255,0.04) bg",
        "  • Nav brand color must be #FF4500 (orange), NOT white",
        "  • #FF4500 accent ONLY on buttons, icons, glows, badges, checkmarks, stars",
        "  • NOISE texture on every card (const NOISE = '...' + template literal)",
        "  • Hero: pill badge + gradient h1 + glow orbs + grid + kbd hint",
        "  • Ambient corner glows inside feature/testimonial cards",
        "  • All 10 sections complete"
    ]
    return "\n".join(lines)


def _clean(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code  = "\n".join(lines[1:-1] if lines[-1].strip()=="```" else lines[1:])
    code = code.strip()
    def fix_fn(m):
        return ('export default function ' +
                ''.join(w.capitalize() for w in m.group(1).strip().split()) + '(')
    code = re.sub(r'export default function ([A-Za-z][A-Za-z0-9 ]*)\(', fix_fn, code)
    code = (code.replace("&#x27;","'").replace("&#39;","'")
                .replace("&quot;",'"').replace("&amp;","&"))
    return code.strip()


# ─────────────────────────────────────────────────────────────────────────────
# RICH FALLBACK — premium dark + noise cards  (Image 2 colors)
# ─────────────────────────────────────────────────────────────────────────────
def _rich_fallback(page_name: str, is_landing: bool,
                   c0: str, c1: str, c2: str) -> GeneratedPage:
    fn  = ''.join(w.capitalize() for w in page_name.strip().split()) + "Page"
    ttl = page_name.strip().title()
    # Noise string for f-string (no braces)
    noise = NOISE_SVG

    tsx = f'''"use client"
import Link from 'next/link'
import {{ Inter }} from 'next/font/google'
const inter = Inter({{ subsets: ['latin'] }})

export default function {fn}() {{
  const NOISE = "{noise}"

  return (
    <main className={{inter.className}} style={{{{background:'{c1}',minHeight:'100vh'}}}}>
      <style suppressHydrationWarning>{{`
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        @keyframes fadeInUp{{from{{opacity:0;transform:translateY(50px)}}to{{opacity:1;transform:translateY(0)}}}}
        @keyframes float{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-28px) scale(1.04)}}}}
        @keyframes glow-pulse{{0%,100%{{box-shadow:0 0 20px {c0}55,0 0 40px {c0}22}}50%{{box-shadow:0 0 60px {c0}99,0 0 120px {c0}44}}}}
        .nav-link{{color:rgba(255,255,255,0.55);font-size:14px;font-weight:500;text-decoration:none;transition:color 0.2s;}}
        .nav-link:hover{{color:{c0};}}
        .card-hover{{transition:all 0.3s ease;}}
        .card-hover:hover{{transform:translateY(-4px) scale(1.03);border-color:{c0}44!important;box-shadow:0 8px 40px {c0}22!important;}}
        .int-card{{transition:all 0.25s ease;}}
        .int-card:hover{{transform:scale(1.05);border-color:{c0}55!important;}}
        .footer-link{{display:block;font-size:14px;color:rgba(255,255,255,0.38);text-decoration:none;margin-bottom:10px;transition:color 0.2s;}}
        .footer-link:hover{{color:{c0};}}
        .social-icon{{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.09);font-size:16px;text-decoration:none;transition:border-color 0.2s,background 0.2s;}}
        .social-icon:hover{{border-color:{c0}55;background:{c0}18;}}
        .pricing-card{{transition:transform 0.3s ease;}}
        .pricing-card:hover{{transform:translateY(-6px);}}
        @media(max-width:768px){{
          .nav-links{{display:none!important;}}
          .features-grid{{grid-template-columns:1fr!important;}}
          .pricing-grid{{grid-template-columns:1fr!important;}}
          .footer-grid{{grid-template-columns:1fr 1fr!important;}}
        }}
      `}}</style>

      {{/* ── Navigation ── */}}
      <nav style={{{{
        position:'fixed',top:0,width:'100%',zIndex:50,
        display:'flex',justifyContent:'space-between',alignItems:'center',
        padding:'14px 40px',backdropFilter:'blur(24px)',
        background:'{c1}ee',borderBottom:'1px solid rgba(255,255,255,0.08)'
      }}}}>
        {{/* CHANGED: brand color is now {c0} (orange) not white */}}
        <span style={{{{fontWeight:900,fontSize:20,color:'{c0}',letterSpacing:'-0.03em',cursor:'pointer'}}}}>
          Momentum.
        </span>
        <div className="nav-links" style={{{{display:'flex',gap:32}}}}>
          {{['Features','How It Works','Integrations','Pricing'].map((l,i)=>(
            <a key={{i}} href={{`#${{l.toLowerCase().replace(/ /g,'-')}}`}} className="nav-link">{{l}}</a>
          ))}}
        </div>
        <a href="#pricing" style={{{{
          background:'{c0}',color:'white',padding:'10px 22px',
          borderRadius:10,fontWeight:700,fontSize:14,textDecoration:'none',
          boxShadow:'0 0 24px {c0}55',animation:'glow-pulse 3s infinite'
        }}}}>Get Started</a>
      </nav>

      {{/* ── Hero ── */}}
      <section style={{{{
        minHeight:'100vh',display:'flex',alignItems:'center',
        justifyContent:'center',position:'relative',overflow:'hidden',paddingTop:80,
        background:'radial-gradient(ellipse 80% 55% at 50% -15%, {c0}40 0%, transparent 62%), #0a0a0a'
      }}}}>
        {{/* Glow orb top-left */}}
        <div style={{{{
          position:'absolute',width:700,height:700,borderRadius:'50%',
          filter:'blur(160px)',opacity:0.14,background:'{c0}',
          top:-200,left:-180,animation:'float 10s ease infinite',pointerEvents:'none'
        }}}} />
        {{/* Glow orb bottom-right */}}
        <div style={{{{
          position:'absolute',width:500,height:500,borderRadius:'50%',
          filter:'blur(130px)',opacity:0.09,background:'{c0}',
          bottom:-150,right:-120,animation:'float 8s ease infinite reverse',pointerEvents:'none'
        }}}} />
        {{/* Grid dot texture */}}
        <div style={{{{
          position:'absolute',inset:0,pointerEvents:'none',
          backgroundImage:'radial-gradient(circle,rgba(255,255,255,0.04) 1px,transparent 1px)',
          backgroundSize:'28px 28px',opacity:0.7
        }}}} />

        <div style={{{{textAlign:'center',position:'relative',zIndex:1,padding:'0 20px',maxWidth:900,margin:'0 auto'}}}}>
          {{/* Pill badge */}}
          <div style={{{{
            display:'inline-flex',alignItems:'center',gap:8,padding:'6px 18px',
            borderRadius:999,background:'{c0}18',border:'1px solid {c0}44',
            color:'{c0}',fontSize:12,fontWeight:800,letterSpacing:'0.12em',
            textTransform:'uppercase',marginBottom:32,animation:'fadeInUp 0.7s both'
          }}}}>
            <span style={{{{width:6,height:6,borderRadius:'50%',background:'{c0}',boxShadow:'0 0 8px {c0}'}}}} />
            New · AI-Powered Generation
          </div>

          {{/* Headline */}}
          <h1 style={{{{
            fontSize:'clamp(52px,9vw,104px)',fontWeight:900,
            letterSpacing:'-0.04em',lineHeight:0.95,color:'white',
            marginBottom:28,animation:'fadeInUp 0.9s ease 0.1s both'
          }}}}>
            Unleash Your<br />
            <span style={{{{
              background:'linear-gradient(135deg,#fff 0%,{c0} 55%)',
              WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',backgroundClip:'text'
            }}}}>
              {ttl}
            </span>
          </h1>

          {{/* Subtitle */}}
          <p style={{{{
            fontSize:20,color:'rgba(255,255,255,0.55)',maxWidth:580,
            margin:'0 auto 16px',lineHeight:1.7,animation:'fadeInUp 0.9s ease 0.25s both'
          }}}}>
            The ultimate productivity tool for developers. Fast, extensible, and built for speed.
          </p>

          {{/* Kbd hint */}}
          <div style={{{{
            display:'flex',alignItems:'center',gap:8,justifyContent:'center',
            marginBottom:40,opacity:0.35,fontSize:13,color:'rgba(255,255,255,0.6)',
            animation:'fadeInUp 0.9s ease 0.35s both'
          }}}}>
            <span>Press</span>
            <kbd style={{{{
              padding:'2px 10px',borderRadius:6,background:'rgba(255,255,255,0.08)',
              border:'1px solid rgba(255,255,255,0.12)',fontFamily:'monospace',fontSize:12,color:'white'
            }}}}>⌘ Space</kbd>
            <span>to open</span>
          </div>

          {{/* CTA buttons */}}
          <div style={{{{display:'flex',gap:16,justifyContent:'center',flexWrap:'wrap',animation:'fadeInUp 0.9s ease 0.4s both'}}}}>
            <a href="#pricing" style={{{{
              background:'{c0}',color:'white',padding:'14px 34px',
              borderRadius:12,fontWeight:700,fontSize:16,textDecoration:'none',
              boxShadow:'0 0 40px {c0}66',animation:'glow-pulse 3s ease infinite'
            }}}}>Download for Mac →</a>
            <a href="#features" style={{{{
              background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.14)',
              color:'white',padding:'14px 34px',borderRadius:12,fontWeight:600,
              fontSize:16,textDecoration:'none',backdropFilter:'blur(12px)'
            }}}}>Learn More</a>
          </div>
          <p style={{{{fontSize:13,color:'rgba(255,255,255,0.25)',marginTop:24}}}}>
            Trusted by 100,000+ developers · Free · No credit card
          </p>
        </div>
      </section>

      {{/* ── Stats bar with noise ── */}}
      <section style={{{{
        padding:'32px 0',
        background:`${{NOISE}}, #111111`,
        borderTop:'1px solid rgba(255,255,255,0.08)',
        borderBottom:'1px solid rgba(255,255,255,0.08)'
      }}}}>
        <div style={{{{maxWidth:860,margin:'0 auto',display:'grid',
          gridTemplateColumns:'1fr 1px 1fr 1px 1fr',alignItems:'center',
          textAlign:'center',padding:'0 40px'}}}}>
          {{[['100K+','Active Developers'],null,['1M+','Commands Executed Daily'],null,['99%','Productivity Boost']].map((item,i)=>(
            item===null
              ? <div key={{i}} style={{{{width:1,height:48,background:'rgba(255,255,255,0.08)',margin:'0 auto'}}}} />
              : <div key={{i}}>
                  <div style={{{{fontSize:44,fontWeight:900,color:'{c0}',marginBottom:4,letterSpacing:'-0.03em'}}}}>{{item[0]}}</div>
                  <div style={{{{fontSize:13,color:'rgba(255,255,255,0.5)'}}}}>{{item[1]}}</div>
                </div>
          ))}}
        </div>
      </section>

      {{/* ── Features with noise cards ── */}}
      <section id="features" style={{{{padding:'96px 40px',background:'{c1}'}}}}>
        <div style={{{{maxWidth:1200,margin:'0 auto'}}}}>
          <p style={{{{color:'{c0}',fontSize:12,fontWeight:800,letterSpacing:'0.16em',textTransform:'uppercase',textAlign:'center',marginBottom:14}}}}>FEATURES</p>
          <h2 style={{{{fontSize:42,fontWeight:900,color:'white',textAlign:'center',letterSpacing:'-0.03em',marginBottom:14}}}}>
            Features That <span style={{{{color:'{c0}'}}}}>Drive You Forward</span>
          </h2>
          <p style={{{{textAlign:'center',color:'rgba(255,255,255,0.5)',fontSize:18,marginBottom:64,maxWidth:480,margin:'0 auto 64px'}}}}>
            Everything you need to supercharge your workflow — nothing you don&apos;t.
          </p>
          <div className="features-grid" style={{{{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:20}}}}>
            {{[
              {{i:'⚡',t:'Blazing Fast',d:'Execute commands, search files, and launch apps at unparalleled speed. No more waiting.'}},
              {{i:'🔧',t:'Highly Extensible',d:'Build custom extensions or choose from a vast marketplace to tailor Momentum to your workflow.'}},
              {{i:'✦', t:'Sleek & Minimal',d:'A beautiful dark-themed UI that stays out of your way, letting you focus on what matters.'}},
              {{i:'🤖',t:'AI-Powered Workflows',d:'Automate tasks, generate content, and get intelligent suggestions with built-in AI.'}},
              {{i:'🔌',t:'Deep Integrations',d:'Connect to all your apps and services to control everything from one place.'}},
              {{i:'⌨️',t:'Keyboard-First Design',d:'Navigate and execute commands without ever touching your mouse. Pure efficiency.'}}
            ].map((f,idx)=>(
              <div key={{idx}} className="card-hover" style={{{{
                background:`${{NOISE}}, rgba(255,255,255,0.03)`,
                border:'1px solid rgba(255,255,255,0.08)',
                backdropFilter:'blur(20px)',borderRadius:16,padding:32,
                transition:'all 0.3s',cursor:'default',
                position:'relative',overflow:'hidden'
              }}}}>
                {{/* Ambient corner glow */}}
                <div style={{{{position:'absolute',bottom:-20,right:-20,width:110,height:110,borderRadius:'50%',filter:'blur(42px)',background:'{c0}0e',pointerEvents:'none'}}}} />
                <div style={{{{
                  width:52,height:52,borderRadius:14,display:'flex',alignItems:'center',
                  justifyContent:'center',background:'{c0}1a',border:'1px solid {c0}33',
                  marginBottom:20,fontSize:26
                }}}}>{{f.i}}</div>
                <h3 style={{{{fontSize:17,fontWeight:700,color:'white',marginBottom:10}}}}>{{f.t}}</h3>
                <p style={{{{fontSize:14,color:'rgba(255,255,255,0.5)',lineHeight:1.68}}}}>{{f.d}}</p>
              </div>
            ))}}
          </div>
        </div>
      </section>

      {{/* ── Pricing with noise cards ── */}}
      <section id="pricing" style={{{{padding:'96px 40px',background:'{c1}'}}}}>
        <div style={{{{maxWidth:1100,margin:'0 auto'}}}}>
          <p style={{{{color:'{c0}',fontSize:12,fontWeight:800,letterSpacing:'0.16em',textTransform:'uppercase',textAlign:'center',marginBottom:14}}}}>PRICING</p>
          <h2 style={{{{fontSize:42,fontWeight:900,color:'white',textAlign:'center',letterSpacing:'-0.03em',marginBottom:14}}}}>
            Choose Your <span style={{{{color:'{c0}'}}}}>Momentum Plan</span>
          </h2>
          <p style={{{{textAlign:'center',color:'rgba(255,255,255,0.5)',fontSize:18,marginBottom:60}}}}>Simple pricing. No hidden fees.</p>
          <div className="pricing-grid" style={{{{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:20,alignItems:'start'}}}}>
            {{/* Free */}}
            <div className="pricing-card" style={{{{background:`${{NOISE}}, rgba(255,255,255,0.025)`,border:'1px solid rgba(255,255,255,0.08)',borderRadius:16,padding:36,position:'relative',overflow:'hidden'}}}}>
              <p style={{{{fontSize:12,fontWeight:700,color:'rgba(255,255,255,0.5)',textTransform:'uppercase',letterSpacing:'0.12em',marginBottom:12}}}}>Starter</p>
              <p style={{{{fontSize:56,fontWeight:900,color:'white',marginBottom:4,letterSpacing:'-0.04em'}}}}>Free</p>
              <p style={{{{fontSize:14,color:'rgba(255,255,255,0.5)',marginBottom:32}}}}>For developers getting started.</p>
              {{['Core Commands','Basic Integrations','Community Support','AI Lite (10 req/day)'].map(f=>(
                <div key={{f}} style={{{{display:'flex',alignItems:'center',gap:10,marginBottom:12}}}}>
                  <span style={{{{color:'{c0}',fontWeight:800,fontSize:15}}}}>✓</span>
                  <span style={{{{fontSize:14,color:'rgba(255,255,255,0.65)'}}}}>{{f}}</span>
                </div>
              ))}}
              <a href="#" style={{{{display:'block',textAlign:'center',marginTop:32,padding:'12px 0',borderRadius:10,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.04)',color:'white',fontWeight:600,fontSize:15,textDecoration:'none'}}}}>Get Started Free</a>
            </div>
            {{/* Pro — highlighted */}}
            <div className="pricing-card" style={{{{
              background:`${{NOISE}}, rgba(255,69,0,0.07)`,
              border:'2px solid {c0}',
              boxShadow:'0 0 80px {c0}33, inset 0 0 40px {c0}08',
              backdropFilter:'blur(20px)',borderRadius:16,padding:36,
              position:'relative',overflow:'hidden',marginTop:-10
            }}}}>
              <div style={{{{position:'absolute',top:16,right:16,background:'{c0}',color:'white',fontSize:11,fontWeight:800,padding:'4px 10px',borderRadius:6,textTransform:'uppercase',letterSpacing:'0.08em',boxShadow:'0 0 16px {c0}66'}}}}>Most Popular</div>
              <p style={{{{fontSize:12,fontWeight:700,color:'{c0}',textTransform:'uppercase',letterSpacing:'0.12em',marginBottom:12}}}}>Pro</p>
              <div style={{{{display:'flex',alignItems:'baseline',gap:4,marginBottom:4}}}}>
                <p style={{{{fontSize:56,fontWeight:900,color:'white',letterSpacing:'-0.04em'}}}}>$8</p>
                <span style={{{{fontSize:16,color:'rgba(255,255,255,0.5)'}}}}>/ month</span>
              </div>
              <p style={{{{fontSize:14,color:'rgba(255,255,255,0.5)',marginBottom:32}}}}>For power users who demand the best.</p>
              {{['AI Starter Features','Advanced Extensions','Priority Integrations','Cloud Sync & Backup','Premium Support'].map(f=>(
                <div key={{f}} style={{{{display:'flex',alignItems:'center',gap:10,marginBottom:12}}}}>
                  <span style={{{{color:'{c0}',fontWeight:800,fontSize:15,textShadow:'0 0 8px {c0}'}}}}>✓</span>
                  <span style={{{{fontSize:14,color:'rgba(255,255,255,0.80)'}}}}>{{f}}</span>
                </div>
              ))}}
              <a href="#" style={{{{display:'block',textAlign:'center',marginTop:32,padding:'13px 0',borderRadius:10,background:'{c0}',color:'white',fontWeight:700,fontSize:15,textDecoration:'none',boxShadow:'0 0 32px {c0}55',animation:'glow-pulse 3s infinite'}}}}>Start Pro Trial</a>
            </div>
            {{/* Enterprise */}}
            <div className="pricing-card" style={{{{background:`${{NOISE}}, rgba(255,255,255,0.025)`,border:'1px solid rgba(255,255,255,0.08)',borderRadius:16,padding:36,position:'relative',overflow:'hidden'}}}}>
              <p style={{{{fontSize:12,fontWeight:700,color:'rgba(255,255,255,0.5)',textTransform:'uppercase',letterSpacing:'0.12em',marginBottom:12}}}}>Enterprise</p>
              <p style={{{{fontSize:56,fontWeight:900,color:'white',marginBottom:4,letterSpacing:'-0.04em'}}}}>Custom</p>
              <p style={{{{fontSize:14,color:'rgba(255,255,255,0.5)',marginBottom:32}}}}>Scale across your entire organization.</p>
              {{['All Pro Features','Dedicated Account Manager','Custom Integrations','On-Premise Deployment','SLA & Priority Support'].map(f=>(
                <div key={{f}} style={{{{display:'flex',alignItems:'center',gap:10,marginBottom:12}}}}>
                  <span style={{{{color:'{c0}',fontWeight:800,fontSize:15}}}}>✓</span>
                  <span style={{{{fontSize:14,color:'rgba(255,255,255,0.65)'}}}}>{{f}}</span>
                </div>
              ))}}
              <a href="#" style={{{{display:'block',textAlign:'center',marginTop:32,padding:'12px 0',borderRadius:10,border:'1px solid rgba(255,255,255,0.08)',background:'rgba(255,255,255,0.04)',color:'white',fontWeight:600,fontSize:15,textDecoration:'none'}}}}>Contact Sales</a>
            </div>
          </div>
        </div>
      </section>

      {{/* ── CTA with noise + gradient ── */}}
      <section style={{{{padding:'80px 40px',background:'{c1}'}}}}>
        <div style={{{{
          maxWidth:860,margin:'0 auto',borderRadius:24,padding:'80px 60px',
          textAlign:'center',position:'relative',overflow:'hidden',
          background:`${{NOISE}}, linear-gradient(135deg,{c0}22 0%,{c1} 50%,{c0}15 100%)`,
          border:'1px solid {c0}30'
        }}}}>
          <div style={{{{position:'absolute',top:-80,right:-80,width:320,height:320,borderRadius:'50%',filter:'blur(100px)',background:'{c0}18',pointerEvents:'none'}}}} />
          <div style={{{{position:'absolute',bottom:-80,left:-80,width:280,height:280,borderRadius:'50%',filter:'blur(100px)',background:'{c0}12',pointerEvents:'none'}}}} />
          <div style={{{{position:'relative',zIndex:1}}}}>
            <h2 style={{{{fontSize:42,fontWeight:900,color:'white',letterSpacing:'-0.03em',marginBottom:16}}}}>
              Ready to <span style={{{{color:'{c0}'}}}}>Boost Your Productivity?</span>
            </h2>
            <p style={{{{fontSize:18,color:'rgba(255,255,255,0.55)',maxWidth:460,margin:'0 auto 40px'}}}}>
              Join thousands of developers who are already using Momentum to work faster and smarter.
            </p>
            <a href="#" style={{{{
              display:'inline-block',background:'{c0}',color:'white',
              padding:'16px 44px',borderRadius:14,fontWeight:700,fontSize:17,
              textDecoration:'none',animation:'glow-pulse 3s infinite'
            }}}}>Download Momentum Now →</a>
          </div>
        </div>
      </section>

      {{/* ── Footer ── */}}
      <footer style={{{{borderTop:'1px solid rgba(255,255,255,0.08)',padding:'60px 40px 40px',background:'{c1}'}}}}>
        <div style={{{{maxWidth:1200,margin:'0 auto'}}}}>
          <div className="footer-grid" style={{{{display:'grid',gridTemplateColumns:'2fr 1fr 1fr 1fr',gap:48,marginBottom:48}}}}>
            <div>
              {{/* CHANGED: brand color is {c0} (orange) */}}
              <span style={{{{fontWeight:900,fontSize:20,color:'{c0}',display:'block',marginBottom:14}}}}>Momentum.</span>
              <p style={{{{fontSize:14,color:'rgba(255,255,255,0.38)',lineHeight:1.7,marginBottom:20}}}}>
                The ultimate productivity tool for developers. Fast, extensible, and built for speed.
              </p>
              <div style={{{{display:'flex',gap:8}}}}>
                {{['𝕏','📘','💼','📸'].map((ic,i)=>(
                  <a key={{i}} href="#" className="social-icon">{{ic}}</a>
                ))}}
              </div>
            </div>
            {{[
              {{h:'Product', ls:['Features','Integrations','Pricing','Download','Changelog']}},
              {{h:'Resources',ls:['Documentation','Blog','Community','Support','Status']}},
              {{h:'Company', ls:['About Us','Careers','Press','Contact','Privacy Policy']}}
            ].map(col=>(
              <div key={{col.h}}>
                <span style={{{{fontWeight:700,fontSize:12,color:'white',display:'block',marginBottom:16,textTransform:'uppercase',letterSpacing:'0.1em'}}}}>{{col.h}}</span>
                {{col.ls.map(l=>(
                  <a key={{l}} href="#" className="footer-link">{{l}}</a>
                ))}}
              </div>
            ))}}
          </div>
          <div style={{{{borderTop:'1px solid rgba(255,255,255,0.08)',paddingTop:24,display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:12}}}}>
            <span style={{{{fontSize:13,color:'rgba(255,255,255,0.22)'}}}}>© 2026 Momentum. All rights reserved.</span>
            <div style={{{{display:'flex',gap:24}}}}>
              {{['Privacy Policy','Terms of Service','Cookie Policy'].map(l=>(
                <a key={{l}} href="#" style={{{{fontSize:13,color:'rgba(255,255,255,0.22)',textDecoration:'none'}}}}>{{l}}</a>
              ))}}
            </div>
          </div>
        </div>
      </footer>
    </main>
  )
}}
'''
    return GeneratedPage(
        page_name=page_name, tsx_code=tsx, is_landing=is_landing,
        route_path="/" if is_landing else f"/{page_name.lower().replace(' ','-')}"
    )