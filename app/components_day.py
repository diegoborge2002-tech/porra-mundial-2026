"""Componentes UI específicos del 'Día de partido' y widget en-vivo."""
from __future__ import annotations
import streamlit as st

from app.styles import PRIMARY, ACCENT, BG_CARD, TEXT, TEXT_DIM, GOOD, DANGER
from src.data.team_profile import ISO_CODES, build_profile
from src.data.venues import VENUE_ALTITUDE
from src.data.squad import load_squad
from src.data.h2h import get_h2h
from src.model.match_day import UpcomingMatch, time_to_kickoff
from src.model.match_probs import live_outcome_probs


def _flag(team: str, size: int = 30) -> str:
    iso = ISO_CODES.get(team, "un")
    return (f'<img src="https://flagcdn.com/w80/{iso}.png" '
            f'style="width:{size}px;height:{int(size*0.75)}px;border-radius:3px;'
            f'object-fit:cover;vertical-align:middle;">')


def render_upcoming_card(m: UpcomingMatch, idx: int = 0):
    """Render de una tarjeta de partido próximo (hero card)."""
    ttk = time_to_kickoff(m.date)
    if m.is_played and m.home_score is not None:
        kick_label = f'<span style="color:{GOOD}; font-weight:700;">FINAL · {m.home_score}-{m.away_score}</span>'
    elif ttk["negative"]:
        kick_label = f'<span style="color:{ACCENT}; font-weight:700;">EN JUEGO o RECIENTE</span>'
    elif ttk["days"] == 0:
        kick_label = (f'<span style="color:{PRIMARY}; font-weight:700;">'
                       f'⏱ HOY · {m.date.strftime("%H:%M")}h'
                       f'</span>')
    elif ttk["days"] == 1:
        kick_label = f'<span style="color:{ACCENT}; font-weight:700;">⏱ Mañana</span>'
    else:
        kick_label = f'<span style="color:{TEXT_DIM}; font-weight:600;">En {ttk["days"]}d</span>'

    alt_badge = ""
    if m.altitude and m.altitude > 1500:
        alt_badge = (f'<span style="color:{ACCENT};font-size:0.72rem;margin-left:8px;">'
                     f'⛰ {m.altitude}m</span>')

    venue = f"📍 {m.city}" if m.city else ""
    group_badge = (f'<span style="background:#1f2937;color:{TEXT_DIM};font-size:0.7rem;'
                   f'padding:2px 8px;border-radius:4px;margin-left:8px;">Grupo {m.group}</span>'
                   if m.group in "ABCDEFGHIJKL" else "")

    # Cabecera de la card
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg, rgba(16,185,129,0.04) 0%, rgba(245,158,11,0.04) 100%);
                    border:1px solid rgba(16,185,129,0.25); border-radius:14px; padding:18px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div style="font-size:0.78rem; color:{TEXT_DIM};">
                    {venue}{alt_badge}{group_badge}
                </div>
                <div>{kick_label}</div>
            </div>
            <div style="display:flex; align-items:center; justify-content:center; gap:24px; margin:14px 0;">
                <div style="display:flex; flex-direction:column; align-items:center; min-width:120px;">
                    {_flag(m.home, 56)}
                    <div style="margin-top:6px; font-weight:700; font-size:1.05rem; text-align:center;">{m.home}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:2.2rem; font-weight:800; color:{PRIMARY};">vs</div>
                    <div style="font-size:0.72rem; color:{TEXT_DIM}; margin-top:4px;">
                        λ {m.lambda_home:.2f} – {m.lambda_away:.2f}
                    </div>
                </div>
                <div style="display:flex; flex-direction:column; align-items:center; min-width:120px;">
                    {_flag(m.away, 56)}
                    <div style="margin-top:6px; font-weight:700; font-size:1.05rem; text-align:center;">{m.away}</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Barra 1X2
    p_h, p_d, p_a = m.p_home, m.p_draw, m.p_away
    st.markdown(
        f"""
            <div style="display:flex; height:32px; border-radius:8px; overflow:hidden; margin-top:6px;">
                <div style="width:{p_h*100}%; background:{PRIMARY}; display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:0.85rem;">
                    {p_h*100:.0f}%
                </div>
                <div style="width:{p_d*100}%; background:#4b5563; display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:0.85rem;">
                    {p_d*100:.0f}%
                </div>
                <div style="width:{p_a*100}%; background:{ACCENT}; display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:0.85rem;">
                    {p_a*100:.0f}%
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:{TEXT_DIM}; margin-top:4px;">
                <span>V {m.home}</span><span>Empate</span><span>V {m.away}</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Top marcadores
    score_html = '<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; justify-content:center;">'
    for (h, a), p in m.top_scores[:5]:
        score_html += (
            f'<div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:8px; padding:6px 10px; min-width:78px; text-align:center;">'
            f'<div style="font-size:1.05rem; font-weight:800; color:{TEXT};">{h}-{a}</div>'
            f'<div style="font-size:0.72rem; color:{PRIMARY}; font-weight:600;">{p*100:.1f}%</div>'
            f'</div>'
        )
    score_html += "</div>"
    st.markdown(score_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _form_pills_html(streak: str) -> str:
    """Render WDL pills compactos."""
    if not streak:
        return f'<span style="color:{TEXT_DIM}; font-size:0.78rem;">sin histórico</span>'
    pills = []
    for c in streak[-5:]:
        color = GOOD if c == "W" else (DANGER if c == "L" else "#6b7280")
        pills.append(
            f'<span style="display:inline-flex;width:18px;height:18px;border-radius:4px;'
            f'background:{color};color:#fff;align-items:center;justify-content:center;'
            f'font-size:0.65rem;font-weight:800;margin-right:3px;">{c}</span>'
        )
    return "".join(pills)


def render_pre_match_extras(home: str, away: str) -> None:
    """Bloque adicional bajo la card: forma reciente, h2h breve, top forma jugadores.

    Diseñado para llamarse justo después de `render_upcoming_card` cuando faltan <24h.
    """
    try:
        prof_h = build_profile(home, "?", 1500.0)
        prof_a = build_profile(away, "?", 1500.0)
    except Exception:
        return

    home_squad = load_squad(home)
    away_squad = load_squad(away)

    # H2H histórico
    try:
        h2h = get_h2h(home, away, max_recent=10)
        h2h_html = (
            f'<div style="display:flex;justify-content:space-around;align-items:center;'
            f'background:rgba(15,23,42,0.4);border:1px solid rgba(255,255,255,0.04);'
            f'border-radius:10px;padding:10px;font-size:0.85rem;">'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.2rem;font-weight:800;color:{PRIMARY};">{h2h.wins_a}</div>'
            f'<div style="font-size:0.7rem;color:{TEXT_DIM};">V {home}</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.2rem;font-weight:800;color:{TEXT_DIM};">{h2h.draws}</div>'
            f'<div style="font-size:0.7rem;color:{TEXT_DIM};">Empates</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.2rem;font-weight:800;color:{ACCENT};">{h2h.wins_b}</div>'
            f'<div style="font-size:0.7rem;color:{TEXT_DIM};">V {away}</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.2rem;font-weight:800;color:{TEXT};">{h2h.total}</div>'
            f'<div style="font-size:0.7rem;color:{TEXT_DIM};">Partidos</div></div>'
            f'</div>'
        )
    except Exception:
        h2h_html = ""

    # Top 3 jugadores en forma de cada equipo
    def _top_form(squad):
        if not squad.players:
            return []
        return sorted(squad.players,
                      key=lambda p: -(p.recent_form or 0))[:3]

    def _format_player_list(players):
        if not players:
            return f'<span style="color:{TEXT_DIM};font-size:0.78rem;">Sin datos de plantilla.</span>'
        rows = []
        for p in players:
            f = p.recent_form or 6.0
            color = GOOD if f >= 7.5 else (ACCENT if f >= 6.5 else TEXT_DIM)
            rows.append(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:3px 0;font-size:0.82rem;">'
                f'<span style="color:{TEXT};font-weight:600;">{p.name}</span>'
                f'<span style="color:{color};font-weight:800;">{f:.1f}</span></div>'
            )
        return "".join(rows)

    top_h = _top_form(home_squad)
    top_a = _top_form(away_squad)

    streak_h_html = _form_pills_html(getattr(prof_h, "form_streak", ""))
    streak_a_html = _form_pills_html(getattr(prof_a, "form_streak", ""))

    st.markdown(
        f"""
        <div style="background:rgba(15,23,42,0.35); border:1px solid rgba(255,255,255,0.04);
                    border-radius:12px; padding:14px; margin-top:-10px; margin-bottom:14px;">
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:14px;">
                <div>
                    <div style="font-size:0.72rem; color:{TEXT_DIM}; text-transform:uppercase;
                                letter-spacing:0.08em; font-weight:700; margin-bottom:8px;">
                        Forma últimos 5
                    </div>
                    <div style="margin-bottom:6px; font-size:0.82rem; color:{TEXT};">
                        <span style="font-weight:700;">{home}:</span> {streak_h_html}
                    </div>
                    <div style="font-size:0.82rem; color:{TEXT};">
                        <span style="font-weight:700;">{away}:</span> {streak_a_html}
                    </div>
                </div>
                <div>
                    <div style="font-size:0.72rem; color:{TEXT_DIM}; text-transform:uppercase;
                                letter-spacing:0.08em; font-weight:700; margin-bottom:8px;">
                        Histórico H2H
                    </div>
                    {h2h_html}
                </div>
                <div>
                    <div style="font-size:0.72rem; color:{TEXT_DIM}; text-transform:uppercase;
                                letter-spacing:0.08em; font-weight:700; margin-bottom:8px;">
                        🔥 En forma
                    </div>
                    <div style="font-size:0.7rem; color:{PRIMARY}; font-weight:700;
                                margin-bottom:3px;">{home}</div>
                    {_format_player_list(top_h)}
                    <div style="font-size:0.7rem; color:{ACCENT}; font-weight:700;
                                margin:6px 0 3px 0;">{away}</div>
                    {_format_player_list(top_a)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_widget(default_home: str = "", default_away: str = "",
                       default_lh: float = 1.5, default_la: float = 1.5,
                       key_prefix: str = "live"):
    """Widget para introducir minuto + marcador y ver probas en vivo.

    Si se le pasan default_home/default_away se usan como etiquetas; las
    lambdas iniciales suelen venir del modelo pre-partido del propio partido.
    """
    st.markdown("##### Probabilidades en vivo")
    st.caption("Introduce el minuto actual y el marcador para recalcular probabilidades de victoria/empate/derrota con el tiempo restante.")

    c1, c2, c3 = st.columns(3)
    with c1:
        minute = st.slider("Minuto", 0, 90, 45, step=1, key=f"{key_prefix}_min")
    with c2:
        h_score = st.number_input(f"Goles {default_home or 'local'}", 0, 15, 0, 1,
                                   key=f"{key_prefix}_hg")
    with c3:
        a_score = st.number_input(f"Goles {default_away or 'visitante'}", 0, 15, 0, 1,
                                   key=f"{key_prefix}_ag")

    live = live_outcome_probs(default_lh, default_la, minute, int(h_score), int(a_score))
    p_h, p_d, p_a = live["p_home"], live["p_draw"], live["p_away"]

    # Hero KPIs
    ch, cd, ca = st.columns(3)
    with ch:
        st.markdown(
            f'<div style="text-align:center; padding:14px; background:{BG_CARD}; border:1px solid #1f2937; border-radius:10px;">'
            f'<div style="font-size:0.78rem; color:{TEXT_DIM};">VICTORIA {default_home or "LOCAL"}</div>'
            f'<div style="font-size:2.2rem; font-weight:800; color:{PRIMARY};">{p_h*100:.0f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cd:
        st.markdown(
            f'<div style="text-align:center; padding:14px; background:{BG_CARD}; border:1px solid #1f2937; border-radius:10px;">'
            f'<div style="font-size:0.78rem; color:{TEXT_DIM};">EMPATE</div>'
            f'<div style="font-size:2.2rem; font-weight:800; color:{TEXT};">{p_d*100:.0f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with ca:
        st.markdown(
            f'<div style="text-align:center; padding:14px; background:{BG_CARD}; border:1px solid #1f2937; border-radius:10px;">'
            f'<div style="font-size:0.78rem; color:{TEXT_DIM};">VICTORIA {default_away or "VISITANTE"}</div>'
            f'<div style="font-size:2.2rem; font-weight:800; color:{ACCENT};">{p_a*100:.0f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Marcador final más probable
    st.markdown("###### Marcadores finales más probables")
    score_html = '<div style="display:flex; gap:8px; margin-top:6px; flex-wrap:wrap;">'
    for (h, a), p in live["top_final_scores"][:5]:
        score_html += (
            f'<div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:8px; padding:6px 10px; min-width:78px; text-align:center;">'
            f'<div style="font-size:1.05rem; font-weight:800; color:{TEXT};">{h}-{a}</div>'
            f'<div style="font-size:0.72rem; color:{PRIMARY}; font-weight:600;">{p*100:.1f}%</div>'
            f'</div>'
        )
    score_html += "</div>"
    st.markdown(score_html, unsafe_allow_html=True)

    st.caption(
        f"⏱ {live['remaining_minutes']} min restantes · "
        f"λ restante {live['lambda_home_remaining']:.2f}/{live['lambda_away_remaining']:.2f} · "
        f"goles esperados finales {live['expected_final_home']:.2f}/{live['expected_final_away']:.2f}"
    )
