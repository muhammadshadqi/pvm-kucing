"""
brand.py — Pricing Toolkit single source of visual truth.

Aesthetic: "Classic Premium" — deep forest green + warm cream, serif display
(Fraunces) for headers, refined sans (Source Sans 3) for body. Earthy, calm,
editorial. Import and call inject_brand() at the top of every page.

Usage:
    from brand import inject_brand, render_brand_header, COLORS
    inject_brand()                       # global CSS + fonts (call once per page)
    render_brand_header("PVM Analyzer",  # logo + wordmark + page title
                        "Sequential Hypothetical Margin Bridge")
"""
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# COLOR TOKENS — the only place colors are defined.
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "green_900": "#163C2C",   # darkest — wordmark, strong headers
    "green_700": "#1F4D3A",   # primary accent — buttons, active, logo
    "green_500": "#2E6B52",   # mid green — secondary accent
    "green_200": "#CFE0D6",   # tint — chips, subtle fills
    "cream_50":  "#FBF8F1",   # main background
    "cream_100": "#F3EDE0",   # cards / sidebar background
    "cream_200": "#E9E0CE",   # borders on cream
    "ink_900":   "#22291F",   # body text (warm near-black)
    "ink_500":   "#5C6356",   # muted text / labels
    "ink_300":   "#8A9183",   # faint sub-text
    "gold_500":  "#B58A3E",   # warm accent — sparingly, for highlights
    "pos":       "#2E6B52",   # gains (green, on-brand)
    "neg":       "#A93B2C",   # losses (terracotta, warmer than pure red)
    "neu":       "#5C6356",
    "warn_bg":   "#FBEFD6",
    "warn_br":   "#B58A3E",
    "ok_bg":     "#DCE9E0",
    "ok_br":     "#2E6B52",
    "info_bg":   "#E4ECE6",
    "info_br":   "#2E6B52",
    "white":     "#FFFFFF",
}

# Business-line palette, harmonized to the earthy theme (used by charts)
BL_COLORS = {
    "Dry":    "#2E6B52",
    "Fresh":  "#6B8E4E",
    "Frozen": "#3E7C8C",
    "PL":     "#9C6B3E",
}


def _css() -> str:
    c = COLORS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {{
    --green-900: {c['green_900']}; --green-700: {c['green_700']};
    --green-500: {c['green_500']}; --green-200: {c['green_200']};
    --cream-50: {c['cream_50']};   --cream-100: {c['cream_100']};
    --cream-200: {c['cream_200']}; --ink-900: {c['ink_900']};
    --ink-500: {c['ink_500']};     --ink-300: {c['ink_300']};
    --gold-500: {c['gold_500']};
}}

/* ---- Base canvas ---- */
.stApp {{ background: {c['cream_50']}; }}
html, body, [class*="css"], .stMarkdown, p, span, div, label,
.stDataFrame, .stTextInput, .stSelectbox, .stNumberInput {{
    font-family: 'Source Sans 3', -apple-system, sans-serif;
    color: {c['ink_900']};
}}
.main > div {{ padding-top: 1.2rem; }}

/* ---- Headings: serif display ---- */
h1, h2, h3, h4, h5, h6 {{
    font-family: 'Fraunces', Georgia, serif !important;
    color: {c['green_900']};
    letter-spacing: -0.01em;
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
    background: {c['cream_100']};
    border-right: 1px solid {c['cream_200']};
}}
section[data-testid="stSidebar"] * {{ color: {c['ink_900']}; }}

/* ---- Section header (the .section-header class used everywhere) ---- */
.section-header {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 22px;
    font-weight: 600;
    color: {c['green_900']};
    margin-top: 28px;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1.5px solid {c['cream_200']};
}}
.section-sub {{ font-size: 13px; color: {c['ink_500']}; margin-bottom: 12px; }}

/* ---- KPI card ---- */
.kpi-card {{
    border: 1px solid {c['cream_200']};
    border-radius: 12px;
    padding: 16px 20px;
    background: {c['white']};
    height: 100%;
    box-shadow: 0 1px 2px rgba(22,60,44,0.04);
}}
.kpi-label {{
    font-family: 'Source Sans 3', sans-serif;
    font-size: 11px; color: {c['ink_500']};
    text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600;
}}
.kpi-value {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 28px; font-weight: 600; color: {c['green_900']}; margin: 4px 0;
}}
.kpi-delta-pos, .delta-pos {{ font-size: 14px; color: {c['pos']}; font-weight: 600; }}
.kpi-delta-neg, .delta-neg {{ font-size: 14px; color: {c['neg']}; font-weight: 600; }}
.kpi-delta-neu, .delta-neu {{ font-size: 14px; color: {c['neu']}; font-weight: 600; }}
.kpi-sub {{ font-size: 11px; color: {c['ink_300']}; margin-top: 4px; }}

/* ---- Banners ---- */
.banner-warn {{
    background: {c['warn_bg']}; border-left: 4px solid {c['warn_br']};
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
}}
.banner-ok {{
    background: {c['ok_bg']}; border-left: 4px solid {c['ok_br']};
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
}}
.banner-info {{
    background: {c['info_bg']}; border-left: 4px solid {c['info_br']};
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
}}
.banner-title {{ font-weight: 700; margin-bottom: 4px; }}

/* ---- Info box (Query Builder) ---- */
.info-box {{
    background: {c['info_bg']}; border-left: 4px solid {c['info_br']};
    padding: 12px 16px; border-radius: 8px; margin: 8px 0 16px 0;
    font-size: 13px; color: {c['ink_900']};
}}

/* ---- Mover cards ---- */
.mover-card {{
    border: 1px solid {c['cream_200']}; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 6px; background: {c['white']}; font-size: 12px;
}}
.mover-rank {{ font-weight: 700; color: {c['ink_500']}; }}
.mover-name {{ font-weight: 600; color: {c['green_900']}; }}
.mover-gain {{ color: {c['pos']}; font-weight: 600; }}
.mover-loss {{ color: {c['neg']}; font-weight: 600; }}
.mover-meta {{ color: {c['ink_500']}; font-size: 11px; }}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button {{
    background: {c['green_700']}; color: {c['white']};
    border: none; border-radius: 8px; font-weight: 600;
    font-family: 'Source Sans 3', sans-serif;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: {c['green_900']}; color: {c['white']};
}}

/* ---- Tabs accent ---- */
.stTabs [aria-selected="true"] {{ color: {c['green_700']}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {c['green_700']}; }}

/* ---- Brand header bar ---- */
.brand-bar {{
    display: flex; align-items: center; gap: 14px;
    padding: 4px 0 14px 0; margin-bottom: 8px;
    border-bottom: 1px solid {c['cream_200']};
}}
.brand-wordmark {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 19px; font-weight: 600; color: {c['green_900']};
    line-height: 1.1; letter-spacing: -0.01em;
}}
.brand-wordmark .sub {{
    display: block; font-family: 'Source Sans 3', sans-serif;
    font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
    text-transform: uppercase; color: {c['gold_500']}; margin-top: 2px;
}}
.page-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 32px; font-weight: 600; color: {c['green_900']};
    margin: 10px 0 2px 0; letter-spacing: -0.02em;
}}
.page-subtitle {{
    font-family: 'Source Sans 3', sans-serif;
    font-size: 15px; color: {c['ink_500']}; margin-bottom: 6px;
}}

/* ---- Home: hero + tool cards ---- */
.hero-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 40px; font-weight: 600; color: {c['green_900']};
    margin-bottom: 4px; letter-spacing: -0.02em;
}}
.hero-sub {{ font-size: 17px; color: {c['ink_500']}; margin-bottom: 28px;
            font-family: 'Source Sans 3', sans-serif; }}
.tool-card {{
    border: 1px solid {c['cream_200']}; border-radius: 14px;
    padding: 24px; background: {c['white']}; margin-bottom: 16px; height: 100%;
    box-shadow: 0 1px 3px rgba(22,60,44,0.05);
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}}
.tool-card:hover {{ box-shadow: 0 6px 18px rgba(22,60,44,0.10); transform: translateY(-2px); }}
.tool-title {{ font-family: 'Fraunces', Georgia, serif; font-size: 22px;
              font-weight: 600; color: {c['green_900']}; margin-bottom: 8px; }}
.tool-sub {{ font-size: 14px; color: {c['ink_500']}; margin-bottom: 16px;
            font-family: 'Source Sans 3', sans-serif; }}
.tool-tag {{ font-size: 11px; color: {c['green_700']}; background: {c['green_200']};
            padding: 4px 10px; border-radius: 12px; display: inline-block;
            font-weight: 700; letter-spacing: 0.5px; }}
</style>
"""


def logo_svg(size: int = 38) -> str:
    """
    Brand monogram: a deep-green roundel with an 'A' apex and a small orbiting
    mark — evokes orbit/star + an upward price line. Inline SVG, no asset.
    """
    g900 = COLORS["green_900"]; g700 = COLORS["green_700"]; gold = COLORS["gold_500"]
    cream = COLORS["cream_50"]
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Pricing Toolkit logo">
  <circle cx="24" cy="24" r="22" fill="{g900}"/>
  <circle cx="24" cy="24" r="22" fill="none" stroke="{gold}" stroke-width="1.2" opacity="0.5"/>
  <!-- upward chart line -->
  <path d="M13 31 L21 24 L27 28 L36 16" stroke="{cream}" stroke-width="2.4"
        stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <!-- apex node (the 'star') -->
  <circle cx="36" cy="16" r="3.4" fill="{gold}"/>
  <circle cx="36" cy="16" r="3.4" fill="none" stroke="{cream}" stroke-width="1"/>
  <!-- baseline ticks -->
  <path d="M13 35 L36 35" stroke="{g700}" stroke-width="1.4" opacity="0.6"/>
</svg>
"""


def inject_brand():
    """Inject global fonts + CSS. Call once at the top of every page."""
    st.markdown(_css(), unsafe_allow_html=True)


def render_brand_header(page_title: str, page_subtitle: str = ""):
    """Render the logo + wordmark bar, then the page title block."""
    sub_html = f'<div class="page-subtitle">{page_subtitle}</div>' if page_subtitle else ""
    st.markdown(
        f"""
        <div class="brand-bar">
            {logo_svg(38)}
            <div class="brand-wordmark">Pricing Toolkit
                <span class="sub">Pricing Strategy</span>
            </div>
        </div>
        <div class="page-title">{page_title}</div>
        {sub_html}
        """,
        unsafe_allow_html=True,
    )
