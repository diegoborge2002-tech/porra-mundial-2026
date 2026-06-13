"""Pestana de calendario del Mundial 2026 - 104 partidos."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import math
import datetime

from app.utils import ROOT, get_elo_with_biases
from app.components_media import render_tab_banner
from app.styles import TEXT_DIM, PRIMARY, ACCENT, GOOD, DANGER
from src.data.team_names import EN_TO_ES
from src.data.venues import VENUE_ALTITUDE
from src.model.poisson import expected_goals_ensemble
from src.model.match_probs import top_exact_scores, match_outcome_probs
from src.tournament.groups import GROUPS


def get_exact_score_probabilities(lh: float, la: float, top_n: int = 5) -> list[tuple[tuple[int, int], float]]:
    """Wrapper de compatibilidad: usa el modelo Dixon-Coles del módulo compartido."""
    return top_exact_scores(lh, la, n=top_n, use_dc=True)


def _load_wc_matches() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "raw" / "results.csv")
    df["date"] = pd.to_datetime(df["date"])
    wc = df[df["date"] >= "2026-06-01"].copy()
    # Traducir nombres
    wc["home_es"] = wc["home_team"].map(lambda x: EN_TO_ES.get(x, x))
    wc["away_es"] = wc["away_team"].map(lambda x: EN_TO_ES.get(x, x))
    wc["jugado"] = wc["home_score"].notna()
    return wc.sort_values("date").reset_index(drop=True)


def render():
    st.header("Calendario del Mundial")
    st.caption("Los 72 partidos de la fase de grupos · los 32 cruces eliminatorios están en la pestaña 🔮 Partidos")
    render_tab_banner("map_motif.png")

    elo = get_elo_with_biases()
    matches = _load_wc_matches()

    # =========================================================================
    # ⏰ BANNER DE CUENTA REGRESIVA PREMIUM
    # =========================================================================
    today = datetime.date.today()
    wc_start = datetime.date(2026, 6, 11)
    
    if today < wc_start:
        days_left = (wc_start - today).days
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.65) 0%, rgba(6, 182, 212, 0.05) 100%); 
                        border: 1px solid rgba(6, 182, 212, 0.15); border-radius: 12px; padding: 16px; margin-bottom: 24px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: softPulse 3s infinite;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <h4 style="margin: 0; color: {PRIMARY}; font-size: 1.15rem; font-weight: 800;">🏆 Copa del Mundo FIFA 2026</h4>
                        <p style="margin: 4px 0 0 0; color: {TEXT_DIM}; font-size: 0.82rem;">
                            Partido inaugural: <b>México vs Sudáfrica</b> en el Estadio Azteca 🇲🇽
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.7rem; font-weight: 900; color: {PRIMARY}; text-shadow: 0 0 10px rgba(6,182,212,0.3);">
                            Faltan {days_left} días
                        </span>
                        <div style="font-size: 0.65rem; color: {TEXT_DIM}; text-transform: uppercase; letter-spacing: 0.05em;">Para el pitazo inicial</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # =========================================================================
    # 🎛️ FILTROS AVANZADOS DE BÚSQUEDA
    # =========================================================================
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        all_teams = sorted(set(matches["home_es"]) | set(matches["away_es"]))
        team_filter = st.selectbox("Filtrar por equipo", ["Todos"] + all_teams)
    with c2:
        group_filter = st.selectbox("Filtrar por Grupo", ["Todos"] + sorted(list(GROUPS.keys())))
    with c3:
        date_min, date_max = matches["date"].min().date(), matches["date"].max().date()
        date_range = st.date_input("Rango de fechas", value=(date_min, date_max),
                                   min_value=date_min, max_value=date_max)
    with c4:
        status_filter = st.selectbox("Estado", ["Todos", "Pendientes", "Jugados"])

    # === Mapa de sedes ===
    with st.expander("🗺️ Mapa de sedes del Mundial 2026", expanded=False):
        _render_venues_map(matches)

    # Aplicar filtros
    filtered = matches.copy()
    if team_filter != "Todos":
        filtered = filtered[(filtered["home_es"] == team_filter) | (filtered["away_es"] == team_filter)]
    if group_filter != "Todos":
        group_teams = GROUPS[group_filter]
        filtered = filtered[(filtered["home_es"].isin(group_teams)) | (filtered["away_es"].isin(group_teams))]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        d1, d2 = date_range
        filtered = filtered[(filtered["date"].dt.date >= d1) & (filtered["date"].dt.date <= d2)]
    if status_filter == "Pendientes":
        filtered = filtered[~filtered["jugado"]]
    elif status_filter == "Jugados":
        filtered = filtered[filtered["jugado"]]

    st.caption(f"Mostrando **{len(filtered)}** partidos")

    from src.data.team_profile import ISO_CODES
    
    # Agrupados por fecha
    for date, group in filtered.groupby("date"):
        st.markdown(f"##### {date.strftime('%A, %d %b %Y').capitalize()}")
        for _, m in group.iterrows():
            home, away = m["home_es"], m["away_es"]
            elo_h, elo_a = elo.get(home, 1500), elo.get(away, 1500)
            lh, la = expected_goals_ensemble(elo_h, elo_a, home, away)
            iso_h = ISO_CODES.get(home, "un")
            iso_a = ISO_CODES.get(away, "un")
            
            # Obtener grupo
            group_letter = ""
            for gl, gteams in GROUPS.items():
                if home in gteams:
                    group_letter = f"Grupo {gl}"
                    break

            if m["jugado"]:
                score_html = f'<span class="match-score">{int(m["home_score"])} - {int(m["away_score"])}</span>'
            else:
                # Prediccion del modelo: 1X2 desde las lambdas del ensemble (Dixon-Coles)
                from src.model.match_probs import match_outcome_probs
                p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
                score_html = (
                    f'<span style="color:{TEXT_DIM}; font-size:0.8rem; text-align:right;">'
                    f'<span title="Probabilidad victoria local">{p_h*100:.0f}%</span> · '
                    f'<span title="Probabilidad empate">{p_d*100:.0f}%</span> · '
                    f'<span title="Probabilidad victoria visitante">{p_a*100:.0f}%</span>'
                    f'<br><span style="color:#9ca3af; font-size:0.7rem;">Goles esperados: {lh:.1f} – {la:.1f}</span>'
                    f'</span>'
                )
            
            city = m.get("city") if "city" in m else None
            if city is None or (isinstance(city, float) and pd.isna(city)):
                city = ""
            alt = VENUE_ALTITUDE.get(str(city), 0)
            alt_badge = ""
            if alt > 1500:
                alt_badge = f'<span style="color:{ACCENT}; font-size:0.7rem; margin-left:6px;" title="Altitud elevada">⛰ {alt}m</span>'
            venue_html = (f'<span style="color:{TEXT_DIM}; font-size:0.7rem; margin-left:6px;">📍 {city}{alt_badge}</span>'
                          if city else "")
            
            # Render del renglon principal de partido
            st.markdown(
                f'<div class="match-row">'
                f'<span class="match-date">{date.strftime("%H:%M") if date.hour else ""}</span>'
                f'<span class="match-teams" style="display:flex; align-items:center; gap:8px;">'
                f'<img src="https://flagcdn.com/w40/{iso_h}.png" style="width:24px; height:18px; border-radius:2px;">'
                f'<span>{home}</span>'
                f'<span style="color:{TEXT_DIM}">vs</span>'
                f'<img src="https://flagcdn.com/w40/{iso_a}.png" style="width:24px; height:18px; border-radius:2px;">'
                f'<span>{away}</span>'
                f'<span style="background: rgba(255,255,255,0.03); color: {TEXT_DIM}; font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">{group_letter}</span>'
                f'{venue_html}'
                f'</span>'
                f'{score_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
            
            # Centro de Partido Interactivo (Estadísticas, H2H y Marcadores)
            with st.expander(f"⚽ Centro de Partido: {home} vs {away}", expanded=False):
                from src.data.h2h import get_h2h
                h2h = get_h2h(home, away)
                exact_probs = get_exact_score_probabilities(lh, la, top_n=5)
                
                ch2h, cscores = st.columns(2)
                with ch2h:
                    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-bottom:6px;'>⚔️ Historial Cara a Cara (H2H)</p>", unsafe_allow_html=True)
                    if h2h.total > 0:
                        p_wins_h = (h2h.wins_a / h2h.total) * 100
                        p_draws = (h2h.draws / h2h.total) * 100
                        p_wins_a = (h2h.wins_b / h2h.total) * 100
                        
                        st.markdown(
                            f"""
                            <div style="font-size:0.75rem; color:{TEXT_DIM}; margin-bottom:4px;">
                                Partidos registrados: <b>{h2h.total}</b> · Primero en: <b>{h2h.first_match_date[:4]}</b>
                            </div>
                            <div style="margin-bottom:12px;">
                                <div style="display:flex; justify-content:space-between; font-size:0.74rem; margin-bottom:4px;">
                                    <span style="color:{PRIMARY}; font-weight:700;">{home} ({h2h.wins_a})</span>
                                    <span style="color:{TEXT_DIM}; font-weight:600;">Empates ({h2h.draws})</span>
                                    <span style="color:{ACCENT}; font-weight:700;">{away} ({h2h.wins_b})</span>
                                </div>
                                <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.02);">
                                    <div style="width:{p_wins_h}%; background:{PRIMARY};"></div>
                                    <div style="width:{p_draws}%; background:#475569;"></div>
                                    <div style="width:{p_wins_a}%; background:{ACCENT};"></div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        # Lista de partidos recientes
                        recent_h2h = []
                        for rm in h2h.last_matches[:3]:
                            recent_h2h.append(
                                f'<div style="font-size:0.73rem; color:{TEXT_DIM}; margin:3px 0;">'
                                f'• {rm.date[:4]} ({rm.tournament[:12]}): {rm.home} <b>{rm.home_goals} - {rm.away_goals}</b> {rm.away}'
                                f'</div>'
                            )
                        st.markdown("".join(recent_h2h), unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div style="background: rgba(6, 182, 212, 0.03); border: 1px dashed rgba(6, 182, 212, 0.15); border-radius: 8px; padding: 10px; text-align: center; font-size: 0.74rem; color: {PRIMARY}; font-weight: 600;">'
                            f'⚔️ ¡Primer enfrentamiento histórico en partidos oficiales!'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        
                with cscores:
                    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-bottom:6px;'>🎯 Marcadores Exactos Más Probables</p>", unsafe_allow_html=True)
                    for (hg, ag), p in exact_probs:
                        st.markdown(
                            f"""
                            <div style="display:flex; align-items:center; justify-content:space-between; margin:4px 0; font-size:0.75rem;">
                                <span style="font-weight:700; width:55px; color:#ffffff;">{hg} - {ag}</span>
                                <div style="flex:1; height:6px; background:rgba(255,255,255,0.05); border-radius:3px; margin:0 10px; overflow:hidden;">
                                    <div style="width:{p*100}%; background:linear-gradient(90deg, {PRIMARY} 0%, {ACCENT} 100%); height:100%;"></div>
                                </div>
                                <span style="color:{PRIMARY}; font-weight:700; width:45px; text-align:right;">{p*100:.1f}%</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                # Advertencia de Altitud
                if alt > 1500:
                    st.markdown(
                        f"""
                        <div style="background: rgba(139, 92, 246, 0.04); border: 1px solid rgba(139, 92, 246, 0.12); border-radius: 8px; padding: 10px; margin-top: 10px;">
                            <p style="color: {ACCENT}; font-size: 0.76rem; font-weight: 700; margin: 0 0 3px 0;">⛰️ Alerta de Oxígeno / Altitud ({alt}m en {city})</p>
                            <p style="color: {TEXT_DIM}; font-size: 0.72rem; line-height: 1.35; margin: 0;">
                                El aire a esta altitud reduce la resistencia aerobica. El balon viaja un ~5% mas veloz en disparos de larga distancia. 
                                El modelo compensa la fatiga acumulada en selecciones con menor profundidad de plantilla.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )



def _render_venues_map(matches: pd.DataFrame):
    """Mapa Plotly Geo con las 16 sedes coloreadas por altitud y tamaño por partidos."""
    import plotly.graph_objects as go
    from src.data.venues import VENUE_COORDS, VENUE_ALTITUDE, VENUE_COUNTRY

    # Contar partidos por sede
    counts = matches.groupby("city").size().to_dict()
    rows = []
    for city, (lat, lon) in VENUE_COORDS.items():
        rows.append({
            "city": city,
            "lat": lat, "lon": lon,
            "altitude": VENUE_ALTITUDE.get(city, 0),
            "matches": counts.get(city, 0),
            "country": VENUE_COUNTRY.get(city, "USA"),
        })
    df = pd.DataFrame(rows)
    # Quedarse sólo con sedes que tienen partidos asignados
    df = df[df["matches"] > 0]
    if df.empty:
        st.info("No hay sedes con partidos asignados en el dataset.")
        return

    fig = go.Figure(go.Scattergeo(
        lon=df["lon"], lat=df["lat"],
        text=df.apply(lambda r: f"<b>{r['city']}</b> ({r['country']})<br>"
                                f"Altitud: {r['altitude']}m<br>"
                                f"Partidos: {r['matches']}", axis=1),
        mode="markers",
        marker=dict(
            size=df["matches"] * 4 + 10,
            color=df["altitude"],
            colorscale="Viridis",
            colorbar=dict(title="Altitud (m)"),
            line=dict(color="white", width=1),
            sizemode="area",
        ),
        hovertemplate="%{text}<extra></extra>",
        name="Sedes",
    ))
    fig.update_layout(
        geo=dict(
            scope="north america",
            projection_type="mercator",
            showland=True, landcolor="#1f2937",
            showcountries=True, countrycolor="#374151",
            showocean=True, oceancolor="#0a0e14",
            bgcolor="#111827",
            lataxis_range=[15, 60], lonaxis_range=[-130, -65],
        ),
        plot_bgcolor="#111827", paper_bgcolor="#111827",
        font=dict(color=TEXT_DIM),
        height=450, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"🇲🇽 México · 🇺🇸 USA · 🇨🇦 Canadá — {len(df)} sedes activas. "
        f"Tamaño del punto = nº de partidos. Color = altitud."
    )
