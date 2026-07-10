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

import json
import math
import streamlit as st

from app.styles import inject, TEXT_DIM, PRIMARY, ACCENT
from app.components_media import render_hero, render_background, render_matchday_brief
from app.tabs import (
    predicciones, selecciones, biases, seguimiento,
    rendimiento, plantilla, partidos, actualidad, mercado, cuadro,
)
# comparador y calendario ya no son pestañas propias: comparador vive dentro de
# Selecciones (toggle) y el mapa de Calendario dentro de Partidos. Se importan
# de forma diferida en esos módulos. 'en_vivo' (calculadora minuto a minuto) se retiró.


KICKOFF = datetime(2026, 6, 11, 20, 0, 0)


st.set_page_config(
    page_title="Mi Mundial 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject()
render_background()


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
        n_played = sum(1 for v in (real.get("group_matches") or {}).values() if v)
        # Sumar eliminatorias jugadas
        ko = real.get("knockout_matches") or {}
        for r in ["r32", "r16", "qf", "sf", "final"]:
            n_played += len(ko.get(r) or {})
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


def _freshness_bar() -> None:
    """Expone cuándo se refrescó cada fuente para que la web sea auditable."""
    def _read_date(path: Path, field: str) -> str:
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get(field, "")
            return str(value).replace("T", " ")[:16] or "sin datos"
        except Exception:
            return "sin datos"

    actual = _read_date(ROOT / "data" / "processed" / "actualidad.json", "updated")
    odds = _read_date(ROOT / "data" / "processed" / "odds.json", "fetched_at")
    st.caption(
        f"🛰️ Datos verificados · Resultados: API football-data.org · "
        f"Actualidad: {actual} · Mercado: {odds} · Modelo: ensemble Elo + stats"
    )


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
        # Resultados ya jugados: prioriza eliminatorias, que son lo relevante
        # durante la fase final, y completa con los últimos grupos si hace falta.
        finals = []
        for rnd in (real.get("knockout_matches") or {}).values():
            for m in rnd.values():
                if m.get("home_score") is not None:
                    finals.append((m["home"], m["away"], m["home_score"], m["away_score"]))
        group_finals = []
        for key, scores in (real.get("group_matches") or {}).items():
            if scores and len(scores) >= 2 and " vs " in key:
                h, a = key.split(" vs ")
                group_finals.append((h, a, scores[0], scores[1]))
        for h, a, gh, ga in (finals[-6:] or group_finals[-6:]):
            items.append(
                f'<span class="wc-tick">{flag(h)} {h} '
                f'<span class="score">{gh}–{ga}</span> {a} {flag(a)} '
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
        if hasattr(m.date, "strftime"):
            _has_time = bool(getattr(m.date, "hour", 0) or getattr(m.date, "minute", 0))
            kick = m.date.strftime("%a %d %b · %H:%M h" if _has_time else "%a %d %b").upper()
        else:
            kick = ""
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
# Hero cinematográfico (vídeo de fondo + título superpuesto)
# ============================================================
render_hero()
_global_search()

_ticker_bar()
_next_match_panel()
_header_kpi_bar()
_freshness_bar()
_news_banner()
render_matchday_brief()


# ============================================================
# Navegación lazy: solo se renderiza la pestaña activa.
# Con st.tabs, Streamlit ejecuta el render() de TODAS las pestañas en CADA
# interacción (las oculta por CSS, pero el Python corre entero). Con un
# segmented_control rendereamos únicamente la activa → mucho menos trabajo
# por clic. Bonus: permite deep-links con ?goto= (st.tabs no podía).
# ============================================================
_TABS = [
    ("📊 Predicciones", predicciones.render),
    ("🔥 Actualidad", actualidad.render),
    ("🔮 Partidos", partidos.render),
    ("🏆 Cuadro", cuadro.render),
    ("💰 Mercado", mercado.render),
    ("🌍 Selecciones", selecciones.render),
    ("👥 Plantilla", plantilla.render),
    ("🎯 Mis ajustes", biases.render),
    ("📡 Seguimiento en vivo", seguimiento.render),
    ("📈 Rendimiento del modelo", rendimiento.render),
]
_LABELS = [t[0] for t in _TABS]
_RENDER = dict(_TABS)
_GOTO = {  # claves cortas de ?goto= → etiqueta de pestaña
    "predicciones": _LABELS[0], "actualidad": _LABELS[1], "partidos": _LABELS[2],
    "cuadro": _LABELS[3], "bracket": _LABELS[3], "cruces": _LABELS[3],
    "mercado": _LABELS[4], "cuotas": _LABELS[4], "selecciones": _LABELS[5],
    "plantilla": _LABELS[6], "biases": _LABELS[7], "ajustes": _LABELS[7],
    "seguimiento": _LABELS[8], "rendimiento": _LABELS[9],
}

_NAV_KEY = "active_tab"
_NAV_AREAS = {
    "Mundial": _LABELS[:6],
    "Modelo": [_LABELS[0], _LABELS[4], _LABELS[9]],
    "Mi espacio": [_LABELS[6], _LABELS[7], _LABELS[8]],
}
_AREA_FOR_TAB: dict[str, str] = {}
for _area_name, _area_tabs in _NAV_AREAS.items():
    for _tab_label in _area_tabs:
        # Predicciones pertenece también al área Modelo; en la primera visita
        # priorizamos Mundial para conservar una portada editorial.
        _AREA_FOR_TAB.setdefault(_tab_label, _area_name)
_goto = st.query_params.get("goto")
if _goto and _goto in _GOTO:
    st.session_state[_NAV_KEY] = _GOTO[_goto]
    st.session_state["nav_area"] = _AREA_FOR_TAB[_GOTO[_goto]]
    del st.query_params["goto"]
elif _NAV_KEY not in st.session_state:
    st.session_state[_NAV_KEY] = _LABELS[0]

if "nav_area" not in st.session_state:
    st.session_state["nav_area"] = _AREA_FOR_TAB[st.session_state[_NAV_KEY]]

_area = st.segmented_control(
    "Área", list(_NAV_AREAS), key="nav_area", label_visibility="collapsed",
)
_area = _area or st.session_state["nav_area"]
_area_labels = _NAV_AREAS[_area]
if st.session_state[_NAV_KEY] not in _area_labels:
    st.session_state[_NAV_KEY] = _area_labels[0]

_active = st.segmented_control(
    "Navegación", _area_labels, key=_NAV_KEY, label_visibility="collapsed",
)
_RENDER.get(_active or st.session_state[_NAV_KEY], predicciones.render)()
