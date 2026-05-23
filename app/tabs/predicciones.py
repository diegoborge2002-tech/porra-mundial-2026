"""Pestana de predicciones del modelo - rediseno oscuro."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from app.utils import load_base_elo, get_biases, get_elo_with_biases, run_simulation_with_real, load_real_results
from app.components import big_stat
from app.components_day import render_upcoming_card, render_pre_match_extras
from app.styles import PRIMARY, ACCENT, BG_CARD, TEXT, TEXT_DIM, GOOD
from src.data.team_profile import ISO_CODES
from src.tournament.groups import ALL_TEAMS, GROUPS
from src.model.calibration import shannon_entropy, bootstrap_champion_ci
from src.model.match_day import find_upcoming_matches, find_recently_played, days_to_next_match, time_to_kickoff
import math


def plotly_theme(**overrides) -> dict:
    """Tema oscuro Plotly. Cualquier override (yaxis, xaxis, etc.) sustituye al default."""
    theme = dict(
        plot_bgcolor=BG_CARD,
        paper_bgcolor=BG_CARD,
        font=dict(family="Inter", color=TEXT),
        xaxis=dict(gridcolor="#1f2937"),
        yaxis=dict(gridcolor="#1f2937"),
    )
    # Mergear dicts cuando hay override (xaxis/yaxis especialmente)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(theme.get(k), dict):
            theme[k] = {**theme[k], **v}
        else:
            theme[k] = v
    return theme


def render():
    st.header("Predicciones del modelo")
    st.caption("Monte Carlo de 10.000 torneos · Elo entrenado con 49.215 partidos historicos + tus ajustes")

    # =========================================================================
    # 🎓 ACADEMIA DE MODELADO & CALCULADORA INTERACTIVA 1X2
    # =========================================================================
    with st.expander("🎓 Academia de Modelado & Simulador Rápido 1X2", expanded=False):
        st.markdown(
            f"""
            <div style="margin-bottom: 16px;">
                <p style="color: {TEXT_DIM}; font-size: 0.9rem; line-height: 1.6; margin: 0;">
                    ¡Bienvenido a la sala de control! Aquí el modelado de datos objetivos y tu intuición de fútbol se fusionan para dar vida a las predicciones.
                    Descubre cómo el simulador predice el Mundial explorando las fuerzas conceptuales subyacentes.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        c_theory_left, c_theory_right = st.columns(2)
        with c_theory_left:
            st.markdown(
                f"""
                <div class="card-mates" style="height: 100%; margin-bottom: 0;">
                    <div class="badge-mates">📊 Motor Matemático (El Dato)</div>
                    <h4 style="margin: 0 0 10px 0; color: {PRIMARY}; font-size: 1.15rem;">El Sistema de Puntuación Elo</h4>
                    <p style="color: {TEXT_DIM}; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                        Inspirado en el ajedrez y eloratings.net, cada selección tiene una puntuación (base neutral de <b>1500</b>). 
                        El Elo es un juego de suma cero: <b>robas puntos de tu oponente</b>. Si vences a un rival fuerte, tu Elo sube drásticamente. 
                        Si empatas con un rival débil, pierdes puntos a su favor.<br><br>
                        <b>La ventaja de localía (Sede)</b> suma automáticamente <b>+65 puntos</b> al Elo del equipo local, 
                        lo que representa estadísticamente el aliento de la afición y la familiaridad con el terreno.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c_theory_right:
            st.markdown(
                f"""
                <div class="card-intuicion" style="height: 100%; margin-bottom: 0;">
                    <div class="badge-intuicion">✨ Juicio Humano (Tu Voz)</div>
                    <h4 style="margin: 0 0 10px 0; color: {ACCENT}; font-size: 1.15rem;">Simulaciones de Monte Carlo</h4>
                    <p style="color: {TEXT_DIM}; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                        ¿Cómo pasamos de puntos Elo a saber quién levantará la Copa? Usamos **simulaciones de Monte Carlo**.<br><br>
                        El modelo no dice simplemente "ganará Francia". En su lugar, calcula las probabilidades de cada partido y <b>lanza un dado virtual 10.000 veces</b> para jugar todo el torneo desde la fase de grupos hasta la gran final. 
                        El porcentaje de campeón es la cantidad de veces que cada país levantó el trofeo en esos 10.000 mundios virtuales alternativos.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.35); border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; padding: 20px;">
                <h4 style="margin-top:0; color:{PRIMARY}; text-align: center; font-size: 1.1rem; font-weight: 700;">🧪 Simulador Rápido 1X2 (Calculadora de Probabilidades)</h4>
                <p style="color:{TEXT_DIM}; font-size:0.82rem; text-align: center; margin-bottom: 16px; margin-top: 4px;">
                    Desplaza los Elos ficticios abajo para simular un partido en campo neutral. Observa cómo el algoritmo traduce la brecha Elo en probabilidades 1X2 reales en tiempo real.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Sliders de la calculadora
        cc1, cc2 = st.columns(2)
        with cc1:
            elo_a = st.slider("Elo Equipo Local", 1000, 2200, 1700, step=10, key="calc_elo_a")
        with cc2:
            elo_b = st.slider("Elo Equipo Visitante", 1000, 2200, 1600, step=10, key="calc_elo_b")
            
        # Calcular probabilidades reales del modelo
        diff = elo_a - elo_b
        p_home_raw = 1.0 / (1.0 + 10 ** (-diff / 400.0))
        p_away_raw = 1.0 - p_home_raw
        closeness = 1 - 2 * abs(p_home_raw - 0.5)
        p_draw = (1/3) * closeness
        rest = 1 - p_draw
        p_home = rest * p_home_raw
        p_away = rest * p_away_raw
        
        # Mostrar barra apilada premium
        st.markdown(
            f"""
            <div style="margin-top: 15px; margin-bottom: 10px; padding: 10px 0;">
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 800; margin-bottom: 10px;">
                    <span style="color: {PRIMARY};">Local gana: {p_home*100:.1f}%</span>
                    <span style="color: {TEXT_DIM}; font-weight: 600;">Empate: {p_draw*100:.1f}%</span>
                    <span style="color: {ACCENT};">Visitante gana: {p_away*100:.1f}%</span>
                </div>
                <div style="display: flex; height: 26px; border-radius: 13px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <div style="width: {p_home*100}%; background: linear-gradient(90deg, #0891b2 0%, {PRIMARY} 100%); transition: width 0.3s ease;"></div>
                    <div style="width: {p_draw*100}%; background: #334155; transition: width 0.3s ease;"></div>
                    <div style="width: {p_away*100}%; background: linear-gradient(90deg, {ACCENT} 0%, #7c3aed 100%); transition: width 0.3s ease;"></div>
                </div>
                <p style="color: {TEXT_DIM}; font-size: 0.78rem; text-align: center; margin-top: 12px; font-style: italic; margin-bottom: 0;">
                    Fórmula matemática del partido: P(Victoria) se calcula mediante distribución logística Elo, y el empate disminuye a medida que aumenta la brecha competitiva.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    elo = get_elo_with_biases()
    base = load_base_elo()
    cfg = get_biases()
    n_sims = st.sidebar.slider("Simulaciones Monte Carlo", 1_000, 30_000, 10_000, step=1_000)
    summary = run_simulation_with_real(elo, n_sims, seed=42)

    # =========================================================================
    # 🔥 DÍA DE PARTIDO: hero card si hay partidos próximos / recién jugados
    # =========================================================================
    real_results = load_real_results()
    upcoming = find_upcoming_matches(elo, window_hours=36, fallback_days=14)
    recent_played = find_recently_played(elo, real_results, window_hours=36)

    if upcoming or recent_played:
        st.markdown("### 🔥 Día de partido")
        if recent_played:
            st.caption("Resultados recientes")
            for m in recent_played[:3]:
                render_upcoming_card(m)
        if upcoming:
            label = "Próximos partidos" if not recent_played else "Siguientes en el calendario"
            st.caption(label)
            for m in upcoming[:3]:
                render_upcoming_card(m)
                # Extras (forma, h2h, jugadores en forma) sólo para el partido más inminente
                ttk = time_to_kickoff(m.date) if hasattr(m, "date") else {"days": 999}
                if ttk["days"] <= 1 and not ttk["negative"]:
                    try:
                        render_pre_match_extras(m.home, m.away)
                    except Exception:
                        pass
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    else:
        d = days_to_next_match()
        if d < 999:
            st.info(f"📅 Próximo partido en {d} días. La pestaña 'Día de partido' aparecerá automáticamente 36h antes del kickoff.")
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === KPI top: 3 favoritos al titulo (con intervalos de confianza) ===
    top3 = sorted(summary["champion"].items(), key=lambda x: -x[1])[:3]
    cis = bootstrap_champion_ci(summary.get("champion_by_sim", []),
                                 [t for t, _ in top3], n_boot=200, seed=42)
    cols = st.columns(3)
    for i, (team, p) in enumerate(top3):
        iso = ISO_CODES.get(team, "un")
        flag = f"https://flagcdn.com/w80/{iso}.png"
        delta = cfg.get_delta(team)
        delta_str = f" {'+' if delta>0 else ''}{int(delta)}" if delta else ""
        p10, _p50, p90 = cis.get(team, (p, p, p))
        ci_html = (f'<div style="color:{TEXT_DIM}; font-size:0.75rem; margin-top:4px;">'
                   f'IC 80%: {p10*100:.1f}% – {p90*100:.1f}%</div>')
        with cols[i]:
            st.markdown(
                f'<div class="team-card">'
                f'<div class="team-card-header">'
                f'<img src="{flag}" class="team-flag">'
                f'<div><p class="team-name">#{i+1} {team}</p>'
                f'<p class="team-meta">Elo {int(elo[team])}{delta_str}</p></div>'
                f'</div>'
                f'<div style="text-align:center;">'
                f'<div style="font-size:3rem; font-weight:800; color:{PRIMARY};">{p*100:.1f}%</div>'
                f'<div style="color:{TEXT_DIM}; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.08em;">Probabilidad de ser campeon</div>'
                f'{ci_html}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # === KPI de incertidumbre: entropía del torneo ===
    entropy = shannon_entropy(summary["champion"])
    max_entropy = math.log2(48)
    openness_pct = (entropy / max_entropy) * 100
    if openness_pct >= 70:
        open_color, open_label = "#ef4444", "MUY ABIERTO"
    elif openness_pct >= 50:
        open_color, open_label = "#f59e0b", "ABIERTO"
    elif openness_pct >= 30:
        open_color, open_label = ACCENT, "DEFINIDO"
    else:
        open_color, open_label = PRIMARY, "CERRADO"
    eff_n = 2 ** entropy
    cE1, cE2, cE3 = st.columns(3)
    with cE1:
        st.markdown(
            f'<div class="team-card" style="text-align:center;">'
            f'<div style="font-size:0.75rem; color:{TEXT_DIM}; text-transform:uppercase; letter-spacing:0.08em;">Apertura del torneo</div>'
            f'<div style="font-size:2.4rem; font-weight:800; color:{open_color};">{openness_pct:.0f}%</div>'
            f'<div style="font-size:0.85rem; color:{open_color}; font-weight:600;">{open_label}</div>'
            f'</div>', unsafe_allow_html=True)
    with cE2:
        st.markdown(
            f'<div class="team-card" style="text-align:center;">'
            f'<div style="font-size:0.75rem; color:{TEXT_DIM}; text-transform:uppercase; letter-spacing:0.08em;">Candidatos efectivos</div>'
            f'<div style="font-size:2.4rem; font-weight:800; color:{PRIMARY};">{eff_n:.1f}</div>'
            f'<div style="font-size:0.85rem; color:{TEXT_DIM};">equipos equiprobables = mismo entropy</div>'
            f'</div>', unsafe_allow_html=True)
    with cE3:
        suma_top5 = sum(p for _, p in top3) + sum(
            p for _, p in sorted(summary["champion"].items(), key=lambda x: -x[1])[3:5]
        )
        st.markdown(
            f'<div class="team-card" style="text-align:center;">'
            f'<div style="font-size:0.75rem; color:{TEXT_DIM}; text-transform:uppercase; letter-spacing:0.08em;">% campeón en top-5</div>'
            f'<div style="font-size:2.4rem; font-weight:800; color:{ACCENT};">{suma_top5*100:.0f}%</div>'
            f'<div style="font-size:0.85rem; color:{TEXT_DIM};">Concentración del título</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Tabla completa + grafico ===
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.subheader("Ranking completo de probabilidades")
        df = pd.DataFrame([
            {"Equipo": t,
             "Campeon %": summary["champion"].get(t, 0) * 100,
             "Final %": summary["finalist"].get(t, 0) * 100,
             "Semi %": summary["semifinal"].get(t, 0) * 100,
             "Cuartos %": summary["quarter"].get(t, 0) * 100,
             "Octavos %": summary["r16"].get(t, 0) * 100,
             "Elo": round(elo[t], 0)}
            for t in ALL_TEAMS
        ]).sort_values("Campeon %", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        st.dataframe(
            df.style.format({
                "Campeon %": "{:.2f}",
                "Final %": "{:.2f}",
                "Semi %": "{:.2f}",
                "Cuartos %": "{:.2f}",
                "Octavos %": "{:.2f}",
                "Elo": "{:.0f}",
            }).background_gradient(subset=["Campeon %"], cmap="Greens"),
            height=600, use_container_width=True,
        )

    with col_right:
        st.subheader("Top 12 al titulo")
        top12 = df.head(12)
        fig = go.Figure(go.Bar(
            x=top12["Campeon %"],
            y=top12["Equipo"],
            orientation="h",
            marker=dict(
                color=top12["Campeon %"],
                colorscale=[[0, "#1f2937"], [1, PRIMARY]],
                line=dict(color=PRIMARY, width=1),
            ),
            text=[f"{x:.1f}%" for x in top12["Campeon %"]],
            textposition="outside",
            textfont=dict(color=TEXT),
        ))
        fig.update_layout(**plotly_theme(
            height=560,
            margin=dict(l=10, r=40, t=10, b=10),
            yaxis=dict(autorange="reversed"),
            showlegend=False,
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Probabilidades por grupo (cards) ===
    st.subheader("Probabilidades por grupo")
    cols = st.columns(4)
    for i, g in enumerate(sorted(GROUPS)):
        with cols[i % 4]:
            ranking = sorted(
                [(t, summary["group_winner"].get(g, {}).get(t, 0),
                     summary["group_top2"].get(g, {}).get(t, 0),
                     summary["group_top3"].get(g, {}).get(t, 0))
                 for t in GROUPS[g]],
                key=lambda x: -x[3],
            )
            inner = f"<h4 style='margin: 0 0 8px 0; color:{PRIMARY};'>Grupo {g}</h4>"
            for team, p1, p2, p3 in ranking:
                iso = ISO_CODES.get(team, "un")
                inner += (
                    f'<div style="display:flex; align-items:center; gap:8px; margin:6px 0;">'
                    f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:24px; height:18px; border-radius:2px; object-fit:cover;">'
                    f'<span style="flex:1; color:{TEXT}; font-size:0.85rem;">{team}</span>'
                    f'<span style="color:{TEXT_DIM}; font-size:0.75rem;">{p3*100:.0f}%</span>'
                    f'</div>'
                )
            st.markdown(f'<div class="team-card">{inner}</div>', unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Goles + top goleadores ===
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Goles totales del Mundial")
        goals_series = pd.Series(summary["total_goals_distribution"])
        c1, c2, c3 = st.columns(3)
        c1.markdown(big_stat(f"{goals_series.quantile(0.1):.0f}", "P10"), unsafe_allow_html=True)
        c2.markdown(big_stat(f"{summary['expected_total_goals']:.0f}", "Esperados"), unsafe_allow_html=True)
        c3.markdown(big_stat(f"{goals_series.quantile(0.9):.0f}", "P90"), unsafe_allow_html=True)
        fig = go.Figure(go.Histogram(
            x=goals_series, nbinsx=40,
            marker=dict(color=PRIMARY, line=dict(color=ACCENT, width=0)),
        ))
        fig.update_layout(**plotly_theme(
            height=320, margin=dict(t=10, b=10, l=10, r=10),
            xaxis_title="Goles totales", yaxis_title="Frecuencia", showlegend=False,
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.subheader("Goles esperados por equipo")
        eg = pd.DataFrame(summary["expected_team_goals"].items(),
                          columns=["Equipo", "Goles"])
        eg = eg.sort_values("Goles", ascending=False).head(15)
        fig = go.Figure(go.Bar(
            x=eg["Goles"], y=eg["Equipo"], orientation="h",
            marker=dict(color=eg["Goles"],
                        colorscale=[[0, "#1f2937"], [1, ACCENT]],
                        line=dict(color=ACCENT, width=1)),
            text=[f"{x:.1f}" for x in eg["Goles"]],
            textposition="outside",
            textfont=dict(color=TEXT),
        ))
        fig.update_layout(**plotly_theme(
            height=440, margin=dict(l=10, r=40, t=10, b=10),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Goles esperados en el Mundial", showlegend=False,
        ))
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 📈 EVOLUCIÓN DE PROBABILIDADES (snapshots longitudinales)
    # =========================================================================
    _render_probability_evolution(summary)


def _render_probability_evolution(summary: dict) -> None:
    """Gráfico de cómo ha evolucionado P(campeón) de los top equipos día a día."""
    from src.data.snapshots import list_snapshots, count_snapshots, history_top_teams

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("### 📈 Evolución de probabilidades")

    n = count_snapshots()
    if n == 0:
        st.info(
            "Aún no hay snapshots históricos. Cada día que abras la app se guarda "
            "automáticamente uno → en pocos días verás aquí cómo ha evolucionado "
            "P(campeón) de cada equipo."
        )
        return
    if n < 2:
        st.caption(
            f"Hay {n} snapshot guardado. La gráfica empezará a ser útil con ≥2 días "
            "de historia. Vuelve mañana 😉"
        )
        return

    metric = st.radio(
        "Métrica",
        ["champion", "finalist", "semifinal"],
        horizontal=True,
        format_func=lambda x: {"champion": "🏆 Campeón",
                                "finalist": "🥈 Finalista",
                                "semifinal": "🎖 Semifinal"}[x],
        key="snap_metric",
    )
    n_top = st.slider("Equipos a mostrar (top del último snapshot)", 3, 12, 8,
                      key="snap_top_n")

    histories = history_top_teams(n=n_top, metric=metric)
    if not histories:
        st.info("Sin datos suficientes.")
        return

    fig = go.Figure()
    palette = ["#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#f43f5e",
               "#ec4899", "#3b82f6", "#84cc16", "#a855f7", "#06d6a0",
               "#fbbf24", "#fb7185"]
    for i, (team, serie) in enumerate(histories.items()):
        if not serie:
            continue
        xs = [s["date"] for s in serie]
        ys = [s["p"] * 100 for s in serie]
        color = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, name=team, mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
            hovertemplate=f"<b>{team}</b><br>%{{x}}: %{{y:.2f}}%<extra></extra>",
        ))
    fig.update_layout(
        height=430,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.4)",
        font=dict(color=TEXT),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title=""),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", title=f"P({metric}) %", ticksuffix="%"),
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"📸 {n} snapshots guardados. Cada vez que se abre la app se hace "
        "uno como máximo al día (idempotente)."
    )
