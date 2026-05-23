"""Pestaña 'Comparador': vista lado a lado de 2-3 selecciones."""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go

from app.utils import get_elo_with_biases, load_base_elo, run_simulation_with_real, load_real_results
from app.styles import PRIMARY, ACCENT, TEXT, TEXT_DIM, BG_CARD, GOOD, DANGER
from app.components import big_stat
from src.data.team_profile import build_profile, ISO_CODES
from src.tournament.groups import GROUPS, ALL_TEAMS
from src.data.h2h import get_h2h
from src.data.squad import load_squad
from src.model.elo import win_draw_loss_probs


PALETTE = [PRIMARY, ACCENT, "#a78bfa"]  # hasta 3 equipos


def render():
    st.header("🆚 Comparador de selecciones")
    st.caption("Elige hasta 3 selecciones y comparalas lado a lado: Elo, forma, camino al título, plantilla.")

    elo = get_elo_with_biases()
    base_elo = load_base_elo()
    summary = run_simulation_with_real(elo, 10_000, seed=42)

    # === Selector múltiple (hasta 3) ===
    teams_to_compare = st.multiselect(
        "Selecciones a comparar (elige 2 o 3)",
        sorted(ALL_TEAMS),
        default=["Espana", "Francia"],
        max_selections=3,
    )
    if len(teams_to_compare) < 2:
        st.info("Elige al menos 2 selecciones para comparar.")
        return

    # === Bloque KPI lado a lado ===
    cols = st.columns(len(teams_to_compare))
    profiles = {}
    for col, team, color in zip(cols, teams_to_compare, PALETTE):
        try:
            group_letter = next(g for g, teams in GROUPS.items() if team in teams)
            profile = build_profile(team, group_letter, base_elo[team])
        except Exception:
            with col:
                st.error(f"No se pudo cargar {team}")
            continue
        profiles[team] = profile
        iso = ISO_CODES.get(team, "un")
        p_camp = summary["champion"].get(team, 0)
        p_r16 = summary["r16"].get(team, 0)
        with col:
            st.markdown(
                f"""
                <div style="background:{BG_CARD}; border:2px solid {color}; border-radius:14px; padding:18px; text-align:center;">
                    <img src="https://flagcdn.com/w160/{iso}.png" style="width:84px; height:60px; border-radius:4px;">
                    <h3 style="margin:8px 0 4px 0;">{team}</h3>
                    <div style="color:{TEXT_DIM}; font-size:0.78rem;">Grupo {profile.group} · {profile.confederation}</div>
                    <div style="margin-top:14px;">
                        <div style="font-size:2.6rem; font-weight:800; color:{color};">{int(elo[team])}</div>
                        <div style="font-size:0.72rem; color:{TEXT_DIM};">Elo actual</div>
                    </div>
                    <div style="margin-top:12px; display:flex; justify-content:center; gap:14px;">
                        <div>
                            <div style="font-weight:700; font-size:1.1rem;">{p_camp*100:.1f}%</div>
                            <div style="font-size:0.7rem; color:{TEXT_DIM};">Campeón</div>
                        </div>
                        <div>
                            <div style="font-weight:700; font-size:1.1rem;">{p_r16*100:.0f}%</div>
                            <div style="font-size:0.7rem; color:{TEXT_DIM};">Octavos</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not profiles:
        return

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Radar chart de probabilidades por ronda ===
    st.subheader("Probabilidad de avance por ronda")
    categories = ["Top 3 grupo", "Top 2 grupo", "Gana grupo",
                   "Octavos", "Cuartos", "Semis", "Final", "Campeón"]
    fig = go.Figure()
    for team, color in zip(teams_to_compare, PALETTE):
        if team not in profiles: continue
        g = next(gr for gr, tt in GROUPS.items() if team in tt)
        values = [
            summary["group_top3"].get(g, {}).get(team, 0) * 100,
            summary["group_top2"].get(g, {}).get(team, 0) * 100,
            summary["group_winner"].get(g, {}).get(team, 0) * 100,
            summary["r16"].get(team, 0) * 100,
            summary["quarter"].get(team, 0) * 100,
            summary["semifinal"].get(team, 0) * 100,
            summary["finalist"].get(team, 0) * 100,
            summary["champion"].get(team, 0) * 100,
        ]
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself", name=team,
            line=dict(color=color, width=2),
            opacity=0.6,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1f2937", color=TEXT),
            angularaxis=dict(gridcolor="#1f2937", color=TEXT),
            bgcolor=BG_CARD,
        ),
        plot_bgcolor=BG_CARD, paper_bgcolor=BG_CARD,
        font=dict(color=TEXT), showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        height=480, margin=dict(l=40, r=40, t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Forma + goles + valor mercado (tabla comparativa) ===
    st.subheader("Forma reciente y valor")
    cmp_cols = st.columns(len(teams_to_compare))
    for col, team, color in zip(cmp_cols, teams_to_compare, PALETTE):
        if team not in profiles: continue
        p = profiles[team]
        squad = load_squad(team)
        total_val = sum(pl.market_value for pl in squad.players if pl.market_value is not None)
        wins = p.form_streak.count("W")
        draws = p.form_streak.count("D")
        losses = p.form_streak.count("L")
        with col:
            st.markdown(
                f"<h5 style='color:{color}; margin-bottom:6px;'>{team}</h5>",
                unsafe_allow_html=True,
            )
            st.markdown(big_stat(f"{wins}-{draws}-{losses}", "V-E-D (últ. 10)"),
                        unsafe_allow_html=True)
            st.markdown(big_stat(f"{p.goals_for_last10}:{p.goals_against_last10}",
                                  "Goles a favor / en contra"), unsafe_allow_html=True)
            st.markdown(big_stat(f"🏆 {p.wc_titles}", "Mundiales"), unsafe_allow_html=True)
            st.markdown(big_stat(f"{total_val:.0f} M€", "Valor plantilla"),
                        unsafe_allow_html=True)
            if squad.star_player:
                st.caption(f"⭐ {squad.star_player}")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === H2H entre cada par (si exactamente 2 o 3) ===
    if len(teams_to_compare) == 2:
        st.subheader("Cara a cara histórico")
        ta, tb = teams_to_compare
        h2h = get_h2h(ta, tb)
        if h2h.total == 0:
            st.info("Sin historial entre ambas.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(big_stat(f"{h2h.total}", "Partidos"), unsafe_allow_html=True)
            c2.markdown(big_stat(f"{h2h.wins_a}", f"V {ta}"), unsafe_allow_html=True)
            c3.markdown(big_stat(f"{h2h.draws}", "Empates"), unsafe_allow_html=True)
            c4.markdown(big_stat(f"{h2h.wins_b}", f"V {tb}"), unsafe_allow_html=True)
            # Predicción si jugaran ahora
            p_h, p_d, p_a = win_draw_loss_probs(elo[ta], elo[tb])
            st.markdown(
                f"<div style='margin-top:10px; padding:14px; background:{BG_CARD}; "
                f"border:1px solid #1f2937; border-radius:10px;'>"
                f"<div style='display:flex; height:28px; border-radius:6px; overflow:hidden;'>"
                f"<div style='width:{p_h*100}%; background:{PRIMARY}; display:flex; align-items:center; justify-content:center; color:white; font-weight:700;'>V {ta} {p_h*100:.0f}%</div>"
                f"<div style='width:{p_d*100}%; background:{TEXT_DIM}; display:flex; align-items:center; justify-content:center; color:white; font-weight:700;'>X {p_d*100:.0f}%</div>"
                f"<div style='width:{p_a*100}%; background:{ACCENT}; display:flex; align-items:center; justify-content:center; color:white; font-weight:700;'>V {tb} {p_a*100:.0f}%</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    elif len(teams_to_compare) == 3:
        st.subheader("Matrix de partidos hipotéticos (sede neutral)")
        teams = teams_to_compare
        st.caption("Probabilidades 1X2 según Elo si se enfrentaran ahora.")
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                ta, tb = teams[i], teams[j]
                p_h, p_d, p_a = win_draw_loss_probs(elo[ta], elo[tb])
                st.markdown(
                    f"<div style='margin:6px 0; padding:10px; background:{BG_CARD}; "
                    f"border:1px solid #1f2937; border-radius:8px;'>"
                    f"<div style='display:flex; justify-content:space-between; font-size:0.85rem; font-weight:600; margin-bottom:6px;'>"
                    f"<span>{ta}</span><span>vs</span><span>{tb}</span></div>"
                    f"<div style='display:flex; height:18px; border-radius:6px; overflow:hidden;'>"
                    f"<div style='width:{p_h*100}%; background:{PRIMARY}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.78rem; font-weight:700;'>{p_h*100:.0f}%</div>"
                    f"<div style='width:{p_d*100}%; background:{TEXT_DIM}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.78rem; font-weight:700;'>{p_d*100:.0f}%</div>"
                    f"<div style='width:{p_a*100}%; background:{ACCENT}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.78rem; font-weight:700;'>{p_a*100:.0f}%</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
