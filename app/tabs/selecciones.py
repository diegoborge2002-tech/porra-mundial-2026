"""Pestana de fichas detalladas por seleccion + editor de plantilla."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from app.utils import get_elo_with_biases, run_simulation_with_real, get_biases, load_base_elo, load_real_results
from app.components import team_header, prob_bar, form_streak, big_stat
from app.styles import PRIMARY, ACCENT, TEXT_DIM, GOOD, DANGER, BG_CARD, TEXT
from src.tournament.groups import GROUPS, HOST_NATIONS
from src.data.team_profile import build_profile, ISO_CODES
from src.data.squad import (
    load_squad, save_squad, squad_completeness, ratings_to_elo_bias,
    Player, POSITIONS, POSITION_LABELS, RATING_AXES,
)
from src.model.schedule_difficulty import compute_schedule_difficulty
from src.data.h2h import get_h2h
from src.data.venues import get_team_schedule, VENUE_ALTITUDE
from src.model.elo import win_draw_loss_probs


def render():
    st.header("Selecciones")
    st.caption("Ficha completa de cada equipo · historico, forma, calendario, plantilla")

    elo = get_elo_with_biases()
    base_elo = load_base_elo()
    cfg = get_biases()
    summary = run_simulation_with_real(elo, 10_000, seed=42)

    # Selector con bandera al lado
    c1, c2 = st.columns([3, 1])
    with c1:
        sorted_teams = []
        for g in sorted(GROUPS):
            for t in GROUPS[g]:
                sorted_teams.append(f"{t}  ·  Grupo {g}")
        # Honra ?team=… del buscador global
        qp_team = st.query_params.get("team", "")
        default_idx = 0
        try:
            if qp_team:
                default_idx = next(i for i, s in enumerate(sorted_teams) if s.startswith(f"{qp_team} "))
            else:
                default_idx = next(i for i, s in enumerate(sorted_teams) if s.startswith("Espana"))
        except StopIteration:
            default_idx = 0
        selected_label = st.selectbox("Equipo", sorted_teams, index=default_idx)
        team_es = selected_label.split("  ·  ")[0]
        # Limpia el query param una vez consumido
        if qp_team and qp_team == team_es:
            try:
                del st.query_params["team"]
            except KeyError:
                pass
    with c2:
        iso = ISO_CODES.get(team_es, "un")
        is_host = team_es in HOST_NATIONS
        host_str = "🏠 Anfitrion" if is_host else ""
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:10px; padding-top:24px;">'
            f'<img src="https://flagcdn.com/w80/{iso}.png" style="width:48px; height:36px; border-radius:3px;">'
            f'<span style="color:{TEXT_DIM};">{host_str}</span></div>',
            unsafe_allow_html=True,
        )

    group = next(g for g, teams in GROUPS.items() if team_es in teams)
    profile = build_profile(team_es, group, base_elo[team_es])
    elo_delta = cfg.get_delta(team_es)

    # ====== HEADER GRANDE ======
    st.markdown(team_header(
        name=profile.name_es,
        flag_url=profile.flag_url,
        group=profile.group,
        confederation=profile.confederation,
        wc_titles=profile.wc_titles,
        elo_base=profile.elo_base,
        elo_delta=elo_delta,
    ), unsafe_allow_html=True)

    # ====== STATS GRANDES ======
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    p_group_winner = summary["group_winner"].get(group, {}).get(team_es, 0)
    p_qualify = summary["group_top3"].get(group, {}).get(team_es, 0)
    p_r16 = summary["r16"].get(team_es, 0)
    p_qf = summary["quarter"].get(team_es, 0)
    p_sf = summary["semifinal"].get(team_es, 0)
    p_f = summary["finalist"].get(team_es, 0)
    p_camp = summary["champion"].get(team_es, 0)

    c1.markdown(big_stat(f"{p_group_winner*100:.0f}%", "Gana grupo"), unsafe_allow_html=True)
    c2.markdown(big_stat(f"{p_r16*100:.0f}%", "Octavos"), unsafe_allow_html=True)
    c3.markdown(big_stat(f"{p_qf*100:.0f}%", "Cuartos"), unsafe_allow_html=True)
    c4.markdown(big_stat(f"{p_sf*100:.0f}%", "Semis"), unsafe_allow_html=True)
    c5.markdown(big_stat(f"{p_f*100:.0f}%", "Final"), unsafe_allow_html=True)
    c6.markdown(big_stat(f"{p_camp*100:.1f}%", "Campeon"), unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ====== TABS DENTRO DE LA FICHA ======
    sub_t1, sub_t2, sub_t3, sub_t4, sub_t5, sub_t6 = st.tabs([
        "📈 Forma y calendario",
        "👥 Plantilla",
        "📋 Informe de Scouting",
        "📊 Comparativa de grupo",
        "🤝 Head-to-Head",
        "🎯 Ajuste de Elo",
    ])

    with sub_t1:
        _render_form_and_calendar(profile, summary, group, p_qualify, p_group_winner,
                                  p_r16, p_qf, p_sf, p_f, p_camp)
        _render_schedule_difficulty(team_es, group, elo, summary)
        _render_path_to_title(team_es, summary)
        _render_logistic_schedule(team_es)
    with sub_t2:
        _render_squad_editor(team_es)
    with sub_t3:
        _render_scouting_report(team_es, elo, cfg)
    with sub_t4:
        _render_group_comparison(team_es, group, elo, summary)
    with sub_t5:
        _render_h2h(team_es, elo)
    with sub_t6:
        _render_quick_bias(team_es, elo_delta, cfg)


def _render_logistic_schedule(team_es: str):
    sched = get_team_schedule(team_es)
    if not sched.matches:
        return
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.subheader("Calendario y logística")
    st.caption("Sede, altitud y días de descanso entre partidos. Calendario oficial del Mundial 2026.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(big_stat(f"{sched.avg_rest:.1f}" if sched.avg_rest else "—",
                              "Descanso medio (días)"), unsafe_allow_html=True)
    with c2:
        st.markdown(big_stat(f"{sched.min_rest}" if sched.min_rest else "—",
                              "Mínimo descanso (días)"), unsafe_allow_html=True)
    with c3:
        st.markdown(big_stat(f"{len(set(sched.cities_visited))}",
                              "Sedes visitadas"), unsafe_allow_html=True)

    for m in sched.matches:
        rest_str = ""
        rest_color = TEXT_DIM
        if m["rest_days_prev"] is not None:
            d = m["rest_days_prev"]
            if d < 3:
                rest_color = DANGER
            elif d <= 4:
                rest_color = ACCENT
            else:
                rest_color = GOOD
            rest_str = f' · <span style="color:{rest_color};">⏱ {d}d</span>'
        alt_str = ""
        if m["altitude"] and m["altitude"] > 1500:
            alt_str = f' · <span style="color:{ACCENT};">⛰ {m["altitude"]}m</span>'
        score_html = (f'<span class="match-score">{m["home_score"]}-{m["away_score"]}</span>'
                      if m["played"] else f'<span class="match-score" style="color:{TEXT_DIM};">—</span>')
        opp = m["opponent"]
        iso = ISO_CODES.get(opp, "un")
        venue = f' 📍 {m["city"]}' if m["city"] else ""
        st.markdown(
            f'<div class="match-row">'
            f'<span class="match-date">{m["date"]}</span>'
            f'<span class="match-teams" style="display:flex;align-items:center;gap:6px;">'
            f'{"vs " if m["is_home"] else "@ "}<img src="https://flagcdn.com/w20/{iso}.png" style="width:16px;height:12px;">'
            f'{opp}<span style="color:{TEXT_DIM}; font-size:0.7rem; margin-left:6px;">{venue}{rest_str}{alt_str}</span>'
            f'</span>'
            f'{score_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_h2h(team_es, elo):
    st.subheader("Comparativa cara a cara (histórica)")
    st.caption("Cualquier seleccion del mundo, no solo del Mundial.")
    # Lista de rivales: todas las del Mundial primero, después el resto del dataset
    from src.data.team_names import ES_TO_EN
    wc_options = sorted([t for t in ES_TO_EN if t != team_es])
    rival = st.selectbox("Rival", wc_options, key=f"h2h_{team_es}")

    h2h = get_h2h(team_es, rival, max_recent=10)

    if h2h.total == 0:
        st.info(f"No hay encuentros históricos entre {team_es} y {rival} en el dataset.")
        return

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(big_stat(f"{h2h.total}", f"Total partidos"), unsafe_allow_html=True)
    c2.markdown(big_stat(f"{h2h.wins_a}-{h2h.draws}-{h2h.wins_b}", f"V-E-D ({team_es})"),
                unsafe_allow_html=True)
    c3.markdown(big_stat(f"{h2h.goals_a}", f"Goles {team_es}"), unsafe_allow_html=True)
    c4.markdown(big_stat(f"{h2h.goals_b}", f"Goles {rival}"), unsafe_allow_html=True)

    if h2h.total > 0:
        win_rate_a = h2h.wins_a / h2h.total
        draw_rate = h2h.draws / h2h.total
        win_rate_b = h2h.wins_b / h2h.total
        st.markdown("##### Reparto histórico")
        bar_html = (
            f'<div style="display:flex; height:28px; border-radius:6px; overflow:hidden;">'
            f'<div style="width:{win_rate_a*100}%; background:{GOOD}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
            f'{team_es}: {win_rate_a*100:.0f}%</div>'
            f'<div style="width:{draw_rate*100}%; background:{TEXT_DIM}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
            f'Empates: {draw_rate*100:.0f}%</div>'
            f'<div style="width:{win_rate_b*100}%; background:{DANGER}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
            f'{rival}: {win_rate_b*100:.0f}%</div>'
            f'</div>'
        )
        st.markdown(bar_html, unsafe_allow_html=True)

    # Predicción si jugaran ahora
    elo_a = elo.get(team_es, 1500.0)
    elo_b = elo.get(rival, 1500.0)
    p_h, p_d, p_a = win_draw_loss_probs(elo_a, elo_b, home_advantage=0.0)
    st.markdown("##### Si jugaran hoy (sede neutral)")
    st.caption(f"Elos actuales: {team_es} {elo_a:.0f} · {rival} {elo_b:.0f}")
    pred_html = (
        f'<div style="display:flex; height:28px; border-radius:6px; overflow:hidden;">'
        f'<div style="width:{p_h*100}%; background:{PRIMARY}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
        f'V {team_es}: {p_h*100:.0f}%</div>'
        f'<div style="width:{p_d*100}%; background:{TEXT_DIM}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
        f'Empate: {p_d*100:.0f}%</div>'
        f'<div style="width:{p_a*100}%; background:{ACCENT}; display:flex; align-items:center; justify-content:center; color:white; font-size:0.85rem; font-weight:700;">'
        f'V {rival}: {p_a*100:.0f}%</div>'
        f'</div>'
    )
    st.markdown(pred_html, unsafe_allow_html=True)

    # Histórico reciente
    st.markdown("##### Últimos cruces")
    for m in h2h.last_matches:
        result_color = GOOD if m.result_for_a == "W" else (DANGER if m.result_for_a == "L" else TEXT_DIM)
        iso_h = ISO_CODES.get(m.home, "un")
        iso_a = ISO_CODES.get(m.away, "un")
        st.markdown(
            f'<div class="match-row">'
            f'<span class="match-date">{m.date}</span>'
            f'<span class="match-teams" style="display:flex;align-items:center;gap:6px;">'
            f'<img src="https://flagcdn.com/w20/{iso_h}.png" style="width:16px;height:12px;border-radius:1px;">'
            f'{m.home} <span style="color:{TEXT_DIM}">vs</span>'
            f'<img src="https://flagcdn.com/w20/{iso_a}.png" style="width:16px;height:12px;border-radius:1px;">'
            f'{m.away}'
            f'<span style="color:{TEXT_DIM}; font-size:0.7rem; margin-left:6px;">{m.tournament}</span></span>'
            f'<span class="match-score" style="color:{result_color}; font-weight:700;">{m.home_goals}-{m.away_goals}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_form_and_calendar(profile, summary, group, p_qualify, p_group_winner,
                              p_r16, p_qf, p_sf, p_f, p_camp):
    left, right = st.columns(2)

    with left:
        st.subheader("Estado de forma")
        st.markdown(f'**Ultimos {len(profile.last_10_matches)} partidos**', unsafe_allow_html=True)
        st.markdown(form_streak(profile.form_streak), unsafe_allow_html=True)

        wins = profile.form_streak.count("W")
        draws = profile.form_streak.count("D")
        losses = profile.form_streak.count("L")
        points = wins * 3 + draws

        ca, cb, cc, cd = st.columns(4)
        ca.markdown(big_stat(f"{wins}", "Victorias"), unsafe_allow_html=True)
        cb.markdown(big_stat(f"{draws}", "Empates"), unsafe_allow_html=True)
        cc.markdown(big_stat(f"{losses}", "Derrotas"), unsafe_allow_html=True)
        cd.markdown(big_stat(f"{points}", "Puntos"), unsafe_allow_html=True)

        ce, cf = st.columns(2)
        ce.markdown(big_stat(profile.goals_for_last10, "Goles a favor"), unsafe_allow_html=True)
        cf.markdown(big_stat(profile.goals_against_last10, "Goles en contra"), unsafe_allow_html=True)

        st.markdown("##### Detalle de los partidos")
        for m in profile.last_10_matches:
            score = f"{m.home_goals}-{m.away_goals}"
            tnt = m.tournament if len(m.tournament) < 30 else m.tournament[:27] + "..."
            iso_h = ISO_CODES.get(m.home, "un")
            iso_a = ISO_CODES.get(m.away, "un")
            st.markdown(
                f'<div class="match-row">'
                f'<span class="match-date">{m.date}</span>'
                f'<span class="match-teams" style="display:flex;align-items:center;gap:6px;">'
                f'<img src="https://flagcdn.com/w20/{iso_h}.png" style="width:16px;height:12px;border-radius:1px;">'
                f'{m.home} <span style="color:{TEXT_DIM}">vs</span>'
                f'<img src="https://flagcdn.com/w20/{iso_a}.png" style="width:16px;height:12px;border-radius:1px;">'
                f'{m.away}'
                f'<span style="color:{TEXT_DIM}; font-size:0.7rem; margin-left:6px;">{tnt}</span></span>'
                f'<span class="match-score">{score}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.subheader("Calendario Mundial 2026")
        if not profile.upcoming_wc_matches:
            st.info("No hay proximos partidos programados.")
        else:
            for m in profile.upcoming_wc_matches:
                iso_h = ISO_CODES.get(m.home, "un")
                iso_a = ISO_CODES.get(m.away, "un")
                st.markdown(
                    f'<div class="match-row">'
                    f'<span class="match-date">{m.date}</span>'
                    f'<span class="match-teams" style="display:flex;align-items:center;gap:6px;">'
                    f'<img src="https://flagcdn.com/w20/{iso_h}.png" style="width:16px;height:12px;border-radius:1px;">'
                    f'{m.home} <span style="color:{TEXT_DIM}">vs</span>'
                    f'<img src="https://flagcdn.com/w20/{iso_a}.png" style="width:16px;height:12px;border-radius:1px;">'
                    f'{m.away}</span>'
                    f'<span class="match-score">-</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.subheader("Camino al titulo")
        st.markdown(prob_bar("Pasa grupo (Top 3)", p_qualify * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("Gana grupo (1.º)", p_group_winner * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("Octavos de final", p_r16 * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("Cuartos de final", p_qf * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("Semifinal", p_sf * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("Final", p_f * 100), unsafe_allow_html=True)
        st.markdown(prob_bar("CAMPEON", p_camp * 100), unsafe_allow_html=True)

        # Distribución de posición final
        fp = summary.get("final_position_by_team", {}).get(profile.name_es, {})
        if fp:
            from app.styles import PRIMARY as _P, ACCENT as _A
            n_sims = sum(fp.values())
            order = ["Campeón", "Subcampeón", "Semis", "Cuartos", "Octavos", "R32", "Fase grupos"]
            colors = ["#fbbf24", "#a78bfa", "#10b981", "#22d3ee", "#60a5fa", "#9ca3af", "#ef4444"]
            st.markdown("##### Distribución de posición final")
            st.caption("Cómo termina este equipo a lo largo de las 10.000 simulaciones.")
            bar_html = '<div style="display:flex; gap:2px; height:24px; border-radius:6px; overflow:hidden; margin-top:8px;">'
            legend = ""
            for label, color in zip(order, colors):
                cnt = fp.get(label, 0)
                pct = (cnt / n_sims) * 100 if n_sims else 0
                if pct >= 0.5:
                    bar_html += (f'<div title="{label}: {pct:.1f}%" '
                                 f'style="width:{pct}%; background:{color};"></div>')
                    legend += (f'<span style="margin-right:14px; font-size:0.75rem;">'
                               f'<span style="display:inline-block;width:10px;height:10px;background:{color};'
                               f'border-radius:2px;margin-right:4px;vertical-align:middle;"></span>'
                               f'{label}: {pct:.1f}%</span>')
            bar_html += "</div>"
            st.markdown(bar_html, unsafe_allow_html=True)
            st.markdown(f'<div style="margin-top:8px;">{legend}</div>', unsafe_allow_html=True)


def _render_path_to_title(team_es: str, summary: dict):
    """Para el equipo seleccionado, distribución de rivales probables por ronda."""
    opp = summary.get("opponent_probs_per_team", {}).get(team_es, {})
    if not opp:
        return
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.subheader("Camino al título probabilístico")
    st.caption(
        "Para cada ronda de eliminatoria, los rivales más probables del equipo según las "
        "10.000 simulaciones de Monte Carlo. La probabilidad incluye el riesgo de no llegar a esa ronda."
    )
    rounds_order = ["R32", "Octavos", "Cuartos", "Semis", "Final"]
    cols = st.columns(len(rounds_order))
    for col, label in zip(cols, rounds_order):
        opponents = opp.get(label, {})
        if not opponents:
            with col:
                st.markdown(
                    f"<div style='text-align:center; padding:10px; color:{TEXT_DIM};'>"
                    f"<div style='font-size:0.78rem; font-weight:700; color:{ACCENT}; "
                    f"text-transform:uppercase; letter-spacing:0.06em;'>{label}</div>"
                    f"<div style='margin-top:8px; font-size:0.85rem;'>— No llega —</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            continue
        sorted_opps = sorted(opponents.items(), key=lambda x: -x[1])[:5]
        total_reaches = sum(opponents.values())
        with col:
            html = (
                f"<div style='background:{BG_CARD}; border:1px solid #1f2937; "
                f"border-radius:10px; padding:10px;'>"
                f"<div style='font-size:0.78rem; font-weight:700; color:{ACCENT}; "
                f"text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px; text-align:center;'>{label}</div>"
                f"<div style='font-size:0.72rem; color:{TEXT_DIM}; text-align:center; margin-bottom:8px;'>"
                f"P(llega) = {total_reaches*100:.0f}%</div>"
            )
            for opp_team, p in sorted_opps:
                iso = ISO_CODES.get(opp_team, "un")
                bar_w = int((p / total_reaches) * 100) if total_reaches > 0 else 0
                html += (
                    f"<div style='display:flex; align-items:center; gap:6px; margin:4px 0; font-size:0.78rem;'>"
                    f"<img src='https://flagcdn.com/w20/{iso}.png' style='width:18px;height:14px;border-radius:1px;'>"
                    f"<span style='flex:1;'>{opp_team}</span>"
                    f"<span style='color:{PRIMARY}; font-weight:700;'>{p*100:.0f}%</span>"
                    f"</div>"
                    f"<div style='background:#1f2937; height:3px; border-radius:2px;'>"
                    f"<div style='width:{bar_w}%; background:{PRIMARY}; height:100%;'></div></div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)


def _render_schedule_difficulty(team_es, group, elo, summary):
    real_results = load_real_results()
    sd = compute_schedule_difficulty(team_es, group, elo, summary, real_results)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.subheader("Dificultad del calendario")
    st.caption("Cuanto mayor el Elo medio de los rivales, más difícil el camino restante.")

    col_g, col_ko = st.columns(2)
    with col_g:
        st.markdown("##### Rivales en grupo")
        for rival, e_rival, is_played in sd.group_opponents:
            iso = ISO_CODES.get(rival, "un")
            badge = "✅ Jugado" if is_played else "🕒 Pendiente"
            badge_color = GOOD if is_played else ACCENT
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:8px; padding:8px 12px; '
                f'background:{BG_CARD}; border:1px solid #1f2937; border-radius:8px; margin-bottom:6px;">'
                f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:24px;height:18px;border-radius:2px;">'
                f'<span style="flex:1; font-weight:600;">{rival}</span>'
                f'<span style="color:{TEXT_DIM}; font-size:0.85rem;">Elo {int(e_rival)}</span>'
                f'<span style="color:{badge_color}; font-size:0.75rem; font-weight:600;">{badge}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        cP, cQ = st.columns(2)
        with cP:
            if sd.mean_elo_played > 0:
                st.markdown(big_stat(f"{sd.mean_elo_played:.0f}", "Elo medio rivales jugados"),
                            unsafe_allow_html=True)
            else:
                st.markdown(big_stat("—", "Elo medio rivales jugados"), unsafe_allow_html=True)
        with cQ:
            if sd.mean_elo_pending > 0:
                st.markdown(big_stat(f"{sd.mean_elo_pending:.0f}", "Elo medio rivales pendientes"),
                            unsafe_allow_html=True)
            else:
                st.markdown(big_stat("—", "Elo medio rivales pendientes"), unsafe_allow_html=True)

    with col_ko:
        st.markdown("##### Posibles rivales en eliminatorias")
        st.caption("Rivales potenciales según probabilidad de llegar a Octavos.")
        for rival, p_r16, e_rival in sd.expected_ko_opponents:
            iso = ISO_CODES.get(rival, "un")
            bar_w = int(p_r16 * 100)
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:8px; padding:6px 10px; '
                f'background:{BG_CARD}; border:1px solid #1f2937; border-radius:8px; margin-bottom:4px;">'
                f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:22px;height:16px;border-radius:2px;">'
                f'<span style="flex:1; font-weight:600; font-size:0.85rem;">{rival}</span>'
                f'<span style="color:{TEXT_DIM}; font-size:0.75rem;">Elo {int(e_rival)}</span>'
                f'<div style="width:60px; background:#1f2937; height:5px; border-radius:3px; overflow:hidden;">'
                f'<div style="width:{bar_w}%; background:{PRIMARY}; height:100%;"></div></div>'
                f'<span style="color:{TEXT_DIM}; font-size:0.75rem; min-width:30px; text-align:right;">{p_r16*100:.0f}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(big_stat(f"{sd.expected_ko_difficulty:.0f}",
                              "Elo esperado del rival en Octavos"),
                    unsafe_allow_html=True)


def _render_group_comparison(team_es, group, elo, summary):
    st.subheader(f"Comparativa Grupo {group}")
    group_data = []
    for t in GROUPS[group]:
        group_data.append({
            "Equipo": t,
            "Elo": int(elo[t]),
            "P(1.º) %": round(summary["group_winner"].get(group, {}).get(t, 0) * 100, 1),
            "P(Top 2) %": round(summary["group_top2"].get(group, {}).get(t, 0) * 100, 1),
            "P(Top 3) %": round(summary["group_top3"].get(group, {}).get(t, 0) * 100, 1),
            "P(Cuartos) %": round(summary["quarter"].get(t, 0) * 100, 1),
            "P(Campeon) %": round(summary["champion"].get(t, 0) * 100, 2),
        })
    df_group = pd.DataFrame(group_data).sort_values("P(Top 3) %", ascending=False)
    def highlight_team(row):
        if row["Equipo"] == team_es:
            return [f"background-color: {PRIMARY}; color: white; font-weight: 700;"] * len(row)
        return [""] * len(row)
    st.dataframe(df_group.style.apply(highlight_team, axis=1),
                 hide_index=True, use_container_width=True)


def _render_quick_bias(team_es, elo_delta, cfg):
    st.subheader("Ajuste rapido de Elo")
    st.caption("Tu intuicion. Se sincroniza con la pestana 'Mis ajustes'.")
    new_delta = st.slider(
        "Ajuste Elo", -150, 150, int(elo_delta), step=5,
        key=f"selecciones_bias_{team_es}",
        help="Cada +50 puntos Elo = +20% probabilidad de ganar partido parejo",
    )
    new_reason = st.text_input(
        "Motivo",
        value=cfg.team_biases.get(team_es).reason if team_es in cfg.team_biases else "",
        key=f"selecciones_reason_{team_es}",
        placeholder="ej. mejor generacion en anios, anfitrion, lesion del capitan...",
    )
    if st.button("Aplicar ajuste"):
        cfg.set_bias(team_es, new_delta, new_reason)
        cfg.save()
        st.success("Aplicado y guardado")
        st.rerun()


def _render_scouting_report(team_es: str, elo: dict[str, float], cfg):
    st.subheader("📋 Informe de Scouting y Táctica")
    st.caption("Análisis estratégico en vivo de la selección, su estilo de juego, racha de rendimiento en clubs y alineación en pizarra.")

    from src.data.squad import load_squad
    squad = load_squad(team_es)
    
    if not squad.players:
        st.info("⚠️ No hay datos de plantilla todavía para generar el informe de scouting. Ve a la pestaña '👥 Plantilla' para añadir jugadores.")
        return

    # Style definitions
    ratings = squad.ratings or {}
    att = ratings.get("attack", 5)
    mid = ratings.get("midfield", 5)
    dfn = ratings.get("defense", 5)
    
    # 1. TACTICAL BANNER
    if mid >= 8:
        style_title = "Tiki-Taka y Posesión Dominante"
        style_desc = "Fútbol asociativo y paciente en zona de gestación. Circulación fluida, achique de espacios altos tras pérdida y control absoluto del ritmo del partido."
        badge_class = "badge-mates"
        badge_label = "📊 Posesión y Control"
        banner_border = PRIMARY
    elif dfn >= 8:
        style_title = "Bloque Defensivo Férreo y Transiciones Directas"
        style_desc = "Repliegue bajo muy coordinado, densidad defensiva en campo propio y contragolpes letales explotando la velocidad de sus extremos."
        badge_class = "badge-mates"
        badge_label = "🛡️ Solidez Defensiva"
        banner_border = "#94a3b8"
    elif att >= 8:
        style_title = "Ataque Vertical y Presión Asfixiante"
        style_desc = "Presión muy alta sobre la salida rival, verticalidad pura y gran acumulación de efectivos ofensivos en el área rival."
        badge_class = "badge-intuicion"
        badge_label = "⚡ Ofensiva Explosiva"
        banner_border = ACCENT
    else:
        style_title = "Fútbol Equilibrado y Adaptabilidad Táctica"
        style_desc = "Estructura flexible de bloque medio. Capacidad de alternar entre control posicional y repliegue estratégico según las fases del encuentro."
        badge_class = "badge-mates"
        badge_label = "⚔️ Táctica Flexible"
        banner_border = GOOD

    # Render Tactical Banner using custom colors
    st.markdown(
        f'<div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 41, 59, 0.3) 100%); '
        f'border-left: 5px solid {banner_border}; border-top: 1px solid rgba(255,255,255,0.03); border-right: 1px solid rgba(255,255,255,0.03); border-bottom: 1px solid rgba(255,255,255,0.03); '
        f'border-radius: 12px; padding: 20px; margin-bottom: 24px;">'
        f'<div class="{badge_class}">{badge_label}</div>'
        f'<h4 style="margin: 0 0 6px 0; color: #ffffff; font-weight: 700; font-size: 1.25rem;">Estilo Predominante: {style_title}</h4>'
        f'<p style="margin: 0; color: {TEXT_DIM}; font-size: 0.88rem; line-height: 1.6;">{style_desc}</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # 2. COLUMNS FOR TACTICAL PILLS & INFO
    c_meta, c_pitch = st.columns([1, 1])

    with c_meta:
        st.markdown(f"<h5 style='color: {PRIMARY}; margin-bottom: 8px;'>📋 Ficha Técnica</h5>", unsafe_allow_html=True)
        # Coach / Captain / Star
        st.markdown(
            f'<div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.02); border-radius: 10px; padding: 12px; margin-bottom: 16px;">'
            f'<div style="font-size: 0.85rem; color: {TEXT_DIM};">Director Técnico</div>'
            f'<div style="font-size: 1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{squad.coach or "No definido"}</div>'
            f'<div style="font-size: 0.85rem; color: {TEXT_DIM};">Capitán</div>'
            f'<div style="font-size: 1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{squad.captain or "No definido"} 👑</div>'
            f'<div style="font-size: 0.85rem; color: {TEXT_DIM};">Jugador Clave / Estrella</div>'
            f'<div style="font-size: 1rem; font-weight: 700; color: #ffffff;">{squad.star_player or "No definido"} ⭐</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Strengths & Weaknesses (Pros y Contras)
        st.markdown(f"<h5 style='color: {ACCENT}; margin-bottom: 8px;'>🔍 Análisis FODA</h5>", unsafe_allow_html=True)
        
        pros = []
        contras = []
        
        if att >= 8:
            pros.append("Ataque élite con gran pegada.")
        elif att <= 5:
            contras.append("Falta de gol y colmillos ofensivos.")
            
        if dfn >= 8:
            pros.append("Defensa muy consolidada y difícil de batir.")
        elif dfn <= 5:
            contras.append("Vulnerable defensivamente en transiciones rápidas.")
            
        if mid >= 8:
            pros.append("Centro del campo de clase mundial para controlar posesión.")
        elif mid <= 5:
            contras.append("Dificultad en la salida de balón y pérdidas peligrosas.")
            
        if ratings.get("bench_depth", 5) >= 8:
            pros.append("Excelente banquillo con profundidad y variantes.")
        elif ratings.get("bench_depth", 5) <= 5:
            contras.append("Plantilla corta, alta dependencia del once inicial.")
            
        if ratings.get("experience", 5) >= 8:
            pros.append("Gran oficio y experiencia en citas internacionales clave.")
        elif ratings.get("experience", 5) <= 5:
            contras.append("Falta de experiencia competitiva en escenarios de alta presión.")
            
        if ratings.get("motivation", 5) >= 8:
            pros.append("Gran química grupal y moral extremadamente alta.")

        # Default fallback
        if not pros:
            pros.append("Bloque equilibrado con solidez general en todas sus líneas.")
        if not contras:
            contras.append("Sin vulnerabilidades críticas obvias a nivel estadístico.")

        pro_list_html = "".join([f'<li style="color: #ffffff; font-size: 0.85rem; margin-bottom: 6px;">🟢 {p}</li>' for p in pros])
        contra_list_html = "".join([f'<li style="color: #ffffff; font-size: 0.85rem; margin-bottom: 6px;">🔴 {c}</li>' for c in contras])

        st.markdown(
            f'<div style="background: rgba(15, 23, 42, 0.3); border: 1px solid rgba(255,255,255,0.02); border-radius: 10px; padding: 14px; margin-bottom: 16px;">'
            f'<div style="font-weight: 700; font-size: 0.85rem; color: {GOOD}; text-transform: uppercase; margin-bottom: 6px;">Fortalezas (Puntos Fuertes)</div>'
            f'<ul style="margin: 0 0 12px 0; padding-left: 12px; list-style-type: none;">{pro_list_html}</ul>'
            f'<div style="font-weight: 700; font-size: 0.85rem; color: {DANGER}; text-transform: uppercase; margin-bottom: 6px;">Debilidades (Vulnerabilidades)</div>'
            f'<ul style="margin: 0; padding-left: 12px; list-style-type: none;">{contra_list_html}</ul>'
            f'</div>',
            unsafe_allow_html=True
        )

    with c_pitch:
        st.markdown(f"<h5 style='color: {PRIMARY}; margin-bottom: 8px;'>📋 Pizarra Táctica ({squad.formation or '4-3-3'})</h5>", unsafe_allow_html=True)
        
        # Generar las coordenadas tácticas
        import re
        parts = [int(x) for x in re.findall(r'\d+', squad.formation or "4-3-3")]
        if not parts:
            parts = [4, 3, 3]
            
        coords = []
        coords.append({"role": "GK", "pos": "POR", "x": 60, "y": 200})
        
        num_lines = len(parts)
        x_positions = []
        if num_lines == 1:
            x_positions = [300]
        else:
            for i in range(num_lines):
                x = 160 + i * (380 / (num_lines - 1))
                x_positions.append(x)
                
        roles = []
        if num_lines == 3:
            roles = ["DEF", "MED", "DEL"]
        elif num_lines == 4:
            roles = ["DEF", "MED", "MED", "DEL"]
        elif num_lines == 5:
            roles = ["DEF", "MED", "MED", "MED", "DEL"]
        else:
            roles = ["DEF"] * (num_lines - 1) + ["DEL"]
            
        for i, count in enumerate(parts):
            x = x_positions[i]
            role = roles[i] if i < len(roles) else "MED"
            for j in range(count):
                y = (j + 0.5) * (400 / count)
                coords.append({"role": role, "pos": role, "x": x, "y": y})
                
        # Emparejar titulares
        starters = [p for p in squad.players if p.starter]
        starters_by_pos = {
            "POR": [p for p in starters if p.position == "POR"],
            "DEF": [p for p in starters if p.position == "DEF"],
            "MED": [p for p in starters if p.position == "MED"],
            "DEL": [p for p in starters if p.position == "DEL"],
        }
        
        node_players = []
        for c in coords:
            pos = c["pos"]
            p_match = None
            if pos in starters_by_pos and starters_by_pos[pos]:
                p_match = starters_by_pos[pos].pop(0)
                
            if p_match:
                node_players.append({
                    "name": p_match.name,
                    "recent_form": p_match.recent_form if hasattr(p_match, 'recent_form') and p_match.recent_form is not None else 6.0,
                    "is_star": p_match.name == squad.star_player,
                    "is_captain": p_match.name == squad.captain,
                    "x": c["x"],
                    "y": c["y"],
                    "position": p_match.position,
                })
            else:
                node_players.append({
                    "name": pos,
                    "recent_form": 6.0,
                    "is_star": False,
                    "is_captain": False,
                    "x": c["x"],
                    "y": c["y"],
                    "position": pos,
                })
                
        # Dibujar SVG
        svg_elements = []
        for node in node_players:
            x = node["x"]
            y = node["y"]
            name = node["name"]
            form = node["recent_form"]
            is_star = node["is_star"]
            is_capt = node["is_captain"]
            
            # Color
            if form >= 7.5:
                dot_color = "#06b6d4"  # Cyan
                glow_color = "rgba(6, 182, 212, 0.4)"
            elif form <= 5.0:
                dot_color = "#f43f5e"  # Coral
                glow_color = "rgba(244, 63, 94, 0.4)"
            else:
                dot_color = "#8b5cf6"  # Violet
                glow_color = "rgba(139, 92, 246, 0.2)"
                
            # Stroke
            border_stroke = "white"
            border_width = 1.5
            if is_star:
                border_stroke = "#eab308"
                border_width = 2.5
            elif is_capt:
                border_stroke = "#f97316"
                border_width = 2.0
                
            # Glow rings
            if form >= 7.5 or is_star:
                svg_elements.append(f'<circle cx="{x}" cy="{y}" r="14" fill="none" stroke="{glow_color}" stroke-width="4" />')
                
            # Circle
            svg_elements.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{dot_color}" stroke="{border_stroke}" stroke-width="{border_width}" />')
            
            # Label
            disp_name = name.split(" ")[-1] if " " in name else name
            if len(disp_name) > 8:
                disp_name = disp_name[:7] + "."
            if is_star:
                disp_name += "★"
            if is_capt:
                disp_name += "C"
                
            svg_elements.append(f'<text x="{x}" y="{y+22}" fill="#ffffff" font-size="10" font-weight="700" text-anchor="middle" font-family="Outfit">{disp_name}</text>')
            svg_elements.append(f'<text x="{x}" y="{y+32}" fill="#94a3b8" font-size="8" font-weight="500" text-anchor="middle" font-family="Plus Jakarta Sans">{form:.1f}</text>')

        svg_field = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" style="background-color: #080c14; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; width: 100%; height: auto;">
          <rect x="25" y="25" width="550" height="350" rx="8" fill="#0b0f19" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <line x1="300" y1="25" x2="300" y2="375" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <circle cx="300" cy="200" r="50" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <circle cx="300" cy="200" r="3" fill="rgba(255,255,255,0.03)" />
          
          <rect x="25" y="115" width="60" height="170" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <rect x="515" y="115" width="60" height="170" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <rect x="25" y="155" width="20" height="90" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <rect x="555" y="155" width="20" height="90" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          
          <path d="M 85 160 A 50 50 0 0 1 85 240" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          <path d="M 515 160 A 50 50 0 0 0 515 240" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2" />
          
          {"".join(svg_elements)}
        </svg>
        """
        
        st.markdown(svg_field, unsafe_allow_html=True)
        st.caption(r"🟢 Forma Reciente $\ge$ 7.5 (Pico) | 🟣 Forma Neutral/Regular | 🔴 Alerta de Forma $\le$ 5.0 (Baja)")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # 3. CLUB MOMENTUM (HOT vs COLD STREAKS)
    st.markdown(f"<h4 style='color: {TEXT}; margin-bottom: 12px;'>🔥 Momentum de Rendimiento en Clubes (Últimos 3 Meses)</h4>", unsafe_allow_html=True)
    c_hot, c_cold = st.columns(2)

    with c_hot:
        st.markdown(f"<span style='color: {GOOD}; font-weight: 700;'>📈 Jugadores en Estado de Gracia (Racha)</span>", unsafe_allow_html=True)
        hot_list = [p for p in squad.players if (p.recent_form if hasattr(p, 'recent_form') and p.recent_form is not None else 6.0) >= 7.5]
        if hot_list:
            for p in sorted(hot_list, key=lambda x: -x.recent_form):
                starter_label = "· Titular" if p.starter else ""
                st.markdown(
                    f'<div style="background: rgba(16, 185, 129, 0.04); border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 8px; padding: 10px; margin-bottom: 6px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span style="font-weight: 700; color: #ffffff;">{p.name} <span style="font-size:0.75rem; color:{TEXT_DIM}; font-weight:normal;">({p.club or "Sin club"}) {starter_label}</span></span>'
                    f'<span style="font-weight: 800; color: {GOOD}; font-size:1.05rem;">{p.recent_form:.1f} 🔥</span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Sin jugadores en racha destacable en los últimos 3 meses.")

    with c_cold:
        st.markdown(f"<span style='color: {DANGER}; font-weight: 700;'>📉 Alertas de Forma / Bajo Rendimiento</span>", unsafe_allow_html=True)
        cold_list = [p for p in squad.players if (p.recent_form if hasattr(p, 'recent_form') and p.recent_form is not None else 6.0) <= 5.0]
        if cold_list:
            for p in sorted(cold_list, key=lambda x: x.recent_form):
                starter_label = "· Titular" if p.starter else ""
                st.markdown(
                    f'<div style="background: rgba(244, 63, 94, 0.04); border: 1px solid rgba(244, 63, 94, 0.15); border-radius: 8px; padding: 10px; margin-bottom: 6px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span style="font-weight: 700; color: #ffffff;">{p.name} <span style="font-size:0.75rem; color:{TEXT_DIM}; font-weight:normal;">({p.club or "Sin club"}) {starter_label}</span></span>'
                    f'<span style="font-weight: 800; color: {DANGER}; font-size:1.05rem;">{p.recent_form:.1f} ⚠️</span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Todos los convocados registran regularidad en su forma reciente.")


def _render_squad_editor(team_es):
    """Editor de plantilla por seleccion."""
    squad = load_squad(team_es)
    completeness = squad_completeness(squad)

    # Header con completitud y valor de mercado
    valid_values = [p.market_value for p in squad.players if p.market_value is not None]
    total_val = sum(valid_values)

    c1, c2, c3, c4 = st.columns([1.8, 1, 1, 1.2])
    with c1:
        st.subheader(f"Plantilla de {team_es}")
        st.caption(f"Última actualización: {squad.updated_at or 'sin guardar'}")
    with c2:
        st.markdown(big_stat(f"{completeness}%", "Completitud"), unsafe_allow_html=True)
    with c3:
        st.markdown(big_stat(f"{len(squad.players)}", "Jugadores"), unsafe_allow_html=True)
    with c4:
        st.markdown(big_stat(f"{total_val:.1f} M€", "Valor Total"), unsafe_allow_html=True)

    # === Once probable visualizado en campo ===
    from app.components_squad import render_lineup_html, lineup_summary
    summ = lineup_summary(squad)
    if summ["n_starters"] > 0:
        st.markdown("##### 👕 Once probable")
        st.caption(
            f"Formación: **{summ['formation']}** · {summ['n_starters']} titulares · "
            f"Valor del once: **{summ['total_mv']:.0f} M€** · "
            f"Forma media: **{summ['mean_form']:.1f}/10**"
        )
        st.markdown(render_lineup_html(squad), unsafe_allow_html=True)
        st.caption(
            "🔴 Naranja = forma >7.5 · 🔵 Cian = >6.5 · ⚪ Gris = neutro · ⚫ Apagado = bajo "
            "rendimiento. Pasa el cursor para ver datos completos."
        )
    else:
        st.info("Marca a los titulares (`starter=true`) para ver el once probable sobre el campo.")

    # === Datos basicos ===
    st.markdown("##### Cuerpo tecnico y datos basicos")
    cA, cB = st.columns(2)
    with cA:
        squad.coach = st.text_input("Seleccionador", value=squad.coach, key=f"coach_{team_es}",
                                    placeholder="ej. Luis de la Fuente")
        squad.captain = st.text_input("Capitan", value=squad.captain, key=f"capt_{team_es}",
                                      placeholder="ej. Alvaro Morata")
    with cB:
        squad.formation = st.text_input("Formacion habitual", value=squad.formation,
                                        key=f"form_{team_es}", placeholder="ej. 4-3-3")
        squad.star_player = st.text_input("Mejor jugador / estrella", value=squad.star_player,
                                          key=f"star_{team_es}", placeholder="ej. Lamine Yamal")
    squad.notes = st.text_area("Notas (estado de forma, lesiones, contexto)",
                                value=squad.notes, key=f"notes_{team_es}",
                                placeholder="ej. Llega como favorita tras ganar la Euro 2024. Sin lesiones importantes...",
                                height=80)

    # === Ratings subjetivos ===
    st.markdown("##### Tu rating subjetivo (1-10)")
    st.caption("Estos ratings se pueden usar mas adelante para auto-ajustar el Elo del equipo.")
    rcols = st.columns(len(RATING_AXES))
    for col, (key, label) in zip(rcols, RATING_AXES.items()):
        with col:
            squad.ratings[key] = st.slider(
                label, 1, 10, squad.ratings.get(key, 5),
                key=f"rate_{team_es}_{key}",
            )
    avg = squad.avg_rating()
    suggested_bias = ratings_to_elo_bias(squad)
    st.caption(
        f"Media: **{avg:.1f}** → bias Elo sugerido: **{suggested_bias:+.0f}** "
        f"(no se aplica automaticamente; usalo como referencia en la pestana 'Mis ajustes')"
    )

    if squad.players:
        total_mv = sum(p.market_value for p in squad.players if p.market_value is not None)
        from src.data.squad import calculate_club_performance_bias
        cfg = get_biases()
        club_delta = calculate_club_performance_bias(
            squad,
            weight_mv=cfg.weight_market_value,
            weight_pedigree=cfg.weight_club_pedigree,
            weight_recent_form=cfg.weight_recent_form
        )
        status_text = "activada" if cfg.use_club_performance else "desactivada"
        st.caption(
            f"Valor de Mercado Total: **{total_mv:.1f} M€** | "
            f"Pedigrí de Club & Valor Elo bias calculado: **{club_delta:+.1f}** "
            f"(la vinculación está actualmente **{status_text}** en la pestaña 'Mis ajustes')"
        )

    # === Lista de jugadores ===
    st.markdown("##### Jugadores")
    st.caption("Anade hasta 26 jugadores. Puedes editarlos directamente abajo en la tabla.")

    if st.button("➕ Anadir jugador", key=f"add_{team_es}"):
        squad.players.append(Player(name="(nuevo jugador)"))

    if squad.players:
        # Tabla editable
        players_df = pd.DataFrame([{
            "Nombre": p.name, "Pos": p.position, "Club": p.club,
            "Dorsal": p.number if p.number else "",
            "Valor (M€)": p.market_value if p.market_value else "",
            "Forma (3 meses)": p.recent_form if hasattr(p, "recent_form") and p.recent_form is not None else 6.0,
            "Titular": p.starter, "Notas": p.notes,
        } for p in squad.players])

        edited = st.data_editor(
            players_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pos": st.column_config.SelectboxColumn("Pos", options=POSITIONS, required=True),
                "Titular": st.column_config.CheckboxColumn("Titular"),
                "Dorsal": st.column_config.NumberColumn("Dorsal", min_value=1, max_value=99),
                "Valor (M€)": st.column_config.NumberColumn("Valor (M€)", min_value=0),
                "Forma (3 meses)": st.column_config.NumberColumn("Forma (3 meses)", min_value=1.0, max_value=10.0, step=0.5, format="%.1f"),
            },
            key=f"editor_{team_es}",
        )
        # Sincronizar edits hacia squad.players
        new_players = []
        for _, row in edited.iterrows():
            new_players.append(Player(
                name=row["Nombre"] or "",
                position=row["Pos"] or "MED",
                club=row["Club"] or "",
                number=int(row["Dorsal"]) if pd.notna(row["Dorsal"]) and row["Dorsal"] != "" else None,
                market_value=float(row["Valor (M€)"]) if pd.notna(row["Valor (M€)"]) and row["Valor (M€)"] != "" else None,
                recent_form=float(row["Forma (3 meses)"]) if pd.notna(row["Forma (3 meses)"]) and row["Forma (3 meses)"] != "" else 6.0,
                starter=bool(row["Titular"]),
                notes=row["Notas"] or "",
            ))
        squad.players = new_players

        # Resumen por posicion
        count = squad.player_count_by_position()
        cols = st.columns(4)
        for col, pos in zip(cols, POSITIONS):
            col.markdown(big_stat(count[pos], POSITION_LABELS[pos]), unsafe_allow_html=True)
    else:
        st.info(f"No hay jugadores aun. Pulsa '➕ Anadir jugador' para empezar a construir la plantilla.")

    # === Guardar ===
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    cG, cD = st.columns([1, 3])
    with cG:
        if st.button("💾 Guardar plantilla", type="primary", key=f"save_squad_{team_es}",
                     use_container_width=True):
            save_squad(squad)
            st.success(f"Plantilla guardada")
    with cD:
        st.caption(
            "💡 Tip: Conforme se vayan publicando las convocatorias oficiales, "
            "actualiza la plantilla aqui. Los jugadores titulares y el rating "
            "subjetivo nos ayudan a ajustar el modelo."
        )
