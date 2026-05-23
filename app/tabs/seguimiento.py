"""Pestaña de seguimiento en vivo: introduce resultados reales y actualiza predicciones."""
from __future__ import annotations
import streamlit as st
import json
from itertools import combinations
from pathlib import Path

from app.utils import (
    load_real_results,
    save_real_results,
    load_base_elo,
    get_elo_with_biases,
    run_simulation_with_real,
    ROOT,
)
from src.tournament.groups import GROUPS, ALL_TEAMS
from src.tournament.bracket import (
    R32_FIFA, R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA,
)
from src.data.team_profile import ISO_CODES
from src.model.group_sim import TeamGroupStats
from src.model.tournament_sim import _resolve_r32_pairings
from src.model.history import append_snapshot, clear_history
from src.model.calibration import shannon_entropy
from app.styles import PRIMARY, ACCENT, TEXT_DIM, GOOD, DANGER, BG_CARD


def clean_html(html_str: str) -> str:
    """Elimina los espacios en blanco iniciales de cada línea para evitar que Streamlit los interprete como bloques de código Markdown."""
    return "\n".join(line.lstrip() for line in html_str.splitlines())



def _flag_html(team: str | None, size: int = 24) -> str:
    """Devuelve el código HTML para renderizar la bandera de un equipo."""
    team_str = str(team) if team is not None else ""
    if not team or team_str == "-" or team_str.startswith("1") or team_str.startswith("2") or team_str.startswith("3") or "Ganador" in team_str or "Por definir" in team_str or team not in ALL_TEAMS:
        return f'<div style="width:{size}px;height:{int(size*0.75)}px;border:1px dashed rgba(255,255,255,0.25);background:rgba(255,255,255,0.03);border-radius:2px;display:inline-block;vertical-align:middle;margin-right:8px;"></div>'
    iso = ISO_CODES.get(team, "un")
    return f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:{size}px;height:{int(size*0.75)}px;border-radius:2px;object-fit:cover;display:inline-block;vertical-align:middle;margin-right:8px;box-shadow: 0 1px 3px rgba(0,0,0,0.3);">'


def get_live_tournament_state(real_results: dict, elo_dict: dict[str, float]) -> dict:
    """Calcula el estado del torneo actual a partir de los marcadores reales."""
    group_standings = {}
    
    # 1. Calcular clasificación en vivo para todos los grupos
    for g, teams in GROUPS.items():
        stats = {
            t: {
                "team": t,
                "group": g,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0,
                "points": 0,
                "elo": elo_dict.get(t, 1500.0)
            } for t in teams
        }
        
        # Procesar los 6 emparejamientos del grupo
        for ta, tb in combinations(teams, 2):
            score = None
            if f"{ta} vs {tb}" in real_results["group_matches"]:
                score = real_results["group_matches"][f"{ta} vs {tb}"]
                team_h, team_a = ta, tb
            elif f"{tb} vs {ta}" in real_results["group_matches"]:
                score = real_results["group_matches"][f"{tb} vs {ta}"]
                team_h, team_a = tb, ta
                
            if score is not None:
                gh, ga = score
                stats[team_h]["played"] += 1
                stats[team_a]["played"] += 1
                stats[team_h]["gf"] += gh
                stats[team_h]["ga"] += ga
                stats[team_a]["gf"] += ga
                stats[team_a]["ga"] += gh
                stats[team_h]["gd"] = stats[team_h]["gf"] - stats[team_h]["ga"]
                stats[team_a]["gd"] = stats[team_a]["gf"] - stats[team_a]["ga"]
                
                if gh > ga:
                    stats[team_h]["won"] += 1
                    stats[team_h]["points"] += 3
                    stats[team_a]["lost"] += 1
                elif gh < ga:
                    stats[team_a]["won"] += 1
                    stats[team_a]["points"] += 3
                    stats[team_h]["lost"] += 1
                else:
                    stats[team_h]["drawn"] += 1
                    stats[team_h]["points"] += 1
                    stats[team_a]["drawn"] += 1
                    stats[team_a]["points"] += 1

        # Ordenar grupo según: puntos, diferencia de goles, goles a favor, elo base
        sorted_stats = sorted(
            stats.values(),
            key=lambda s: (s["points"], s["gd"], s["gf"], s["elo"]),
            reverse=True
        )
        group_standings[g] = sorted_stats

    # Verificar si toda la fase de grupos está completada
    all_groups_complete = True
    for g, standings in group_standings.items():
        if any(team_stat["played"] < 3 for team_stat in standings):
            all_groups_complete = False
            break

    # 2. Resolver los emparejamientos de Dieciseisavos (R32)
    r32_pairings = {}
    best_thirds = []
    
    if all_groups_complete:
        # Extraer terceros
        thirds = [group_standings[g][2] for g in sorted(group_standings.keys())]
        thirds_sorted = sorted(
            thirds,
            key=lambda s: (s["points"], s["gd"], s["gf"], s["elo"]),
            reverse=True
        )
        best_thirds = thirds_sorted[:8]
        
        # Convertir a objetos TeamGroupStats para reutilizar la lógica de cruces FIFA
        sim_thirds = [
            TeamGroupStats(
                team=t["team"], group=t["group"], points=t["points"],
                gd=t["gd"], gf=t["gf"], ga=t["ga"], elo=t["elo"]
            ) for t in best_thirds
        ]
        
        sim_standings = {}
        for g, st in group_standings.items():
            sim_standings[g] = [
                TeamGroupStats(
                    team=t["team"], group=t["group"], points=t["points"],
                    gd=t["gd"], gf=t["gf"], ga=t["ga"], elo=t["elo"]
                ) for t in st
            ]
            
        r32_pairings = _resolve_r32_pairings(sim_standings, sim_thirds)
    else:
        # Fase de grupos incompleta: resolver parcialmente sólo cruces directos
        # (ej. 2A vs 2B) de grupos que ya están completados.
        p1 = {}
        p2 = {}
        for g, st in group_standings.items():
            group_complete = all(t["played"] == 3 for t in st)
            if group_complete:
                p1[g] = st[0]["team"]
                p2[g] = st[1]["team"]
                
        for fifa_id, (slot_l, slot_r) in R32_FIFA.items():
            home = p1.get(slot_l[1]) if slot_l.startswith("1") and slot_l[1] in p1 else (p2.get(slot_l[1]) if slot_l.startswith("2") and slot_l[1] in p2 else slot_l)
            away = p1.get(slot_r[1]) if slot_r.startswith("1") and slot_r[1] in p1 else (p2.get(slot_r[1]) if slot_r.startswith("2") and slot_r[1] in p2 else slot_r)
            r32_pairings[fifa_id] = (home, away)

    # 3. Resolver ganadores de eliminatorias de manera secuencial
    r32_winners = {}
    r16_pairings = {}
    r16_winners = {}
    qf_pairings = {}
    qf_winners = {}
    sf_pairings = {}
    sf_winners = {}
    final_pairings = {}
    champion = None

    # R32
    r32_matches = real_results.get("knockout_matches", {}).get("r32", {})
    for fifa_id, (home, away) in r32_pairings.items():
        match_data = r32_matches.get(str(fifa_id)) or r32_matches.get(fifa_id)
        if match_data and match_data.get("winner"):
            r32_winners[fifa_id] = match_data["winner"]

    # R16
    for fifa_id, (slot_h, slot_a) in R16_FIFA.items():
        home = r32_winners.get(slot_h)
        away = r32_winners.get(slot_a)
        r16_pairings[fifa_id] = (home, away)
        
        r16_matches = real_results.get("knockout_matches", {}).get("r16", {})
        match_data = r16_matches.get(str(fifa_id)) or r16_matches.get(fifa_id)
        if match_data and match_data.get("winner"):
            r16_winners[fifa_id] = match_data["winner"]

    # QF
    for fifa_id, (slot_h, slot_a) in QF_FIFA.items():
        home = r16_winners.get(slot_h)
        away = r16_winners.get(slot_a)
        qf_pairings[fifa_id] = (home, away)
        
        qf_matches = real_results.get("knockout_matches", {}).get("qf", {})
        match_data = qf_matches.get(str(fifa_id)) or qf_matches.get(fifa_id)
        if match_data and match_data.get("winner"):
            qf_winners[fifa_id] = match_data["winner"]

    # SF
    for fifa_id, (slot_h, slot_a) in SF_FIFA.items():
        home = qf_winners.get(slot_h)
        away = qf_winners.get(slot_a)
        sf_pairings[fifa_id] = (home, away)
        
        sf_matches = real_results.get("knockout_matches", {}).get("sf", {})
        match_data = sf_matches.get(str(fifa_id)) or sf_matches.get(fifa_id)
        if match_data and match_data.get("winner"):
            sf_winners[fifa_id] = match_data["winner"]

    # Final
    final_winners = {}
    for fifa_id, (slot_h, slot_a) in F_FIFA.items():
        home = sf_winners.get(slot_h)
        away = sf_winners.get(slot_a)
        final_pairings[fifa_id] = (home, away)
        
        final_matches = real_results.get("knockout_matches", {}).get("final", {})
        match_data = final_matches.get(str(fifa_id)) or final_matches.get(fifa_id)
        if match_data and match_data.get("winner"):
            champion = match_data["winner"]
            final_winners[fifa_id] = champion

    return {
        "group_standings": group_standings,
        "all_groups_complete": all_groups_complete,
        "best_thirds": best_thirds,
        "r32_pairings": r32_pairings,
        "r32_winners": r32_winners,
        "r16_pairings": r16_pairings,
        "r16_winners": r16_winners,
        "qf_pairings": qf_pairings,
        "qf_winners": qf_winners,
        "sf_pairings": sf_pairings,
        "sf_winners": sf_winners,
        "final_pairings": final_pairings,
        "final_winners": final_winners,
        "champion": champion,
    }


def render_standings_table(standings: list[dict]) -> str:
    """Genera una tabla HTML interactiva y premium para la clasificación."""
    html = """
    <table style="width:100%; border-collapse: collapse; font-size: 0.85rem; color: #e5e7eb; background-color: #111827; border-radius: 8px; overflow: hidden; border: 1px solid #1f2937;">
        <thead>
            <tr style="background-color: #1f2937; border-bottom: 2px solid #1f2937; text-align: center; font-weight: 600;">
                <th style="padding: 10px 8px; text-align: left; width: 40px;">Pos</th>
                <th style="padding: 10px 8px; text-align: left;">Equipo</th>
                <th style="padding: 10px 4px; width: 35px;">PJ</th>
                <th style="padding: 10px 4px; width: 30px;">PG</th>
                <th style="padding: 10px 4px; width: 30px;">PE</th>
                <th style="padding: 10px 4px; width: 30px;">PP</th>
                <th style="padding: 10px 4px; width: 45px;">GF:GC</th>
                <th style="padding: 10px 4px; width: 35px;">DG</th>
                <th style="padding: 10px 8px; width: 40px; font-weight: 700; color: #10b981;">Pts</th>
            </tr>
        </thead>
        <tbody>
    """
    for pos, s in enumerate(standings):
        team = s["team"]
        
        # Bordes y colores premium para destacar posiciones
        if pos < 2:
            border_style = "border-left: 3px solid #10b981;"  # Clasificado directo (verde)
            bg_color = "rgba(16, 185, 129, 0.04)"
        elif pos == 2:
            border_style = "border-left: 3px solid #f59e0b;"  # Posible mejor tercero (ámbar)
            bg_color = "rgba(245, 158, 11, 0.02)"
        else:
            border_style = "border-left: 3px solid transparent;"
            bg_color = "transparent"
            
        html += f"""
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #1f2937; text-align: center;">
                <td style="padding: 10px 8px; text-align: left; font-weight: 600; {border_style}">{pos+1}</td>
                <td style="padding: 10px 8px; text-align: left; font-weight: 600;">{_flag_html(team, 18)}{team}</td>
                <td style="padding: 10px 4px;">{s["played"]}</td>
                <td style="padding: 10px 4px;">{s["won"]}</td>
                <td style="padding: 10px 4px;">{s["drawn"]}</td>
                <td style="padding: 10px 4px;">{s["lost"]}</td>
                <td style="padding: 10px 4px; color: #9ca3af;">{s["gf"]}:{s["ga"]}</td>
                <td style="padding: 10px 4px; font-weight: 500; color: {'#10b981' if s['gd'] > 0 else '#ef4444' if s['gd'] < 0 else '#9ca3af'};">
                    {'+' if s['gd'] > 0 else ''}{s['gd']}
                </td>
                <td style="padding: 10px 8px; font-weight: 700; color: #10b981;">{s["points"]}</td>
            </tr>
        """
    html += """
        </tbody>
    </table>
    """
    return clean_html(html)


def render():
    st.header("Seguimiento en vivo")
    st.caption(
        "Introduce los resultados reales del Mundial 2026 a medida que se jueguen. "
        "La aplicación congelará los partidos jugados, calculará dinámicamente las clasificaciones y la porra, y simulará el resto del torneo en tiempo real."
    )

    elo_dict = load_base_elo()

    # Cargar / inicializar resultados reales temporales en session_state
    if "temp_real_results" not in st.session_state:
        st.session_state.temp_real_results = load_real_results()
        
    temp_results = st.session_state.temp_real_results
    
    # Calcular estado completo del torneo al inicio para alimentar el progreso
    state = get_live_tournament_state(temp_results, elo_dict)

    col_actions, col_info = st.columns([2, 3])
    with col_actions:
        st.markdown(
            clean_html(f"""
            <div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:12px; padding:16px; margin-bottom:16px;">
                <h4 style="margin:0 0 12px 0; font-size:1rem; color:{PRIMARY};">Acciones de Datos</h4>
            """), 
            unsafe_allow_html=True
        )
        
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            save_real_results(temp_results)
            # Snapshot del estado actual del torneo (probabilidades + entropía)
            try:
                new_elo = get_elo_with_biases()
                new_summary = run_simulation_with_real(new_elo, 10_000, seed=42)
                append_snapshot(
                    temp_results,
                    new_summary["champion"],
                    shannon_entropy(new_summary["champion"]),
                )
            except Exception as e:
                st.warning(f"No se pudo registrar snapshot: {e}")
            st.success("¡Resultados guardados y simulación recalculada!")
            st.rerun()
            
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
        if st.button("🗑️ Resetear Marcadores", use_container_width=True, type="secondary"):
            empty_results = {
                "group_matches": {},
                "knockout_matches": {
                    "r32": {}, "r16": {}, "qf": {}, "sf": {}, "final": {}
                }
            }
            st.session_state.temp_real_results = empty_results
            save_real_results(empty_results)
            clear_history()
            st.info("Marcadores borrados.")
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_info:
        # Calcular algunas métricas de avance del torneo real
        n_group_played = len(temp_results["group_matches"])
        
        # Calcular partidos jugados por ronda
        n_r32 = len(temp_results.get("knockout_matches", {}).get("r32", {}))
        n_r16 = len(temp_results.get("knockout_matches", {}).get("r16", {}))
        n_qf = len(temp_results.get("knockout_matches", {}).get("qf", {}))
        n_sf = len(temp_results.get("knockout_matches", {}).get("sf", {}))
        n_final = len(temp_results.get("knockout_matches", {}).get("final", {}))
        
        n_ko_played = n_r32 + n_r16 + n_qf + n_sf + n_final
        total_played = n_group_played + n_ko_played
        
        # Información de fases para el timeline
        phases_info = [
            {"name": "Fase de Grupos", "played": n_group_played, "total": 72, "prev_complete": True},
            {"name": "Dieciseisavos (R32)", "played": n_r32, "total": 16, "prev_complete": n_group_played == 72},
            {"name": "Octavos (R16)", "played": n_r16, "total": 8, "prev_complete": n_group_played == 72 and n_r32 == 16},
            {"name": "Cuartos (QF)", "played": n_qf, "total": 4, "prev_complete": n_group_played == 72 and n_r32 == 16 and n_r16 == 8},
            {"name": "Semifinales (SF)", "played": n_sf, "total": 2, "prev_complete": n_group_played == 72 and n_r32 == 16 and n_r16 == 8 and n_qf == 4},
            {"name": "Gran Final", "played": n_final, "total": 1, "prev_complete": n_group_played == 72 and n_r32 == 16 and n_r16 == 8 and n_qf == 4 and n_sf == 2},
        ]
        
        timeline_html = ""
        for phase in phases_info:
            p_name = phase["name"]
            p_played = phase["played"]
            p_total = phase["total"]
            prev_comp = phase["prev_complete"]
            
            is_comp = (p_played == p_total)
            is_prog = (0 < p_played < p_total)
            is_lck = not prev_comp
            
            if is_comp:
                bullet_style = f"background: {GOOD}; color: #020617; box-shadow: 0 0 10px {GOOD}40;"
                bullet_content = "✓"
                text_color = "color: #ffffff;"
                badge_color = f"color: {GOOD};"
                status_text = "Fase completada"
            elif is_prog:
                bullet_style = f"background: {ACCENT}; color: #ffffff; box-shadow: 0 0 10px {ACCENT}40;"
                bullet_content = "▶"
                text_color = "color: #ffffff;"
                badge_color = f"color: {ACCENT};"
                status_text = "En desarrollo en vivo..."
            elif is_lck:
                bullet_style = "background: rgba(255, 255, 255, 0.05); color: #475569; border: 1px solid rgba(255,255,255,0.05);"
                bullet_content = "🔒"
                text_color = "color: #475569;"
                badge_color = "color: #475569;"
                status_text = "Esperando fase previa"
            else:
                bullet_style = f"background: rgba(6, 182, 212, 0.05); color: {PRIMARY}; border: 1px dashed {PRIMARY};"
                bullet_content = "○"
                text_color = "color: #94a3b8;"
                badge_color = f"color: {PRIMARY};"
                status_text = "Disponible para jugar"
                
            timeline_html += f"""
            <div style="display: flex; align-items: flex-start; margin-bottom: 12px; position: relative;">
                <div style="width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px; font-size: 0.65rem; font-weight: bold; z-index: 2; {bullet_style}">
                    {bullet_content}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                        <span style="font-size: 0.8rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; {text_color}">{p_name}</span>
                        <span style="font-size: 0.72rem; font-weight: 700; {badge_color}">{p_played}/{p_total}</span>
                    </div>
                    <div style="font-size: 0.65rem; color: #64748b; font-style: italic; margin-top: 1px;">{status_text}</div>
                </div>
            </div>
            """
            
        st.markdown(
            clean_html(f"""
            <div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:12px; padding:16px; height: 100%;">
                <h4 style="margin:0 0 12px 0; font-size:1rem; color:{PRIMARY};">Progreso del Torneo Real</h4>
                <div style="position: relative; padding-top: 4px;">
                    <div style="position: absolute; left: 9px; top: 10px; bottom: 10px; width: 2px; border-left: 2px dashed rgba(255, 255, 255, 0.08); z-index: 1;"></div>
                    {timeline_html}
                </div>
            </div>
            """), 
            unsafe_allow_html=True
        )

    # === Selectores de Fase ===
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    fase = st.selectbox(
        "Seleccionar Fase de Edición",
        ["Fase de Grupos", "Dieciseisavos (R32)", "Octavos (R16)", "Cuartos (QF)", "Semifinales (SF)", "Final (F)"]
    )

    if fase == "Fase de Grupos":
        st.subheader("Fase de Grupos")
        grupo = st.selectbox("Seleccionar Grupo", sorted(GROUPS.keys()))
        
        teams = GROUPS[grupo]
        
        st.markdown(f"#### Partidos del Grupo {grupo}")
        # Renderizar los 6 partidos del grupo
        for ta, tb in combinations(teams, 2):
            # Obtener resultado existente
            score = None
            key_name = f"{ta} vs {tb}"
            if f"{ta} vs {tb}" in temp_results["group_matches"]:
                score = temp_results["group_matches"][f"{ta} vs {tb}"]
            elif f"{tb} vs {ta}" in temp_results["group_matches"]:
                score = temp_results["group_matches"][f"{tb} vs {ta}"]
                key_name = f"{tb} vs {ta}"
            
            is_played = score is not None
            goals_a = score[0] if is_played else 0
            goals_b = score[1] if is_played else 0
            
            st.markdown(
                clean_html(f"""
                <div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:10px; padding:12px; margin-bottom:8px;">
                """), 
                unsafe_allow_html=True
            )
            
            c_home_name, c_g1, c_g2, c_away_name, c_played = st.columns([3.5, 1.25, 1.25, 3.5, 2.5])
            
            with c_played:
                played = st.checkbox("Jugado", value=is_played, key=f"check_play_{ta}_{tb}")
            
            with c_home_name:
                st.markdown(
                    f"<div style='text-align:right; font-weight:600; padding-top:4px;'>{ta} {_flag_html(ta, 20)}</div>",
                    unsafe_allow_html=True
                )
            
            with c_g1:
                g_a = st.number_input(
                    "Goles Local", min_value=0, max_value=20, value=int(goals_a), step=1,
                    disabled=not played, key=f"g_a_{ta}_{tb}", label_visibility="collapsed"
                )
            with c_g2:
                g_b = st.number_input(
                    "Goles Visitante", min_value=0, max_value=20, value=int(goals_b), step=1,
                    disabled=not played, key=f"g_b_{ta}_{tb}", label_visibility="collapsed"
                )
                    
            with c_away_name:
                st.markdown(
                    f"<div style='font-weight:600; padding-top:4px;'>{_flag_html(tb, 20)} {tb}</div>",
                    unsafe_allow_html=True
                )
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Actualizar el diccionario temporal
            if played:
                # Siempre guardamos en orden de la combinación
                temp_results["group_matches"][f"{ta} vs {tb}"] = [int(g_a), int(g_b)]
                if f"{tb} vs {ta}" in temp_results["group_matches"] and f"{tb} vs {ta}" != f"{ta} vs {tb}":
                    temp_results["group_matches"].pop(f"{tb} vs {ta}")
            else:
                if f"{ta} vs {tb}" in temp_results["group_matches"]:
                    temp_results["group_matches"].pop(f"{ta} vs {tb}")
                if f"{tb} vs {ta}" in temp_results["group_matches"]:
                    temp_results["group_matches"].pop(f"{tb} vs {ta}")

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.markdown(f"#### Clasificación Grupo {grupo} en vivo")
        # Mostrar la tabla en vivo actual
        st.markdown(render_standings_table(state["group_standings"][grupo]), unsafe_allow_html=True)
        
        # Ayuda didáctica
        st.caption("Verde: Pasa directo a R32. Ámbar: Posible mejor tercero.")

    else:
        # Eliminatorias: Dieciseisavos (R32) hasta la Final
        round_mapping = {
            "Dieciseisavos (R32)": ("r32", R32_FIFA, "Dieciseisavos de Final"),
            "Octavos (R16)": ("r16", R16_FIFA, "Octavos de Final"),
            "Cuartos (QF)": ("qf", QF_FIFA, "Cuartos de Final"),
            "Semifinales (SF)": ("sf", SF_FIFA, "Semifinales"),
            "Final (F)": ("final", F_FIFA, "Gran Final"),
        }
        
        round_key, bracket_data, round_title = round_mapping[fase]
        st.subheader(round_title)
        
        # Obtener emparejamientos calculados
        if round_key == "r32":
            pairings = state["r32_pairings"]
        elif round_key == "r16":
            pairings = state["r16_pairings"]
        elif round_key == "qf":
            pairings = state["qf_pairings"]
        elif round_key == "sf":
            pairings = state["sf_pairings"]
        else:
            pairings = state["final_pairings"]

        # Mostrar los partidos de la ronda
        st.markdown(f"#### Partidos oficiales ({len(bracket_data)} partidos)")
        
        for idx, (fifa_id, (slot_h, slot_a)) in enumerate(bracket_data.items()):
            home_team = pairings.get(fifa_id, (None, None))[0]
            away_team = pairings.get(fifa_id, (None, None))[1]
            
            is_home_resolved = home_team in ALL_TEAMS
            is_away_resolved = away_team in ALL_TEAMS
            is_resolved = is_home_resolved and is_away_resolved
            
            if is_resolved:
                # Mostrar partido activo para ingresar marcadores
                st.markdown(
                    f"""
                    <div style="background:{BG_CARD}; border:1px solid {PRIMARY}; border-radius:12px; padding:16px; margin-bottom:12px;">
                        <div style="color:{PRIMARY}; font-size:0.75rem; font-weight:700; margin-bottom:8px; text-transform:uppercase;">
                            Partido FIFA #{fifa_id}
                        </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                round_matches = temp_results["knockout_matches"].setdefault(round_key, {})
                match_data = round_matches.get(str(fifa_id)) or round_matches.get(fifa_id) or {}
                is_played = "winner" in match_data
                
                goals_h = match_data.get("home_score", 0) if is_played else 0
                goals_a = match_data.get("away_score", 0) if is_played else 0
                saved_winner = match_data.get("winner", home_team) if is_played else home_team
                
                c_home, c_g1, c_g2, c_away, c_play = st.columns([3.5, 1.25, 1.25, 3.5, 2.5])
                
                with c_play:
                    played = st.checkbox("Jugado", value=is_played, key=f"ko_check_{round_key}_{fifa_id}")
                
                with c_home:
                    st.markdown(
                        f"<div style='text-align:right; font-weight:600; padding-top:4px;'>{home_team} {_flag_html(home_team, 20)}</div>",
                        unsafe_allow_html=True
                    )
                    
                with c_g1:
                    g_h = st.number_input(
                        "Goles Local", min_value=0, max_value=20, value=int(goals_h), step=1,
                        disabled=not played, key=f"ko_g_h_{round_key}_{fifa_id}", label_visibility="collapsed"
                    )
                with c_g2:
                    g_a = st.number_input(
                        "Goles Visitante", min_value=0, max_value=20, value=int(goals_a), step=1,
                        disabled=not played, key=f"ko_g_a_{round_key}_{fifa_id}", label_visibility="collapsed"
                    )
                        
                with c_away:
                    st.markdown(
                        f"<div style='font-weight:600; padding-top:4px;'>{_flag_html(away_team, 20)} {away_team}</div>",
                        unsafe_allow_html=True
                    )
                
                # Decisión del ganador (obligatorio en eliminatoria)
                winner_picked = None
                if played:
                    if g_h > g_a:
                        winner_picked = home_team
                        st.markdown(
                            f"<div style='color:{GOOD}; font-size:0.8rem; text-align:center; font-weight:600; margin-top:8px;'> Ganador: {home_team} (Tiempo Regular)</div>",
                            unsafe_allow_html=True
                        )
                    elif g_h < g_a:
                        winner_picked = away_team
                        st.markdown(
                            f"<div style='color:{GOOD}; font-size:0.8rem; text-align:center; font-weight:600; margin-top:8px;'> Ganador: {away_team} (Tiempo Regular)</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        # Empate, requiere penaltis
                        winner_options = [home_team, away_team]
                        default_idx = winner_options.index(saved_winner) if saved_winner in winner_options else 0
                        winner_picked = st.selectbox(
                            "Ganador tras Penaltis",
                            winner_options,
                            index=default_idx,
                            key=f"ko_win_{round_key}_{fifa_id}"
                        )
                        st.markdown(
                            f"<div style='color:{ACCENT}; font-size:0.8rem; text-align:center; font-weight:500;'>Empate. Se requiere ganador vía Penaltis.</div>",
                            unsafe_allow_html=True
                        )
                
                # Guardar marcadores
                if played and winner_picked:
                    temp_results["knockout_matches"][round_key][str(fifa_id)] = {
                        "home": home_team,
                        "away": away_team,
                        "home_score": int(g_h),
                        "away_score": int(g_a),
                        "winner": winner_picked
                    }
                else:
                    if str(fifa_id) in temp_results["knockout_matches"][round_key]:
                        temp_results["knockout_matches"][round_key].pop(str(fifa_id))
                    if fifa_id in temp_results["knockout_matches"][round_key]:
                        temp_results["knockout_matches"][round_key].pop(fifa_id)
                        
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Mostrar partido bloqueado (no se han resuelto los clasificados)
                slot_h_display = slot_h if not is_home_resolved else home_team
                slot_a_display = slot_a if not is_away_resolved else away_team
                st.markdown(
                    f"""
                    <div style="background:{BG_CARD}; border:1px solid #1f2937; border-radius:12px; padding:16px; margin-bottom:12px; opacity:0.5;">
                        <div style="color:{TEXT_DIM}; font-size:0.75rem; font-weight:600; margin-bottom:8px; text-transform:uppercase;">
                            Partido FIFA #{fifa_id} · Bloqueado
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem; font-weight:500;">
                            <span>{_flag_html(slot_h_display, 18)} {slot_h_display}</span>
                            <span style="color:{TEXT_DIM}; font-weight:400; padding:0 8px;">vs</span>
                            <span>{_flag_html(slot_a_display, 18)} {slot_a_display}</span>
                        </div>
                        <div style="font-size:0.75rem; color:{TEXT_DIM}; text-align:center; margin-top:8px;">
                            Esperando definición de clasificados de la fase previa.
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

    # Renderizar el bracket visual interactivo al final de la pestaña
    render_bracket_visual(state, temp_results)

    # === Goleadores en vivo ===
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _render_goleadores(temp_results)

    # === What-if simulator ===
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    _render_what_if(temp_results)


def _render_goleadores(real_results: dict):
    """UI para registrar goleadores por partido + tabla de Pichichi en vivo."""
    from src.model.scorers import (
        load_scorers, save_scorers, add_scorer, remove_scorer,
        pichichi_live, total_goals_logged,
    )

    st.subheader("🥅 Goleadores en vivo · Pichichi tracker")
    st.caption(
        "Registra los goleadores de cada partido jugado. La tabla del Pichichi "
        "se actualiza automáticamente."
    )

    scorers_data = load_scorers()

    # === Selector de partido (sólo de los jugados) ===
    played_matches: list[tuple[str, str, str, int, int]] = []
    # Grupos
    for k, score in real_results.get("group_matches", {}).items():
        if score and len(score) >= 2:
            ta, tb = k.split(" vs ")
            played_matches.append((f"grupos::{k}", ta, tb, int(score[0]), int(score[1])))
    # Eliminatorias
    for r_key in ("r32", "r16", "qf", "sf", "final"):
        round_data = real_results.get("knockout_matches", {}).get(r_key, {})
        for mid, info in round_data.items():
            ta, tb = info.get("home"), info.get("away")
            if not ta or not tb:
                continue
            played_matches.append((
                f"{r_key}::{mid}", ta, tb,
                int(info.get("home_score", 0)),
                int(info.get("away_score", 0)),
            ))

    if not played_matches:
        st.info("Aún no hay partidos jugados. Cuando registres marcadores podrás añadir goleadores aquí.")
    else:
        labels = [f"{ta} {sa}-{sb} {tb}" for _, ta, tb, sa, sb in played_matches]
        sel = st.selectbox("Partido a editar", labels, key="scorers_match_sel")
        idx = labels.index(sel)
        key, ta, tb, sa, sb = played_matches[idx]
        existing = scorers_data.get("matches", {}).get(key, [])

        # Mostrar goleadores ya registrados
        if existing:
            st.markdown("**Goleadores registrados**")
            for i, s in enumerate(existing):
                cols = st.columns([3, 2, 1, 1, 1])
                cols[0].markdown(f"⚽ **{s['player']}**")
                cols[1].markdown(f"<span style='color:{TEXT_DIM};'>{s['team']}</span>", unsafe_allow_html=True)
                cols[2].markdown(f"min {s['minute']}")
                cols[3].markdown("🎯 pen." if s.get("penalty") else "")
                if cols[4].button("🗑", key=f"rm_scorer_{key}_{i}"):
                    remove_scorer(scorers_data, key, i)
                    save_scorers(scorers_data)
                    st.rerun()

        # Validar suma de goles
        total_real = sa + sb
        total_logged_match = len(existing)
        if total_logged_match != total_real:
            st.warning(f"Has registrado {total_logged_match} goleador(es) pero el marcador real "
                        f"es {sa}-{sb} (total {total_real}). Añade {total_real - total_logged_match} más.")
        else:
            st.success(f"✅ Goleadores cuadrados con el marcador real ({total_real} goles).")

        # Formulario para añadir nuevo goleador
        st.markdown("**Añadir goleador**")
        cf1, cf2, cf3, cf4, cf5 = st.columns([2, 2, 1, 1, 1])
        with cf1:
            new_player = st.text_input("Jugador", key=f"new_player_{key}",
                                          placeholder="ej. Lamine Yamal")
        with cf2:
            new_team = st.selectbox("Equipo", [ta, tb], key=f"new_team_{key}")
        with cf3:
            new_minute = st.number_input("Min", 1, 120, 45, 1, key=f"new_min_{key}")
        with cf4:
            new_pen = st.checkbox("Penal", key=f"new_pen_{key}")
        with cf5:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕", key=f"add_scorer_{key}"):
                if new_player.strip():
                    add_scorer(scorers_data, key, new_player, new_team, new_minute, new_pen)
                    save_scorers(scorers_data)
                    st.rerun()

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Tabla Pichichi en vivo ===
    st.markdown("##### 🏅 Pichichi en vivo")
    ranking = pichichi_live(scorers_data)
    if not ranking:
        st.caption("Cuando registres goleadores aparecerá aquí el ranking.")
    else:
        total = total_goals_logged(scorers_data)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div style='font-size:0.78rem; color:{TEXT_DIM};'>Goles registrados</div>"
                         f"<div style='font-size:1.6rem; font-weight:800; color:{PRIMARY};'>{total}</div>",
                         unsafe_allow_html=True)
        with c2:
            top_player = ranking[0]
            st.markdown(f"<div style='font-size:0.78rem; color:{TEXT_DIM};'>Líder actual</div>"
                         f"<div style='font-size:1.2rem; font-weight:700;'>{top_player[0]} "
                         f"<span style='color:{ACCENT}; font-size:1.4rem;'>({top_player[2]})</span></div>",
                         unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(ranking, columns=["Jugador", "Equipo", "Goles", "Penaltis"])
        df.insert(0, "#", range(1, len(df) + 1))
        st.dataframe(df.style.background_gradient(subset=["Goles"], cmap="Greens"),
                      hide_index=True, use_container_width=True, height=380)


def _render_what_if(real_results: dict):
    """Permite probar un resultado hipotético y ver cómo cambian las probas sin guardar."""
    from src.model.what_if import compute_what_if, inject_group_result, inject_knockout_result
    import pandas as pd
    from itertools import combinations as _comb
    from src.tournament.bracket import R32_FIFA, R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA

    st.subheader("🔮 What-if simulator")
    st.caption(
        "Prueba el efecto de un resultado hipotético sin guardarlo. Útil para ver "
        "cómo cambiaría el torneo si X gana, empata o pierde."
    )

    with st.expander("Configurar escenario hipotético", expanded=False):
        kind = st.radio(
            "Tipo de partido", ["Fase de grupos", "Eliminatoria"],
            horizontal=True, key="whatif_kind",
        )

        elo_dict = get_elo_with_biases()

        if kind == "Fase de grupos":
            group = st.selectbox("Grupo", sorted(GROUPS.keys()), key="whatif_group")
            teams = GROUPS[group]
            pair_options = [f"{a} vs {b}" for a, b in _comb(teams, 2)]
            pair = st.selectbox("Partido", pair_options, key="whatif_pair")
            ta, tb = pair.split(" vs ")
            cgs1, cgs2, cgs3 = st.columns(3)
            with cgs1:
                ga = st.number_input(f"Goles {ta}", 0, 10, 1, 1, key="whatif_ga")
            with cgs2:
                st.markdown("<div style='text-align:center; padding-top:24px; color:#9ca3af;'>vs</div>",
                            unsafe_allow_html=True)
            with cgs3:
                gb = st.number_input(f"Goles {tb}", 0, 10, 1, 1, key="whatif_gb")

            if st.button("🔮 Calcular what-if", type="primary"):
                hypothetical = inject_group_result(real_results, ta, tb, int(ga), int(gb))
                with st.spinner("Simulando 4.000 torneos hipotéticos…"):
                    res = compute_what_if(elo_dict, real_results, hypothetical, n_sims=4_000)
                _render_what_if_results(res, label=f"Hipótesis: {ta} {ga}-{gb} {tb}")
        else:
            rounds = {
                "Dieciseisavos (R32)": ("r32", R32_FIFA),
                "Octavos (R16)": ("r16", R16_FIFA),
                "Cuartos (QF)": ("qf", QF_FIFA),
                "Semifinales (SF)": ("sf", SF_FIFA),
                "Final (F)": ("final", F_FIFA),
            }
            r_label = st.selectbox("Ronda", list(rounds.keys()), key="whatif_round")
            r_key, bracket_data = rounds[r_label]
            mid_options = list(bracket_data.keys())
            mid = st.selectbox("Partido FIFA #", mid_options, key="whatif_mid")
            # Inferir home/away desde el estado actual
            state_now = get_live_tournament_state(real_results, elo_dict)
            pairings_key = "r32_pairings" if r_key == "r32" else f"{r_key}_pairings"
            pair = state_now[pairings_key].get(mid)
            if not pair or not all(p in ALL_TEAMS for p in pair):
                st.warning("Este partido aún no tiene equipos resueltos. Avanza primero las rondas previas.")
            else:
                home, away = pair
                cks1, cks2, cks3 = st.columns(3)
                with cks1:
                    gh_w = st.number_input(f"Goles {home}", 0, 10, 1, 1, key="whatif_gh_w")
                with cks2:
                    st.markdown("<div style='text-align:center; padding-top:24px; color:#9ca3af;'>vs</div>",
                                unsafe_allow_html=True)
                with cks3:
                    ga_w = st.number_input(f"Goles {away}", 0, 10, 1, 1, key="whatif_ga_w")
                winner_pick = None
                if gh_w == ga_w:
                    winner_pick = st.selectbox(f"Ganador tras penaltis", [home, away],
                                                 key="whatif_winner")
                if st.button("🔮 Calcular what-if", type="primary"):
                    hypothetical = inject_knockout_result(
                        real_results, r_key, mid, home, away,
                        int(gh_w), int(ga_w), winner=winner_pick,
                    )
                    with st.spinner("Simulando 4.000 torneos hipotéticos…"):
                        res = compute_what_if(elo_dict, real_results, hypothetical, n_sims=4_000)
                    _render_what_if_results(res, label=f"Hipótesis: {home} {gh_w}-{ga_w} {away}"
                                                       + (f" (penaltis: {winner_pick})" if winner_pick else ""))


def _render_what_if_results(res: dict, label: str):
    """Renderiza el resultado del simulador what-if: movers y diff barchart."""
    import pandas as pd
    st.markdown(f"**{label}**")
    movers = res["movers"]
    top_movers = [m for m in movers if abs(m[3]) >= 0.005][:10]
    if not top_movers:
        st.info("No hay cambios significativos en las probabilidades de campeón con este resultado.")
        return
    df_m = pd.DataFrame([
        {"Equipo": t, "Antes": b * 100, "Después": a * 100, "Δ": d * 100}
        for t, b, a, d in top_movers
    ])
    st.dataframe(
        df_m.style.format({"Antes": "{:.1f}%", "Después": "{:.1f}%", "Δ": "{:+.2f}pp"})
            .background_gradient(subset=["Δ"], cmap="RdYlGn", vmin=-5, vmax=5),
        hide_index=True, use_container_width=True,
    )

    # Bar chart de top 8 movers
    import plotly.graph_objects as go
    deltas = top_movers[:8]
    fig = go.Figure(go.Bar(
        x=[d[3] * 100 for d in deltas],
        y=[d[0] for d in deltas],
        orientation="h",
        marker=dict(
            color=[d[3] for d in deltas],
            colorscale=[[0, DANGER], [0.5, "#1f2937"], [1, GOOD]],
            cmin=-max(abs(d[3]) for d in deltas), cmax=max(abs(d[3]) for d in deltas),
            line=dict(color="white", width=0.5),
        ),
        text=[f"{d[3]*100:+.2f}pp" for d in deltas],
        textposition="outside",
    ))
    fig.update_layout(
        plot_bgcolor=BG_CARD, paper_bgcolor=BG_CARD,
        font=dict(family="Inter", color="white"),
        xaxis=dict(gridcolor="#1f2937", title="Δ % campeón"),
        yaxis=dict(autorange="reversed"),
        height=320, margin=dict(l=10, r=30, t=10, b=10), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bracket_visual(state: dict, temp_results: dict):
    """Dibuja un árbol de eliminatorias interactivo y premium desde Octavos hasta la Final."""
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.subheader("📊 Cuadro de Eliminatorias Interactivo")
    st.caption("Visualiza el desarrollo del torneo en tiempo real desde Octavos de Final hasta la Gran Final.")
    
    st.markdown(clean_html("""
    <style>
    .bracket-placeholder {
        color: #64748b !important;
        font-size: 0.72rem;
        font-style: italic;
        font-weight: 400;
        opacity: 0.75;
    }
    .bracket-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: stretch;
        gap: 16px;
        width: 100%;
        overflow-x: auto;
        padding: 20px 0;
    }
    .bracket-col {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        flex: 1;
        min-width: 190px;
    }
    .bracket-match {
        background: rgba(17, 24, 39, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 10px 14px;
        margin: 8px 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    .bracket-match:hover {
        border-color: #10b981;
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.15);
    }
    .bracket-match-title {
        font-size: 0.65rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
    }
    .bracket-team-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .bracket-team-name {
        display: flex;
        align-items: center;
        color: #e5e7eb;
    }
    .bracket-team-score {
        font-weight: 700;
        color: #10b981;
        font-size: 0.85rem;
    }
    .bracket-winner {
        color: #10b981 !important;
        font-weight: 700;
    }
    .bracket-loser {
        color: #6b7280 !important;
        opacity: 0.6;
    }
    .bracket-champion-card {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%);
        border: 2px solid #f59e0b;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
        align-self: center;
        transition: all 0.3s ease;
        min-width: 180px;
    }
    .bracket-champion-card:hover {
        transform: scale(1.05);
        box-shadow: 0 0 30px rgba(245, 158, 11, 0.3);
    }
    </style>
    """), unsafe_allow_html=True)
    
    def make_match_card(round_key: str, match_id: int, pairings: dict, winners: dict) -> str:
        home, away = pairings.get(match_id, (None, None))
        match_data = temp_results.get("knockout_matches", {}).get(round_key, {}).get(str(match_id)) or {}
        
        home_score = match_data.get("home_score", "")
        away_score = match_data.get("away_score", "")
        winner = winners.get(match_id)
        
        home_class = ""
        away_class = ""
        if winner:
            if winner == home:
                home_class = "bracket-winner"
                away_class = "bracket-loser"
            elif winner == away:
                home_class = "bracket-loser"
                away_class = "bracket-winner"
        
        if not home or home not in ALL_TEAMS:
            home_class += " bracket-placeholder"
        if not away or away not in ALL_TEAMS:
            away_class += " bracket-placeholder"
                
        home_display = home
        away_display = away
        
        if not home_display:
            if match_id in F_FIFA:
                slot_h, _ = F_FIFA[match_id]
                home_display = f"Ganador P{slot_h}"
            elif match_id in SF_FIFA:
                slot_h, _ = SF_FIFA[match_id]
                home_display = f"Ganador P{slot_h}"
            elif match_id in QF_FIFA:
                slot_h, _ = QF_FIFA[match_id]
                home_display = f"Ganador P{slot_h}"
            elif match_id in R16_FIFA:
                slot_h, _ = R16_FIFA[match_id]
                home_display = f"Ganador P{slot_h}"
            else:
                home_display = "Por definir"
                
        if not away_display:
            if match_id in F_FIFA:
                _, slot_a = F_FIFA[match_id]
                away_display = f"Ganador P{slot_a}"
            elif match_id in SF_FIFA:
                _, slot_a = SF_FIFA[match_id]
                away_display = f"Ganador P{slot_a}"
            elif match_id in QF_FIFA:
                _, slot_a = QF_FIFA[match_id]
                away_display = f"Ganador P{slot_a}"
            elif match_id in R16_FIFA:
                _, slot_a = R16_FIFA[match_id]
                away_display = f"Ganador P{slot_a}"
            else:
                away_display = "Por definir"
                
        if isinstance(home_display, int) or (isinstance(home_display, str) and home_display.isdigit()):
            home_display = f"Ganador P{home_display}"
        if isinstance(away_display, int) or (isinstance(away_display, str) and away_display.isdigit()):
            away_display = f"Ganador P{away_display}"
            
        return f"""
        <div class="bracket-match">
            <div class="bracket-match-title">
                <span>Partido #{match_id}</span>
                <span>{round_key.upper()}</span>
            </div>
            <div class="bracket-team-row">
                <span class="bracket-team-name {home_class}">{_flag_html(home, 16)} {home_display}</span>
                <span class="bracket-team-score">{home_score if home_score != "" else "-"}</span>
            </div>
            <div class="bracket-team-row">
                <span class="bracket-team-name {away_class}">{_flag_html(away, 16)} {away_display}</span>
                <span class="bracket-team-score">{away_score if away_score != "" else "-"}</span>
            </div>
        </div>
        """

    # Ordering matches visually from left to right (aligning top and bottom bracket flows)
    r16_order = [89, 90, 93, 94, 91, 92, 95, 96]
    qf_order = [97, 98, 99, 100]
    sf_order = [101, 102]
    f_order = [104]
    
    col_r16_html = "".join(make_match_card("r16", mid, state["r16_pairings"], state["r16_winners"]) for mid in r16_order)
    col_qf_html = "".join(make_match_card("qf", mid, state["qf_pairings"], state["qf_winners"]) for mid in qf_order)
    col_sf_html = "".join(make_match_card("sf", mid, state["sf_pairings"], state["sf_winners"]) for mid in sf_order)
    col_f_html = "".join(make_match_card("final", mid, state["final_pairings"], state["final_winners"]) for mid in f_order)
    
    champ = state["champion"]
    if champ:
        champ_html = f"""
        <div class="bracket-champion-card">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">🏆</div>
            <div style="font-size: 0.7rem; color: #f59e0b; text-transform: uppercase; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 4px;">CAMPEÓN</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #fff;">{_flag_html(champ, 22)}{champ}</div>
        </div>
        """
    else:
        champ_html = """
        <div class="bracket-champion-card" style="opacity: 0.5; border-color: #1f2937; box-shadow: none;">
            <div style="font-size: 1.5rem; margin-bottom: 8px;">🏆</div>
            <div style="font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 4px;">CAMPEÓN</div>
            <div style="font-size: 1rem; font-weight: 600; color: #9ca3af;">Por definir</div>
        </div>
        """
        
    bracket_html = f"""
    <div class="bracket-container">
        <div class="bracket-col">
            <div style="text-align: center; font-size: 0.75rem; color: #10b981; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">Octavos</div>
            {col_r16_html}
        </div>
        <div class="bracket-col">
            <div style="text-align: center; font-size: 0.75rem; color: #10b981; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">Cuartos</div>
            {col_qf_html}
        </div>
        <div class="bracket-col">
            <div style="text-align: center; font-size: 0.75rem; color: #10b981; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">Semifinales</div>
            {col_sf_html}
        </div>
        <div class="bracket-col">
            <div style="text-align: center; font-size: 0.75rem; color: #10b981; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">Final</div>
            {col_f_html}
        </div>
        <div class="bracket-col" style="justify-content: center;">
            {champ_html}
        </div>
    </div>
    """
    st.markdown(clean_html(bracket_html), unsafe_allow_html=True)

