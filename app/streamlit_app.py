"""Web app del Mundial 2026.

Lanzar con:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import math
import streamlit as st

from app.styles import inject, TEXT_DIM, PRIMARY, ACCENT
from app.tabs import (
    predicciones, selecciones, biases, porra, calendario, seguimiento,
    rendimiento, en_vivo, comparador, plantilla,
)


KICKOFF = datetime(2026, 6, 11, 20, 0, 0)


st.set_page_config(
    page_title="Porra Mundial 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject()


def _header_kpi_bar() -> None:
    """Banda persistente con KPIs globales bajo el h1."""
    try:
        from app.utils import run_simulation_with_real, get_elo_with_biases, load_real_results
        elo = get_elo_with_biases()
        summary = run_simulation_with_real(elo, n_sims=10_000, seed=42)
        champ = summary.get("champion", {})
        if champ:
            top_team, top_p = max(champ.items(), key=lambda x: x[1])
            # Entropía → candidatos efectivos
            ent = 0.0
            for p in champ.values():
                if p > 0:
                    ent -= p * math.log2(p)
            n_eff = 2 ** ent
        else:
            top_team, top_p, n_eff = "—", 0.0, 0.0

        real = load_real_results() or {}
        n_played = sum(1 for v in (real.get("group_results") or {}).values() if v)
        # Sumar ko games jugados
        for r in ["r32", "r16", "qf", "sf", "final"]:
            n_played += len((real.get(f"{r}_winners") or {}))
    except Exception:
        top_team, top_p, n_eff, n_played = "—", 0.0, 0.0, 0

    today = date.today()
    days_to = (KICKOFF.date() - today).days
    if days_to > 0:
        kickoff_pill = (
            f'<div class="headerkpi-pill"><span class="lbl">Kickoff</span>'
            f'<span class="val">{days_to}</span> días</div>'
        )
    elif days_to == 0:
        kickoff_pill = (
            '<div class="headerkpi-pill"><span class="lbl">Estado</span>'
            '<span class="val val-good">¡Hoy arranca!</span></div>'
        )
    else:
        kickoff_pill = (
            '<div class="headerkpi-pill"><span class="lbl">Estado</span>'
            '<span class="val val-good">⚽ En curso</span></div>'
        )

    parts = [
        '<div class="headerkpi-bar">',
        kickoff_pill,
        f'<div class="headerkpi-pill"><span class="lbl">Favorito</span>'
        f'<span class="val">{top_team}</span> <span style="color:{TEXT_DIM}">·</span> '
        f'<span class="val val-accent">{top_p*100:.1f}%</span></div>',
        f'<div class="headerkpi-pill"><span class="lbl">Candidatos efectivos</span>'
        f'<span class="val">{n_eff:.1f}</span></div>',
        f'<div class="headerkpi-pill"><span class="lbl">Partidos jugados</span>'
        f'<span class="val">{n_played}</span><span style="color:{TEXT_DIM}">/104</span></div>',
        '</div>',
    ]
    st.markdown("".join(parts), unsafe_allow_html=True)


def _news_banner() -> None:
    """Banner con las 3 noticias activas más recientes."""
    try:
        from src.data.news import list_news, NEWS_TYPES
        items = list_news(only_active=True)
    except Exception:
        items = []
    if not items:
        return
    rows = [
        '<div class="news-banner">',
        '<div class="news-banner-title">📰 Últimas noticias del Mundial</div>',
    ]
    for n in items[:4]:
        emoji, label = NEWS_TYPES.get(n.tipo, ("📰", "Otro"))
        delta_html = ""
        if n.elo_delta:
            cls = "delta-pos" if n.elo_delta > 0 else "delta-neg"
            sign = "+" if n.elo_delta > 0 else ""
            delta_html = f' <span class="delta {cls}">{sign}{int(n.elo_delta)} Elo</span>'
        rows.append(
            f'<div class="news-item">'
            f'<span class="type-tag">{emoji} {label}</span>'
            f'<span class="team">{n.equipo}</span>'
            f'<span class="text">{n.texto}</span>'
            f'{delta_html}</div>'
        )
    rows.append('</div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def _global_search() -> None:
    """Buscador global: salta a la ficha de una selección."""
    from src.tournament.groups import ALL_TEAMS
    teams = sorted(ALL_TEAMS)
    with st.popover("🔍 Buscar equipo", use_container_width=False):
        sel = st.selectbox(
            "Saltar a la ficha de…",
            ["— Seleccionar —"] + teams,
            key="__global_search",
        )
        if sel and sel != "— Seleccionar —":
            st.query_params["team"] = sel
            st.query_params["goto"] = "selecciones"
            st.success(f"Abriendo ficha de {sel} → pestaña **Selecciones**")


# ============================================================
# Header
# ============================================================
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.markdown(
        f"""
        <div style="margin-bottom: 4px;">
            <h1 style="margin:0;">⚽ Porra Mundial 2026</h1>
            <p style="color:{TEXT_DIM}; margin:4px 0 0 0; font-size:0.95rem;">
                Modelo Elo · Monte Carlo · 48 equipos · 104 partidos · 11 jun → 19 jul
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hc2:
    _global_search()

_header_kpi_bar()
_news_banner()


tab1, tab2, tab2b, tab2c, tab3, tab4, tab5, tab6, tab7, tab9 = st.tabs([
    "📊 Predicciones",
    "🌍 Selecciones",
    "🆚 Comparador",
    "👥 Plantilla",
    "🗓 Calendario",
    "🎯 Mis ajustes",
    "📋 Mi porra",
    "📡 Seguimiento en vivo",
    "⚡ En vivo",
    "📈 Rendimiento del modelo",
])

with tab1: predicciones.render()
with tab2: selecciones.render()
with tab2b: comparador.render()
with tab2c: plantilla.render()
with tab3: calendario.render()
with tab4: biases.render()
with tab5: porra.render()
with tab6: seguimiento.render()
with tab7: en_vivo.render()
with tab9: rendimiento.render()
