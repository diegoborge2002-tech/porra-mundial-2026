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
</style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
