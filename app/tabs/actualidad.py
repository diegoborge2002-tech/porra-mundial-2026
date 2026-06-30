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
    recent_match_breakdowns, upcoming_watchouts, unavailable_list,
)


def _flag(team: str, w: int = 20) -> str:
    iso = ISO_CODES.get(team, "un")
    # flagcdn solo sirve anchos concretos (20/40/80/160…). Pedimos w40 (nítido en
    # retina) y escalamos por CSS al ancho de display; así nunca pedimos un ancho
    # inválido (p. ej. w32) que devuelve 404 y rompe la bandera.
    return (f'<img src="https://flagcdn.com/w40/{iso}.png" loading="lazy" '
            f'style="width:{w}px;height:{round(w*0.7)}px;border-radius:3px;'
            f'vertical-align:middle;object-fit:cover;box-shadow:0 1px 2px rgba(0,0,0,.4);">')


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


def _team_score_row(b: dict) -> str:
    """Fila con los dos equipos y el marcador, ganador en negrita."""
    h, a, gh, ga = b["home"], b["away"], b["gh"], b["ga"]
    if b.get("winner"):
        h_win, a_win = b["winner"] == h, b["winner"] == a
    else:
        h_win, a_win = gh > ga, ga > gh
    def side(team, win, align):
        col = "#eafff5" if win else TEXT_DIM
        wt = "800" if win else "600"
        order = f'{_flag(team,18)}<span>{team}</span>' if align == "l" else f'<span>{team}</span>{_flag(team,18)}'
        just = "flex-start" if align == "l" else "flex-end"
        return (f'<div style="flex:1;display:flex;align-items:center;gap:6px;justify-content:{just};'
                f'color:{col};font-weight:{wt};font-size:0.86rem;min-width:0;">{order}</div>')
    pen = '<span style="font-size:0.6rem;color:%s;font-weight:700;"> pen</span>' % ACCENT if b.get("pens") else ""
    return (f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
            f'{side(h, h_win, "l")}'
            f'<span style="font-weight:800;font-size:0.95rem;font-variant-numeric:tabular-nums;'
            f'background:#0c1119;border:1px solid #1f2937;border-radius:6px;padding:1px 8px;white-space:nowrap;">{gh}–{ga}{pen}</span>'
            f'{side(a, a_win, "r")}</div>')


def _render_breakdowns(elo: dict, real: dict) -> None:
    bd = recent_match_breakdowns(elo, real, limit=10)
    if not bd:
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:14px 0 8px;">🧮 Resultados al detalle '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· marcador real vs lo que esperaba el modelo</span></div>',
        unsafe_allow_html=True,
    )
    cards = ['<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px;">']
    for b in bd:
        if b["hit"]:
            tag, tcol = "✓ acierto", GOOD
        elif b["surprise"]:
            tag, tcol = "😱 sorpresón", ACCENT
        else:
            tag, tcol = "✗ falló", DANGER
        scorers = ""
        if b.get("scorers"):
            chips = " · ".join(
                f'<span style="white-space:nowrap;">⚽ {g["player"]}'
                + (f' <span style="color:{TEXT_DIM};">{g["minute"]}</span>' if g.get("minute") else "")
                + "</span>"
                for g in b["scorers"])
            scorers = (f'<div style="font-size:0.76rem;margin-top:4px;line-height:1.5;">{chips}</div>')
        mvp = ""
        if b.get("mvp"):
            mvp = (f'<div style="color:{TEXT_DIM};font-size:0.76rem;margin-top:3px;">'
                   f'🏅 <b style="color:{ACCENT};">{b["mvp"]["player"]}</b> · {b["mvp"].get("note","")}</div>')
        cards.append(
            f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:12px;padding:10px 12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">'
            f'<span style="font-size:0.64rem;font-weight:700;letter-spacing:.04em;color:{TEXT_DIM};text-transform:uppercase;">{b["stage"]}</span>'
            f'<span style="font-size:0.7rem;font-weight:800;color:{tcol};">{tag}</span></div>'
            f'{_team_score_row(b)}'
            f'{scorers}'
            f'<div style="color:{TEXT_DIM};font-size:0.76rem;margin-top:4px;">'
            f'Modelo: esperaba <b>{b["exp_home"]}–{b["exp_away"]}</b> · 1X2 '
            f'{b["p_home"]*100:.0f}/{b["p_draw"]*100:.0f}/{b["p_away"]*100:.0f} · Brier {b["brier"]:.2f}</div>'
            f'{mvp}</div>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def _render_upcoming(elo: dict, real: dict) -> None:
    ups = upcoming_watchouts(elo, real, limit=6)
    if not ups:
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:14px 0 8px;">🔭 Lo que viene '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· resultado esperado y a qué tener cuidado</span></div>',
        unsafe_allow_html=True,
    )
    cards = ['<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px;">']
    for u in ups:
        cards.append(
            f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:12px;padding:10px 12px;">'
            f'<div style="font-size:0.64rem;font-weight:700;letter-spacing:.04em;color:{TEXT_DIM};text-transform:uppercase;margin-bottom:4px;">{u.get("stage","")}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="flex:1;display:flex;align-items:center;gap:6px;font-weight:700;font-size:0.86rem;min-width:0;">{_flag(u["home"],18)}<span>{u["home"]}</span></div>'
            f'<span style="font-weight:800;color:{PRIMARY};background:#0c1119;border:1px solid #1f2937;border-radius:6px;padding:1px 8px;">{u["exp_home"]}–{u["exp_away"]}</span>'
            f'<div style="flex:1;display:flex;align-items:center;gap:6px;justify-content:flex-end;font-weight:700;font-size:0.86rem;min-width:0;"><span>{u["away"]}</span>{_flag(u["away"],18)}</div>'
            f'</div>'
            f'<div style="color:{TEXT_DIM};font-size:0.77rem;margin-top:5px;">{u["note"]}</div>'
            f'</div>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def _render_unavailable() -> None:
    rows = unavailable_list()
    if not rows:
        return
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;margin:14px 0 8px;">🚑 Bajas y sancionados '
        f'<span style="color:{TEXT_DIM};font-size:0.8rem;font-weight:500;">· quién no estará</span></div>',
        unsafe_allow_html=True,
    )
    cards = ['<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;">']
    for r in rows:
        reason = r.get("reason", "")
        rcol = DANGER if "esion" in reason or "Lesi" in reason else ACCENT
        cards.append(
            f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:11px;padding:9px 11px;'
            f'display:flex;align-items:center;gap:9px;">'
            f'{_flag(r["team"], 20)}'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-weight:700;font-size:0.86rem;">{r["player"]} '
            f'<span style="color:{TEXT_DIM};font-size:0.74rem;font-weight:500;">· {r["team"]}</span></div>'
            f'<div style="color:{TEXT_DIM};font-size:0.74rem;">{r.get("detail","")}</div></div>'
            f'<span style="font-size:0.64rem;font-weight:800;color:{rcol};text-transform:uppercase;'
            f'white-space:nowrap;">{reason}</span></div>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


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
            html = [f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:12px;padding:11px 13px;margin-bottom:12px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px;">'
                    f'<span style="font-weight:800;color:{PRIMARY};">Grupo {g}</span>'
                    f'<span style="font-size:0.62rem;color:{TEXT_DIM};font-weight:600;letter-spacing:.04em;">PJ · DG · PTS</span></div>']
            for pos, t in enumerate(gs[g]):
                top = pos < 2
                badge_bg = TERTIARY if top else "rgba(255,255,255,0.06)"
                badge_col = "#06231c" if top else TEXT_DIM
                rowbg = "background:rgba(78,222,163,0.08);" if top else ""
                html.append(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 5px;margin:1px -5px;border-radius:7px;{rowbg}">'
                    f'<span style="display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;'
                    f'border-radius:50%;background:{badge_bg};color:{badge_col};font-size:0.68rem;font-weight:800;flex:none;">{pos+1}</span>'
                    f'{_flag(t["team"], 18)}'
                    f'<span style="flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:0.84rem;font-weight:600;">{t["team"]}</span>'
                    f'<span style="color:{TEXT_DIM};font-size:0.7rem;font-variant-numeric:tabular-nums;flex:none;">{t["played"]}</span>'
                    f'<span style="color:{TEXT_DIM};font-size:0.7rem;width:24px;text-align:right;font-variant-numeric:tabular-nums;flex:none;">{t["gd"]:+d}</span>'
                    f'<span style="font-weight:800;width:18px;text-align:right;color:{PRIMARY};font-variant-numeric:tabular-nums;flex:none;">{t["points"]}</span></div>'
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
    _render_breakdowns(elo, real)
    _render_upcoming(elo, real)
    _render_unavailable()
    _render_storylines(elo, real)
    _render_standings(elo, real)
