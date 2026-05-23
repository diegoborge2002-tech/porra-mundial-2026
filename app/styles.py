"""CSS custom inyectado en la web para tema oscuro premium y ultra-elegante (De-AI) con temática táctica futbolística."""
from __future__ import annotations
import base64
import streamlit as st


PRIMARY = "#06b6d4"      # Ice-Cyan / Electric Cyan (Mates)
ACCENT = "#8b5cf6"       # Electric Violet (Intuición)
BG = "#020617"           # Deep space slate-black
BG_CARD = "rgba(15, 23, 42, 0.45)"      # Vidrio oscuro obsidian
BG_CARD_HOVER = "rgba(30, 41, 59, 0.6)"
TEXT = "#f8fafc"         # Blanco hielo brillante
TEXT_DIM = "#94a3b8"     # Slate atenuado
BORDER = "rgba(99, 102, 241, 0.12)"     # Borde vidrio índigo
DANGER = "#f43f5e"       # Rosa coral neón
GOOD = "#10b981"        # Verde esmeralda neón


# Patrón SVG ultra-elegante y sutil para las líneas de una pizarra táctica de fútbol
SVG_PITCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" fill="none" stroke="rgba(6, 182, 212, 0.018)" stroke-width="1.5">
  <rect x="30" y="30" width="940" height="540" rx="8" />
  <line x1="500" y1="30" x2="500" y2="570" />
  <circle cx="500" cy="300" r="90" />
  <circle cx="500" cy="300" r="4" fill="rgba(6, 182, 212, 0.018)" />
  <rect x="30" y="180" width="140" height="240" />
  <rect x="830" y="180" width="140" height="240" />
  <rect x="30" y="240" width="55" height="120" />
  <rect x="915" y="240" width="55" height="120" />
  <circle cx="140" cy="300" r="3" fill="rgba(6, 182, 212, 0.018)" />
  <circle cx="860" cy="300" r="3" fill="rgba(6, 182, 212, 0.018)" />
  <path d="M 170 245 A 90 90 0 0 1 170 355" />
  <path d="M 830 245 A 90 90 0 0 0 830 355" />
  <path d="M 30 45 A 15 15 0 0 0 45 30" />
  <path d="M 970 45 A 15 15 0 0 1 955 30" />
  <path d="M 30 555 A 15 15 0 0 1 45 570" />
  <path d="M 970 555 A 15 15 0 0 0 955 570" />
</svg>"""

b64_svg = base64.b64encode(SVG_PITCH.encode("utf-8")).decode("utf-8")


CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

@keyframes fadeInUp {{
    from {{
        opacity: 0;
        transform: translateY(12px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}

@keyframes softPulse {{
    0% {{ box-shadow: 0 0 15px rgba(6, 182, 212, 0.1); }}
    50% {{ box-shadow: 0 0 25px rgba(6, 182, 212, 0.25); }}
    100% {{ box-shadow: 0 0 15px rgba(6, 182, 212, 0.1); }}
}}

/* Tipografía general */
html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}}

h1, h2, h3, h4, .team-name, .big-stat-value, [data-testid="stMetricValue"] {{
    font-family: 'Outfit', sans-serif !important;
}}

/* Fondo de Pizarra Táctica de Fútbol */
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

[data-testid="stHeader"] {{
    background-color: transparent !important;
}}

[data-testid="stSidebar"] {{
    background-color: rgba(15, 23, 42, 0.88);
    border-right: 1px solid rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
}}

h1, h2, h3, h4 {{
    color: {TEXT} !important;
    font-weight: 700;
    letter-spacing: -0.03em;
}}

h1 {{ font-size: 2.5rem !important; }}
h2 {{ font-size: 1.8rem !important; }}
h3 {{ font-size: 1.35rem !important; }}

/* Rediseño total de st.metric */
[data-testid="stMetric"] {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.5) 0%, rgba(30, 41, 59, 0.3) 100%) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 20px !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25) !important;
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both !important;
}}

[data-testid="stMetric"]:hover {{
    border-color: rgba(6, 182, 212, 0.5) !important;
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.15), inset 0 0 10px rgba(6, 182, 212, 0.05) !important;
    transform: translateY(-4px) scale(1.01) !important;
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_DIM} !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}}

[data-testid="stMetricValue"] {{
    background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    text-shadow: 0 0 15px rgba(6, 182, 212, 0.25) !important;
}}

/* Rediseño de st.tabs - Aspecto premium de píldoras integradas */
[data-testid="stTabs"] {{
    background-color: rgba(15, 23, 42, 0.55) !important;
    border-radius: 12px !important;
    padding: 6px !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    margin-bottom: 24px !important;
    backdrop-filter: blur(12px) !important;
}}

[data-testid="stTabs"] button {{
    background-color: transparent !important;
    color: {TEXT_DIM} !important;
    border: none !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    font-family: 'Outfit', sans-serif !important;
}}

[data-testid="stTabs"] button:hover {{
    color: {PRIMARY} !important;
    background-color: rgba(6, 182, 212, 0.06) !important;
}}

[data-testid="stTabs"] button[aria-selected="true"] {{
    color: #ffffff !important;
    background-color: rgba(6, 182, 212, 0.15) !important;
    box-shadow: 0 4px 15px rgba(6, 182, 212, 0.1) !important;
    border: 1px solid rgba(6, 182, 212, 0.25) !important;
}}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    display: none !important;
}}
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: none !important;
}}

[data-testid="stTable"], [data-testid="stDataFrame"] {{
    background-color: rgba(15, 23, 42, 0.4) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
}}

/* Hover interactivo sobre filas de tablas */
tbody tr {{
    transition: background-color 0.2s ease, border-color 0.2s ease !important;
}}
tbody tr:hover {{
    background-color: rgba(6, 182, 212, 0.05) !important;
}}

/* Rediseño espectacular de botones st.button */
.stButton button {{
    background: linear-gradient(135deg, {ACCENT} 0%, {PRIMARY} 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.9rem !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    width: 100% !important;
}}

.stButton button:hover {{
    background: linear-gradient(135deg, #a78bfa 0%, #22d3ee 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(6, 182, 212, 0.4) !important;
    color: #ffffff !important;
}}

.stButton button:active {{
    transform: translateY(0) !important;
    box-shadow: 0 2px 10px rgba(6, 182, 212, 0.2) !important;
}}

/* === Tarjetas de Equipo (Team Card) Glassmorphism === */
.team-card {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.5) 0%, rgba(30, 41, 59, 0.3) 100%) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 20px !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    margin-bottom: 16px !important;
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
}}

.team-card:hover {{
    border-color: rgba(6, 182, 212, 0.5) !important;
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.15), inset 0 0 10px rgba(6, 182, 212, 0.05) !important;
    transform: translateY(-4px) scale(1.01) !important;
}}

.team-card-header {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
}}

.team-flag {{
    width: 64px;
    height: 48px;
    object-fit: cover;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
}}

.team-name {{
    font-size: 1.4rem;
    font-weight: 700;
    color: {TEXT};
    margin: 0;
}}

.team-meta {{
    font-size: 0.85rem;
    color: {TEXT_DIM};
    margin: 0;
}}

/* Barras de probabilidad elegantes */
.prob-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 8px 0;
    font-size: 0.85rem;
}}

.prob-label {{
    color: {TEXT_DIM};
    min-width: 80px;
    font-weight: 500;
}}

.prob-bar-container {{
    flex: 1;
    height: 8px;
    background-color: rgba(15, 23, 42, 0.8) !important;
    border-radius: 4px;
    margin: 0 12px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.03);
}}

.prob-bar {{
    height: 100%;
    background: linear-gradient(90deg, {PRIMARY} 0%, {ACCENT} 100%) !important;
    border-radius: 4px;
}}

.prob-value {{
    color: {TEXT};
    font-weight: 700;
    min-width: 50px;
    text-align: right;
}}

/* Form streak (W/D/L pills) */
.form-streak {{
    display: flex;
    gap: 6px;
    margin: 8px 0;
}}

.form-pill {{
    width: 24px;
    height: 24px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.75rem;
    color: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}}

.form-W {{ background-color: {GOOD}; }}
.form-D {{ background-color: {TEXT_DIM}; color: {BG}; }}
.form-L {{ background-color: {DANGER}; }}

/* Separadores limpios */
.section-divider {{
    border-top: 1px solid rgba(255, 255, 255, 0.03);
    margin: 24px 0;
}}

/* Ocultar barra de Streamlit */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

/* Custom slider color */
[data-testid="stSlider"] [role="slider"] {{
    background-color: {PRIMARY} !important;
    box-shadow: 0 0 10px {PRIMARY} !important;
}}

/* Selectbox e Inputs */
[data-baseweb="select"] > div {{
    background-color: rgba(15, 23, 42, 0.65) !important;
    border-color: rgba(255, 255, 255, 0.05) !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    transition: border-color 0.2s !important;
}}
[data-baseweb="select"] > div:hover {{
    border-color: {PRIMARY} !important;
}}

/* Expander con Glassmorphism */
.streamlit-expanderHeader {{
    background-color: rgba(15, 23, 42, 0.5) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    color: {TEXT} !important;
}}

/* Filas de Partidos (Match Row) */
.match-row {{
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 12px 16px !important;
    background: rgba(15, 23, 42, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    border-radius: 12px !important;
    margin: 6px 0 !important;
    font-size: 0.85rem !important;
    transition: all 0.3s ease !important;
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both !important;
}}

.match-row:hover {{
    background: rgba(30, 41, 59, 0.4) !important;
    border-color: rgba(6, 182, 212, 0.2) !important;
    transform: translateX(4px) !important;
}}

.match-date {{
    color: {TEXT_DIM};
    min-width: 80px;
    font-weight: 500;
}}

.match-teams {{
    flex: 1;
    color: {TEXT};
    font-weight: 600;
}}

.match-score {{
    font-weight: 700;
    color: {PRIMARY};
    text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
}}

/* Tarjetas Estadísticas Gigantes (Big Stat) */
.big-stat {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.5) 0%, rgba(30, 41, 59, 0.3) 100%) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 16px !important;
    padding: 18px 12px !important;
    text-align: center !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
}}

.big-stat:hover {{
    border-color: rgba(6, 182, 212, 0.5) !important;
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.15), inset 0 0 10px rgba(6, 182, 212, 0.05) !important;
    transform: translateY(-4px) scale(1.02) !important;
}}

.big-stat-value {{
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    line-height: 1.1 !important;
    text-shadow: 0 0 15px rgba(6, 182, 212, 0.25) !important;
}}

.big-stat-label {{
    font-size: 0.7rem !important;
    color: {TEXT_DIM} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    margin-top: 6px !important;
    font-weight: 600 !important;
}}


/* =========================================================================
   DISEÑO CONCEPTUAL ADICIONAL: MATES vs INTUICIÓN
   ========================================================================= */

/* Tarjetas Mates - Cian Eléctrico */
.card-mates {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(6, 182, 212, 0.03) 100%) !important;
    border: 1px solid rgba(6, 182, 212, 0.18) !important;
    border-radius: 16px !important;
    padding: 22px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(6, 182, 212, 0.04) !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

.card-mates:hover {{
    border-color: rgba(6, 182, 212, 0.65) !important;
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.16), inset 0 0 10px rgba(6, 182, 212, 0.05) !important;
    transform: translateY(-2px) !important;
}}

/* Tarjetas Intuición - Violeta Eléctrico */
.card-intuicion {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(139, 92, 246, 0.03) 100%) !important;
    border: 1px solid rgba(139, 92, 246, 0.18) !important;
    border-radius: 16px !important;
    padding: 22px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(139, 92, 246, 0.04) !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

.card-intuicion:hover {{
    border-color: rgba(139, 92, 246, 0.65) !important;
    box-shadow: 0 0 25px rgba(139, 92, 246, 0.16), inset 0 0 10px rgba(139, 92, 246, 0.05) !important;
    transform: translateY(-2px) !important;
}}

/* Badges distintivos */
.badge-mates {{
    display: inline-block !important;
    background: rgba(6, 182, 212, 0.12) !important;
    color: #22d3ee !important;
    border: 1px solid rgba(6, 182, 212, 0.3) !important;
    border-radius: 6px !important;
    padding: 3px 10px !important;
    font-size: 0.72rem !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 12px !important;
}}

.badge-intuicion {{
    display: inline-block !important;
    background: rgba(139, 92, 246, 0.12) !important;
    color: #c084fc !important;
    border: 1px solid rgba(139, 92, 246, 0.3) !important;
    border-radius: 6px !important;
    padding: 3px 10px !important;
    font-size: 0.72rem !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 12px !important;
}}

/* =========================================================================
   CAMPO DE FÚTBOL (Once probable)
   ========================================================================= */
.pitch {{
    position: relative;
    width: 100%;
    aspect-ratio: 5 / 7;
    max-width: 460px;
    margin: 16px auto;
    background:
        radial-gradient(ellipse at center, rgba(6,182,212,0.06) 0%, rgba(6,182,212,0) 60%),
        linear-gradient(180deg, #053827 0%, #0a4a35 50%, #053827 100%);
    border-radius: 14px;
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
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.85rem; color: #fff;
    border: 2px solid rgba(255,255,255,0.55);
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    font-family: 'Outfit', sans-serif;
}}
.jersey-hot  {{ background: linear-gradient(135deg, #f97316 0%, #ef4444 100%); }}
.jersey-good {{ background: linear-gradient(135deg, {PRIMARY} 0%, #10b981 100%); }}
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

/* =========================================================================
   HEADER KPI BAR (banda persistente bajo el h1)
   ========================================================================= */
.headerkpi-bar {{
    display: flex; gap: 12px; flex-wrap: wrap;
    margin: 4px 0 18px 0;
}}
.headerkpi-pill {{
    background: linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(30,41,59,0.55) 100%);
    border: 1px solid {BORDER};
    border-radius: 999px;
    padding: 7px 16px;
    font-size: 0.85rem; font-weight: 600;
    color: {TEXT};
    backdrop-filter: blur(10px);
    display: inline-flex; align-items: center; gap: 6px;
}}
.headerkpi-pill .lbl {{ color: {TEXT_DIM}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; }}
.headerkpi-pill .val {{ font-weight: 800; color: {PRIMARY}; font-size: 1rem; }}
.headerkpi-pill .val-accent {{ color: {ACCENT}; }}
.headerkpi-pill .val-good {{ color: {GOOD}; }}
.headerkpi-pill .val-danger {{ color: {DANGER}; }}

/* =========================================================================
   NEWSFEED BANNER
   ========================================================================= */
.news-banner {{
    background: linear-gradient(135deg, rgba(245,158,11,0.10) 0%, rgba(244,63,94,0.08) 100%);
    border: 1px solid rgba(245,158,11,0.30);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 18px;
    backdrop-filter: blur(10px);
}}
.news-banner-title {{
    font-size: 0.78rem; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700;
    margin-bottom: 8px;
}}
.news-item {{
    display: flex; align-items: center; gap: 10px;
    padding: 6px 0;
    font-size: 0.88rem;
    border-top: 1px solid rgba(255,255,255,0.04);
}}
.news-item:first-of-type {{ border-top: none; }}
.news-item .team {{ font-weight: 700; color: {TEXT}; min-width: 130px; }}
.news-item .type-tag {{
    font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,0.08); color: {TEXT_DIM};
}}
.news-item .text {{ flex: 1; color: {TEXT}; }}
.news-item .delta {{ font-weight: 800; }}
.news-item .delta-pos {{ color: {GOOD}; }}
.news-item .delta-neg {{ color: {DANGER}; }}
</style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
