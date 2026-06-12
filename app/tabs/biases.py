"""Pestana de ajustes manuales (biases) por equipo - rediseno."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from app.utils import load_base_elo, get_biases
from app.components import big_stat
from app.styles import PRIMARY, ACCENT, TEXT, TEXT_DIM, GOOD, DANGER
from src.tournament.groups import GROUPS, HOST_NATIONS, ALL_TEAMS
from src.data.team_profile import ISO_CODES


SLIDER_HELP = (
    "Ajuste manual a la fortaleza del equipo, en puntos Elo. "
    "Cada +50 puntos = +20% probabilidad de ganar un partido parejo. "
    "Reflejas: estado de forma, lesiones, generacion, motivacion, sede..."
)


def render():
    st.header("Mis ajustes")
    st.caption("Configura el motor matemático subyacente y aplica tus propios sesgos de intuición futbolística sobre el Elo.")

    cfg = get_biases()

    # =========================================================================
    # 📊 SECCIÓN 1: MOTOR MATEMÁTICO (DATO PURO - CIAN)
    # =========================================================================
    st.markdown(
        f'<div class="card-mates">'
        f'<div class="badge-mates">📊 Motor Matemático (El Dato Objetivo)</div>'
        f'<h3 style="color: {PRIMARY}; margin-top: 4px; margin-bottom: 8px; font-size: 1.35rem;">⚙️ Calibración del Motor de Simulación</h3>'
        f'<p style="color: {TEXT_DIM}; font-size: 0.88rem; line-height: 1.5; margin-bottom: 18px;">'
        f'Controla el comportamiento de las matemáticas de simulación. Ajusta la memoria temporal del Elo histórico y la ponderación en tiempo real del valor de mercado de Transfermarkt.</p>',
        unsafe_allow_html=True
    )

    c_half, c_club = st.columns(2)

    with c_half:
        st.markdown(f"##### ⏳ Memoria Histórica (Elo)", unsafe_allow_html=True)
        st.caption("Pondera qué tan atrás en el tiempo mira el modelo.")
        new_half_life = st.slider(
            "Vida media de partidos (años)",
            2.0, 15.0, float(cfg.half_life), step=0.5,
            key="model_half_life",
            help="Una vida media menor (ej. 3.0 años) devalúa los partidos antiguos con rapidez, dando un peso sustancial al rendimiento en los últimos ciclos. Una vida media alta (ej. 10.0 años) valora la consistencia histórica a largo plazo."
        )
        if new_half_life != cfg.half_life:
            cfg.half_life = new_half_life
            st.rerun()

    with c_club:
        st.markdown(f"##### 🏆 Factor Plantilla & Clubs (Transfermarkt)", unsafe_allow_html=True)
        st.caption("Inyecta calidad del fútbol de clubs en el Elo.")
        new_use_club = st.toggle(
            "Vincular poderío de clubs en vivo",
            value=cfg.use_club_performance,
            key="model_use_club",
            help="Si se activa, el simulador aplicará un modificador automático de Elo a cada selección según el valor de mercado logarítmico de su plantilla confirmada y la cantidad de estrellas jugando en la élite de Europa."
        )
        if new_use_club != cfg.use_club_performance:
            cfg.use_club_performance = new_use_club
            st.rerun()

    if cfg.use_club_performance:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        c_w1, c_w2, c_w3 = st.columns(3)
        with c_w1:
            new_w_mv = st.slider(
                "Intensidad Valor de Mercado (M€)",
                0.0, 2.0, float(cfg.weight_market_value), step=0.1,
                key="model_weight_mv",
                help="Controla el impacto del valor de mercado logarítmico total de la plantilla (Transfermarkt) sobre el Elo."
            )
            if new_w_mv != cfg.weight_market_value:
                cfg.weight_market_value = new_w_mv
                st.rerun()
        with c_w2:
            new_w_ped = st.slider(
                "Intensidad Pedigrí de Élite",
                0.0, 2.0, float(cfg.weight_club_pedigree), step=0.1,
                key="model_weight_pedigree",
                help="Controla la bonificación otorgada por jugadores en equipos de la élite de Champions (ej. Real Madrid, Man City, Bayern, PSG...)."
            )
            if new_w_ped != cfg.weight_club_pedigree:
                cfg.weight_club_pedigree = new_w_ped
                st.rerun()
        with c_w3:
            curr_w_form = cfg.weight_recent_form if hasattr(cfg, "weight_recent_form") else 1.0
            new_w_form = st.slider(
                "Intensidad Forma Reciente",
                0.0, 2.0, float(curr_w_form), step=0.1,
                key="model_weight_recent_form",
                help="Controla el impacto del rendimiento de los jugadores en sus clubes en los últimos 3 meses (Forma 1.0 - 10.0)."
            )
            if new_w_form != curr_w_form:
                cfg.weight_recent_form = new_w_form
                st.rerun()

        # Previsualización de impacto en vivo
        from src.data.squad import load_squad, calculate_club_performance_bias
        
        impact_rows = []
        for team in ALL_TEAMS:
            squad = load_squad(team)
            if squad.players:
                total_mv = sum(p.market_value for p in squad.players if p.market_value is not None)
                club_delta = calculate_club_performance_bias(
                    squad, 
                    weight_mv=cfg.weight_market_value, 
                    weight_pedigree=cfg.weight_club_pedigree,
                    weight_recent_form=cfg.weight_recent_form
                )
                impact_rows.append({
                    "Selección": team,
                    "Valor Plantilla (M€)": f"{total_mv:.1f} M€",
                    "Impacto Elo Base": f"{club_delta:+.1f} pts"
                })

        if impact_rows:
            with st.expander("📈 Ver impacto en vivo del Factor Club sobre el Elo base", expanded=False):
                df_impact = pd.DataFrame(impact_rows).sort_values("Impacto Elo Base", ascending=False).reset_index(drop=True)
                st.dataframe(
                    df_impact,
                    hide_index=True,
                    use_container_width=True
                )

    # --- Mezcla de modelos: Elo vs XGBoost de stats ---
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(f"##### 🧬 Mezcla de modelos (Elo ↔ XGBoost de stats)", unsafe_allow_html=True)
    from src.model import ensemble as _ens
    if _ens.stats_available():
        meta = _ens.get_stats_meta()
        st.caption(
            "El Elo solo ve resultados; el modelo XGBoost (repo Simulaciones_Mundial) ve CÓMO juega "
            "cada equipo: xG, posesión, remates y ranking FIFA de los últimos 5 años. "
            "Si crees que el Elo no es representativo, sube este peso."
        )
        new_sw = st.slider(
            "Peso del modelo de stats en los goles esperados",
            0.0, 1.0, float(cfg.stats_weight), step=0.05,
            key="model_stats_weight",
            help=(
                "0.0 = solo Elo (modelo clásico) · 1.0 = solo XGBoost-stats. "
                f"El modelo de stats acertó el {meta.get('holdout', {}).get('accuracy', 0)*100:.0f}% "
                "de los 1X2 en su holdout temporal 2025-26. Recomendado: 0.5."
            ),
        )
        if new_sw != cfg.stats_weight:
            cfg.stats_weight = new_sw
            _ens.set_stats_weight(new_sw)
            st.rerun()
        wl, wr = (1 - cfg.stats_weight) * 100, cfg.stats_weight * 100
        st.markdown(
            f'<div style="display:flex; height:8px; border-radius:4px; overflow:hidden; max-width:480px;">'
            f'<div style="width:{wl:.0f}%; background:{PRIMARY};" title="Elo {wl:.0f}%"></div>'
            f'<div style="width:{wr:.0f}%; background:{ACCENT};" title="Stats {wr:.0f}%"></div></div>'
            f'<p style="color:{TEXT_DIM}; font-size:0.75rem; margin-top:4px;">'
            f'<span style="color:{PRIMARY};">⚖️ Elo {wl:.0f}%</span> · '
            f'<span style="color:{ACCENT};">🤖 XGBoost-stats {wr:.0f}%</span></p>',
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "Modelo de stats no disponible. Genera `data/processed/stats_model.json` con "
            "`python notebooks/04_entrenar_stats_model.py` para activar el ensemble."
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # ✨ SECCIÓN 2: JUICIO HUMANO (INTUICIÓN - VIOLETA)
    # =========================================================================
    st.markdown(
        f'<div class="card-intuicion">'
        f'<div class="badge-intuicion">✨ Juicio Humano (Tu Intuición)</div>'
        f'<h3 style="color: {ACCENT}; margin-top: 4px; margin-bottom: 8px; font-size: 1.35rem;">🔮 Ajustes de Intuición Futbolística</h3>'
        f'<p style="color: {TEXT_DIM}; font-size: 0.88rem; line-height: 1.5; margin-bottom: 18px;">'
        f'Inyecta tus corazonadas y conocimientos extra-futbolísticos. Ajusta manualmente el Elo de selecciones específicas (ej. lesiones de última hora, dinámicas de equipo, o corazón de localía) para desviar la predicción puramente matemática.</p>'
        f'<div style="background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 8px; padding: 12px; margin-bottom: 20px; text-align: center; font-size: 0.85rem; font-weight: 600; color: {TEXT};">'
        f'FÓRMULA ELO FINAL: <span style="color: {PRIMARY}; font-weight:700;">Elo Base</span> + '
        f'<span style="color: {PRIMARY}; font-weight:700;">Club Factor (Cian)</span> ± '
        f'<span style="color: {ACCENT}; font-weight:700;">Tu Ajuste (Violeta)</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    base = load_base_elo()
    
    active = [(t, b.elo_delta, b.reason) for t, b in cfg.team_biases.items() if b.elo_delta != 0]
    cA, cB, cC, cD = st.columns([1, 1, 1, 2])
    with cA:
        st.markdown(big_stat(f"{len(active)}", "Equipos ajustados"), unsafe_allow_html=True)
    with cB:
        positives = sum(1 for _, d, _ in active if d > 0)
        st.markdown(big_stat(f"{positives}", "Reforzados"), unsafe_allow_html=True)
    with cC:
        negatives = sum(1 for _, d, _ in active if d < 0)
        st.markdown(big_stat(f"{negatives}", "Debilitados"), unsafe_allow_html=True)
    with cD:
        if st.button("💾 Guardar configuración", type="primary", use_container_width=True):
            cfg.save()
            st.success("Configuración guardada correctamente")
        if st.button("🔄 Resetear sesgos manuales a 0", use_container_width=True):
            for team in list(cfg.team_biases.keys()):
                cfg.team_biases[team].elo_delta = 0.0
            st.rerun()

    if cfg.notes:
        with st.expander(f"📝 Notas pendientes ({len(cfg.notes)})", expanded=False):
            for n in cfg.notes:
                st.markdown(f"• {n}")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Sliders en cards por grupo
    grids = st.columns(2)
    for i, letter in enumerate(sorted(GROUPS)):
        with grids[i % 2]:
            st.markdown(f"<h4 style='color:{ACCENT}; margin-bottom:8px;'>Grupo {letter}</h4>", unsafe_allow_html=True)
            for team in GROUPS[letter]:
                current = cfg.get_delta(team)
                iso = ISO_CODES.get(team, "un")
                is_host = team in HOST_NATIONS
                club_delta = 0.0
                if cfg.use_club_performance:
                    from src.data.squad import load_squad, calculate_club_performance_bias
                    squad = load_squad(team)
                    club_delta = calculate_club_performance_bias(
                        squad, 
                        weight_mv=cfg.weight_market_value, 
                        weight_pedigree=cfg.weight_club_pedigree,
                        weight_recent_form=cfg.weight_recent_form
                    )
                
                final_elo = base[team] + current + club_delta
                delta_color = ACCENT if current > 0 else (DANGER if current < 0 else TEXT_DIM)
                delta_sign = "+" if current > 0 else ""
                badge = " 🏠" if is_host else ""
                club_badge = f" (Club {club_delta:+.0f})" if cfg.use_club_performance and club_delta != 0 else ""
                
                # Desglose matemático ultra-explícito en los sliders
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px; margin-top:8px;">'
                    f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:28px; height:21px; border-radius:3px;">'
                    f'<span style="color:{TEXT}; font-weight:600; flex:1;">{team}{badge}</span>'
                    f'<span style="color:{TEXT_DIM}; font-size:0.8rem;">base {base[team]:.0f}<span style="color:{PRIMARY};">{club_badge}</span> + <span style="color:{ACCENT};">ajuste {current:+.0f}</span> → </span>'
                    f'<span style="color:#ffffff; text-shadow:0 0 10px rgba(6,182,212,0.4); font-weight:800; font-size: 1.02rem;">{final_elo:.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                delta = st.slider(
                    f"Ajuste {team}", -150, 150, int(current), step=5,
                    key=f"bias_{team}", help=SLIDER_HELP, label_visibility="collapsed",
                )
                reason_default = cfg.team_biases[team].reason if team in cfg.team_biases else ""
                reason = st.text_input(
                    "Motivo", value=reason_default, key=f"reason_{team}",
                    placeholder="Motivo del ajuste (opcional)", label_visibility="collapsed",
                )
                cfg.set_bias(team, delta, reason)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    st.subheader("Resumen de ajustes activos")
    if active:
        df = pd.DataFrame(active, columns=["Equipo", "Ajuste Elo", "Motivo"])
        df = df.sort_values("Ajuste Elo", ascending=False).reset_index(drop=True)
        st.dataframe(
            df.style.background_gradient(subset=["Ajuste Elo"], cmap="RdYlGn", vmin=-100, vmax=100),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("Sin sesgos manuales activos: Elo base sin retoques (la mezcla con XGBoost se controla arriba).")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _render_news_editor()


def _render_news_editor() -> None:
    """Editor de noticias / lesiones / cambios de plantilla.

    Cada noticia aplica un delta Elo temporal al equipo (si elo_delta != 0).
    """
    from src.data.news import (
        list_news, add_news, delete_news, toggle_active, NEWS_TYPES,
    )
    from src.tournament.groups import ALL_TEAMS
    from datetime import date, timedelta

    st.subheader("📰 Noticias del Mundial")
    st.caption(
        "Lesiones, bajas, cambios técnicos o refuerzos. Cada noticia puede aplicar "
        "un **delta Elo temporal** al equipo y se muestra como banner en el home."
    )

    items = list_news(only_active=False)
    n_active = sum(1 for n in items if n.active)
    n_total = len(items)

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total noticias", n_total)
    kpi2.metric("Activas", n_active)
    deltas = sum(n.elo_delta for n in items if n.active)
    kpi3.metric("Suma Δ Elo activas", f"{deltas:+.0f}")

    with st.expander("➕ Añadir nueva noticia", expanded=(n_total == 0)):
        with st.form("add_news_form", clear_on_submit=True):
            cc1, cc2 = st.columns(2)
            with cc1:
                equipo = st.selectbox("Equipo", sorted(ALL_TEAMS), key="news_team")
                tipo = st.selectbox(
                    "Tipo",
                    list(NEWS_TYPES.keys()),
                    format_func=lambda x: f"{NEWS_TYPES[x][0]} {NEWS_TYPES[x][1]}",
                    key="news_type",
                )
            with cc2:
                elo_delta = st.slider(
                    "Delta Elo (puntos)", -80, 80, 0, step=5, key="news_delta",
                    help="Negativo si la noticia debilita (lesión, baja). "
                          "Positivo si refuerza (recuperación, refuerzo).",
                )
                vence = st.date_input(
                    "Caduca el (opcional)", value=None,
                    min_value=date.today(), max_value=date(2026, 7, 19),
                    key="news_expires",
                )
            texto = st.text_input("Texto", placeholder="ej: Lesión de Pedri, fuera 3 semanas",
                                   key="news_text")
            submitted = st.form_submit_button("📰 Guardar noticia", use_container_width=True)
            if submitted:
                if not texto.strip():
                    st.error("Falta el texto.")
                else:
                    add_news(
                        equipo=equipo, tipo=tipo, texto=texto.strip(),
                        elo_delta=float(elo_delta),
                        expires_at=vence.isoformat() if vence else None,
                    )
                    st.cache_data.clear()
                    st.success(f"Noticia añadida para **{equipo}**.")
                    st.rerun()

    if not items:
        st.info("Sin noticias todavía. Añade la primera.")
        return

    st.markdown("##### Listado")
    for n in items:
        emoji, label = NEWS_TYPES.get(n.tipo, ("📰", "Otro"))
        is_expired = n.expires_at and n.expires_at < date.today().isoformat()
        status = "🟢" if (n.active and not is_expired) else ("⏰" if is_expired else "⚪")
        col_text, col_delta, col_toggle, col_del = st.columns([8, 1.4, 1.2, 0.8])
        with col_text:
            exp_str = f" · expira {n.expires_at}" if n.expires_at else ""
            st.markdown(
                f"{status} **{emoji} {n.equipo}** — *{label}*  \n"
                f"<span style='color:{TEXT_DIM}; font-size:0.8rem;'>"
                f"{n.fecha}{exp_str}</span>  \n"
                f"{n.texto}",
                unsafe_allow_html=True,
            )
        with col_delta:
            if n.elo_delta:
                color = GOOD if n.elo_delta > 0 else DANGER
                sign = "+" if n.elo_delta > 0 else ""
                st.markdown(
                    f"<div style='text-align:right; font-weight:800; color:{color};'>"
                    f"{sign}{int(n.elo_delta)} Elo</div>",
                    unsafe_allow_html=True,
                )
        with col_toggle:
            label_btn = "Desactivar" if n.active else "Activar"
            if st.button(label_btn, key=f"toggle_{n.id}"):
                toggle_active(n.id)
                st.cache_data.clear()
                st.rerun()
        with col_del:
            if st.button("🗑", key=f"del_{n.id}"):
                delete_news(n.id)
                st.cache_data.clear()
                st.rerun()
        st.markdown("<div style='border-bottom:1px solid rgba(255,255,255,0.04);"
                    " margin: 6px 0;'></div>", unsafe_allow_html=True)
