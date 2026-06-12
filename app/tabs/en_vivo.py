"""Pestaña 'En vivo': calculadora de probabilidades minuto a minuto."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from app.utils import get_elo_with_biases, load_real_results
from app.styles import PRIMARY, ACCENT, TEXT_DIM, BG_CARD, GOOD
from app.components_day import render_live_widget, render_upcoming_card
from src.model.match_day import (
    find_upcoming_matches, find_recently_played, _wc_schedule
)
from src.data.team_names import EN_TO_ES
from src.data.team_profile import ISO_CODES
from src.model.poisson import expected_goals_ensemble
from src.model.match_day import _host_advantage
from src.tournament.groups import HOST_NATIONS
from src.model.match_probs import top_exact_scores, match_outcome_probs


def render():
    st.header("⚡ En vivo")
    st.caption(
        "Calculadora de probabilidades minuto a minuto. Elige un partido del Mundial, "
        "introduce el minuto actual y el marcador, y verás cómo cambian las probabilidades en tiempo real."
    )

    elo = get_elo_with_biases()
    real_results = load_real_results()

    # === Selector de partido ===
    df = _wc_schedule()
    df = df.sort_values("date").reset_index(drop=True)
    options = []
    for idx, row in df.iterrows():
        h = EN_TO_ES.get(row["home_team"], row["home_team"])
        a = EN_TO_ES.get(row["away_team"], row["away_team"])
        date = row["date"].strftime("%d %b %H:%M")
        played = "✅" if pd.notna(row["home_score"]) else "🔵"
        options.append((idx, f"{played} {date} · {h} vs {a}"))

    # Default = próximo partido pendiente (o el primero del calendario)
    default_idx = 0
    upcoming = find_upcoming_matches(elo, window_hours=36, fallback_days=30)
    if upcoming:
        first_up = upcoming[0]
        for idx, label in options:
            if first_up.home in label and first_up.away in label:
                default_idx = idx
                break

    selected_label = st.selectbox(
        "Selecciona el partido",
        [label for _, label in options],
        index=default_idx,
    )
    selected_idx = next(i for i, lbl in options if lbl == selected_label)
    row = df.iloc[selected_idx]

    home_es = EN_TO_ES.get(row["home_team"], row["home_team"])
    away_es = EN_TO_ES.get(row["away_team"], row["away_team"])
    elo_h = elo.get(home_es, 1500.0)
    elo_a = elo.get(away_es, 1500.0)
    ha = _host_advantage(home_es, away_es) if not row.get("neutral", True) else 0.0
    lh, la = expected_goals_ensemble(elo_h, elo_a, home_es, away_es, home_advantage=ha)
    p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
    top = top_exact_scores(lh, la, n=5, use_dc=True)

    # === Predicción pre-partido (referencia) ===
    st.markdown("##### Predicción del modelo PRE-partido")
    iso_h = ISO_CODES.get(home_es, "un")
    iso_a = ISO_CODES.get(away_es, "un")
    st.markdown(
        f"""
        <div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:12px; padding:14px;">
            <div style="display:flex; align-items:center; justify-content:center; gap:18px; font-size:1rem; font-weight:600;">
                <img src="https://flagcdn.com/w40/{iso_h}.png" style="width:26px;height:18px;border-radius:2px;"> {home_es}
                <span style="color:{TEXT_DIM};">vs</span>
                <img src="https://flagcdn.com/w40/{iso_a}.png" style="width:26px;height:18px;border-radius:2px;"> {away_es}
            </div>
            <div style="margin-top:8px; display:flex; justify-content:center; gap:18px; font-size:0.85rem; color:{TEXT_DIM};">
                <span>Elo {int(elo_h)} – {int(elo_a)}</span>
                <span>λ {lh:.2f} – {la:.2f}</span>
                <span>{p_h*100:.0f}% / {p_d*100:.0f}% / {p_a*100:.0f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top scores compactos
    score_html = '<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; justify-content:center;">'
    for (h, a), p in top:
        score_html += (
            f'<div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:8px; padding:6px 10px; min-width:78px; text-align:center;">'
            f'<div style="font-size:1.05rem; font-weight:800;">{h}-{a}</div>'
            f'<div style="font-size:0.72rem; color:{PRIMARY}; font-weight:600;">{p*100:.1f}%</div>'
            f'</div>'
        )
    score_html += "</div>"
    st.markdown(score_html, unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Widget en vivo ===
    render_live_widget(
        default_home=home_es, default_away=away_es,
        default_lh=lh, default_la=la,
        key_prefix=f"live_{selected_idx}",
    )

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Tabla de evolución (cómo cambian las probs cada 15 min) ===
    st.markdown("##### Cómo cambian las probabilidades si el partido va 0-0")
    st.caption("Evolución hipotética minuto a minuto manteniendo el 0-0. Útil para entender la 'cuenta atrás' del modelo.")
    from src.model.match_probs import live_outcome_probs
    minutes = [0, 15, 30, 45, 60, 75, 85, 90]
    rows = []
    for m in minutes:
        live = live_outcome_probs(lh, la, m, 0, 0)
        rows.append({
            "Minuto": m,
            f"V {home_es}": live["p_home"],
            "Empate": live["p_draw"],
            f"V {away_es}": live["p_away"],
        })
    df_evo = pd.DataFrame(rows)
    st.dataframe(
        df_evo.style.format({
            f"V {home_es}": "{:.0%}",
            "Empate": "{:.0%}",
            f"V {away_es}": "{:.0%}",
        }).background_gradient(subset=[f"V {home_es}"], cmap="Greens")
          .background_gradient(subset=["Empate"], cmap="Greys")
          .background_gradient(subset=[f"V {away_es}"], cmap="Oranges"),
        hide_index=True, use_container_width=True,
    )
