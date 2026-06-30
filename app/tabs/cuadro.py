"""Pestaña '🏆 Cuadro': el árbol de eliminatorias (Dieciseisavos → Final).

Se rellena solo desde `real_results.json`: los cruces de R32 se resuelven de las
clasificaciones reales y los ganadores se propagan por las rondas. Los partidos
por jugar con ambos equipos definidos muestran el marcador esperado del ensemble.
No hay que tocar código: registrar los KO con `scripts/dia.py ko ...` basta.
"""
from __future__ import annotations

import streamlit as st

from app.utils import get_elo_with_biases, load_real_results
from app.styles import PRIMARY, ACCENT, TEXT_DIM, GOOD, DANGER
from src.data.team_profile import ISO_CODES
from src.data.bracket_view import (
    build_bracket, bracket_progress, FEEDERS, ROUND_LABEL,
)

_CSS = f"""
<style>
.bk-scroll {{ overflow-x:auto; padding:6px 2px 16px; }}
.bk-wrap {{ display:flex; align-items:stretch; gap:10px; min-width:1180px; }}
.bk-side {{ display:flex; gap:10px; flex:1; }}
.bk-col {{ display:flex; flex-direction:column; flex:1; min-width:128px; }}
.bk-col-body {{ flex:1; display:flex; flex-direction:column;
               justify-content:space-around; gap:8px; }}
.bk-col-h {{ font-size:0.62rem; font-weight:800; letter-spacing:.06em;
            color:{TEXT_DIM}; text-transform:uppercase; text-align:center;
            margin-bottom:6px; height:14px; }}
.bk-m {{ background:#11161f; border:1px solid #1f2937; border-radius:9px;
        padding:5px 7px; }}
.bk-m.exp {{ border-style:dashed; border-color:#26304a; }}
.bk-m.tbd {{ opacity:.5; }}
.bk-id {{ font-size:0.56rem; color:{TEXT_DIM}; font-weight:700;
         letter-spacing:.03em; margin-bottom:3px; display:flex;
         justify-content:space-between; }}
.bk-tag {{ color:#5a6577; }}
.bk-tm {{ display:flex; align-items:center; gap:6px; padding:2px 0; }}
.bk-tm .fl {{ width:18px; height:13px; border-radius:2px; object-fit:cover;
             box-shadow:0 1px 2px rgba(0,0,0,.4); flex:none; }}
.bk-tm .nm {{ flex:1; font-size:0.8rem; font-weight:600; white-space:nowrap;
             overflow:hidden; text-overflow:ellipsis; }}
.bk-tm .sc {{ font-weight:800; font-size:0.84rem; min-width:16px; text-align:right; }}
.bk-tm.win .nm {{ color:#eafff5; }}
.bk-tm.win .sc {{ color:{GOOD}; }}
.bk-tm.lose .nm {{ color:#6b7585; }}
.bk-tm.lose .sc {{ color:#6b7585; }}
.bk-tm.fav .nm {{ color:{PRIMARY}; }}
.bk-tm .sc.dim {{ color:#566; font-weight:700; }}
.bk-tm.tbdrow .nm {{ color:#5a6577; font-weight:500; font-style:italic; font-size:0.74rem; }}
.bk-final-card {{ background:linear-gradient(160deg,#1b2333,#11161f);
                 border:1px solid {PRIMARY}; border-radius:12px; padding:10px 12px; }}
.bk-champ {{ text-align:center; margin-top:8px; }}
.bk-champ .lbl {{ font-size:0.62rem; color:{TEXT_DIM}; font-weight:800;
                 letter-spacing:.1em; text-transform:uppercase; }}
.bk-champ .nm {{ font-size:1.05rem; font-weight:900; color:{PRIMARY}; }}
</style>
"""


def _flag(team: str | None) -> str:
    if not team:
        return ""
    iso = ISO_CODES.get(team, "un")
    return f'<img class="fl" loading="lazy" src="https://flagcdn.com/w40/{iso}.png">'


def _team_row(team: str | None, score, cls: str, feeder_id: int | None) -> str:
    if team:
        sc = "" if score is None else f'<span class="sc{" dim" if "exp" in cls else ""}">{score}</span>'
        return (f'<div class="bk-tm {cls}">{_flag(team)}'
                f'<span class="nm">{team}</span>{sc}</div>')
    label = f"Ganador P{feeder_id}" if feeder_id else "Por definir"
    return f'<div class="bk-tm tbdrow"><span class="nm">{label}</span></div>'


def _card(m: dict) -> str:
    fid = m["fifa_id"]
    rnd = m["round"]
    feeders = FEEDERS.get(rnd, {}).get(fid, (None, None))

    if m["played"]:
        w = m["winner"]
        h_cls = "win" if m["home"] == w else "lose"
        a_cls = "win" if m["away"] == w else "lose"
        tag = "pen." if m["pens"] else "✓"
        body = (_team_row(m["home"], m["home_goals"], h_cls, feeders[0])
                + _team_row(m["away"], m["away_goals"], a_cls, feeders[1]))
        cls = "played"
    elif m["expected"]:
        e = m["expected"]
        h_fav = e["p_home"] >= e["p_away"]
        body = (_team_row(m["home"], e["exp_home"], "fav exp" if h_fav else "exp", feeders[0])
                + _team_row(m["away"], e["exp_away"], "exp" if h_fav else "fav exp", feeders[1]))
        tag = "esperado"
        cls = "exp"
    else:
        body = (_team_row(m["home"], None, "", feeders[0])
                + _team_row(m["away"], None, "", feeders[1]))
        tag = ""
        cls = "tbd"

    idline = (f'<div class="bk-id"><span>P{fid}</span>'
              f'<span class="bk-tag">{tag}</span></div>')
    return f'<div class="bk-m {cls}">{idline}{body}</div>'


def _column(ids: list[int], matches: dict, header: str) -> str:
    cards = "".join(_card(matches[i]) for i in ids)
    return (f'<div class="bk-col"><div class="bk-col-h">{header}</div>'
            f'<div class="bk-col-body">{cards}</div></div>')


def render() -> None:
    st.header("🏆 Cuadro · Eliminatorias")
    elo = get_elo_with_biases()
    real = load_real_results() or {}

    b = build_bracket(real, elo)
    if b is None:
        st.info("El cuadro de cruces se dibuja en cuanto **termine la fase de grupos** "
                "(faltan partidos por registrar). Mientras tanto, mira las clasificaciones "
                "en 🔥 Actualidad.")
        return

    prog = bracket_progress(real)
    pills = []
    for r in ("r32", "r16", "qf", "sf", "final"):
        pl, to = prog["played"][r], prog["totals"][r]
        done = "color:%s;" % GOOD if pl == to and pl > 0 else f"color:{TEXT_DIM};"
        pills.append(
            f'<span style="background:#11161f;border:1px solid #1f2937;border-radius:999px;'
            f'padding:3px 11px;font-size:0.74rem;font-weight:700;{done}">'
            f'{ROUND_LABEL[r]} <b>{pl}/{to}</b></span>')
    st.markdown(
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 4px;">'
        + "".join(pills) + "</div>", unsafe_allow_html=True)
    st.caption("Verde lleno = ganador · raya discontinua = aún por jugar (marcador "
               "esperado del modelo) · *Ganador Pxx* = pendiente del partido anterior. "
               "Se actualiza solo con cada resultado que registro.")

    L, R = b["layout_left"], b["layout_right"]
    matches = b["matches"]
    final_m = matches[b["final"]]

    # Final (centro)
    final_inner = _card(final_m).replace('class="bk-m', 'class="bk-final-card bk-m')
    champ_html = ""
    if b["champion"]:
        champ_html = (f'<div class="bk-champ"><div class="lbl">🏆 Campeón</div>'
                      f'<div class="nm">{_flag(b["champion"])} {b["champion"]}</div></div>')
    center = (f'<div class="bk-col" style="flex:1.1;min-width:150px;">'
              f'<div class="bk-col-h">Final</div>'
              f'<div class="bk-col-body" style="justify-content:center;">'
              f'{final_inner}{champ_html}</div></div>')

    html = [_CSS, '<div class="bk-scroll"><div class="bk-wrap">']
    # Mitad izquierda: R32 → R16 → QF → SF
    html.append('<div class="bk-side">')
    html.append(_column(L["r32"], matches, "16avos"))
    html.append(_column(L["r16"], matches, "8vos"))
    html.append(_column(L["qf"], matches, "Cuartos"))
    html.append(_column(L["sf"], matches, "Semis"))
    html.append('</div>')
    # Centro
    html.append(center)
    # Mitad derecha: SF → QF → R16 → R32 (espejo)
    html.append('<div class="bk-side">')
    html.append(_column(R["sf"], matches, "Semis"))
    html.append(_column(R["qf"], matches, "Cuartos"))
    html.append(_column(R["r16"], matches, "8vos"))
    html.append(_column(R["r32"], matches, "16avos"))
    html.append('</div>')
    html.append('</div></div>')
    st.markdown("".join(html), unsafe_allow_html=True)
