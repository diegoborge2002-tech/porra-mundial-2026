"""Pestaña '🔥 Actualidad': el pulso del Mundial, al día.

Mezcla datos externos cotejados por web (goleadores, MVP) con bloques derivados
automáticamente de los resultados (en forma, movimientos de la porra, titulares
y clasificaciones). Todo se refresca en cada 'actualiza'.
"""
from __future__ import annotations

import streamlit as st

from app.utils import get_elo_with_biases, load_real_results
from app.styles import PRIMARY, ACCENT, TEXT_DIM, BG_CARD, GOOD, DANGER, TERTIARY
from src.data.team_profile import ISO_CODES
from src.data.actualidad import (
    load_actualidad, top_scorers, recent_mvps, form_table,
    champion_movers, auto_storylines, group_standings,
)


def _flag(team: str, w: int = 20) -> str:
    iso = ISO_CODES.get(team, "un")
    return (f'<img src="https://flagcdn.com/w{w*2}/{iso}.png" '
            f'style="width:{w}px;height:{round(w*0.7)}px;border-radius:2px;'
            f'vertical-align:middle;object-fit:cover;">')


def _card_open(title: str) -> str:
    return (f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:14px;'
            f'padding:14px 16px;margin-bottom:14px;height:100%;">'
            f'<div style="font-weight:700;font-size:1.02rem;margin-bottom:10px;">{title}</div>')


def _render_scorers() -> None:
    scorers = top_scorers(15)
    rows = [_card_open("🥇 Bota de Oro · máximos goleadores")]
    if not scorers:
        rows.append(f'<div style="color:{TEXT_DIM};">Sin goleadores registrados todavía.</div>')
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    # ranking por goles: el puesto lo marca el nº de goles, no el índice
    last_goals, rank = None, 0
    for i, s in enumerate(scorers):
        if s["goals"] != last_goals:
            rank = i + 1
            last_goals = s["goals"]
        badge = medals.get(rank - 1, f'<span style="color:{TEXT_DIM};">{rank}.</span>') if rank <= 3 else f'<span style="color:{TEXT_DIM};">{rank}.</span>'
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<span style="width:24px;text-align:center;">{badge}</span>'
            f'{_flag(s["team"])}'
            f'<span style="flex:1;font-weight:600;">{s["player"]}</span>'
            f'<span style="color:{TEXT_DIM};font-size:0.8rem;">{s["team"]}</span>'
            f'<span style="font-weight:800;color:{PRIMARY};min-width:42px;text-align:right;">{s["goals"]} ⚽</span>'
            f'</div>'
        )
    rows.append("</div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def _render_mvps() -> None:
    mvps = recent_mvps(8)
    rows = [_card_open("🏅 Jugador del partido")]
    if not mvps:
        rows.append(f'<div style="color:{TEXT_DIM};">Sin MVPs registrados todavía.</div>')
    for m in mvps:
        note = f'<div style="color:{TEXT_DIM};font-size:0.74rem;margin-top:1px;">{m["note"]}</div>' if m.get("note") else ""
        rows.append(
            f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'{_flag(m["team"])}'
            f'<span style="font-weight:700;color:{ACCENT};">{m["player"]}</span></div>'
            f'<div style="color:{TEXT_DIM};font-size:0.78rem;">{m.get("match","")}</div>'
            f'{note}</div>'
        )
    rows.append("</div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def _form_col(title: str, rows_data: list[dict], color: str, sign: str) -> str:
    html = [f'<div style="font-weight:700;margin-bottom:6px;">{title}</div>']
    for r in rows_data:
        html.append(
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
            f'{_flag(r["team"])}'
            f'<span style="flex:1;font-weight:600;">{r["team"]}</span>'
            f'<span style="color:{TEXT_DIM};font-size:0.76rem;">{r["points"]} pts (esp {r["expected"]:.1f})</span>'
            f'<span style="font-weight:800;color:{color};min-width:46px;text-align:right;">{sign}{abs(r["delta"]):.1f}</span>'
            f'</div>'
        )
    return "".join(html)


def _render_form(elo: dict, real: dict) -> None:
    ft = form_table(elo, real, limit=5)
    if not ft["risers"]:
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:6px 0 8px;">🔥 Estado de forma '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· rendimiento real vs esperado por el modelo</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_card_open("") + _form_col("📈 Sobre lo esperado", ft["risers"], GOOD, "+") + "</div>",
                    unsafe_allow_html=True)
    with c2:
        st.markdown(_card_open("") + _form_col("📉 Por debajo", [r for r in ft["fallers"] if r["delta"] < 0][:5], DANGER, "−") + "</div>",
                    unsafe_allow_html=True)


def _render_movers() -> None:
    cm = champion_movers(limit=5)
    if not cm or (not cm["up"] and not cm["down"]):
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:6px 0 8px;">📈 Movimientos de la porra '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· prob. de campeón, {cm["date_prev"]} → {cm["date_now"]}</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)

    def block(title, items, color, arrow):
        html = [_card_open(title)]
        for t, p, d in items:
            html.append(
                f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
                f'{_flag(t)}<span style="flex:1;font-weight:600;">{t}</span>'
                f'<span style="color:{TEXT_DIM};font-size:0.78rem;">{p*100:.1f}%</span>'
                f'<span style="font-weight:800;color:{color};min-width:54px;text-align:right;">{arrow}{abs(d)*100:.1f}pp</span></div>'
            )
        html.append("</div>")
        return "".join(html)

    with c1:
        st.markdown(block("⬆️ Suben", cm["up"], GOOD, "▲ "), unsafe_allow_html=True)
    with c2:
        st.markdown(block("⬇️ Bajan", cm["down"], DANGER, "▼ "), unsafe_allow_html=True)


def _render_storylines(elo: dict, real: dict) -> None:
    items = auto_storylines(elo, real, limit=6)
    news = []
    try:
        from src.data.news import list_news, NEWS_TYPES
        for n in list_news(only_active=True)[:4]:
            emoji, _ = NEWS_TYPES.get(n.tipo, ("📰", "Otro"))
            news.append((emoji, f"{n.equipo}: {n.texto}"))
    except Exception:
        pass
    if not items and not news:
        return
    rows = [_card_open("📰 Titulares de la jornada")]
    for it in items:
        rows.append(f'<div style="padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                    f'<span style="margin-right:6px;">{it["emoji"]}</span>{it["text"]}</div>')
    for emoji, txt in news:
        rows.append(f'<div style="padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                    f'<span style="margin-right:6px;">{emoji}</span>{txt}</div>')
    rows.append("</div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def _render_standings(elo: dict, real: dict) -> None:
    gs = group_standings(real, elo)
    # solo mostrar si hay algún partido jugado
    if not any(t["played"] for g in gs.values() for t in g):
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:14px 0 8px;">📊 Clasificaciones '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· verde = puestos de clasificación (top 2)</span></div>',
        unsafe_allow_html=True,
    )
    groups = list(gs.keys())
    for i in range(0, len(groups), 3):
        cols = st.columns(3)
        for col, g in zip(cols, groups[i:i + 3]):
            html = [f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:12px;padding:10px 12px;margin-bottom:12px;">'
                    f'<div style="font-weight:800;color:{PRIMARY};margin-bottom:6px;">Grupo {g}</div>']
            for pos, t in enumerate(gs[g]):
                qual = TERTIARY if pos < 2 else TEXT_DIM
                html.append(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:2px 0;font-size:0.82rem;">'
                    f'<span style="width:14px;color:{qual};font-weight:700;">{pos+1}</span>'
                    f'{_flag(t["team"], 16)}'
                    f'<span style="flex:1;">{t["team"]}</span>'
                    f'<span style="color:{TEXT_DIM};font-size:0.72rem;width:58px;text-align:right;">'
                    f'{t["played"]}PJ {t["gd"]:+d}</span>'
                    f'<span style="font-weight:800;width:24px;text-align:right;">{t["points"]}</span></div>'
                )
            html.append("</div>")
            col.markdown("".join(html), unsafe_allow_html=True)


def render():
    st.header("🔥 Actualidad · Pulso del Mundial")
    data = load_actualidad()
    updated = data.get("updated", "")
    st.caption(
        "Lo que está pasando en el Mundial, de un vistazo. Goleadores y MVP cotejados por "
        f"web{' (act. ' + updated + ')' if updated else ''}; el resto se calcula solo desde los resultados."
    )

    elo = get_elo_with_biases()
    real = load_real_results()

    c1, c2 = st.columns([3, 2])
    with c1:
        _render_scorers()
    with c2:
        _render_mvps()

    _render_form(elo, real)
    _render_movers()
    _render_storylines(elo, real)
    _render_standings(elo, real)
