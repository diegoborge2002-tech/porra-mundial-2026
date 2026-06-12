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
    rendimiento, en_vivo, comparador, plantilla, partidos,
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


def _ticker_bar() -> None:
    """Cinta LED tipo videomarcador: resultados recientes + próximos con pronóstico."""
    try:
        from app.utils import get_elo_with_biases, load_real_results
        from src.model.match_day import find_upcoming_matches
        from src.model.match_probs import representative_score
        from src.data.team_profile import ISO_CODES

        elo = get_elo_with_biases()
        real = load_real_results() or {}

        def flag(team: str) -> str:
            iso = ISO_CODES.get(team, "un")
            return f'<img src="https://flagcdn.com/w40/{iso}.png">'

        items: list[str] = []
        # Resultados ya jugados (últimos 6)
        for key, scores in list((real.get("group_matches") or {}).items())[-6:]:
            if not scores or len(scores) < 2:
                continue
            h, a = key.split(" vs ")
            items.append(
                f'<span class="wc-tick">{flag(h)} {h} '
                f'<span class="score">{scores[0]}–{scores[1]}</span> {a} {flag(a)} '
                f'<span class="ok">FINAL</span></span>'
            )
        # Próximos partidos con resultado esperado
        for m in find_upcoming_matches(elo, window_hours=72, fallback_days=10)[:8]:
            (bh, ba), _ = representative_score(m.lambda_home, m.lambda_away)
            when = m.date.strftime("%d %b").upper() if hasattr(m.date, "strftime") else ""
            items.append(
                f'<span class="wc-tick"><span class="when">{when}</span> '
                f'{flag(m.home)} {m.home} <span class="exp">vs</span> {m.away} {flag(m.away)} '
                f'<span class="exp">{bh}–{ba} esperado · {m.p_home*100:.0f}/{m.p_draw*100:.0f}/{m.p_away*100:.0f}</span></span>'
            )
        if not items:
            return
        track = "".join(items)
        # Duplicado para loop infinito sin salto
        st.markdown(
            f'<div class="wc-ticker"><div class="wc-ticker-track">{track}{track}</div></div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def _next_match_panel() -> None:
    """Panel protagonista: el próximo partido con pronóstico del ensemble."""
    try:
        from app.utils import get_elo_with_biases
        from src.model.match_day import find_upcoming_matches
        from src.model.match_probs import representative_score
        from src.data.team_profile import ISO_CODES

        elo = get_elo_with_biases()
        up = find_upcoming_matches(elo, window_hours=36, fallback_days=10)
        if not up:
            return
        m = up[0]
        (bh, ba), bp = representative_score(m.lambda_home, m.lambda_away)
        iso_h = ISO_CODES.get(m.home, "un")
        iso_a = ISO_CODES.get(m.away, "un")
        kick = m.date.strftime("%a %d %b · %H:%M").upper() if hasattr(m.date, "strftime") else ""
        venue = f" · {m.city}" if m.city else ""
        group = f"GRUPO {m.group}" if m.group not in ("?", "KO") else "ELIMINATORIA"

        st.markdown(
            f"""
            <div class="next-match">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="nm-label"><span class="dot"></span>Próximo partido · {group}{venue}</span>
                <span class="nm-kick">⏱ {kick}</span>
              </div>
              <div class="nm-grid">
                <div class="nm-team"><img src="https://flagcdn.com/w80/{iso_h}.png"> {m.home}</div>
                <div class="nm-center">
                  <div class="nm-score">{bh}<span class="sep">–</span>{ba}</div>
                  <div class="nm-meta">esperado ({bp*100:.0f}%) · xG {m.lambda_home:.2f}–{m.lambda_away:.2f}
                  · 1X2 {m.p_home*100:.0f}/{m.p_draw*100:.0f}/{m.p_away*100:.0f}</div>
                </div>
                <div class="nm-team right">{m.away} <img src="https://flagcdn.com/w80/{iso_a}.png"></div>
              </div>
              <div style="height:10px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass


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
# Header — hero de estadio
# ============================================================
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.markdown(
        f"""
        <div class="wc-hero">
            <h1 class="wc-title"><span class="ball">⚽</span> Porra Mundial 2026
                <span class="hosts">🇺🇸 🇨🇦 🇲🇽</span></h1>
            <p class="sub">
                Ensemble Elo + XGBoost · Monte Carlo 10.000 torneos · 48 equipos · 104 partidos · 11 jun → 19 jul
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hc2:
    _global_search()

_ticker_bar()
_next_match_panel()
_header_kpi_bar()
_news_banner()


tab1, tab1b, tab2, tab2b, tab2c, tab3, tab4, tab5, tab6, tab7, tab9 = st.tabs([
    "📊 Predicciones",
    "🔮 Partidos",
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
with tab1b: partidos.render()
with tab2: selecciones.render()
with tab2b: comparador.render()
with tab2c: plantilla.render()
with tab3: calendario.render()
with tab4: biases.render()
with tab5: porra.render()
with tab6: seguimiento.render()
with tab7: en_vivo.render()
with tab9: rendimiento.render()
