"""CSS custom inyectado en la web. Paleta Material Design 3 del mockup Google Stitch.

Mantenemos los nombres PRIMARY/ACCENT/etc por compatibilidad con el código existente,
pero los hex apuntan ahora a los tokens del mockup.
"""
from __future__ import annotations
import base64
import streamlit as st


# === Paleta del mockup Stitch (Material 3) =====================================
PRIMARY = "#4cd7f6"          # Cyan brillante (era Mates)
ACCENT = "#d0bcff"           # Violeta pastel (era Intuición)
TERTIARY = "#4edea3"         # Verde esmeralda menta
BG = "#0c1324"               # Background principal
SURFACE = "#0c1324"
SURFACE_CONTAINER_LOWEST = "#070d1f"
SURFACE_CONTAINER_LOW = "#151b2d"
SURFACE_CONTAINER = "#191f31"
SURFACE_CONTAINER_HIGH = "#23293c"
SURFACE_CONTAINER_HIGHEST = "#2e3447"
BG_CARD = "rgba(21, 27, 45, 0.7)"
BG_CARD_HOVER = "rgba(35, 41, 60, 0.8)"
TEXT = "#dce1fb"             # On-surface (texto principal, ligeramente lavanda)
TEXT_DIM = "#bcc9cd"         # On-surface-variant
BORDER = "rgba(61, 73, 76, 0.5)"  # Outline-variant
DANGER = "#ffb4ab"           # Error
GOOD = "#4edea3"             # Verde tertiary
SECONDARY_CONTAINER = "#571bc1"  # Contenedor violeta oscuro
ERROR_CONTAINER = "#93000a"
TERTIARY_CONTAINER = "#1bbd85"


# Patrón táctico SVG ultra-sutil (mantenido del diseño anterior, ahora más tenue)
SVG_PITCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" fill="none" stroke="rgba(76, 215, 246, 0.012)" stroke-width="1.2">
  <rect x="30" y="30" width="940" height="540" rx="8" />
  <line x1="500" y1="30" x2="500" y2="570" />
  <circle cx="500" cy="300" r="90" />
  <rect x="30" y="180" width="140" height="240" />
  <rect x="830" y="180" width="140" height="240" />
  <rect x="30" y="240" width="55" height="120" />
  <rect x="915" y="240" width="55" height="120" />
</svg>"""

b64_svg = base64.b64encode(SVG_PITCH.encode("utf-8")).decode("utf-8")


CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@700;800&display=swap');

/* ========================================================================
   GLOBAL
   ======================================================================== */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes shimmer {{
    0%, 100% {{ box-shadow: 0 0 12px rgba(76,215,246,0.10); }}
    50% {{ box-shadow: 0 0 22px rgba(76,215,246,0.22); }}
}}

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: {TEXT};
}}

h1, h2, h3, h4, h5, .team-name, .big-stat-value, [data-testid="stMetricValue"] {{
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
}}

/* === Fondo de pizarra táctica === */
.stApp {{
    background-color: {BG};
    background-image:
        radial-gradient(circle at 50% 30%, rgba(15, 23, 42, 0.25) 0%, {BG} 85%),
        url("data:image/svg+xml;base64,{b64_svg}");
    background-size: cover, 1150px 690px;
    background-position: center, center 60px;
    background-repeat: no-repeat, no-repeat;
    background-attachment: fixed, fixed;
    color: {TEXT};
}}

[data-testid="stHeader"] {{ background-color: transparent !important; }}
[data-testid="stSidebar"] {{
    background-color: rgba(15, 23, 42, 0.92);
    border-right: 1px solid {BORDER};
    backdrop-filter: blur(20px);
}}

h1 {{ font-size: 2.8rem !important; font-weight: 800 !important; letter-spacing: -0.04em !important; color: {TEXT} !important; }}
h2 {{ font-size: 2rem !important; font-weight: 700 !important; color: {TEXT} !important; }}
h3 {{ font-size: 1.5rem !important; font-weight: 600 !important; color: {TEXT} !important; }}
h4 {{ font-size: 1.1rem !important; font-weight: 600 !important; color: {TEXT} !important; }}

/* ========================================================================
   st.metric — Bento card estilo Material 3
   ======================================================================== */
[data-testid="stMetric"] {{
    background: rgba(21, 27, 45, 0.7) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 22px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.30) !important;
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both !important;
}}
[data-testid="stMetric"]:hover {{
    border-color: rgba(76, 215, 246, 0.45) !important;
    box-shadow: 0 0 25px rgba(76,215,246,0.16), 0 8px 30px rgba(0,0,0,0.4) !important;
    transform: translateY(-3px) !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_DIM} !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}
[data-testid="stMetricValue"] {{
    color: {PRIMARY} !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    text-shadow: 0 0 18px rgba(76,215,246,0.30) !important;
}}

/* ========================================================================
   st.tabs — píldoras integradas
   ======================================================================== */
[data-testid="stTabs"] {{
    background-color: rgba(21, 27, 45, 0.5) !important;
    border-radius: 16px !important;
    padding: 8px !important;
    border: 1px solid {BORDER} !important;
    margin-bottom: 24px !important;
    backdrop-filter: blur(12px) !important;
}}
[data-testid="stTabs"] button {{
    background-color: transparent !important;
    color: {TEXT_DIM} !important;
    border: none !important;
    padding: 9px 18px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 9999px !important;
    transition: all 0.2s ease !important;
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.005em !important;
}}
[data-testid="stTabs"] button:hover {{
    color: {PRIMARY} !important;
    background-color: rgba(76, 215, 246, 0.08) !important;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {SURFACE} !important;
    background: linear-gradient(135deg, {PRIMARY} 0%, #22d3ee 100%) !important;
    box-shadow: 0 4px 15px rgba(76,215,246,0.30) !important;
    border: none !important;
    font-weight: 700 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ display: none !important; }}
[data-testid="stTabs"] [role="tablist"] {{ border-bottom: none !important; }}

/* ========================================================================
   Navegación principal (st.segmented_control) — mismas píldoras que las tabs.
   Sustituye a st.tabs para renderizar SOLO la pestaña activa (lazy-load).
   ======================================================================== */
[data-testid="stButtonGroup"] {{
    background-color: rgba(21, 27, 45, 0.5) !important;
    border-radius: 16px !important;
    padding: 8px !important;
    border: 1px solid {BORDER} !important;
    margin: 8px 0 24px !important;
    backdrop-filter: blur(12px) !important;
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 4px !important;
    justify-content: center !important;
}}
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"] {{
    background-color: transparent !important;
    color: {TEXT_DIM} !important;
    border: none !important;
    padding: 9px 18px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 9999px !important;
    transition: all 0.2s ease !important;
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.005em !important;
    min-height: 0 !important;
}}
[data-testid="stBaseButton-segmented_control"]:hover {{
    color: {PRIMARY} !important;
    background-color: rgba(76, 215, 246, 0.08) !important;
}}
[data-testid="stBaseButton-segmented_controlActive"] {{
    color: {SURFACE} !important;
    background: linear-gradient(135deg, {PRIMARY} 0%, #22d3ee 100%) !important;
    box-shadow: 0 4px 15px rgba(76,215,246,0.30) !important;
    font-weight: 700 !important;
}}

/* ========================================================================
   Tabla de probabilidades premium (.wc-ptable) — filas-tarjeta con barras.
   Reutilizable: comparativa de grupo, rankings, etc.
   ======================================================================== */
.wc-ptable {{ width:100%; border-collapse:separate; border-spacing:0 7px; font-size:0.86rem; }}
.wc-ptable th {{
    text-align:right; color:{TEXT_DIM}; font-weight:700; font-size:0.66rem;
    text-transform:uppercase; letter-spacing:0.05em; padding:0 12px 2px;
    white-space:nowrap;
}}
.wc-ptable th.lft {{ text-align:left; }}
.wc-ptable td {{ padding:9px 12px; background:{BG_CARD}; vertical-align:middle; }}
.wc-ptable tr td:first-child {{ border-radius:12px 0 0 12px; }}
.wc-ptable tr td:last-child {{ border-radius:0 12px 12px 0; }}
.wc-ptable tr.sel td {{ background:rgba(76,215,246,0.13); box-shadow: inset 3px 0 0 {PRIMARY}; }}
.wc-ptable .pteam {{ display:flex; align-items:center; gap:9px; font-weight:600; white-space:nowrap; }}
.wc-ptable .pelo {{ text-align:right; font-weight:700; color:{TEXT_DIM}; font-variant-numeric:tabular-nums; }}
.wc-pcell {{ position:relative; height:22px; min-width:64px; border-radius:6px;
    background:rgba(255,255,255,0.05); overflow:hidden; }}
.wc-pcell .fill {{ position:absolute; top:0; left:0; bottom:0; border-radius:6px;
    background:linear-gradient(90deg, rgba(76,215,246,0.45), rgba(76,215,246,0.85));
    transition:width .5s cubic-bezier(.22,1,.36,1); }}
.wc-pcell.champ .fill {{ background:linear-gradient(90deg, rgba(208,188,255,0.45), rgba(208,188,255,0.92)); }}
.wc-pcell .v {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:flex-end;
    padding-right:7px; font-size:0.76rem; font-weight:800; font-variant-numeric:tabular-nums;
    text-shadow:0 1px 2px rgba(0,0,0,.5); }}
.wc-pcell.dim .v {{ color:{TEXT_DIM}; }}

/* ========================================================================
   Tablas
   ======================================================================== */
[data-testid="stTable"], [data-testid="stDataFrame"] {{
    background-color: rgba(21, 27, 45, 0.55) !important;
    border-radius: 16px !important;
    border: 1px solid {BORDER} !important;
    backdrop-filter: blur(12px);
}}
tbody tr {{ transition: background-color 0.2s ease !important; }}
tbody tr:hover {{ background-color: rgba(76, 215, 246, 0.04) !important; }}

/* ========================================================================
   Botones (gradiente Cyan→Violet)
   ======================================================================== */
.stButton button {{
    background: linear-gradient(135deg, {ACCENT} 0%, {PRIMARY} 100%) !important;
    color: {SURFACE} !important;
    border: none !important;
    border-radius: 9999px !important;
    padding: 10px 26px !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.88rem !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 15px rgba(76,215,246,0.20) !important;
    text-transform: none !important;
    letter-spacing: -0.005em !important;
    width: 100% !important;
}}
.stButton button:hover {{
    background: linear-gradient(135deg, #e2d2ff 0%, #6ee0ff 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(76,215,246,0.40) !important;
    color: {SURFACE} !important;
}}
.stButton button:active {{
    transform: translateY(0) !important;
    box-shadow: 0 2px 10px rgba(76,215,246,0.20) !important;
}}

/* Botón secundary (toggle/secondary actions) */
.stButton button[kind="secondary"] {{
    background: transparent !important;
    border: 1px solid {ACCENT} !important;
    color: {ACCENT} !important;
    box-shadow: none !important;
}}
.stButton button[kind="secondary"]:hover {{
    background: rgba(208, 188, 255, 0.08) !important;
    color: {ACCENT} !important;
}}

/* ========================================================================
   Team cards (Glassmorphism)
   ======================================================================== */
.team-card {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 22px !important;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
    margin-bottom: 16px !important;
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.30) !important;
    backdrop-filter: blur(12px);
}}
.team-card:hover {{
    border-color: rgba(76,215,246,0.45) !important;
    box-shadow: 0 0 25px rgba(76,215,246,0.15) !important;
    transform: translateY(-3px) !important;
}}
.team-card-header {{
    display: flex; align-items: center; gap: 16px;
    margin-bottom: 16px;
}}
.team-flag {{
    width: 64px; height: 48px;
    object-fit: cover; border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.40);
    border: 1px solid rgba(255, 255, 255, 0.08);
}}
.team-name {{
    font-size: 1.4rem; font-weight: 700;
    color: {TEXT}; margin: 0; font-family: 'Outfit', sans-serif;
}}
.team-meta {{
    font-size: 0.85rem; color: {TEXT_DIM}; margin: 0;
}}

/* ========================================================================
   Barras de probabilidad
   ======================================================================== */
.prob-row {{
    display: flex; align-items: center; justify-content: space-between;
    margin: 8px 0; font-size: 0.85rem;
}}
.prob-label {{ color: {TEXT_DIM}; min-width: 80px; font-weight: 500; }}
.prob-bar-container {{
    flex: 1; height: 8px;
    background-color: {SURFACE_CONTAINER_HIGHEST} !important;
    border-radius: 9999px;
    margin: 0 12px; overflow: hidden;
    border: 1px solid rgba(255,255,255,0.03);
}}
.prob-bar {{
    height: 100%;
    background: linear-gradient(90deg, {PRIMARY} 0%, {ACCENT} 100%) !important;
    border-radius: 9999px;
}}
.prob-value {{ color: {TEXT}; font-weight: 700; min-width: 50px; text-align: right; }}

/* === Form streak (W/D/L pills) === */
.form-streak {{ display: flex; gap: 6px; margin: 8px 0; }}
.form-pill {{
    width: 24px; height: 24px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.75rem; color: {SURFACE};
    box-shadow: 0 2px 4px rgba(0,0,0,0.20);
}}
.form-W {{ background-color: {TERTIARY}; color: {SURFACE}; }}
.form-D {{ background-color: {TEXT_DIM}; color: {SURFACE}; }}
.form-L {{ background-color: {DANGER}; color: {SURFACE}; }}

/* === Separadores === */
.section-divider {{
    border-top: 1px solid {BORDER};
    margin: 28px 0;
}}

/* === Limpiar Streamlit menu === */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

/* === Slider thumb cyan brillante === */
[data-testid="stSlider"] [role="slider"] {{
    background-color: {PRIMARY} !important;
    box-shadow: 0 0 10px rgba(76,215,246,0.7) !important;
}}

/* === Selectbox e inputs === */
[data-baseweb="select"] > div {{
    background-color: {SURFACE_CONTAINER_HIGH} !important;
    border-color: {BORDER} !important;
    border-radius: 12px !important;
    color: {TEXT} !important;
    transition: border-color 0.2s !important;
}}
[data-baseweb="select"] > div:hover {{ border-color: {PRIMARY} !important; }}

/* === Expander === */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {{
    background-color: {SURFACE_CONTAINER_LOW} !important;
    border-radius: 12px !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
}}

/* === Match rows === */
.match-row {{
    display: flex !important; align-items: center !important;
    justify-content: space-between !important;
    padding: 14px 18px !important;
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    margin: 6px 0 !important;
    font-size: 0.88rem !important;
    transition: all 0.3s ease !important;
    backdrop-filter: blur(12px);
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both !important;
}}
.match-row:hover {{
    background: {BG_CARD_HOVER} !important;
    border-color: rgba(76,215,246,0.30) !important;
    transform: translateX(4px) !important;
}}
.match-date {{ color: {TEXT_DIM}; min-width: 84px; font-weight: 500; }}
.match-teams {{ flex: 1; color: {TEXT}; font-weight: 600; }}
.match-score {{
    font-weight: 800; color: {PRIMARY};
    text-shadow: 0 0 10px rgba(76,215,246,0.30);
    font-family: 'Outfit', sans-serif;
}}

/* === Big stat cards === */
.big-stat {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 20px 14px !important;
    text-align: center !important;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
    backdrop-filter: blur(12px);
}}
.big-stat:hover {{
    border-color: rgba(76,215,246,0.45) !important;
    box-shadow: 0 0 25px rgba(76,215,246,0.15) !important;
    transform: translateY(-3px) scale(1.01) !important;
}}
.big-stat-value {{
    font-size: 2.3rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    line-height: 1.1 !important;
    text-shadow: 0 0 18px rgba(76,215,246,0.25) !important;
    font-family: 'Outfit', sans-serif !important;
}}
.big-stat-label {{
    font-size: 0.7rem !important;
    color: {TEXT_DIM} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    margin-top: 8px !important;
    font-weight: 600 !important;
}}

/* ========================================================================
   BENTO CARDS — el patrón principal del mockup
   ======================================================================== */
.card-mates {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-top: 2px solid {PRIMARY} !important;
    border-radius: 16px !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.30) !important;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
    backdrop-filter: blur(12px);
}}
.card-mates:hover {{
    border-color: rgba(76,215,246,0.45) !important;
    border-top-color: {PRIMARY} !important;
    box-shadow: 0 0 25px rgba(76,215,246,0.15) !important;
}}

.card-intuicion {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-top: 2px solid {ACCENT} !important;
    border-radius: 16px !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.30) !important;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
    backdrop-filter: blur(12px);
}}
.card-intuicion:hover {{
    border-color: rgba(208,188,255,0.45) !important;
    box-shadow: 0 0 25px rgba(208,188,255,0.15) !important;
}}

.card-tertiary {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-top: 2px solid {TERTIARY} !important;
    border-radius: 16px !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.30) !important;
    backdrop-filter: blur(12px);
}}

/* Badges Material 3 style */
.badge-mates, .badge-intuicion, .badge-tertiary {{
    display: inline-flex !important;
    align-items: center; gap: 6px;
    border-radius: 9999px !important;
    padding: 4px 12px !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 12px !important;
    font-family: 'Outfit', sans-serif !important;
}}
.badge-mates {{
    background: rgba(76,215,246,0.15) !important;
    color: {PRIMARY} !important;
    border: 1px solid rgba(76,215,246,0.30) !important;
}}
.badge-intuicion {{
    background: rgba(208,188,255,0.15) !important;
    color: {ACCENT} !important;
    border: 1px solid rgba(208,188,255,0.30) !important;
}}
.badge-tertiary {{
    background: rgba(78,222,163,0.15) !important;
    color: {TERTIARY} !important;
    border: 1px solid rgba(78,222,163,0.30) !important;
}}

/* ========================================================================
   CAMPO DE FÚTBOL (once probable)
   ======================================================================== */
.pitch {{
    position: relative;
    width: 100%; aspect-ratio: 5 / 7; max-width: 460px;
    margin: 16px auto;
    background:
        radial-gradient(ellipse at center, rgba(76,215,246,0.06) 0%, rgba(76,215,246,0) 60%),
        linear-gradient(180deg, #053827 0%, #0a4a35 50%, #053827 100%);
    border-radius: 16px;
    border: 2px solid rgba(255,255,255,0.18);
    box-shadow: 0 12px 40px rgba(0,0,0,0.45), inset 0 0 30px rgba(0,0,0,0.35);
    overflow: hidden;
    background-image:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.025) 0px,
            rgba(255,255,255,0.025) 32px,
            transparent 32px, transparent 64px);
}}
.pitch-line.pitch-midline {{
    position: absolute; left: 0; right: 0; top: 50%;
    height: 2px; background: rgba(255,255,255,0.35);
}}
.pitch-circle {{
    position: absolute; left: 50%; top: 50%;
    width: 22%; aspect-ratio: 1;
    transform: translate(-50%, -50%);
    border: 2px solid rgba(255,255,255,0.35);
    border-radius: 50%;
}}
.pitch-box {{
    position: absolute; left: 25%; width: 50%; height: 14%;
    border: 2px solid rgba(255,255,255,0.35);
}}
.pitch-box-top {{ top: 0; border-top: none; border-radius: 0 0 6px 6px; }}
.pitch-box-bottom {{ bottom: 0; border-bottom: none; border-radius: 6px 6px 0 0; }}
.pitch-player {{
    position: absolute;
    transform: translate(-50%, -50%);
    display: flex; flex-direction: column; align-items: center;
    cursor: default;
    transition: transform 0.18s ease;
    width: 64px;
}}
.pitch-player:hover {{ transform: translate(-50%, -50%) scale(1.10); z-index: 5; }}
.jersey {{
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.85rem; color: #fff;
    border: 2px solid rgba(255,255,255,0.55);
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    font-family: 'Outfit', sans-serif;
}}
.jersey-hot  {{ background: linear-gradient(135deg, #f97316 0%, #ef4444 100%); }}
.jersey-good {{ background: linear-gradient(135deg, {PRIMARY} 0%, {TERTIARY} 100%); }}
.jersey-mid  {{ background: linear-gradient(135deg, #64748b 0%, #94a3b8 100%); }}
.jersey-cold {{ background: linear-gradient(135deg, #475569 0%, #334155 100%); }}
.jersey-empty {{
    background: rgba(255,255,255,0.06);
    border-style: dashed;
    color: rgba(255,255,255,0.4);
}}
.player-label {{
    margin-top: 3px;
    font-size: 0.65rem; font-weight: 700;
    color: #fff; text-shadow: 0 1px 3px rgba(0,0,0,0.85);
    text-align: center;
    max-width: 70px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.pitch-player-empty .player-label {{ display: none; }}

/* ========================================================================
   HEADER KPI BAR (banda persistente)
   ======================================================================== */
.headerkpi-bar {{
    display: flex; gap: 10px; flex-wrap: wrap;
    margin: 6px 0 20px 0;
}}
.headerkpi-pill {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 9999px;
    padding: 8px 18px;
    font-size: 0.85rem; font-weight: 600;
    color: {TEXT};
    backdrop-filter: blur(12px);
    display: inline-flex; align-items: center; gap: 8px;
    transition: all 0.2s ease;
}}
.headerkpi-pill:hover {{
    border-color: rgba(76,215,246,0.40);
    transform: translateY(-1px);
}}
.headerkpi-pill .lbl {{
    color: {TEXT_DIM};
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
    font-weight: 600;
}}
.headerkpi-pill .val {{
    font-weight: 800; color: {PRIMARY}; font-size: 1.05rem;
    font-family: 'Outfit', sans-serif;
}}
.headerkpi-pill .val-accent {{ color: {ACCENT}; }}
.headerkpi-pill .val-good {{ color: {TERTIARY}; }}
.headerkpi-pill .val-danger {{ color: {DANGER}; }}

/* ========================================================================
   NEWSFEED — Material 3 con border-left coloreado
   ======================================================================== */
.news-banner {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 22px;
    margin-bottom: 20px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}}
.news-banner-title {{
    font-size: 0.72rem; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700;
    margin-bottom: 12px;
    font-family: 'Outfit', sans-serif;
}}
.news-item {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; margin: 6px 0;
    background: rgba(15, 23, 42, 0.55);
    border-radius: 10px;
    border-left: 4px solid {TEXT_DIM};
    font-size: 0.88rem;
    transition: all 0.2s ease;
}}
.news-item:hover {{
    background: rgba(35, 41, 60, 0.7);
    transform: translateX(2px);
}}
.news-item.news-neg {{ border-left-color: {DANGER}; }}
.news-item.news-pos {{ border-left-color: {TERTIARY}; }}
.news-item .team {{ font-weight: 700; color: {TEXT}; min-width: 130px; font-family: 'Outfit', sans-serif; }}
.news-item .type-tag {{
    font-size: 0.7rem; font-weight: 700; padding: 3px 10px; border-radius: 9999px;
    background: {SURFACE_CONTAINER_HIGH}; color: {TEXT_DIM};
    letter-spacing: 0.04em;
}}
.news-item .text {{ flex: 1; color: {TEXT}; }}
.news-item .delta {{
    font-weight: 800; font-family: 'Outfit', sans-serif;
    padding: 3px 10px; border-radius: 8px;
    font-size: 0.9rem;
}}
.news-item .delta-pos {{
    color: {TERTIARY}; background: rgba(78,222,163,0.12);
    border: 1px solid rgba(78,222,163,0.25);
}}
.news-item .delta-neg {{
    color: {DANGER}; background: rgba(255,180,171,0.10);
    border: 1px solid rgba(255,180,171,0.25);
}}

/* ========================================================================
   Inputs y forms más Material 3
   ======================================================================== */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {{
    background-color: {SURFACE_CONTAINER_HIGH} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    color: {TEXT} !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(76,215,246,0.18) !important;
    outline: none !important;
}}

/* Radio horizontales como pills */
[data-testid="stRadio"] [role="radiogroup"] label {{
    background-color: rgba(21, 27, 45, 0.55);
    border: 1px solid {BORDER};
    border-radius: 9999px;
    padding: 6px 14px;
    margin-right: 6px;
    transition: all 0.2s;
}}
[data-testid="stRadio"] [role="radiogroup"] label:hover {{
    border-color: {PRIMARY};
    background-color: rgba(76,215,246,0.06);
}}

/* Captions más sutiles */
[data-testid="stCaptionContainer"], .stCaption {{
    color: {TEXT_DIM} !important;
    font-size: 0.85rem !important;
}}

/* === Toggle (st.toggle) === */
[data-testid="stToggle"] [role="switch"] {{
    background-color: {SURFACE_CONTAINER_HIGH} !important;
}}
[data-testid="stToggle"] [role="switch"][aria-checked="true"] {{
    background-color: {PRIMARY} !important;
}}

/* === Mejorar st.info / st.warning / st.success / st.error === */
[data-testid="stAlert"] {{
    border-radius: 12px !important;
    border: 1px solid {BORDER} !important;
    backdrop-filter: blur(12px);
}}

/* ========================================================================
   ⚽ CAPA ESTADIO — atmósfera de Mundial
   ======================================================================== */

/* Focos del estadio: dos haces de luz cruzados arriba */
.stApp::before {{
    content: "";
    position: fixed; inset: 0;
    pointer-events: none;
    z-index: 0;
    background:
        conic-gradient(from 115deg at 12% -8%, transparent 0deg, rgba(76,215,246,0.07) 8deg, transparent 22deg),
        conic-gradient(from 245deg at 88% -8%, transparent 0deg, rgba(208,188,255,0.06) 8deg, transparent 22deg),
        radial-gradient(ellipse 90% 35% at 50% -10%, rgba(124, 224, 255, 0.07), transparent 70%);
    animation: floodSweep 14s ease-in-out infinite alternate;
}}
@keyframes floodSweep {{
    0%   {{ opacity: 0.65; }}
    50%  {{ opacity: 1.0; }}
    100% {{ opacity: 0.75; }}
}}

@keyframes ballBounce {{
    0%, 100% {{ transform: translateY(0) rotate(0deg); }}
    35%      {{ transform: translateY(-9px) rotate(12deg); }}
    65%      {{ transform: translateY(-3px) rotate(-6deg); }}
}}
@keyframes titleShine {{
    0%   {{ background-position: 0% 50%; }}
    100% {{ background-position: 200% 50%; }}
}}
@keyframes tickerScroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
@keyframes goalFlash {{
    0%, 100% {{ box-shadow: 0 0 0 rgba(78,222,163,0); }}
    50%      {{ box-shadow: 0 0 18px rgba(78,222,163,0.45); }}
}}
@keyframes livePulse {{
    0%, 100% {{ opacity: 1; }}
    50%      {{ opacity: 0.35; }}
}}

/* --- HERO header --- */
.wc-hero {{
    position: relative;
    margin: -8px 0 6px 0;
}}
.wc-hero .ball {{
    display: inline-block;
    animation: ballBounce 2.6s ease-in-out infinite;
    transform-origin: 50% 90%;
}}
.wc-hero h1.wc-title {{
    margin: 0 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    background: linear-gradient(90deg, {PRIMARY} 0%, #ffe08a 30%, {ACCENT} 55%, {PRIMARY} 80%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: titleShine 7s linear infinite;
}}
.wc-hero .hosts {{
    font-size: 1.2rem; letter-spacing: 0.18em; vertical-align: middle;
}}
.wc-hero .sub {{
    color: {TEXT_DIM}; margin: 4px 0 0 0; font-size: 0.92rem;
}}

/* --- Ticker LED tipo videomarcador --- */
.wc-ticker {{
    position: relative;
    overflow: hidden;
    background: linear-gradient(180deg, #050a18 0%, #0a1226 100%);
    border: 1px solid rgba(76,215,246,0.22);
    border-radius: 10px;
    margin: 12px 0 18px 0;
    box-shadow: inset 0 0 22px rgba(0,0,0,0.65), 0 0 14px rgba(76,215,246,0.08);
}}
.wc-ticker::before, .wc-ticker::after {{
    content: ""; position: absolute; top: 0; bottom: 0; width: 60px; z-index: 2;
    pointer-events: none;
}}
.wc-ticker::before {{ left: 0;  background: linear-gradient(90deg, #050a18, transparent); }}
.wc-ticker::after  {{ right: 0; background: linear-gradient(-90deg, #050a18, transparent); }}
.wc-ticker-track {{
    display: inline-flex; white-space: nowrap;
    animation: tickerScroll 45s linear infinite;
    padding: 8px 0;
}}
.wc-ticker:hover .wc-ticker-track {{ animation-play-state: paused; }}
.wc-tick {{
    display: inline-flex; align-items: center; gap: 7px;
    padding: 0 26px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; font-weight: 700;
    color: {TEXT};
    border-right: 1px solid rgba(76,215,246,0.14);
}}
.wc-tick img {{ width: 20px; height: 14px; border-radius: 2px; }}
.wc-tick .score {{ color: {PRIMARY}; text-shadow: 0 0 8px rgba(76,215,246,0.55); }}
.wc-tick .ok    {{ color: {TERTIARY}; }}
.wc-tick .ko    {{ color: {DANGER}; }}
.wc-tick .when  {{ color: {TEXT_DIM}; font-weight: 700; font-size: 0.72rem; }}
.wc-tick .exp   {{ color: {ACCENT}; }}

/* --- Panel PRÓXIMO PARTIDO --- */
.next-match {{
    position: relative;
    background:
        radial-gradient(ellipse 70% 120% at 50% -30%, rgba(76,215,246,0.10), transparent 60%),
        linear-gradient(135deg, rgba(13, 20, 38, 0.92) 0%, rgba(10, 26, 34, 0.92) 100%);
    border: 1px solid rgba(76,215,246,0.25);
    border-radius: 18px;
    padding: 18px 26px 14px 26px;
    margin-bottom: 18px;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0,0,0,0.45);
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
/* césped: franja inferior con rayas de corte */
.next-match::after {{
    content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 7px;
    background: repeating-linear-gradient(90deg,
        #0c5c3d 0 46px, #0a4a31 46px 92px);
    box-shadow: 0 -1px 8px rgba(12, 92, 61, 0.55);
}}
.next-match .nm-label {{
    display: inline-flex; align-items: center; gap: 8px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.68rem; font-weight: 800; letter-spacing: 0.22em;
    color: {PRIMARY}; text-transform: uppercase;
}}
.next-match .nm-label .dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: {TERTIARY};
    box-shadow: 0 0 8px {TERTIARY};
    animation: livePulse 1.6s ease-in-out infinite;
}}
.next-match .nm-grid {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 18px; margin-top: 8px;
}}
.next-match .nm-team {{
    flex: 1.5; display: flex; align-items: center; gap: 13px;
    font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.35rem;
}}
.next-match .nm-team.right {{ justify-content: flex-end; text-align: right; }}
.next-match .nm-team img {{
    width: 52px; height: 37px; border-radius: 6px;
    box-shadow: 0 5px 16px rgba(0,0,0,0.55);
    border: 1px solid rgba(255,255,255,0.12);
}}
.next-match .nm-center {{ flex: 1.4; text-align: center; }}
.next-match .nm-score {{
    font-family: 'Bebas Neue', 'Outfit', sans-serif;
    font-size: 3.1rem; line-height: 1;
    letter-spacing: 0.06em;
    color: {PRIMARY};
    text-shadow: 0 0 26px rgba(76,215,246,0.45);
}}
.next-match .nm-score .sep {{ color: {TEXT_DIM}; padding: 0 6px; }}
.next-match .nm-meta {{ color: {TEXT_DIM}; font-size: 0.72rem; margin-top: 3px; }}
.next-match .nm-kick {{
    font-family: 'JetBrains Mono', monospace;
    color: {TERTIARY}; font-weight: 800; font-size: 0.8rem;
}}

/* --- Ticket de partido (pestaña Partidos) --- */
.ticket {{
    position: relative;
    background:
        linear-gradient(135deg, rgba(18, 25, 44, 0.88) 0%, rgba(13, 20, 38, 0.92) 100%);
    border: 1px solid {BORDER};
    border-left: 4px solid #0c5c3d;
    border-radius: 14px;
    padding: 13px 18px 11px 18px;
    margin-bottom: 10px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    animation: fadeInUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
    backdrop-filter: blur(10px);
}}
.ticket:hover {{
    transform: translateY(-3px);
    border-color: rgba(76,215,246,0.40);
    border-left-color: {TERTIARY};
    box-shadow: 0 12px 32px rgba(0,0,0,0.45), 0 0 18px rgba(76,215,246,0.10);
}}
.ticket .t-row {{
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
}}
.ticket .t-team {{
    flex: 1.4; display: flex; align-items: center; gap: 9px;
    font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.02rem;
}}
.ticket .t-team.right {{ justify-content: flex-end; text-align: right; }}
.ticket .t-team img {{
    width: 27px; height: 19px; border-radius: 3px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5);
}}
.ticket .t-team .fav {{
    text-shadow: 0 0 14px rgba(76,215,246,0.55);
    color: #eaf6ff;
}}
.ticket .t-center {{ flex: 1.1; text-align: center; }}
.ticket .t-score {{
    font-family: 'Bebas Neue', 'Outfit', sans-serif;
    font-size: 1.9rem; line-height: 1; letter-spacing: 0.07em;
    color: {PRIMARY};
    text-shadow: 0 0 16px rgba(76,215,246,0.40);
}}
.ticket .t-score.played {{ color: {TEXT}; text-shadow: none; }}
.ticket .t-tag {{
    font-size: 0.62rem; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700;
}}
.ticket .t-sub {{ font-size: 0.66rem; color: {TEXT_DIM}; margin-top: 2px; }}
.ticket .t-foot {{
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 6px; font-size: 0.66rem; color: {TEXT_DIM};
}}
.ticket .t-badge {{
    border: 1px solid #334155; border-radius: 6px; padding: 1px 8px;
    font-size: 0.62rem; letter-spacing: 0.06em;
}}
.ticket .hit  {{ color: {TERTIARY}; animation: goalFlash 2.4s ease-in-out infinite; border-radius: 6px; padding: 1px 7px; }}
.ticket .miss {{ color: {DANGER}; }}

/* barra 1X2 dentro del ticket */
.ticket .t-bar {{
    display: flex; height: 9px; border-radius: 5px; overflow: hidden;
    margin-top: 7px;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);
}}
.ticket .t-bar .b1 {{ background: linear-gradient(90deg, #2bb8e0, {PRIMARY}); }}
.ticket .t-bar .bx {{ background: #3c4659; }}
.ticket .t-bar .b2 {{ background: linear-gradient(90deg, {ACCENT}, #b39ef5); }}
.ticket .t-legend {{
    display: flex; justify-content: space-between;
    font-size: 0.68rem; margin-top: 3px;
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
}}

/* sección de ronda eliminatoria */
.ko-round-title {{
    display: flex; align-items: center; gap: 10px;
    font-family: 'Outfit', sans-serif; font-weight: 800;
    color: {TEXT}; font-size: 1.0rem;
    margin: 18px 0 8px 0;
}}
.ko-round-title .line {{ flex: 1; height: 1px; background: linear-gradient(90deg, rgba(76,215,246,0.35), transparent); }}
.ko-round-title .dates {{ color: {TEXT_DIM}; font-size: 0.72rem; font-weight: 600; }}

/* ========================================================================
   📱 MÓVIL — responsive (pantallas estrechas)
   ======================================================================== */
@media (max-width: 640px) {{
    .block-container {{
        padding-left: 0.7rem !important; padding-right: 0.7rem !important;
        padding-top: 0.8rem !important;
    }}
    .wc-hero h1.wc-title {{ font-size: 1.8rem !important; }}
    .wc-hero .hosts {{ font-size: 0.9rem; }}
    .wc-hero .sub {{ font-size: 0.72rem; }}
    .headerkpi-bar {{ gap: 6px; margin: 4px 0 14px 0; }}
    .headerkpi-pill {{ padding: 6px 11px; font-size: 0.72rem; }}
    .wc-tick {{ font-size: 0.7rem; padding: 0 14px; }}
    .wc-tick img {{ width: 16px; height: 11px; }}
    .next-match {{ padding: 13px 13px 11px 13px; border-radius: 14px; }}
    .next-match .nm-label {{ font-size: 0.55rem; letter-spacing: 0.1em; }}
    .next-match .nm-kick {{ font-size: 0.62rem; }}
    .next-match .nm-grid {{ gap: 6px; }}
    .next-match .nm-team {{ font-size: 0.9rem; gap: 6px; }}
    .next-match .nm-team img {{ width: 30px; height: 21px; }}
    .next-match .nm-center {{ flex: 1.1; }}
    .next-match .nm-score {{ font-size: 1.9rem; }}
    .next-match .nm-meta {{ font-size: 0.56rem; }}
    /* apilar columnas de Streamlit en pantalla estrecha */
    div[data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 0.5rem !important; }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
    }}
}}

/* ========================================================================
   ✨ TRANSICIONES / microinteracciones
   ======================================================================== */
@keyframes contentFade {{ from {{ opacity: 0; transform: translateY(7px); }} to {{ opacity: 1; transform: none; }} }}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {{ animation: contentFade .35s ease both; }}
.headerkpi-pill:hover {{ transform: translateY(-2px); border-color: rgba(76,215,246,0.55); box-shadow: 0 6px 18px rgba(0,0,0,0.45); }}
[data-testid="stImage"] img {{ border-radius: 12px; transition: transform .3s ease, box-shadow .3s ease; }}
[data-testid="stImage"] img:hover {{ transform: scale(1.012); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
[data-testid="stVideo"] video {{ border-radius: 14px; }}
.stButton > button {{ transition: transform .15s ease, box-shadow .15s ease; }}
.stButton > button:hover {{ transform: translateY(-1px); }}

/* ========================================================================
   🎞️ Imágenes/vídeo integrados (sin "caja" dura: se funden con el fondo)
   ======================================================================== */
.stApp {{ overflow-x: hidden; }}
[data-testid="stImage"] img {{
    border-radius: 16px;
    box-shadow: 0 18px 50px rgba(0,0,0,0.55);
    -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 80%, transparent 100%);
    mask-image: linear-gradient(to bottom, #000 0%, #000 80%, transparent 100%);
}}
[data-testid="stVideo"] {{ margin: -6px -1.2rem 0 -1.2rem; }}
[data-testid="stVideo"] video {{
    width: calc(100% + 2.4rem);
    border-radius: 0;
    box-shadow: none;
    -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 68%, transparent 100%);
    mask-image: linear-gradient(to bottom, #000 0%, #000 68%, transparent 100%);
}}

/* ========================================================================
   💎 Glassmorphism + glow + hero cinematografico + scroll-reveal
   ======================================================================== */
.next-match {{
    background:
        radial-gradient(ellipse 70% 120% at 50% -30%, rgba(76,215,246,0.12), transparent 60%),
        linear-gradient(135deg, rgba(15,23,42,0.55), rgba(10,26,34,0.45)) !important;
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    animation: fadeInUp 0.5s cubic-bezier(0.16,1,0.3,1) both, panelGlow 4.5s ease-in-out infinite;
}}
@keyframes panelGlow {{
    0%,100% {{ box-shadow: 0 10px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(76,215,246,0.22), 0 0 20px rgba(76,215,246,0.12); }}
    50%     {{ box-shadow: 0 10px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(76,215,246,0.55), 0 0 40px rgba(76,215,246,0.34); }}
}}
.headerkpi-pill {{
    background: rgba(15,23,42,0.42) !important;
    backdrop-filter: blur(14px) saturate(1.2);
    -webkit-backdrop-filter: blur(14px) saturate(1.2);
}}
.news-banner, .wc-ticker {{ backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }}

/* Hero cinematografico: video/imagen de fondo + titulo encima */
.hero-cine {{
    position: relative; width: 100%;
    aspect-ratio: 16 / 6; min-height: 200px; max-height: 400px;
    border-radius: 18px; overflow: hidden;
    margin: -4px 0 12px 0;
    background-size: cover; background-position: center;
    box-shadow: 0 22px 60px rgba(0,0,0,0.6);
}}
.hero-cine .hero-vid {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }}
.hero-cine .hero-scrim {{
    position: absolute; inset: 0; z-index: 1;
    background:
        linear-gradient(90deg, rgba(2,6,23,0.88) 0%, rgba(2,6,23,0.30) 48%, transparent 78%),
        linear-gradient(0deg, rgba(2,6,23,0.92) 0%, transparent 58%);
}}
.hero-cine .hero-text {{ position: absolute; z-index: 2; left: 5%; right: 5%; bottom: 11%; }}
.hero-cine .hero-text h1.wc-title {{ margin: 0 !important; }}
.hero-cine .hero-text .sub {{ max-width: 660px; margin-top: 4px; }}
@media (max-width: 640px) {{
    .hero-cine {{ aspect-ratio: 16/10; max-height: 280px; }}
    .hero-cine .hero-text {{ bottom: 8%; }}
}}

/* scroll-reveal (lo activa /effects.js) */
.reveal-init {{ opacity: 0; transform: translateY(18px); }}
.reveal-in {{ opacity: 1 !important; transform: none !important;
    transition: opacity .6s ease, transform .6s cubic-bezier(0.16,1,0.3,1); }}

/* ========================================================================
   🏆 FINAL FOUR — "Camino a la final"
   Elemento-firma de la fase final: las dos semifinales (cyan a la izquierda,
   violeta a la derecha) convergen sobre un nodo dorado de trofeo. El oro es el
   único color cálido de la paleta: aparece solo aquí porque todo el cuadro
   converge hacia el premio.
   ======================================================================== */
.ff-wrap {{
    position: relative;
    border-radius: 20px;
    padding: 20px 24px 22px;
    margin: 4px 0 20px;
    background:
        radial-gradient(ellipse 60% 130% at 50% -10%, rgba(255,209,92,0.10), transparent 62%),
        linear-gradient(135deg, rgba(15,23,42,0.60), rgba(12,26,34,0.50));
    border: 1px solid {BORDER};
    backdrop-filter: blur(16px) saturate(1.15);
    -webkit-backdrop-filter: blur(16px) saturate(1.15);
    box-shadow: 0 12px 44px rgba(0,0,0,0.45);
    overflow: hidden;
    animation: fadeInUp 0.55s cubic-bezier(0.16,1,0.3,1) both;
}}
/* Hairline tricolor arriba: cyan → oro → violeta = las dos ramas y el trofeo */
.ff-wrap::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, {PRIMARY} 0%, #ffd15c 50%, {ACCENT} 100%);
    opacity: 0.85;
}}
.ff-head {{
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 12px; flex-wrap: wrap; margin-bottom: 16px;
}}
.ff-eyebrow {{
    font-family: 'Outfit', sans-serif; font-weight: 800;
    font-size: 0.74rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: #ffd98a;
    display: inline-flex; align-items: center; gap: 9px;
}}
.ff-eyebrow .rhomb {{ color: #ffd15c; font-size: 0.7rem; }}
.ff-when {{
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    font-size: 0.7rem; color: {TEXT_DIM}; letter-spacing: 0.04em;
}}
.ff-grid {{
    position: relative;
    display: grid; grid-template-columns: 1fr auto 1fr;
    align-items: center; gap: 10px;
}}
/* Raíl que converge en el trofeo: cyan por la izquierda, violeta por la derecha,
   ambos se desvanecen hacia el centro donde el nodo dorado los "absorbe". */
.ff-grid::before {{
    content: ""; position: absolute; left: 8%; right: 8%; top: 50%;
    height: 2px; transform: translateY(-50%); z-index: 0;
    background: linear-gradient(90deg,
        rgba(76,215,246,0) 0%, rgba(76,215,246,0.55) 20%, rgba(76,215,246,0) 44%,
        rgba(208,188,255,0) 56%, rgba(208,188,255,0.55) 80%, rgba(208,188,255,0) 100%);
}}
.ff-semi {{
    position: relative; z-index: 1;
    background: rgba(9,14,28,0.72);
    border: 1px solid {BORDER};
    border-radius: 14px; padding: 13px 15px;
    transition: transform .3s cubic-bezier(0.16,1,0.3,1), box-shadow .3s ease, border-color .3s ease;
}}
.ff-semi.left  {{ border-top: 2px solid {PRIMARY}; }}
.ff-semi.right {{ border-top: 2px solid {ACCENT}; }}
.ff-semi:hover {{ transform: translateY(-3px); }}
.ff-semi.left:hover  {{ border-color: rgba(76,215,246,0.45); box-shadow: 0 0 24px rgba(76,215,246,0.16); }}
.ff-semi.right:hover {{ border-color: rgba(208,188,255,0.45); box-shadow: 0 0 24px rgba(208,188,255,0.16); }}
.ff-semi-tag {{
    display: flex; justify-content: space-between; align-items: center;
    font-family: 'Outfit', sans-serif; font-weight: 700;
    font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: {TEXT_DIM}; margin-bottom: 9px;
}}
.ff-semi.left  .ff-semi-tag .s {{ color: {PRIMARY}; }}
.ff-semi.right .ff-semi-tag .s {{ color: {ACCENT}; }}
.ff-team {{
    display: flex; align-items: center; gap: 10px;
    padding: 4px 0; font-family: 'Outfit', sans-serif;
}}
.ff-team img {{
    width: 30px; height: 21px; border-radius: 3px; flex-shrink: 0;
    box-shadow: 0 2px 7px rgba(0,0,0,0.55); border: 1px solid rgba(255,255,255,0.10);
}}
.ff-team .nm {{ font-weight: 700; font-size: 1.0rem; color: {TEXT_DIM}; flex: 1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ff-team .pc {{
    font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 0.9rem;
    color: {TEXT_DIM}; font-variant-numeric: tabular-nums;
}}
.ff-team.fav .nm {{ color: #eaf6ff; }}
.ff-team.fav .pc {{ color: #fff; }}
.ff-semi.left  .ff-team.fav .nm {{ text-shadow: 0 0 14px rgba(76,215,246,0.55); }}
.ff-semi.left  .ff-team.fav .pc {{ color: {PRIMARY}; }}
.ff-semi.right .ff-team.fav .nm {{ text-shadow: 0 0 14px rgba(208,188,255,0.55); }}
.ff-semi.right .ff-team.fav .pc {{ color: {ACCENT}; }}
.ff-team .arrow {{ width: 10px; font-size: 0.7rem; color: transparent; }}
.ff-team.fav .arrow {{ color: currentColor; }}
.ff-semi.left  .ff-team.fav .arrow {{ color: {PRIMARY}; }}
.ff-semi.right .ff-team.fav .arrow {{ color: {ACCENT}; }}
/* barra de reparto "pasa a la final" */
.ff-split {{ display: flex; height: 7px; border-radius: 4px; overflow: hidden;
    margin-top: 9px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.55); }}
.ff-semi.left  .ff-split .a {{ background: linear-gradient(90deg, #2bb8e0, {PRIMARY}); }}
.ff-semi.left  .ff-split .b {{ background: #263042; }}
.ff-semi.right .ff-split .a {{ background: #263042; }}
.ff-semi.right .ff-split .b {{ background: linear-gradient(90deg, {ACCENT}, #b39ef5); }}
.ff-exp {{ margin-top: 7px; font-size: 0.64rem; color: {TEXT_DIM};
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.02em; text-align: center; }}
.ff-exp b {{ color: #cfe9ff; font-weight: 800; }}

/* Nodo central: el trofeo dorado */
.ff-final {{
    position: relative; z-index: 2;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-width: 132px; padding: 8px 10px 12px; border-radius: 16px;
    background: radial-gradient(ellipse at center, rgba(255,209,92,0.16), rgba(255,209,92,0.02) 70%);
    animation: ffCupGlow 4.5s ease-in-out infinite;
}}
.ff-cup {{ font-size: 2.5rem; line-height: 1;
    filter: drop-shadow(0 0 16px rgba(255,209,92,0.6)); animation: ballBounce 3.2s ease-in-out infinite; }}
.ff-final .lbl {{
    font-family: 'Bebas Neue', 'Outfit', sans-serif; letter-spacing: 0.14em;
    font-size: 1.15rem; color: #ffe08a; margin-top: 4px;
    text-shadow: 0 0 18px rgba(255,209,92,0.45); }}
.ff-final .date {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    color: {TEXT_DIM}; letter-spacing: 0.06em; margin-top: 1px; }}
.ff-final .champ {{ margin-top: 8px; text-align: center; }}
.ff-final .champ .k {{ display: block; font-size: 0.54rem; text-transform: uppercase;
    letter-spacing: 0.12em; color: {TEXT_DIM}; font-weight: 700; }}
.ff-final .champ .v {{ font-family: 'Outfit', sans-serif; font-weight: 800;
    font-size: 0.9rem; color: #ffe08a; }}
.ff-final .champ .v .p {{ font-family: 'JetBrains Mono', monospace; color: #fff; font-size: 0.82rem; }}
@keyframes ffCupGlow {{
    0%,100% {{ box-shadow: 0 0 0 rgba(255,209,92,0); }}
    50%     {{ box-shadow: 0 0 34px rgba(255,209,92,0.22); }}
}}

@media (max-width: 640px) {{
    .ff-wrap {{ padding: 16px 14px 18px; }}
    .ff-grid {{ grid-template-columns: 1fr; gap: 12px; }}
    .ff-grid::before {{ display: none; }}
    .ff-final {{ order: 3; min-width: 0; width: 100%; }}
    .ff-semi.right {{ order: 4; }}
    .ff-team .nm {{ font-size: 0.95rem; }}
    .ff-cup {{ font-size: 2.1rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
    .ff-wrap, .ff-final, .ff-cup {{ animation: none !important; }}
}}
</style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
