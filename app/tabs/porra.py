"""Pestana 'Mi porra': formulario completo de la apuesta + puntos esperados."""
from __future__ import annotations
import json
import streamlit as st

from app.utils import run_simulation, freeze_elo, get_elo_with_biases, ROOT, load_real_results, run_simulation_with_real
from app.styles import PRIMARY, ACCENT, TEXT_DIM, GOOD, DANGER, BG_CARD
from app.components import big_stat
from src.tournament.groups import GROUPS, ALL_TEAMS
from src.data.team_profile import ISO_CODES
from src.scoring.porra import (
    POINTS_R32_EXACT, POINTS_R32_WRONG_POS, POINTS_R16, POINTS_QF, POINTS_SF,
    POINTS_FINAL, POINTS_CHAMPION,
)

from app.tabs.seguimiento import get_live_tournament_state


PORRA_PATH = ROOT / "data" / "processed" / "porra_usuario.json"


def _default_porra() -> dict:
    return {
        "groups": {g: [None, None, None] for g in GROUPS},
        "r16": [None] * 16,   # 16 equipos a octavos
        "qf": [None] * 8,
        "sf": [None] * 4,
        "final": [None] * 2,
        "champion": None,
        "mvp_gold": None, "mvp_silver": None, "mvp_bronze": None,
        "top_scorer": None,
        "total_goals": None,
    }


def _load_porra() -> dict:
    if PORRA_PATH.exists():
        loaded = json.loads(PORRA_PATH.read_text())
        # Merge con default por si hay nuevas claves
        d = _default_porra()
        d.update(loaded)
        # Garantizar listas con tamano correcto
        for key, size in [("r16", 16), ("qf", 8), ("sf", 4), ("final", 2)]:
            cur = d.get(key, [])
            if len(cur) < size: cur = cur + [None] * (size - len(cur))
            d[key] = cur[:size]
        for g in GROUPS:
            cur = d["groups"].get(g, [None, None, None])
            if len(cur) < 3: cur = cur + [None] * (3 - len(cur))
            d["groups"][g] = cur[:3]
        return d
    return _default_porra()


def _save_porra(p: dict) -> None:
    PORRA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORRA_PATH.write_text(json.dumps(p, indent=2, ensure_ascii=False))


def _load_all_confirmed_players() -> list[str]:
    from src.data.squad import SQUADS_DIR
    players_list = []
    if SQUADS_DIR.exists():
        for p_file in SQUADS_DIR.glob("*.json"):
            try:
                sq_data = json.loads(p_file.read_text(encoding="utf-8"))
                team_name = sq_data.get("team", "")
                for pl in sq_data.get("players", []):
                    players_list.append(f"{pl['name']} ({team_name})")
            except Exception:
                pass
    return sorted(players_list)


def _player_select(label: str, all_players_list: list[str], current_val: str | None, key: str) -> str:
    current_val = current_val or ""
    opts = ["-"] + all_players_list + ["✍️ Escribir a mano..."]
    
    default_opt = "-"
    show_manual = False
    
    if not current_val:
        default_opt = "-"
    elif current_val in all_players_list:
        default_opt = current_val
    else:
        default_opt = "✍️ Escribir a mano..."
        show_manual = True
        
    sel_opt = st.selectbox(label, opts, index=opts.index(default_opt), key=f"sel_opt_{key}")
    
    if sel_opt == "✍️ Escribir a mano...":
        manual_val = st.text_input(f"Escribe {label} manualmente", value=current_val if show_manual else "", key=f"man_val_{key}")
        return manual_val
    elif sel_opt == "-":
        return ""
    else:
        return sel_opt


def _flag(team: str | None, size: int = 24) -> str:
    if not team or team == "-":
        return f'<div style="width:{size}px;height:{int(size*0.75)}px;background:#1f2937;border-radius:2px;"></div>'
    iso = ISO_CODES.get(team, "un")
    return f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:{size}px;height:{int(size*0.75)}px;border-radius:2px;object-fit:cover;">'


def _team_select(label: str, options: list[str], current: str | None, key: str,
                 with_flag: bool = True) -> str | None:
    """Selectbox con bandera del equipo seleccionado al lado."""
    opts = ["-"] + options
    default = current if current in opts else "-"
    if with_flag:
        c1, c2 = st.columns([1, 8])
        with c1:
            st.markdown(_flag(current, 28), unsafe_allow_html=True)
        with c2:
            sel = st.selectbox(label, opts, index=opts.index(default), key=key,
                               label_visibility="collapsed")
    else:
        sel = st.selectbox(label, opts, index=opts.index(default), key=key)
    return sel if sel != "-" else None


def render():
    st.header("Mi porra")
    st.caption("Rellena cada fase como en el Excel. La app calcula los puntos esperados segun el modelo.")

    elo = get_elo_with_biases()
    summary = run_simulation(freeze_elo(elo), 10_000, seed=42)

    if "porra" not in st.session_state:
        st.session_state.porra = _load_porra()
    porra = st.session_state.porra

    # === KPI: Puntos Reales, Esperados y Máximos ===
    real_results = load_real_results()
    state = get_live_tournament_state(real_results, elo)
    real_pts, max_pts = compute_real_and_max_points(porra, state)
    expected_pts = _compute_expected_points(porra, summary)

    c_real, c_exp, c_max = st.columns(3)
    with c_real:
        st.markdown(big_stat(f"{real_pts['TOTAL']}", "PUNTOS REALES"), unsafe_allow_html=True)
    with c_exp:
        st.markdown(big_stat(f"{expected_pts['TOTAL']:.1f}", "PUNTOS ESPERADOS"), unsafe_allow_html=True)
    with c_max:
        st.markdown(big_stat(f"{max_pts['TOTAL']}", "PUNTOS MÁXIMOS"), unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    with st.expander("📊 Ver desglose detallado por categorías", expanded=False):
        html_breakdown = f"""
        <table style="width:100%; border-collapse: collapse; font-size: 0.9rem; color: #cbd5e1; background: rgba(15, 23, 42, 0.4); border-radius: 12px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.03); text-align: center;">
            <thead>
                <tr style="background: rgba(15, 23, 42, 0.7); border-bottom: 2px solid rgba(255, 255, 255, 0.03); font-weight: 600;">
                    <th style="padding: 12px 10px; text-align: left; color: #f8fafc;">Categoría</th>
                    <th style="padding: 12px 10px; color: {GOOD};">Puntos Reales</th>
                    <th style="padding: 12px 10px; color: {PRIMARY};">Puntos Esperados</th>
                    <th style="padding: 12px 10px; color: {ACCENT};">Puntos Máximos</th>
                </tr>
            </thead>
            <tbody>
        """
        for cat in ["Grupos", "Octavos", "Cuartos", "Semis", "Final", "Campeon"]:
            val_real = real_pts[cat]
            val_exp = expected_pts[cat]
            val_max = max_pts[cat]
            cat_display = "Campeón" if cat == "Campeon" else cat
            
            html_breakdown += f"""
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                    <td style="padding: 12px 10px; text-align: left; font-weight: 600; color: #cbd5e1;">{cat_display}</td>
                    <td style="padding: 12px 10px; font-weight: 700; color: {GOOD if val_real > 0 else TEXT_DIM};">{val_real}</td>
                    <td style="padding: 12px 10px; font-weight: 700; color: {PRIMARY};">{val_exp:.1f}</td>
                    <td style="padding: 12px 10px; font-weight: 700; color: {ACCENT};">{val_max}</td>
                </tr>
            """
        html_breakdown += f"""
                <tr style="background: rgba(15, 23, 42, 0.7); font-weight: 800; border-top: 2px solid rgba(255, 255, 255, 0.03);">
                    <td style="padding: 14px 10px; text-align: left; color: #ffffff;">TOTAL</td>
                    <td style="padding: 14px 10px; color: {GOOD};">{real_pts['TOTAL']}</td>
                    <td style="padding: 14px 10px; color: {PRIMARY}; font-size: 1.05rem;">{expected_pts['TOTAL']:.1f}</td>
                    <td style="padding: 14px 10px; color: {ACCENT};">{max_pts['TOTAL']}</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(html_breakdown, unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Acciones rapidas ===
    cA, cB, cC = st.columns([1, 1, 2])
    with cA:
        if st.button("💾 Guardar porra", type="primary", use_container_width=True):
            _save_porra(porra)
            from src.data.porra_history import append_version as _av
            _av(porra, note="Guardado manual")
            st.success("Guardada")
    with cB:
        if st.button("🎲 Autorellenar con favoritos del modelo", use_container_width=True):
            _autofill_with_model(porra, summary)
            _save_porra(porra)
            st.rerun()
    with cC:
        st.caption("Los puntos esperados se recalculan en vivo segun el modelo + tus ajustes.")

    # === Optimizador de porra ===
    with st.expander("🧠 Optimizador: ¿qué picks debería cambiar para ganar más puntos esperados?", expanded=False):
        _render_porra_optimizer(porra, summary, state)

    # === Historial de versiones de la porra ===
    with st.expander("📚 Historial de versiones de tu porra", expanded=False):
        _render_porra_history(porra)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Fase de grupos ===
    st.subheader("Fase de grupos")
    st.caption(f"**{POINTS_R32_EXACT} pts** posicion exacta · **{POINTS_R32_WRONG_POS} pts** clasificado en otra posicion")

    grid = st.columns(4)
    for i, letter in enumerate(sorted(GROUPS)):
        with grid[i % 4]:
            st.markdown(f"<h4 style='color:{PRIMARY}; margin-bottom:8px;'>Grupo {letter}</h4>",
                        unsafe_allow_html=True)
            teams_in_group = GROUPS[letter]
            current = porra["groups"].get(letter, [None, None, None])
            picks = []
            for pos, label in enumerate(["1.º", "2.º", "3.º"]):
                # Excluir equipos ya seleccionados arriba (no se puede tener el mismo equipo 2 veces)
                available = [t for t in teams_in_group if t not in picks]
                sel = _team_select(label, available, current[pos],
                                   key=f"grp_{letter}_{pos}")
                picks.append(sel)
            porra["groups"][letter] = picks

            # Ayuda: top3 del modelo
            top3 = sorted(summary["group_top3"].get(letter, {}).items(),
                          key=lambda x: -x[1])[:3]
            help_html = "<div style='font-size:0.75rem; color:" + TEXT_DIM + "; margin-top:8px;'>"
            help_html += "Top modelo:<br>"
            for t, p in top3:
                help_html += f"&nbsp;&bull; {t} ({p*100:.0f}%)<br>"
            help_html += "</div>"
            st.markdown(help_html, unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Octavos (16 clasificados) ===
    st.subheader(f"Octavos de final · {POINTS_R16} pts por cada acierto")
    st.caption("Quienes son los 16 equipos que clasifican a Octavos (1.º y 2.º de cada grupo + 8 mejores terceros).")
    # Sugerencia: los 16 con mas probabilidad de clasificar
    suggested_r16 = [t for t, _ in sorted(summary["r16"].items(), key=lambda x: -x[1])[:16]]

    cols = st.columns(4)
    for i in range(16):
        with cols[i % 4]:
            current = porra["r16"][i]
            sel = _team_select(f"Equipo {i+1}", ALL_TEAMS, current, key=f"r16_{i}")
            porra["r16"][i] = sel
    _render_top_suggestions("Top 16 segun el modelo (probabilidad de pasar a octavos):",
                            summary["r16"], n=16)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Cuartos (8) ===
    st.subheader(f"Cuartos de final · {POINTS_QF} pts por cada acierto")
    cols = st.columns(4)
    for i in range(8):
        with cols[i % 4]:
            current = porra["qf"][i]
            sel = _team_select(f"Equipo {i+1}", ALL_TEAMS, current, key=f"qf_{i}")
            porra["qf"][i] = sel
    _render_top_suggestions("Top 8 segun el modelo:", summary["quarter"], n=8)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Semifinales (4) ===
    st.subheader(f"Semifinales · {POINTS_SF} pts por cada acierto")
    cols = st.columns(4)
    for i in range(4):
        with cols[i % 4]:
            current = porra["sf"][i]
            sel = _team_select(f"Equipo {i+1}", ALL_TEAMS, current, key=f"sf_{i}")
            porra["sf"][i] = sel
    _render_top_suggestions("Top 4 segun el modelo:", summary["semifinal"], n=4)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Final (2 finalistas) ===
    st.subheader(f"Final · {POINTS_FINAL} pts por cada finalista acertado")
    cols = st.columns(2)
    for i in range(2):
        with cols[i]:
            current = porra["final"][i]
            sel = _team_select(f"Finalista {i+1}", ALL_TEAMS, current, key=f"final_{i}")
            porra["final"][i] = sel
    _render_top_suggestions("Top 2 segun el modelo:", summary["finalist"], n=4)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Campeon ===
    st.subheader(f"Campeon · {POINTS_CHAMPION} pts")
    cA, cB = st.columns([1, 2])
    with cA:
        current_champ = porra.get("champion")
        sel = _team_select("Campeon", ALL_TEAMS, current_champ, key="champ_pick")
        porra["champion"] = sel
    with cB:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_top_suggestions("Top 5 candidatos a campeon:", summary["champion"], n=5)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Premios individuales ===
    st.subheader("Premios individuales")
    st.info(
        "💡 **Listas oficiales**: Selecciona jugadores confirmados directamente de las plantillas actualizadas en Transfermarkt, "
        "o selecciona 'Escribir a mano...' si el equipo aún no tiene la lista confirmada."
    )
    all_players = _load_all_confirmed_players()
    
    c1, c2, c3 = st.columns(3)
    with c1: porra["mvp_gold"] = _player_select("🥇 Balón de Oro", all_players, porra.get("mvp_gold"), "mvp_gold")
    with c2: porra["mvp_silver"] = _player_select("🥈 Balón de Plata", all_players, porra.get("mvp_silver"), "mvp_silver")
    with c3: porra["mvp_bronze"] = _player_select("🥉 Balón de Bronce", all_players, porra.get("mvp_bronze"), "mvp_bronze")

    c4, c5 = st.columns(2)
    with c4:
        porra["top_scorer"] = _player_select("⚽ Bota de Oro (Pichichi)", all_players, porra.get("top_scorer"), "top_scorer")

        pichichi_probs = summary.get("pichichi", {})
        if pichichi_probs:
            top_p = sorted(pichichi_probs.items(), key=lambda x: -x[1])[:5]
            pills_p = ""
            for player, p in top_p:
                pills_p += (
                    f'<span style="display:inline-flex;align-items:center;gap:6px;'
                    f'background:{BG_CARD};border:1px solid #1f2937;border-radius:20px;'
                    f'padding:4px 10px;margin:3px;font-size:0.75rem;">'
                    f'{player} <span style="color:{ACCENT};font-weight:600;">{p*100:.1f}%</span>'
                    f'</span>'
                )
            st.markdown(f'<div style="margin-top:6px;"><span style="color:{TEXT_DIM};font-size:0.75rem;">Sugerencias del Pichichi según el modelo:</span><br>{pills_p}</div>',
                        unsafe_allow_html=True)
    with c5:
        default_goals = porra.get("total_goals") or int(summary["expected_total_goals"])
        porra["total_goals"] = st.number_input(
            "🎯 Total goles del Mundial",
            min_value=0, max_value=600,
            value=int(default_goals), step=1,
            help=f"El modelo espera ~{summary['expected_total_goals']:.0f} goles. "
                 f"30 pts por acertar, -1 pt por cada gol que te alejes, hasta 0 pts si te alejas 30 o mas."
        )

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # === Resumen final ===
    st.subheader("Resumen de tu porra")
    if st.button("💾 Guardar porra completa", type="primary"):
        _save_porra(porra)
        st.success(f"Guardada en {PORRA_PATH}")

    # Reimprime KPIs
    c_real, c_exp, c_max = st.columns(3)
    with c_real:
        st.markdown(big_stat(f"{real_pts['TOTAL']}", "PUNTOS REALES"), unsafe_allow_html=True)
    with c_exp:
        st.markdown(big_stat(f"{expected_pts['TOTAL']:.1f}", "PUNTOS ESPERADOS"), unsafe_allow_html=True)
    with c_max:
        st.markdown(big_stat(f"{max_pts['TOTAL']}", "PUNTOS MÁXIMOS"), unsafe_allow_html=True)





def _render_porra_history(current_porra: dict):
    """UI para ver/restaurar versiones anteriores de la porra."""
    from src.data.porra_history import (
        list_versions, append_version, get_version, delete_version,
        _summary_pick, diff_versions,
    )

    versions = list_versions()
    st.caption("Cada vez que pulses 💾 se añade un snapshot. Puedes restaurar versiones anteriores.")

    cH1, cH2 = st.columns([2, 1])
    with cH1:
        note = st.text_input("Nota para el snapshot (opcional)", key="porra_snapshot_note",
                              placeholder="Ej: 'antes de cambiar a Francia campeón'")
    with cH2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("📸 Guardar snapshot ahora", key="snapshot_now", use_container_width=True):
            append_version(current_porra, note=note)
            st.success("Snapshot guardado.")
            st.rerun()

    if not versions:
        st.info("Aún no hay snapshots. Pulsa el botón de arriba o guarda la porra normalmente.")
        return

    st.markdown(f"**{len(versions)} versiones guardadas** (más reciente primero)")
    for idx, v in enumerate(versions):
        ts = v["timestamp"].replace("T", " ")
        summary_line = _summary_pick(v["porra"])
        note = v.get("note") or ""
        with st.container():
            cV1, cV2, cV3 = st.columns([3, 1, 1])
            with cV1:
                st.markdown(f"**{ts}** · {summary_line}")
                if note:
                    st.caption(f"📝 {note}")
            with cV2:
                if st.button("🔄 Restaurar", key=f"restore_{ts}", use_container_width=True):
                    st.session_state.porra = v["porra"]
                    _save_porra(v["porra"])
                    st.success("Porra restaurada.")
                    st.rerun()
            with cV3:
                if idx > 0 and st.button("🔍 Ver cambios", key=f"diff_{ts}", use_container_width=True):
                    newer = versions[idx - 1]
                    diffs = diff_versions(v, newer)
                    if diffs:
                        st.markdown("**Cambios vs la siguiente versión:**")
                        for d in diffs:
                            st.markdown(f"• {d}")
                    else:
                        st.info("Sin cambios entre estas versiones.")


def _eliminated_teams(state: dict) -> set[str]:
    """Equipos descartados según el estado real del torneo (grupos cerrados + eliminatorias jugadas)."""
    eliminated: set[str] = set()
    if state.get("all_groups_complete"):
        qualified: set[str] = set()
        for home, away in state["r32_pairings"].values():
            if home in ALL_TEAMS: qualified.add(home)
            if away in ALL_TEAMS: qualified.add(away)
        for team in ALL_TEAMS:
            if team not in qualified:
                eliminated.add(team)
    else:
        for _g, standings in state.get("group_standings", {}).items():
            if all(t["played"] == 3 for t in standings):
                eliminated.add(standings[3]["team"])
    for round_key in ["r32", "r16", "qf", "sf", "final"]:
        winners = state.get(f"{round_key}_winners", {})
        pairings = state.get("r32_pairings" if round_key == "r32" else f"{round_key}_pairings", {})
        for fifa_id, winner in winners.items():
            home, away = pairings.get(fifa_id, (None, None))
            if home and away:
                loser = away if winner == home else home
                if loser in ALL_TEAMS:
                    eliminated.add(loser)
    return eliminated


def _render_porra_optimizer(porra: dict, summary: dict, state: dict):
    """UI del optimizador de porra."""
    from src.model.porra_optimizer import suggest_changes

    st.caption(
        "Recomendaciones basadas en EV (probabilidad × puntos). "
        "Sólo se muestran cambios que **aumentan los puntos esperados**, "
        "excluyendo equipos ya eliminados."
    )
    objective = st.radio(
        "Objetivo",
        ["max_points", "contrarian", "safe"],
        horizontal=True,
        format_func=lambda x: {"max_points": "Maximizar puntos esperados",
                                "contrarian": "Contrarian (evita favoritos)",
                                "safe": "Hedge / seguro (sólo cambios grandes)"}[x],
        key="optim_obj",
    )
    eliminated = _eliminated_teams(state)
    sugg = suggest_changes(porra, summary, eliminated, objective=objective)

    if not sugg:
        st.success("✅ Tu porra ya está optimizada según este objetivo. No hay cambios que mejoren la EV.")
        return

    st.markdown(f"**Top {min(8, len(sugg))} sugerencias por impacto:**")
    for s in sugg[:8]:
        cur = s.current_pick or "—"
        delta_color = GOOD
        st.markdown(
            f"<div style='background:{BG_CARD}; border:1px solid #1f2937; "
            f"border-radius:10px; padding:10px 14px; margin-bottom:8px;'>"
            f"<div style='display:flex; align-items:center; justify-content:space-between; gap:12px;'>"
            f"<div>"
            f"<div style='font-size:0.75rem; color:{TEXT_DIM}; text-transform:uppercase;'>{s.position}</div>"
            f"<div style='font-size:0.95rem; margin-top:4px;'>"
            f"<span style='color:{TEXT_DIM};'>{cur}</span> "
            f"<span style='color:{PRIMARY}; font-weight:700;'> → {s.suggested_pick}</span>"
            f"</div></div>"
            f"<div style='text-align:right;'>"
            f"<div style='font-size:0.78rem; color:{TEXT_DIM};'>EV {s.current_ev:.2f} → {s.suggested_ev:.2f}</div>"
            f"<div style='font-size:1.25rem; font-weight:800; color:{delta_color};'>+{s.delta:.2f} pts</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )

    # Botón aplicar todo
    if st.button("⚡ Aplicar TODAS las sugerencias (sobrescribe picks)", key="apply_optim"):
        for s in sugg:
            if s.category == "champion":
                porra["champion"] = s.suggested_pick
            elif s.category == "final":
                # Extraer índice de "Finalista #X"
                idx = int(s.position.split("#")[-1]) - 1
                while len(porra.get("final", [])) <= idx:
                    porra.setdefault("final", []).append(None)
                porra["final"][idx] = s.suggested_pick
            elif s.category == "sf":
                idx = int(s.position.split("#")[-1]) - 1
                while len(porra.get("sf", [])) <= idx:
                    porra.setdefault("sf", []).append(None)
                porra["sf"][idx] = s.suggested_pick
            elif s.category == "qf":
                idx = int(s.position.split("#")[-1]) - 1
                while len(porra.get("qf", [])) <= idx:
                    porra.setdefault("qf", []).append(None)
                porra["qf"][idx] = s.suggested_pick
            elif s.category == "r16":
                idx = int(s.position.split("#")[-1]) - 1
                while len(porra.get("r16", [])) <= idx:
                    porra.setdefault("r16", []).append(None)
                porra["r16"][idx] = s.suggested_pick
        _save_porra(porra)
        st.success("Aplicado todo. Recarga para ver los cambios.")
        st.rerun()


def _render_top_suggestions(title: str, probs: dict[str, float], n: int):
    """Renderiza una linea horizontal con los top-N segun probabilidades."""
    top = sorted(probs.items(), key=lambda x: -x[1])[:n]
    pills = ""
    for team, p in top:
        iso = ISO_CODES.get(team, "un")
        pills += (
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'background:{BG_CARD};border:1px solid #1f2937;border-radius:20px;'
            f'padding:4px 10px;margin:3px;font-size:0.8rem;">'
            f'<img src="https://flagcdn.com/w20/{iso}.png" style="width:16px;height:12px;border-radius:1px;">'
            f'{team} <span style="color:{PRIMARY};font-weight:600;">{p*100:.0f}%</span>'
            f'</span>'
        )
    st.markdown(f'<div style="margin-top:8px;"><span style="color:{TEXT_DIM};font-size:0.8rem;">{title}</span><br>{pills}</div>',
                unsafe_allow_html=True)


def _autofill_with_model(porra: dict, summary: dict) -> None:
    """Rellena la porra con la opcion mas probable de cada apartado."""
    # Grupos
    for g in GROUPS:
        gw = summary["group_winner"].get(g, {})
        gtop2 = summary["group_top2"].get(g, {})
        third = summary["third_place"].get(g, {})
        first = max(gw, key=gw.get) if gw else None
        # Segundo: el de top2 con mayor prob que NO sea el primero
        candidates2 = {t: p for t, p in gtop2.items() if t != first}
        second = max(candidates2, key=candidates2.get) if candidates2 else None
        # Tercero: el de prob ser 3.º mas alta que no sea ya 1 ni 2
        candidates3 = {t: p for t, p in third.items() if t != first and t != second}
        third_pick = max(candidates3, key=candidates3.get) if candidates3 else None
        porra["groups"][g] = [first, second, third_pick]

    # R16: top 16 segun p(octavos)
    porra["r16"] = [t for t, _ in sorted(summary["r16"].items(), key=lambda x: -x[1])[:16]]
    porra["qf"] = [t for t, _ in sorted(summary["quarter"].items(), key=lambda x: -x[1])[:8]]
    porra["sf"] = [t for t, _ in sorted(summary["semifinal"].items(), key=lambda x: -x[1])[:4]]
    porra["final"] = [t for t, _ in sorted(summary["finalist"].items(), key=lambda x: -x[1])[:2]]
    porra["champion"] = max(summary["champion"], key=summary["champion"].get)
    porra["total_goals"] = int(summary["expected_total_goals"])


def _compute_expected_points(porra: dict, summary: dict) -> dict[str, float]:
    """Puntos esperados de la porra."""
    b = {"Grupos": 0.0, "Octavos": 0.0, "Cuartos": 0.0, "Semis": 0.0,
         "Final": 0.0, "Campeon": 0.0, "TOTAL": 0.0}

    # Grupos
    for g, picks in porra.get("groups", {}).items():
        gw = summary["group_winner"].get(g, {})
        gtop2 = summary["group_top2"].get(g, {})
        gtop3 = summary["group_top3"].get(g, {})
        third = summary["third_place"].get(g, {})
        # 2.º = top2 - 1.º
        gsecond = {t: gtop2.get(t, 0) - gw.get(t, 0) for t in gtop2}
        for pos, team in enumerate(picks):
            if not team: continue
            p_exact = (gw, gsecond, third)[pos].get(team, 0)
            p_in_top3 = gtop3.get(team, 0)
            p_wrong_pos = max(p_in_top3 - p_exact, 0)
            b["Grupos"] += p_exact * POINTS_R32_EXACT + p_wrong_pos * POINTS_R32_WRONG_POS

    # Octavos (5 pts por cada acierto entre clasificados)
    for t in porra.get("r16", []):
        if t: b["Octavos"] += summary["r16"].get(t, 0) * POINTS_R16

    # Cuartos
    for t in porra.get("qf", []):
        if t: b["Cuartos"] += summary["quarter"].get(t, 0) * POINTS_QF

    # Semis
    for t in porra.get("sf", []):
        if t: b["Semis"] += summary["semifinal"].get(t, 0) * POINTS_SF

    # Final
    for t in porra.get("final", []):
        if t: b["Final"] += summary["finalist"].get(t, 0) * POINTS_FINAL

    # Campeon
    if porra.get("champion"):
        b["Campeon"] += summary["champion"].get(porra["champion"], 0) * POINTS_CHAMPION

    b["TOTAL"] = sum(v for k, v in b.items() if k != "TOTAL")
    return b


def compute_real_and_max_points(porra: dict, state: dict) -> tuple[dict[str, int], dict[str, int]]:
    """Calcula el desglose de Puntos Reales y Puntos Máximos Posibles."""
    eliminated_teams = set()
    
    # A. En la fase de grupos
    if state["all_groups_complete"]:
        qualified_teams = set()
        for home, away in state["r32_pairings"].values():
            if home in ALL_TEAMS: qualified_teams.add(home)
            if away in ALL_TEAMS: qualified_teams.add(away)
        for team in ALL_TEAMS:
            if team not in qualified_teams:
                eliminated_teams.add(team)
    else:
        for g, standings in state["group_standings"].items():
            group_complete = all(t["played"] == 3 for t in standings)
            if group_complete:
                eliminated_teams.add(standings[3]["team"])
                
    # B. En las eliminatorias (cualquier perdedor de un partido jugado queda eliminado)
    for round_key in ["r32", "r16", "qf", "sf", "final"]:
        winners = state[f"{round_key}_winners"]
        pairings = state[f"{round_key}_pairings"] if round_key != "r32" else state["r32_pairings"]
        for fifa_id, winner in winners.items():
            home, away = pairings.get(fifa_id, (None, None))
            if home and away:
                loser = away if winner == home else home
                if loser in ALL_TEAMS:
                    eliminated_teams.add(loser)

    real = {"Grupos": 0, "Octavos": 0, "Cuartos": 0, "Semis": 0, "Final": 0, "Campeon": 0, "TOTAL": 0}
    max_pos = {"Grupos": 0, "Octavos": 0, "Cuartos": 0, "Semis": 0, "Final": 0, "Campeon": 0, "TOTAL": 0}

    # 3. Puntos de la fase de grupos
    for g, picks in porra.get("groups", {}).items():
        standings = state["group_standings"][g]
        group_complete = all(t["played"] == 3 for t in standings)
        
        if group_complete:
            actual_top3 = [standings[0]["team"], standings[1]["team"], standings[2]["team"]]
            g_pts = 0
            for pos, team in enumerate(picks):
                if not team: continue
                if team in actual_top3:
                    if actual_top3[pos] == team:
                        g_pts += POINTS_R32_EXACT
                    else:
                        g_pts += POINTS_R32_WRONG_POS
            real["Grupos"] += g_pts
            max_pos["Grupos"] += g_pts
        else:
            real["Grupos"] += 0
            max_pos["Grupos"] += sum(POINTS_R32_EXACT for t in picks if t)

    # 4. Octavos (Clasificación a R16)
    actual_r16_teams = set(state["r32_winners"].values())
    for t in porra.get("r16", []):
        if not t: continue
        if t in actual_r16_teams:
            real["Octavos"] += POINTS_R16
            max_pos["Octavos"] += POINTS_R16
        elif t in eliminated_teams:
            pass
        else:
            max_pos["Octavos"] += POINTS_R16

    # 5. Cuartos (Clasificación a QF)
    actual_qf_teams = set(state["r16_winners"].values())
    for t in porra.get("qf", []):
        if not t: continue
        if t in actual_qf_teams:
            real["Cuartos"] += POINTS_QF
            max_pos["Cuartos"] += POINTS_QF
        elif t in eliminated_teams:
            pass
        else:
            max_pos["Cuartos"] += POINTS_QF

    # 6. Semis (Clasificación a SF)
    actual_sf_teams = set(state["qf_winners"].values())
    for t in porra.get("sf", []):
        if not t: continue
        if t in actual_sf_teams:
            real["Semis"] += POINTS_SF
            max_pos["Semis"] += POINTS_SF
        elif t in eliminated_teams:
            pass
        else:
            max_pos["Semis"] += POINTS_SF

    # 7. Finalistas (Clasificación a la Final)
    actual_finalists = set(state["sf_winners"].values())
    for t in porra.get("final", []):
        if not t: continue
        if t in actual_finalists:
            real["Final"] += POINTS_FINAL
            max_pos["Final"] += POINTS_FINAL
        elif t in eliminated_teams:
            pass
        else:
            max_pos["Final"] += POINTS_FINAL

    # 8. Campeón
    champ_pick = porra.get("champion")
    actual_champion = state["champion"]
    if champ_pick:
        if champ_pick == actual_champion:
            real["Campeon"] += POINTS_CHAMPION
            max_pos["Campeon"] += POINTS_CHAMPION
        elif champ_pick in eliminated_teams or (actual_champion and champ_pick != actual_champion):
            pass
        else:
            max_pos["Campeon"] += POINTS_CHAMPION

    real["TOTAL"] = sum(v for k, v in real.items() if k != "TOTAL")
    max_pos["TOTAL"] = sum(v for k, v in max_pos.items() if k != "TOTAL")

    return real, max_pos
