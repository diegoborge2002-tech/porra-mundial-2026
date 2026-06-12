"""Pestaña 'Rendimiento del modelo': calibración, precisión y diagnósticos por partido."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from app.utils import get_elo_with_biases, load_base_elo, load_real_results, get_biases
from app.components import big_stat
from app.styles import PRIMARY, ACCENT, BG_CARD, TEXT, TEXT_DIM, GOOD, DANGER
from src.model.live_diagnostics import compute_match_diagnostics, diagnostics_to_dataframe
from src.model.calibration import aggregate_metrics, reliability_bins
from src.model.backtest import load_backtest_summary, run_full_backtest
from src.model.history import load_history
from src.data.team_profile import ISO_CODES
from app.glossary import GLOSSARY, help_for


def _plotly_dark(**overrides) -> dict:
    theme = dict(
        plot_bgcolor=BG_CARD,
        paper_bgcolor=BG_CARD,
        font=dict(family="Inter", color=TEXT),
        xaxis=dict(gridcolor="#1f2937"),
        yaxis=dict(gridcolor="#1f2937"),
    )
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(theme.get(k), dict):
            theme[k] = {**theme[k], **v}
        else:
            theme[k] = v
    return theme


def _flag_inline(team: str, size: int = 18) -> str:
    iso = ISO_CODES.get(team, "un")
    return (f'<img src="https://flagcdn.com/w40/{iso}.png" '
            f'style="width:{size}px;height:{int(size*0.75)}px;border-radius:2px;'
            f'object-fit:cover;vertical-align:middle;margin:0 4px;">')


@st.cache_data(show_spinner="Ejecutando backtesting sobre 400+ partidos históricos...")
def get_custom_backtest(half_life: float) -> dict:
    """Wrapper cacheado para ejecutar el backtest con vida media personalizada."""
    return run_full_backtest(half_life=half_life)


def render():
    st.header("Rendimiento del modelo")
    st.caption(
        "Cómo de bien predice el modelo. Cuanto más bajo Brier/RPS, mejor. "
        "Si el modelo dice 70% y aciertas el 70%, está bien calibrado."
    )

    # Glosario de métricas (siempre visible al principio)
    with st.expander("📖 Glosario de métricas (Brier, RPS, entropía, regret, ...)", expanded=False):
        for key, text in GLOSSARY.items():
            st.markdown(f"- {text}")

    base_elo = load_base_elo()
    elo = get_elo_with_biases()
    real_results = load_real_results()

    # === Widget "Cambios de hoy": delta entre últimos dos snapshots ===
    _render_recent_changes()

    diagnostics = compute_match_diagnostics(base_elo, real_results)

    # === KPI top: estado actual ===
    n_played = len(diagnostics)
    if n_played == 0:
        st.info(
            "Aún no hay partidos reales registrados. Cuando metas resultados en la "
            "pestaña **Seguimiento en vivo**, aquí verás cómo de bien predijo el modelo "
            "cada partido. Mientras tanto puedes mirar el backtest histórico abajo."
        )
    else:
        preds = [((d.p_home, d.p_draw, d.p_away), d.outcome) for d in diagnostics]
        stats = aggregate_metrics(preds)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(big_stat(f"{stats.n}", "PARTIDOS"), unsafe_allow_html=True)
        with c2: st.markdown(big_stat(f"{stats.hit_rate_top1*100:.0f}%", "TOP-1 ACIERTOS",
                                       tooltip=help_for("hit_rate")), unsafe_allow_html=True)
        with c3: st.markdown(big_stat(f"{stats.mean_brier:.3f}", "BRIER MEDIO",
                                       tooltip=help_for("brier")), unsafe_allow_html=True)
        with c4: st.markdown(big_stat(f"{stats.mean_rps:.3f}", "RPS MEDIO",
                                       tooltip=help_for("rps")), unsafe_allow_html=True)

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

        # === Comparativa Elo vs XGBoost vs Ensemble sobre los partidos reales ===
        from src.model import ensemble as _ens
        if _ens.stats_available():
            st.subheader("🥊 Elo vs XGBoost vs Ensemble (partidos reales)")
            st.caption(
                "Mismas métricas, tres motores: el Elo clásico, el modelo de stats XGBoost "
                "(repo Simulaciones_Mundial) y la mezcla que estás usando. Así ves con datos "
                "si el Elo es o no representativo en ESTE Mundial."
            )
            w_user = get_biases().stats_weight
            comp_rows = []
            for label, w in [("⚖️ Elo puro", 0.0),
                             (f"🎯 Ensemble actual ({w_user*100:.0f}% stats)", w_user),
                             ("🤖 XGBoost stats", 1.0)]:
                _ens.set_stats_weight(w)
                diags_w = compute_match_diagnostics(base_elo, real_results)
                preds_w = [((d.p_home, d.p_draw, d.p_away), d.outcome) for d in diags_w]
                s_w = aggregate_metrics(preds_w)
                comp_rows.append({
                    "Modelo": label,
                    "Top-1 aciertos": f"{s_w.hit_rate_top1*100:.0f}%",
                    "Brier ↓": round(s_w.mean_brier, 3),
                    "Log-loss ↓": round(s_w.mean_log_loss, 3),
                    "RPS ↓": round(s_w.mean_rps, 3),
                })
            _ens.set_stats_weight(w_user)  # restaurar el peso del usuario
            df_comp = pd.DataFrame(comp_rows)
            best_brier = df_comp["Brier ↓"].idxmin()
            st.dataframe(df_comp, hide_index=True, use_container_width=True)
            st.caption(
                f"🏆 Mejor Brier hasta ahora: **{df_comp.loc[best_brier, 'Modelo']}**. "
                "Con pocos partidos esto baila mucho; gana valor a medida que avanza el torneo."
            )
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

        # === Tabla diagnóstica por partido ===
        st.subheader("Diagnóstico partido a partido")
        st.caption(
            "Cada fila es un partido jugado. La columna **Surprise** = 1 - p(resultado real). "
            "Cuanto más alta, más sorprendente fue el resultado para el modelo."
        )
        df = diagnostics_to_dataframe(diagnostics)
        df_view = df[[
            "phase", "match_id", "home_score", "away_score",
            "p_home", "p_draw", "p_away", "outcome",
            "xg_home", "xg_away", "surprise", "brier", "rps",
        ]].copy()
        df_view.columns = ["Fase", "Partido", "GL", "GV",
                           "P(H)", "P(X)", "P(A)", "Real",
                           "xG L", "xG V", "Sorpresa", "Brier", "RPS"]
        st.dataframe(
            df_view.style.format({
                "P(H)": "{:.0%}", "P(X)": "{:.0%}", "P(A)": "{:.0%}",
                "xG L": "{:.2f}", "xG V": "{:.2f}",
                "Sorpresa": "{:.0%}", "Brier": "{:.2f}", "RPS": "{:.2f}",
            }).background_gradient(subset=["Sorpresa"], cmap="Reds"),
            hide_index=True, use_container_width=True, height=420,
        )

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

        # === Top sorpresas ===
        col_s, col_xg = st.columns(2)
        with col_s:
            st.subheader("Top sorpresas del torneo")
            top_surp = df.sort_values("surprise", ascending=False).head(5)
            for _, row in top_surp.iterrows():
                pct = row["surprise"] * 100
                bar_width = int(pct)
                html = (
                    f'<div style="background:{BG_CARD};border:1px solid #1f2937;border-radius:10px;'
                    f'padding:10px 14px;margin-bottom:8px;">'
                    f'<div style="display:flex;align-items:center;gap:6px;font-size:0.85rem;font-weight:600;">'
                    f'{_flag_inline(row["home"])}<span>{row["home"]}</span>'
                    f'<span style="color:{TEXT_DIM};font-weight:400;">{row["home_score"]} - {row["away_score"]}</span>'
                    f'{_flag_inline(row["away"])}<span>{row["away"]}</span>'
                    f'</div>'
                    f'<div style="margin-top:6px;display:flex;align-items:center;gap:8px;">'
                    f'<div style="flex:1;background:#1f2937;height:6px;border-radius:3px;overflow:hidden;">'
                    f'<div style="width:{bar_width}%;background:{DANGER};height:100%;"></div></div>'
                    f'<span style="color:{DANGER};font-weight:700;font-size:0.85rem;">{pct:.0f}%</span></div>'
                    f'<div style="font-size:0.75rem;color:{TEXT_DIM};margin-top:4px;">'
                    f'Modelo daba {row["p_home"]*100:.0f}%/{row["p_draw"]*100:.0f}%/{row["p_away"]*100:.0f}% (1/X/2).'
                    f'</div></div>'
                )
                st.markdown(html, unsafe_allow_html=True)

        with col_xg:
            st.subheader("xG esperado vs goles reales")
            df_x = df.copy()
            df_x["xg_total"] = df_x["xg_home"] + df_x["xg_away"]
            df_x["goles_total"] = df_x["home_score"] + df_x["away_score"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_x["xg_total"], y=df_x["goles_total"], mode="markers",
                marker=dict(size=11, color=df_x["surprise"],
                            colorscale=[[0, PRIMARY], [1, DANGER]],
                            showscale=True,
                            colorbar=dict(title=dict(text="Sorpresa", side="right"))),
                text=[f"{r['home']} {r['home_score']}-{r['away_score']} {r['away']}"
                      for _, r in df_x.iterrows()],
                hovertemplate="%{text}<br>xG: %{x:.1f} · Real: %{y}<extra></extra>",
            ))
            mx = max(df_x["xg_total"].max(), df_x["goles_total"].max(), 1) + 1
            fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines",
                                     line=dict(color=TEXT_DIM, dash="dash"),
                                     showlegend=False))
            fig.update_layout(**_plotly_dark(
                height=380,
                xaxis_title="xG total esperado", yaxis_title="Goles reales",
                showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

        # === Calibración real (reliability + hit rate por confianza) ===
        col_r, col_c = st.columns(2)
        with col_r:
            st.subheader("Curva de calibración")
            st.caption(
                "Eje X: probabilidad que daba el modelo. Eje Y: frecuencia real. "
                "La línea diagonal es calibración perfecta."
            )
            bins = reliability_bins(preds, n_bins=10)
            xs = [b["predicted_mean"] for b in bins if b["n"] > 0]
            ys = [b["observed_freq"] for b in bins if b["n"] > 0]
            sizes = [max(8, b["n"] * 3) for b in bins if b["n"] > 0]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                     line=dict(color=TEXT_DIM, dash="dash"),
                                     showlegend=False))
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="markers+lines",
                    marker=dict(size=sizes, color=PRIMARY,
                                line=dict(color=ACCENT, width=1)),
                    line=dict(color=PRIMARY, width=2),
                    name="Modelo",
                ))
            fig.update_layout(**_plotly_dark(
                height=340,
                xaxis_title="Probabilidad predicha", yaxis_title="Frecuencia observada",
                xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1]),
                showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, use_container_width=True)

        with col_c:
            st.subheader("Aciertos por nivel de confianza")
            st.caption("Cuando el modelo dijo X% para el favorito, ¿en qué % de los casos acertó?")
            buckets = list(stats.accuracy_by_confidence.items())
            labels = [b[0] for b in buckets]
            ns = [b[1][0] for b in buckets]
            hits = [b[1][1] * 100 for b in buckets]
            fig = go.Figure(go.Bar(
                x=labels, y=hits,
                marker=dict(color=hits, colorscale=[[0, DANGER], [0.5, ACCENT], [1, GOOD]],
                            line=dict(color=PRIMARY, width=1)),
                text=[f"{h:.0f}% ({n})" for h, n in zip(hits, ns)],
                textposition="outside", textfont=dict(color=TEXT),
            ))
            fig.update_layout(**_plotly_dark(
                height=340,
                xaxis_title="Confianza del modelo (top pick)",
                yaxis_title="Aciertos %",
                yaxis=dict(range=[0, 105]),
                showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
            ))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Evolución de probabilidades a lo largo del torneo ===
    history = load_history()
    if history and len(history) >= 2:
        st.subheader("Evolución de probabilidades de campeón")
        st.caption(
            "Cómo han ido cambiando las probabilidades del modelo tras cada bloque de "
            "resultados reales. Se registra un snapshot cada vez que se pulsa **Guardar** en seguimiento."
        )
        # Recolectar todos los equipos que aparecen en cualquier snapshot
        all_teams = set()
        for snap in history:
            all_teams.update(snap["top_probs"].keys())
        # Mostrar los 8 con mayor probabilidad en el último snapshot
        last_top = sorted(history[-1]["top_probs"].items(), key=lambda x: -x[1])[:8]
        focus_teams = [t for t, _ in last_top]

        fig = go.Figure()
        for t in focus_teams:
            xs = [snap["matches_played"] for snap in history]
            ys = [snap["top_probs"].get(t, 0) * 100 for snap in history]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers", name=t,
                line=dict(width=2), marker=dict(size=7),
            ))
        fig.update_layout(**_plotly_dark(
            height=400,
            xaxis_title="Partidos jugados",
            yaxis_title="Probabilidad de campeón (%)",
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
        ))
        st.plotly_chart(fig, use_container_width=True)

        # Entropía a lo largo del tiempo
        st.markdown("##### Apertura del torneo a lo largo del tiempo")
        st.caption("La entropía (en bits) cae a medida que se confirman los favoritos.")
        fig_e = go.Figure(go.Scatter(
            x=[s["matches_played"] for s in history],
            y=[s["entropy_bits"] for s in history],
            mode="lines+markers", line=dict(color=ACCENT, width=3),
            marker=dict(size=8, color=ACCENT),
        ))
        fig_e.update_layout(**_plotly_dark(
            height=260,
            xaxis_title="Partidos jugados",
            yaxis_title="Entropía (bits) — 5.58 = máx",
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
        ))
        st.plotly_chart(fig_e, use_container_width=True)
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    elif history:
        st.info("Cuando guardes resultados de más partidos verás aquí cómo evolucionan las probabilidades.")
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Backtest histórico ===
    st.subheader("Backtest histórico")
    st.caption(
        "Cómo se comporta el mismo modelo en torneos pasados (Mundial 2010–2022, Eurocopas 2016–2024). "
        "Sirve de baseline para juzgar las métricas en vivo."
    )

    bt_baseline = load_backtest_summary()
    if not bt_baseline:
        with st.spinner("Inicializando backtest base por primera vez (400+ partidos)..."):
            bt_baseline = run_full_backtest(half_life=8.0)

    cfg = get_biases()
    half_life = cfg.half_life
    is_custom = (half_life != 8.0)

    if not is_custom:
        st.markdown(
            f'<div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); '
            f'border-radius: 8px; padding: 12px; margin-bottom: 16px;">'
            f'<span style="color: {GOOD}; font-weight: 700;">🟢 Calibración base activa</span> · '
            f'<span style="color: {TEXT_DIM};">Memoria Histórica Elo = 8.0 años. El backtest mostrado abajo refleja la configuración base.</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        cA, cB = st.columns([3, 1])
        with cB:
            if st.button("🔁 Recalcular backtest base", use_container_width=True):
                with st.spinner("Backtesteando 400+ partidos…"):
                    bt_baseline = run_full_backtest(half_life=8.0)
                st.success("Backtest base actualizado.")
        with cA:
            o = bt_baseline["overall"]
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(big_stat(f"{o['n_matches']}", "Partidos"), unsafe_allow_html=True)
            with c2: st.markdown(big_stat(f"{o['weighted_hit_rate']*100:.1f}%", "Top-1"), unsafe_allow_html=True)
            with c3: st.markdown(big_stat(f"{o['weighted_brier']:.3f}", "Brier"), unsafe_allow_html=True)
            with c4: st.markdown(big_stat(f"{o['weighted_rps']:.3f}", "RPS"), unsafe_allow_html=True)

        df_t = pd.DataFrame(bt_baseline["tournaments"])
        df_t = df_t[["name", "n_matches", "hit_rate_top1", "brier", "log_loss", "rps"]].copy()
        df_t.columns = ["Torneo", "Partidos", "Top-1", "Brier", "Log-loss", "RPS"]
        st.dataframe(
            df_t.style.format({
                "Top-1": "{:.1%}", "Brier": "{:.3f}",
                "Log-loss": "{:.3f}", "RPS": "{:.3f}",
            }).background_gradient(subset=["Top-1"], cmap="Greens")
              .background_gradient(subset=["RPS"], cmap="Reds_r"),
            hide_index=True, use_container_width=True,
        )
    else:
        st.markdown(
            f'<div style="background: rgba(6, 182, 212, 0.05); border: 1px solid rgba(6, 182, 212, 0.2); '
            f'border-radius: 8px; padding: 12px; margin-bottom: 16px;">'
            f'<span style="color: {ACCENT}; font-weight: 700;">⚙️ Calibración personalizada detectada</span> · '
            f'<span style="color: {TEXT};">Memoria Histórica Elo = <b>{half_life:.1f} años</b>. El modelo base usa 8.0 años.</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.caption("Puesto que has calibrado la memoria del modelo, puedes ejecutar el backtest dinámico sobre el historial completo para ver si tu configuración predice mejor o peor que el modelo base.")

        st_key = f"custom_bt_{half_life}"
        
        # Botón para disparar
        if st.button(f"🧪 Comparar Calibración en Vivo ({half_life:.1f} años vs 8.0 años)", type="primary", use_container_width=True):
            with st.spinner("Ejecutando simulación histórica sobre 400+ partidos..."):
                st.session_state[st_key] = get_custom_backtest(half_life)
            st.success("¡Backtest dinámico completado con éxito!")

        if st_key in st.session_state:
            bt_custom = st.session_state[st_key]
            
            # --- COMPARATIVA DE METRICAS PRINCIPALES ---
            o_base = bt_baseline["overall"]
            o_cust = bt_custom["overall"]
            
            diff_hit = o_cust["weighted_hit_rate"] - o_base["weighted_hit_rate"]
            diff_brier = o_cust["weighted_brier"] - o_base["weighted_brier"]
            diff_rps = o_cust["weighted_rps"] - o_base["weighted_rps"]
            
            def fmt_diff(val, invert=False, pct=False):
                mul = 100 if pct else 1
                sym = "%" if pct else ""
                sign = "+" if val > 0 else ""
                
                # invert es True para Brier/RPS donde un valor menor es mejor
                is_better = (val < 0) if invert else (val > 0)
                is_neutral = abs(val) < 1e-6
                
                if is_neutral:
                    return f'<span style="color:{TEXT_DIM}; font-size:0.85rem; font-weight:600;">(Sin cambios)</span>'
                elif is_better:
                    return f'<span style="color:{GOOD}; font-size:0.85rem; font-weight:600;">({sign}{val*mul:+.3f if not pct else val*mul:+.1f}{sym} MEJOR)</span>'
                else:
                    return f'<span style="color:{DANGER}; font-size:0.85rem; font-weight:600;">({sign}{val*mul:+.3f if not pct else val*mul:+.1f}{sym} PEOR)</span>'

            # Cards de métricas
            st.markdown("#### Métricas Agregadas (Mundiales 2010–2022 + Eurocopas 2016–2024)")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(
                    f'<div style="background:{BG_CARD}; border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:15px; text-align:center;">'
                    f'<div style="color:{TEXT_DIM}; font-size:0.75rem; text-transform:uppercase; font-weight:700; letter-spacing:0.5px;">Top-1 Acierto</div>'
                    f'<div style="color:{TEXT}; font-size:1.8rem; font-weight:800; margin:5px 0;">'
                    f'{o_base["weighted_hit_rate"]*100:.1f}% <span style="font-size:1rem; color:{TEXT_DIM};">vs</span> {o_cust["weighted_hit_rate"]*100:.1f}%'
                    f'</div>'
                    f'<div>{fmt_diff(diff_hit, invert=False, pct=True)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with c2:
                st.markdown(
                    f'<div style="background:{BG_CARD}; border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:15px; text-align:center;">'
                    f'<div style="color:{TEXT_DIM}; font-size:0.75rem; text-transform:uppercase; font-weight:700; letter-spacing:0.5px;">Brier Medio</div>'
                    f'<div style="color:{TEXT}; font-size:1.8rem; font-weight:800; margin:5px 0;">'
                    f'{o_base["weighted_brier"]:.3f} <span style="font-size:1rem; color:{TEXT_DIM};">vs</span> {o_cust["weighted_brier"]:.3f}'
                    f'</div>'
                    f'<div>{fmt_diff(diff_brier, invert=True)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with c3:
                st.markdown(
                    f'<div style="background:{BG_CARD}; border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:15px; text-align:center;">'
                    f'<div style="color:{TEXT_DIM}; font-size:0.75rem; text-transform:uppercase; font-weight:700; letter-spacing:0.5px;">RPS Medio</div>'
                    f'<div style="color:{TEXT}; font-size:1.8rem; font-weight:800; margin:5px 0;">'
                    f'{o_base["weighted_rps"]:.3f} <span style="font-size:1rem; color:{TEXT_DIM};">vs</span> {o_cust["weighted_rps"]:.3f}'
                    f'</div>'
                    f'<div>{fmt_diff(diff_rps, invert=True)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            # --- TABLA COMPARATIVA DETALLADA ---
            st.markdown("#### Comparativa torneo a torneo")
            t_base = bt_baseline["tournaments"]
            t_cust = bt_custom["tournaments"]
            
            comp_data = []
            for b, c in zip(t_base, t_cust):
                comp_data.append({
                    "Torneo": b["name"],
                    "Partidos": b["n_matches"],
                    "Top-1 (Base)": b["hit_rate_top1"],
                    "Top-1 (Tuyo)": c["hit_rate_top1"],
                    "Dif. Acierto": c["hit_rate_top1"] - b["hit_rate_top1"],
                    "RPS (Base)": b["rps"],
                    "RPS (Tuyo)": c["rps"],
                    "Dif. RPS": c["rps"] - b["rps"]
                })
            
            df_comp_t = pd.DataFrame(comp_data)
            
            # Pintamos la tabla con estilo premium y color gradients
            st.dataframe(
                df_comp_t.style.format({
                    "Top-1 (Base)": "{:.1%}", "Top-1 (Tuyo)": "{:.1%}", "Dif. Acierto": "{:+.1%}",
                    "RPS (Base)": "{:.3f}", "RPS (Tuyo)": "{:.3f}", "Dif. RPS": "{:+.3f}"
                }).background_gradient(subset=["Dif. Acierto"], cmap="RdYlGn", vmin=-0.05, vmax=0.05)
                  .background_gradient(subset=["Dif. RPS"], cmap="RdYlGn_r", vmin=-0.02, vmax=0.02),
                hide_index=True, use_container_width=True
            )
            st.caption("Una diferencia de acierto positiva (+) y una diferencia de RPS negativa (-) son indicativos de que tu calibración supera al baseline histórico.")
        else:
            st.info("💡 Haz clic en el botón superior para calcular las métricas comparativas del backtest.")

    # Comparativa en vivo vs backtest histórico (se mantiene si hay partidos jugados)
    if n_played > 0:
        o = bt_baseline["overall"]
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.markdown("##### Comparativa: en vivo vs backtest histórico")
        live_stats = stats
        comp_rows = [
            ["Top-1 acierto", live_stats.hit_rate_top1, o["weighted_hit_rate"]],
            ["Brier", live_stats.mean_brier, o["weighted_brier"]],
            ["RPS", live_stats.mean_rps, o["weighted_rps"]],
            ["Log-loss", live_stats.mean_log_loss, o["weighted_log_loss"]],
        ]
        df_comp = pd.DataFrame(comp_rows, columns=["Métrica", "Mundial 2026 (en vivo)", "Backtest histórico"])
        st.dataframe(df_comp.style.format({"Mundial 2026 (en vivo)": "{:.3f}", "Backtest histórico": "{:.3f}"}),
                     hide_index=True, use_container_width=True)
        st.caption(
            "Si Brier/RPS en vivo están **por debajo** del histórico, el modelo está prediciendo "
            "mejor de lo habitual. Si están por encima, peor (más sorpresas o peor calibrado)."
        )


def _render_recent_changes():
    """Muestra el delta entre los dos últimos snapshots: top subidas/bajadas."""
    history = load_history()
    if not history or len(history) < 2:
        return
    prev, curr = history[-2], history[-1]
    teams = set(prev["top_probs"].keys()) | set(curr["top_probs"].keys())
    movers = []
    for t in teams:
        b = prev["top_probs"].get(t, 0.0)
        a = curr["top_probs"].get(t, 0.0)
        movers.append((t, b, a, a - b))
    movers.sort(key=lambda x: -abs(x[3]))
    significant = [m for m in movers if abs(m[3]) >= 0.005][:8]
    if not significant:
        return

    delta_matches = curr["matches_played"] - prev["matches_played"]
    delta_entropy = curr["entropy_bits"] - prev["entropy_bits"]
    label = f"+{delta_matches} partidos" if delta_matches else "mismo punto"

    st.markdown("##### 🔁 Cambios desde el último save")
    cR1, cR2, cR3 = st.columns(3)
    with cR1:
        st.markdown(big_stat(f"{label}", "Snapshot anterior"), unsafe_allow_html=True)
    with cR2:
        st.markdown(big_stat(
            f"{curr['top_pick']} ({curr['top_pick_prob']*100:.1f}%)",
            "Favorito actual",
        ), unsafe_allow_html=True)
    with cR3:
        sign = "+" if delta_entropy >= 0 else ""
        st.markdown(big_stat(
            f"{sign}{delta_entropy:.2f} bits",
            "Apertura del torneo (Δ)",
        ), unsafe_allow_html=True)

    # Render movers como chips coloreadas
    chips_html = '<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">'
    for team, before, after, delta in significant:
        color = GOOD if delta > 0 else DANGER
        arrow = "▲" if delta > 0 else "▼"
        iso = ISO_CODES.get(team, "un")
        chips_html += (
            f'<div style="background:{BG_CARD}; border:1px solid {color}; border-radius:10px; '
            f'padding:8px 14px; display:flex; align-items:center; gap:8px;">'
            f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:22px; height:16px; border-radius:2px;">'
            f'<div>'
            f'<div style="font-weight:700; font-size:0.85rem;">{team}</div>'
            f'<div style="font-size:0.75rem; color:{TEXT_DIM};">{before*100:.1f}% → {after*100:.1f}%</div>'
            f'</div>'
            f'<div style="color:{color}; font-weight:800; font-size:0.95rem;">{arrow} {abs(delta)*100:.2f}pp</div>'
            f'</div>'
        )
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
