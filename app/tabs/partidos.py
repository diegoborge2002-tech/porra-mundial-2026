"""Pestaña Partidos: resultado esperado de cada partido del Mundial.

Para cada partido muestra el pronóstico del ensemble (Elo + modelo de stats
XGBoost del repo Simulaciones_Mundial): marcador más probable, goles
esperados, probabilidades 1X2 y la comparación entre ambos modelos.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st

from app.utils import ROOT, get_elo_with_biases, get_biases, load_real_results
from app.styles import TEXT_DIM, PRIMARY, ACCENT, GOOD, DANGER, BG_CARD
from app.components import render_table
from src.data.team_names import EN_TO_ES
from src.data.team_profile import ISO_CODES
from src.model import ensemble
from src.model.elo import HOME_ADVANTAGE
from src.model.poisson import elo_to_expected_goals
from src.model.match_probs import top_exact_scores, match_outcome_probs, representative_score
from src.tournament.groups import GROUPS, HOST_NATIONS, ALL_TEAMS
from src.tournament.bracket import R32_FIFA, R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA


def _load_wc_matches() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "raw" / "results.csv")
    df["date"] = pd.to_datetime(df["date"])
    wc = df[df["date"] >= "2026-06-01"].copy()
    wc["home_es"] = wc["home_team"].map(lambda x: EN_TO_ES.get(x, x))
    wc["away_es"] = wc["away_team"].map(lambda x: EN_TO_ES.get(x, x))
    # Overlay de resultados reales registrados en "Seguimiento en vivo"
    group_results = (load_real_results() or {}).get("group_matches", {})
    for idx, row in wc.iterrows():
        scores = (group_results.get(f"{row['home_es']} vs {row['away_es']}")
                  or group_results.get(f"{row['away_es']} vs {row['home_es']}"))
        if scores and len(scores) >= 2:
            if f"{row['home_es']} vs {row['away_es']}" in group_results:
                wc.loc[idx, ["home_score", "away_score"]] = [scores[0], scores[1]]
            else:
                wc.loc[idx, ["home_score", "away_score"]] = [scores[1], scores[0]]
    wc["jugado"] = wc["home_score"].notna()
    return wc.sort_values("date").reset_index(drop=True)


def _team_group(team: str) -> str:
    for g, teams in GROUPS.items():
        if team in teams:
            return g
    return ""


def _host_adv(home: str, away: str) -> float:
    h, a = home in HOST_NATIONS, away in HOST_NATIONS
    if h and not a:
        return HOME_ADVANTAGE
    if a and not h:
        return -HOME_ADVANTAGE
    return 0.0


def _predict_match(home: str, away: str, elo: dict[str, float], w: float) -> dict:
    """Pronóstico completo de un partido: Elo puro, stats XGBoost y ensemble."""
    elo_h, elo_a = elo.get(home, 1500.0), elo.get(away, 1500.0)
    ha = _host_adv(home, away)

    lh_elo, la_elo = elo_to_expected_goals(elo_h, elo_a, home_advantage=ha)
    p_elo = match_outcome_probs(lh_elo, la_elo, use_dc=True)

    stats = ensemble.get_stats_prediction(home, away)

    lh, la = ensemble.blended_lambdas(lh_elo, la_elo, home, away, ha, weight=w)
    p_ens = match_outcome_probs(lh, la, use_dc=True)
    top = top_exact_scores(lh, la, n=5, use_dc=True)
    best_score, best_score_p = representative_score(lh, la, use_dc=True)

    return {
        "lh": lh, "la": la,
        "p_h": p_ens[0], "p_x": p_ens[1], "p_a": p_ens[2],
        "top_scores": top,
        "best_score": best_score, "best_score_p": best_score_p,
        "elo": {"lh": lh_elo, "la": la_elo, "p": p_elo},
        "stats": stats,
        "disagreement": abs(p_elo[0] - stats["p_h"]) + abs(p_elo[2] - stats["p_a"]) if stats else 0.0,
    }


def _prob_bar(p_h: float, p_x: float, p_a: float) -> str:
    """Barra 1X2 estilo ticket con leyenda monoespaciada."""
    return (
        f'<div class="t-bar">'
        f'<div class="b1" style="width:{p_h*100:.1f}%;" title="Victoria local {p_h*100:.0f}%"></div>'
        f'<div class="bx" style="width:{p_x*100:.1f}%;" title="Empate {p_x*100:.0f}%"></div>'
        f'<div class="b2" style="width:{p_a*100:.1f}%;" title="Victoria visitante {p_a*100:.0f}%"></div>'
        f'</div>'
        f'<div class="t-legend">'
        f'<span style="color:{PRIMARY};">1 {p_h*100:.0f}%</span>'
        f'<span style="color:{TEXT_DIM};">X {p_x*100:.0f}%</span>'
        f'<span style="color:{ACCENT};">2 {p_a*100:.0f}%</span>'
        f'</div>'
    )


def _match_card(m: pd.Series, pred: dict) -> None:
    home, away = m["home_es"], m["away_es"]
    iso_h, iso_a = ISO_CODES.get(home, "un"), ISO_CODES.get(away, "un")
    g = _team_group(home)
    (best_h, best_a), best_p = pred["best_score"], pred["best_score_p"]

    # Resaltar al favorito con glow
    fav_h = "fav" if pred["p_h"] > max(pred["p_x"], pred["p_a"]) else ""
    fav_a = "fav" if pred["p_a"] > max(pred["p_x"], pred["p_h"]) else ""

    if m["jugado"]:
        gh, ga = int(m["home_score"]), int(m["away_score"])
        real_out = "H" if gh > ga else ("A" if gh < ga else "D")
        pred_out = max([("H", pred["p_h"]), ("D", pred["p_x"]), ("A", pred["p_a"])], key=lambda x: x[1])[0]
        hit_1x2 = real_out == pred_out
        hit_exact = (gh, ga) == (best_h, best_a)
        badge = ('<span class="hit">✓ MARCADOR EXACTO</span>' if hit_exact
                 else ('<span class="hit">✓ ACIERTO 1X2</span>' if hit_1x2
                       else '<span class="miss">✗ FALLO</span>'))
        center = (
            f'<div class="t-tag">Final</div>'
            f'<div class="t-score played">{gh} – {ga}</div>'
            f'<div class="t-sub">{badge}</div>'
            f'<div class="t-sub">esperado {best_h}–{best_a} ({best_p*100:.0f}%)</div>'
        )
    else:
        center = (
            f'<div class="t-tag">Esperado</div>'
            f'<div class="t-score">{best_h} – {best_a}</div>'
            f'<div class="t-sub">prob. {best_p*100:.0f}% · xG {pred["lh"]:.2f} – {pred["la"]:.2f}</div>'
        )

    group_badge = f'<span class="t-badge">GRUPO {g}</span>' if g else ""
    when = m["date"].strftime("%d %b · %H:%M") if hasattr(m["date"], "strftime") else m["date"]

    st.markdown(
        f"""
        <div class="ticket">
          <div class="t-row">
            <div class="t-team"><img src="https://flagcdn.com/w40/{iso_h}.png"> <span class="{fav_h}">{home}</span></div>
            <div class="t-center">{center}</div>
            <div class="t-team right"><span class="{fav_a}">{away}</span> <img src="https://flagcdn.com/w40/{iso_a}.png"></div>
          </div>
          {_prob_bar(pred["p_h"], pred["p_x"], pred["p_a"])}
          <div class="t-foot">
            <span>🗓 {when}</span>
            {group_badge}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"🔬 Detalle del modelo · {home} vs {away}", expanded=False):
        c1, c2, c3 = st.columns(3)
        e = pred["elo"]
        with c1:
            st.markdown(f"**⚖️ Elo dinámico**")
            st.markdown(
                f"xG: `{e['lh']:.2f} – {e['la']:.2f}`  \n"
                f"1X2: `{e['p'][0]*100:.0f}% / {e['p'][1]*100:.0f}% / {e['p'][2]*100:.0f}%`"
            )
        with c2:
            s = pred["stats"]
            st.markdown(f"**🤖 XGBoost (stats)**")
            if s:
                st.markdown(
                    f"xG: `{s['xg_h']:.2f} – {s['xg_a']:.2f}`  \n"
                    f"1X2: `{s['p_h']*100:.0f}% / {s['p_x']*100:.0f}% / {s['p_a']*100:.0f}%`"
                )
            else:
                st.caption("Sin datos para este cruce")
        with c3:
            st.markdown(f"**🎯 Ensemble**")
            st.markdown(
                f"xG: `{pred['lh']:.2f} – {pred['la']:.2f}`  \n"
                f"1X2: `{pred['p_h']*100:.0f}% / {pred['p_x']*100:.0f}% / {pred['p_a']*100:.0f}%`"
            )

        st.markdown("**Marcadores más probables (Dixon-Coles sobre el ensemble):**")
        chips = " · ".join(
            f"`{h}-{a}` {p*100:.1f}%" for (h, a), p in pred["top_scores"]
        )
        st.markdown(chips)

        ts_h, ts_a = ensemble.get_team_stats(home), ensemble.get_team_stats(away)
        if ts_h and ts_a:
            st.markdown("**Forma reciente (últimos 5 partidos, datos scrapeados):**")
            render_table([
                {"team": home, "xg": ts_h["xg5"], "pos": ts_h["posesion5"] * 100,
                 "rem": ts_h["remates5"], "fifa": ts_h["fifa_points"]},
                {"team": away, "xg": ts_a["xg5"], "pos": ts_a["posesion5"] * 100,
                 "rem": ts_a["remates5"], "fifa": ts_a["fifa_points"]},
            ], [
                {"label": "Equipo", "key": "team", "kind": "team"},
                {"label": "xG/partido", "key": "xg", "kind": "num", "fmt": "{:.2f}"},
                {"label": "Posesión", "key": "pos", "kind": "pct"},
                {"label": "Remates puerta", "key": "rem", "kind": "num"},
                {"label": "Ranking FIFA", "key": "fifa", "kind": "num"},
            ])


def _slot_label(slot) -> str:
    """Etiqueta legible para un slot del bracket FIFA."""
    if isinstance(slot, int):
        return f"Ganador P{slot}"
    if slot.startswith("3?"):
        return f"Mejor 3.º (cruza con 1{slot[2]})"
    pos = {"1": "1.º", "2": "2.º", "3": "3.º"}[slot[0]]
    return f"{pos} Grupo {slot[1]}"


_KO_ROUNDS = [
    ("r32", "Dieciseisavos (R32)", R32_FIFA, "28 jun – 3 jul"),
    ("r16", "Octavos de final", R16_FIFA, "4 – 7 jul"),
    ("qf", "Cuartos de final", QF_FIFA, "9 – 11 jul"),
    ("sf", "Semifinales", SF_FIFA, "14 – 15 jul"),
    ("final", "Final (Nueva Jersey)", F_FIFA, "19 jul"),
]


def _render_knockout(elo: dict[str, float], w: float) -> None:
    """Los 32 partidos eliminatorios: predicción si los cruces ya están definidos."""
    ko = (load_real_results() or {}).get("knockout_matches", {})
    for round_key, title, bracket, dates in _KO_ROUNDS:
        defined = ko.get(round_key, {})
        st.markdown(
            f'<div class="ko-round-title">🏆 {title}<span class="line"></span>'
            f'<span class="dates">{dates}</span></div>',
            unsafe_allow_html=True)
        for match_id, (slot_h, slot_a) in sorted(bracket.items()):
            info = defined.get(str(match_id)) or defined.get(match_id)
            if info and info.get("home") and info.get("away"):
                m = pd.Series({
                    "home_es": info["home"], "away_es": info["away"],
                    "home_score": info.get("home_score"),
                    "away_score": info.get("away_score"),
                    "jugado": info.get("home_score") is not None,
                    "date": f"P{match_id} · {title}",
                })
                pred = _predict_match(info["home"], info["away"], elo, w)
                _match_card(m, pred)
            else:
                st.markdown(
                    f'<div style="background:{BG_CARD}; border:1px dashed #334155; border-radius:10px; '
                    f'padding:8px 14px; margin-bottom:6px; display:flex; justify-content:space-between; '
                    f'color:{TEXT_DIM}; font-size:0.85rem;">'
                    f'<span>P{match_id} · {_slot_label(slot_h)} vs {_slot_label(slot_a)}</span>'
                    f'<span style="font-size:0.7rem;">por definir</span></div>',
                    unsafe_allow_html=True,
                )
        if round_key == "sf":
            st.markdown(
                f'<div style="background:{BG_CARD}; border:1px dashed #334155; border-radius:10px; '
                f'padding:8px 14px; margin-bottom:6px; color:{TEXT_DIM}; font-size:0.85rem;">'
                f'P103 · 3.er puesto: perdedores de las semifinales · 18 jul</div>',
                unsafe_allow_html=True,
            )
    st.caption(
        "Los cruces se rellenan automáticamente al registrar resultados "
        "(pestaña Seguimiento en vivo o `python scripts/dia.py ko ...`)."
    )


def render() -> None:
    st.header("🔮 Resultado esperado por partido")
    st.caption("Los 104 partidos del Mundial: 72 de fase de grupos + 32 eliminatorias (R32 → final).")

    elo = get_elo_with_biases()
    cfg = get_biases()
    w = cfg.stats_weight
    matches = _load_wc_matches()
    # Solo partidos entre equipos reales del torneo (excluye placeholders del KO)
    matches = matches[matches["home_es"].isin(ALL_TEAMS) & matches["away_es"].isin(ALL_TEAMS)]

    meta = ensemble.get_stats_meta()
    if ensemble.stats_available():
        hold = meta.get("holdout", {})
        st.caption(
            f"Ensemble **{(1-w)*100:.0f}% Elo + {w*100:.0f}% XGBoost-stats** "
            f"(modelo entrenado con {meta.get('n_matches_train', '?')} partidos 2021-2026 del repo "
            f"[Simulaciones_Mundial]({meta.get('source', '')}); "
            f"acierto 1X2 en holdout: {hold.get('accuracy', 0)*100:.0f}%). "
            f"El peso se ajusta en 🎯 Mis ajustes."
        )
    else:
        st.warning(
            "Modelo de stats no disponible (falta data/processed/stats_model.json). "
            "Ejecuta `python notebooks/04_entrenar_stats_model.py`. Mostrando Elo puro."
        )

    # ---- Filtros ----
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        team_filter = st.selectbox("Equipo", ["Todos"] + sorted(ALL_TEAMS), key="pt_team")
    with c2:
        group_filter = st.selectbox("Grupo", ["Todos"] + sorted(GROUPS.keys()), key="pt_group")
    with c3:
        status_filter = st.selectbox("Estado", ["Todos", "Pendientes", "Jugados"], key="pt_status")
    with c4:
        sort_mode = st.selectbox(
            "Ordenar por", ["Fecha", "Mayor discrepancia Elo vs XGBoost", "Partido más igualado"],
            key="pt_sort",
        )
    view_table = st.toggle("Vista tabla (todos los partidos de un vistazo)", value=False, key="pt_table")

    filtered = matches
    if team_filter != "Todos":
        filtered = filtered[(filtered["home_es"] == team_filter) | (filtered["away_es"] == team_filter)]
    if group_filter != "Todos":
        gteams = GROUPS[group_filter]
        filtered = filtered[filtered["home_es"].isin(gteams) | filtered["away_es"].isin(gteams)]
    if status_filter == "Pendientes":
        filtered = filtered[~filtered["jugado"]]
    elif status_filter == "Jugados":
        filtered = filtered[filtered["jugado"]]

    # ---- Predicciones ----
    preds = {i: _predict_match(m["home_es"], m["away_es"], elo, w) for i, m in filtered.iterrows()}

    if sort_mode == "Mayor discrepancia Elo vs XGBoost":
        order = sorted(preds, key=lambda i: -preds[i]["disagreement"])
    elif sort_mode == "Partido más igualado":
        order = sorted(preds, key=lambda i: abs(preds[i]["p_h"] - preds[i]["p_a"]))
    else:
        order = list(filtered.index)

    # ---- KPIs rápidos ----
    if preds:
        total_xg = sum(p["lh"] + p["la"] for p in preds.values())
        clear_fav = sum(1 for p in preds.values() if max(p["p_h"], p["p_a"]) > 0.55)
        k1, k2, k3 = st.columns(3)
        k1.metric("Partidos mostrados", len(preds))
        k2.metric("Goles esperados (suma)", f"{total_xg:.0f}")
        k3.metric("Con favorito claro (>55%)", f"{clear_fav} ({clear_fav/len(preds)*100:.0f}%)")

    st.divider()

    if view_table:
        rows = []
        for i in order:
            m, p = filtered.loc[i], preds[i]
            (bh, ba), bp = p["best_score"], p["best_score_p"]
            s = p["stats"] or {}
            rows.append({
                "Fecha": m["date"].strftime("%d %b"),
                "Grupo": _team_group(m["home_es"]),
                "Partido": f'{m["home_es"]} vs {m["away_es"]}',
                "Marcador esperado": f"{bh}-{ba}",
                "xG": f'{p["lh"]:.2f} – {p["la"]:.2f}',
                "P(1)": f'{p["p_h"]*100:.0f}%',
                "P(X)": f'{p["p_x"]*100:.0f}%',
                "P(2)": f'{p["p_a"]*100:.0f}%',
                "xG XGBoost": f'{s.get("xg_h", float("nan")):.2f} – {s.get("xg_a", float("nan")):.2f}' if s else "—",
                "Real": f'{int(m["home_score"])}-{int(m["away_score"])}' if m["jugado"] else "",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=600)
    else:
        if sort_mode == "Fecha":
            for date, group in filtered.loc[order].groupby("date", sort=True):
                st.markdown(f"##### {date.strftime('%A, %d %b %Y').capitalize()}")
                for i, m in group.iterrows():
                    _match_card(m, preds[i])
        else:
            for i in order:
                _match_card(filtered.loc[i], preds[i])

    # ---- Eliminatorias: los otros 32 partidos hasta completar los 104 ----
    st.divider()
    st.subheader("🏟 Eliminatorias (32 partidos)")
    _render_knockout(elo, w)

    # ---- Mapa de sedes (integrado desde la antigua pestaña Calendario) ----
    st.divider()
    st.subheader("🗺 Sedes del Mundial")
    st.caption("Las 16 sedes en México, EE. UU. y Canadá. Tamaño = nº de partidos · color = altitud.")
    from app.tabs.calendario import _render_venues_map
    _render_venues_map(_load_wc_matches())
