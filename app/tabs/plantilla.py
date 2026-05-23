"""Pestana 'Plantilla': analisis de plantillas por valor de mercado y rendimiento de club 2026.

La idea: cuantificar como el rendimiento de los jugadores en sus clubes durante la
temporada 2025-26 deberia influir en la probabilidad de cada seleccion en el Mundial.
"""
from __future__ import annotations
import json
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.utils import (
    ROOT, get_biases, freeze_elo, run_simulation, load_real_results,
)
from app.styles import PRIMARY, ACCENT, GOOD, DANGER, TEXT_DIM
from app.components import big_stat
from src.data.squad import (
    Player, Squad, load_squad, SQUADS_DIR, POSITIONS, POSITION_LABELS,
    calculate_club_performance_bias, ratings_to_elo_bias,
)
from src.data.team_profile import CONFEDERATIONS
from src.model.elo_dynamic import recalculate_elo_with_real
from src.tournament.groups import ALL_TEAMS


# Reproducimos las keywords de elite que usa calculate_club_performance_bias
ELITE_KEYWORDS = {
    "real madrid", "madrid", "bayern", "munich", "münchen", "man city", "manchester city",
    "liverpool", "arsenal", "psg", "paris saint", "barcelona", "barca", "inter",
    "juventus", "milan", "chelsea", "tottenham", "spurs", "atletico", "atlético",
    "dortmund", "leverkusen", "bayer", "aston villa", "newcastle", "lazio", "napoli", "roma",
}


def _is_elite(club: str) -> bool:
    if not club:
        return False
    cl = club.lower()
    return any(kw in cl for kw in ELITE_KEYWORDS)


@st.cache_data(show_spinner=False, ttl=600)
def _load_all_squads_with_players() -> dict[str, dict]:
    """Devuelve {team: metricas_agregadas} para selecciones con al menos 5 jugadores."""
    out: dict[str, dict] = {}
    if not SQUADS_DIR.exists():
        return out
    for path in sorted(SQUADS_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        team = raw.get("team", path.stem)
        squad = load_squad(team)
        if len(squad.players) < 5:
            continue

        starters = [p for p in squad.players if p.starter]
        starter_forms = [(p.recent_form if p.recent_form is not None else 6.0) for p in starters]
        all_forms = [(p.recent_form if p.recent_form is not None else 6.0) for p in squad.players]
        mv_values = [p.market_value for p in squad.players if p.market_value is not None]
        total_mv = sum(mv_values) if mv_values else 0.0
        mean_form_all = sum(all_forms) / len(all_forms) if all_forms else 6.0
        mean_form_starters = (
            sum(starter_forms) / len(starter_forms) if starter_forms else mean_form_all
        )
        elite_weighted = sum(
            (1.5 if p.starter else 0.5) for p in squad.players if _is_elite(p.club)
        )
        elite_players = sum(1 for p in squad.players if _is_elite(p.club))

        # Descomposicion del bias con pesos 1.0 (replica calculate_club_performance_bias)
        if total_mv > 0:
            mv_bias = 25.0 * math.log(max(0.1, total_mv / 50.0))
        else:
            mv_bias = -30.0
        pedigree_bias = elite_weighted * 5.0
        form_delta_sum = sum(
            ((p.recent_form if p.recent_form is not None else 6.0) - 6.0)
            * (2.0 if p.starter else 0.5)
            for p in squad.players
        )
        form_bias = form_delta_sum * 2.5
        total_bias = max(-200.0, min(200.0, mv_bias + pedigree_bias + form_bias))

        out[team] = {
            "team": team,
            "n_players": len(squad.players),
            "n_starters": len(starters),
            "total_mv": total_mv,
            "mean_form_all": mean_form_all,
            "mean_form_starters": mean_form_starters,
            "elite_weighted": elite_weighted,
            "elite_players": elite_players,
            "mv_bias": mv_bias,
            "pedigree_bias": pedigree_bias,
            "form_bias": form_bias,
            "club_bias_total": total_bias,
            "confederation": CONFEDERATIONS.get(team, "?"),
            "coach": squad.coach,
            "star_player": squad.star_player,
        }
    return out


def _build_elo(use_club: bool, w_mv: float, w_ped: float, w_form: float) -> dict[str, float]:
    """Construye un Elo aplicando biases manuales + (opcional) club performance con pesos dados.

    Equivalente a `BiasesConfig.apply_to` pero sin tocar el estado guardado del usuario.
    """
    from app.utils import load_base_elo
    base = load_base_elo()
    cfg = get_biases()
    biased: dict[str, float] = {}
    for team, elo in base.items():
        biased[team] = elo + cfg.get_delta(team)
        if use_club:
            sq = load_squad(team)
            biased[team] += calculate_club_performance_bias(
                sq, weight_mv=w_mv, weight_pedigree=w_ped, weight_recent_form=w_form
            )
    real = load_real_results()
    final = recalculate_elo_with_real(biased, real)
    return final


@st.cache_data(show_spinner="🎲 Simulando 5.000 torneos con club bias…", ttl=600)
def _mc_with_club(w_mv: float, w_ped: float, w_form: float, n_sims: int = 5000) -> dict:
    elo = _build_elo(True, w_mv, w_ped, w_form)
    real = load_real_results()
    return run_simulation(
        freeze_elo(elo), n_sims=n_sims, seed=42,
        real_results_str=json.dumps(real, sort_keys=True),
        porra_str="", amigos_fingerprint="plantilla-bias",
    )


@st.cache_data(show_spinner="🎲 Baseline (sin club bias)…", ttl=600)
def _mc_baseline(n_sims: int = 5000) -> dict:
    elo = _build_elo(False, 1.0, 1.0, 1.0)
    real = load_real_results()
    return run_simulation(
        freeze_elo(elo), n_sims=n_sims, seed=42,
        real_results_str=json.dumps(real, sort_keys=True),
        porra_str="", amigos_fingerprint="plantilla-base",
    )


# ─────────────────────────────────────────────────────────────
# Render principal
# ─────────────────────────────────────────────────────────────
def render() -> None:
    st.markdown("### 👥 Plantilla y rendimiento de club 2026")
    st.caption(
        "La gracia: ¿qué selecciones tienen jugadores que han hecho una temporada "
        "2025-26 brillante en sus clubes? Aquí cuantificamos cuánto debería trasladarse "
        "eso a la probabilidad de Mundial."
    )

    data = _load_all_squads_with_players()
    if not data:
        st.warning(
            "No hay plantillas con al menos 5 jugadores. Rellena algunas en "
            "`data/processed/squads/` y vuelve."
        )
        return

    sub1, sub2, sub3, sub4, sub5 = st.tabs([
        "🏆 Ranking", "🔬 Detalle", "⚖️ Impacto en el modelo",
        "🌍 Por confederación", "📊 Plantilla vs Elo",
    ])

    with sub1: _render_ranking(data)
    with sub2: _render_detail(data)
    with sub3: _render_impact(data)
    with sub4: _render_by_confed(data)
    with sub5: _render_vs_elo(data)


# ─────────────────────────────────────────────────────────────
# Sub-tab 1: Ranking
# ─────────────────────────────────────────────────────────────
def _render_ranking(data: dict[str, dict]) -> None:
    df = pd.DataFrame(list(data.values()))
    base_elo = _build_elo(False, 1.0, 1.0, 1.0)
    df["base_elo"] = df["team"].map(lambda t: int(base_elo.get(t, 0)))
    df["delta_elo"] = df["club_bias_total"].round(0).astype(int)

    n = len(df)
    mean_mv = df["total_mv"].mean()
    top5_mv = df.nlargest(5, "total_mv")["total_mv"].sum()
    std_bias = df["club_bias_total"].std()
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(big_stat(f"{n}", "Plantillas analizadas"), unsafe_allow_html=True)
    c2.markdown(big_stat(f"{mean_mv:.0f} M€", "Valor medio de plantilla"), unsafe_allow_html=True)
    c3.markdown(big_stat(f"{top5_mv:.0f} M€", "Suma del top 5"), unsafe_allow_html=True)
    c4.markdown(big_stat(f"{std_bias:.0f}", "σ del club bias",
                          tooltip="Cuánto diferencia el modelo a las selecciones según su plantilla."),
                unsafe_allow_html=True)

    st.markdown("")
    sort_by = st.radio(
        "Ordenar por",
        ["club_bias_total", "total_mv", "mean_form_starters", "elite_players"],
        horizontal=True,
        format_func=lambda x: {
            "club_bias_total": "Club bias total (Elo)",
            "total_mv": "Valor de mercado",
            "mean_form_starters": "Forma titulares 2026",
            "elite_players": "Nº jugadores en élite",
        }[x],
        key="plantilla_sort",
    )
    df_sorted = df.sort_values(sort_by, ascending=False).reset_index(drop=True)
    df_sorted.index = df_sorted.index + 1

    display = df_sorted[[
        "team", "total_mv", "n_players", "n_starters",
        "elite_players", "mean_form_starters",
        "mv_bias", "pedigree_bias", "form_bias",
        "club_bias_total", "base_elo", "delta_elo",
    ]].rename(columns={
        "team": "Selección",
        "total_mv": "Valor (M€)",
        "n_players": "Jugs",
        "n_starters": "Titulares",
        "elite_players": "Élite",
        "mean_form_starters": "Forma titulares",
        "mv_bias": "Δ valor",
        "pedigree_bias": "Δ pedigrí",
        "form_bias": "Δ forma",
        "club_bias_total": "Bias total",
        "base_elo": "Elo base",
        "delta_elo": "Δ Elo",
    })
    st.dataframe(
        display.style.format({
            "Valor (M€)": "{:.0f}",
            "Forma titulares": "{:.2f}",
            "Δ valor": "{:+.0f}",
            "Δ pedigrí": "{:+.0f}",
            "Δ forma": "{:+.0f}",
            "Bias total": "{:+.0f}",
            "Δ Elo": "{:+d}",
        }).background_gradient(subset=["Bias total"], cmap="RdYlGn", vmin=-200, vmax=200),
        use_container_width=True,
        height=560,
    )

    st.caption(
        "**Fórmula**: `bias = 25·log(valor/50M)·w_mv + 5·elite_weighted·w_pedigree + "
        "2.5·Σ(forma−6)·w_form`. Titulares ponderan ×2 (forma) y ×1.5 (pedigrí); "
        "suplentes ×0.5. Cap a ±200 Elo. Pesos aquí 1.0/1.0/1.0 — ajustables en la "
        "sub-pestaña *Impacto en el modelo*."
    )


# ─────────────────────────────────────────────────────────────
# Sub-tab 2: Detalle
# ─────────────────────────────────────────────────────────────
def _render_detail(data: dict[str, dict]) -> None:
    teams = sorted(data.keys())
    team = st.selectbox("Selección", teams, key="plantilla_team_detail")
    info = data[team]
    squad = load_squad(team)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(big_stat(f"{info['total_mv']:.0f} M€", "Valor total de plantilla",
                          tooltip="Suma de market_value de jugadores con dato."),
                unsafe_allow_html=True)
    c2.markdown(big_stat(f"{info['mean_form_starters']:.2f}", "Forma titulares (1–10)",
                          tooltip="Media de recent_form de los titulares (últimos 3 meses)."),
                unsafe_allow_html=True)
    c3.markdown(big_stat(f"{info['elite_players']}", "Jugadores en élite",
                          tooltip="Madrid, Bayern, City, PSG, Barça, Liverpool, Arsenal, "
                                   "Inter, Juve, Milan, Chelsea, Tottenham, Atlético, Dortmund, "
                                   "Leverkusen, Aston Villa, Newcastle, Lazio, Napoli, Roma."),
                unsafe_allow_html=True)
    c4.markdown(big_stat(f"{info['club_bias_total']:+.0f}", "Club bias generado (Elo)",
                          tooltip="Suma de las 3 componentes con pesos 1.0/1.0/1.0."),
                unsafe_allow_html=True)

    # Tabla de jugadores
    st.markdown("#### Jugadores")
    pos_filter = st.multiselect(
        "Filtrar posiciones",
        options=POSITIONS,
        default=POSITIONS,
        format_func=lambda x: POSITION_LABELS.get(x, x),
        key=f"pos_filter_{team}",
    )
    if pos_filter:
        rows = [
            {
                "Nombre": p.name,
                "Pos": p.position,
                "Club": p.club,
                "Titular": "✓" if p.starter else "",
                "Valor (M€)": p.market_value if p.market_value is not None else 0.0,
                "Forma": p.recent_form if p.recent_form is not None else 6.0,
                "Élite": "⭐" if _is_elite(p.club) else "",
            }
            for p in squad.players if p.position in pos_filter
        ]
        if rows:
            players_df = pd.DataFrame(rows)
            st.dataframe(
                players_df.sort_values(
                    ["Titular", "Valor (M€)"], ascending=[False, False]
                ).style.format({"Valor (M€)": "{:.0f}", "Forma": "{:.1f}"})
                  .background_gradient(subset=["Forma"], cmap="RdYlGn", vmin=3, vmax=9),
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    # Top listas
    co1, co2, co3 = st.columns(3)
    with co1:
        st.markdown("**🏷 Top 5 valor**")
        top_val = sorted([p for p in squad.players if p.market_value],
                         key=lambda p: -p.market_value)[:5]
        if not top_val:
            st.markdown(f"<span style='color:{TEXT_DIM}'>Sin datos de valor.</span>",
                        unsafe_allow_html=True)
        for p in top_val:
            st.markdown(f"• {p.name} — *{p.club}* — **{p.market_value:.0f} M€**")
    with co2:
        st.markdown("**🔥 Top 5 forma**")
        top_form = sorted(squad.players, key=lambda p: -(p.recent_form or 6.0))[:5]
        for p in top_form:
            f = p.recent_form or 6.0
            color = GOOD if f >= 7.5 else ACCENT if f >= 6.5 else TEXT_DIM
            st.markdown(
                f"• {p.name} — *{p.club}* — "
                f"<span style='color:{color}'>**{f:.1f}/10**</span>",
                unsafe_allow_html=True,
            )
    with co3:
        st.markdown("**⭐ En clubes élite**")
        elites = [p for p in squad.players if _is_elite(p.club)]
        if not elites:
            st.markdown(f"<span style='color:{TEXT_DIM}'>Sin jugadores en élite.</span>",
                        unsafe_allow_html=True)
        for p in elites[:10]:
            tag = "(T)" if p.starter else "(S)"
            st.markdown(f"• {p.name} {tag} — *{p.club}*")

    # Pirámide de forma jugador a jugador
    if squad.players:
        st.markdown("#### Forma reciente jugador a jugador")
        sorted_players = sorted(squad.players, key=lambda p: -(p.recent_form or 6.0))
        labels = [
            f"{p.name} ({p.position})" + (" ★" if p.starter else "")
            for p in sorted_players
        ]
        forms = [(p.recent_form or 6.0) for p in sorted_players]
        colors = [PRIMARY if p.starter else "#9ca3af" for p in sorted_players]
        fig = go.Figure(go.Bar(
            x=forms, y=labels, orientation="h",
            marker_color=colors, text=[f"{f:.1f}" for f in forms],
            textposition="outside",
        ))
        fig.update_layout(
            height=max(280, len(sorted_players) * 22),
            xaxis=dict(range=[0, 10], title="Forma (1-10)"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=30, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"),
        )
        fig.add_vline(x=6.0, line_dash="dash", line_color="#6b7280",
                      annotation_text="neutro", annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)

    # Comparación rating subjetivo vs club bias
    subj = ratings_to_elo_bias(squad)
    st.markdown("#### Tu intuición vs los datos de mercado")
    cc1, cc2, cc3 = st.columns(3)
    cc1.markdown(big_stat(f"{subj:+.0f}", "Bias subjetivo (tus ratings 1-10)"),
                 unsafe_allow_html=True)
    cc2.markdown(big_stat(f"{info['club_bias_total']:+.0f}", "Bias por club performance"),
                 unsafe_allow_html=True)
    diff = info["club_bias_total"] - subj
    cc3.markdown(big_stat(f"{diff:+.0f}", "Diferencia (datos − intuición)"),
                 unsafe_allow_html=True)
    if abs(diff) >= 30:
        sense = ("infravalorando" if diff > 0 else "sobrevalorando")
        st.caption(
            f"Los datos sugieren que estás **{sense}** a {team} respecto a lo que "
            f"indican los valores de Transfermarkt y la forma reciente de sus jugadores."
        )
    else:
        st.caption(
            "Tu intuición y los datos están alineados (≤30 puntos Elo de diferencia)."
        )


# ─────────────────────────────────────────────────────────────
# Sub-tab 3: Impacto en el modelo
# ─────────────────────────────────────────────────────────────
def _render_impact(data: dict[str, dict]) -> None:
    st.caption(
        "Compara las probabilidades del modelo **sin** vs **con** el bias derivado de la "
        "plantilla. Cada slider modula una de las 3 componentes de la fórmula."
    )

    cs1, cs2, cs3 = st.columns(3)
    w_mv = cs1.slider("Peso del valor de mercado", 0.0, 2.0, 1.0, 0.1, key="w_mv_plantilla")
    w_ped = cs2.slider("Peso del pedigrí de club", 0.0, 2.0, 1.0, 0.1, key="w_ped_plantilla")
    w_form = cs3.slider("Peso de la forma reciente", 0.0, 2.0, 1.0, 0.1, key="w_form_plantilla")

    summary_base = _mc_baseline()
    summary_bias = _mc_with_club(round(w_mv, 1), round(w_ped, 1), round(w_form, 1))

    # Tabla de winners y losers (sobre las 26 selecciones con plantilla)
    rows = []
    for t in data.keys():
        p0 = summary_base["champion"].get(t, 0.0) * 100
        p1 = summary_bias["champion"].get(t, 0.0) * 100
        diff = p1 - p0
        bias_applied = (
            data[t]["mv_bias"] * w_mv
            + data[t]["pedigree_bias"] * w_ped
            + data[t]["form_bias"] * w_form
        )
        bias_applied = max(-200.0, min(200.0, bias_applied))
        rows.append({
            "Selección": t,
            "P(campeón) base": p0,
            "P(campeón) con plantilla": p1,
            "Δ pp": diff,
            "Bias Elo aplicado": bias_applied,
        })
    df = pd.DataFrame(rows).sort_values("Δ pp", ascending=False)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**🟢 Winners** — más prob al activar el club bias")
        st.dataframe(
            df.head(8).style.format({
                "P(campeón) base": "{:.2f}%",
                "P(campeón) con plantilla": "{:.2f}%",
                "Δ pp": "{:+.2f}",
                "Bias Elo aplicado": "{:+.0f}",
            }).background_gradient(subset=["Δ pp"], cmap="Greens"),
            use_container_width=True, hide_index=True,
        )
    with cc2:
        st.markdown("**🔴 Losers** — menos prob al activarlo")
        losers = df.tail(8).sort_values("Δ pp")
        st.dataframe(
            losers.style.format({
                "P(campeón) base": "{:.2f}%",
                "P(campeón) con plantilla": "{:.2f}%",
                "Δ pp": "{:+.2f}",
                "Bias Elo aplicado": "{:+.0f}",
            }).background_gradient(subset=["Δ pp"], cmap="Reds_r"),
            use_container_width=True, hide_index=True,
        )

    # Estado actual + botones de activar/desactivar/actualizar
    st.divider()
    cfg = get_biases()
    is_active = cfg.use_club_performance
    bc1, bc2 = st.columns([1, 2])
    with bc1:
        if not is_active:
            if st.button("⚡ Activar club bias + guardar pesos", type="primary",
                         key="btn_activate_plantilla"):
                cfg.use_club_performance = True
                cfg.weight_market_value = round(w_mv, 1)
                cfg.weight_club_pedigree = round(w_ped, 1)
                cfg.weight_recent_form = round(w_form, 1)
                cfg.save()
                st.cache_data.clear()
                st.success("Activado. Las predicciones globales ya usan estos pesos.")
                st.rerun()
        else:
            if st.button("🔄 Actualizar pesos guardados", key="btn_update_plantilla"):
                cfg.weight_market_value = round(w_mv, 1)
                cfg.weight_club_pedigree = round(w_ped, 1)
                cfg.weight_recent_form = round(w_form, 1)
                cfg.save()
                st.cache_data.clear()
                st.success("Pesos actualizados.")
                st.rerun()
            if st.button("✖️ Desactivar club bias", key="btn_disable_plantilla"):
                cfg.use_club_performance = False
                cfg.save()
                st.cache_data.clear()
                st.success("Club bias desactivado.")
                st.rerun()
    with bc2:
        if is_active:
            st.info(
                f"**Estado actual**: club bias **ACTIVO**. Pesos guardados: "
                f"valor={cfg.weight_market_value}, pedigrí={cfg.weight_club_pedigree}, "
                f"forma={cfg.weight_recent_form}."
            )
        else:
            st.warning(
                "**Estado actual**: club bias desactivado. Las predicciones globales "
                "usan sólo el Elo histórico + tus ajustes manuales."
            )


# ─────────────────────────────────────────────────────────────
# Sub-tab 4: Por confederación
# ─────────────────────────────────────────────────────────────
def _render_by_confed(data: dict[str, dict]) -> None:
    df = pd.DataFrame(list(data.values()))
    df["confed"] = df["team"].map(CONFEDERATIONS).fillna("?")
    agg = df.groupby("confed").agg(
        n=("team", "count"),
        total_mv=("total_mv", "sum"),
        mean_mv=("total_mv", "mean"),
        mean_form=("mean_form_starters", "mean"),
        mean_bias=("club_bias_total", "mean"),
    ).reset_index().sort_values("mean_mv", ascending=False)

    st.markdown("#### Valor medio de plantilla por confederación")
    fig = px.bar(
        agg, x="confed", y="mean_mv", text=agg["mean_mv"].round(0),
        color="mean_bias", color_continuous_scale="RdYlGn", range_color=(-100, 100),
        labels={"confed": "Confederación", "mean_mv": "Valor medio (M€)",
                "mean_bias": "Bias medio"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"), height=380,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Resumen por confederación")
    st.dataframe(
        agg.rename(columns={
            "confed": "Confederación", "n": "Selecciones con squad",
            "total_mv": "Valor total (M€)", "mean_mv": "Media (M€)",
            "mean_form": "Forma media titulares", "mean_bias": "Bias medio",
        }).style.format({
            "Valor total (M€)": "{:.0f}",
            "Media (M€)": "{:.0f}",
            "Forma media titulares": "{:.2f}",
            "Bias medio": "{:+.0f}",
        }),
        use_container_width=True, hide_index=True,
    )

    # Jugador más valioso por confederación
    st.markdown("#### Jugador más valioso por confederación")
    out_rows = []
    for confed in agg["confed"]:
        teams_in = [t for t in data.keys() if CONFEDERATIONS.get(t) == confed]
        best: tuple[str, Player, float] | None = None
        for t in teams_in:
            sq = load_squad(t)
            for p in sq.players:
                if p.market_value is None:
                    continue
                if best is None or p.market_value > best[2]:
                    best = (t, p, p.market_value)
        if best:
            out_rows.append({
                "Confederación": confed, "Selección": best[0],
                "Jugador": best[1].name, "Club": best[1].club,
                "Valor (M€)": best[2],
            })
    if out_rows:
        st.dataframe(
            pd.DataFrame(out_rows).style.format({"Valor (M€)": "{:.0f}"}),
            use_container_width=True, hide_index=True,
        )


# ─────────────────────────────────────────────────────────────
# Sub-tab 5: Plantilla vs Elo (scatter cuadrantes)
# ─────────────────────────────────────────────────────────────
def _render_vs_elo(data: dict[str, dict]) -> None:
    base_elo = _build_elo(False, 1.0, 1.0, 1.0)
    rows = []
    for t, info in data.items():
        rows.append({
            "Selección": t,
            "Elo base": base_elo.get(t, 0),
            "Club bias": info["club_bias_total"],
            "Valor (M€)": info["total_mv"],
            "Confederación": CONFEDERATIONS.get(t, "?"),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Sin datos suficientes para el scatter.")
        return

    median_elo = df["Elo base"].median()
    median_bias = df["Club bias"].median()

    fig = px.scatter(
        df, x="Elo base", y="Club bias",
        text="Selección", size="Valor (M€)",
        color="Confederación", size_max=40,
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.add_hline(y=median_bias, line_dash="dot", line_color="#6b7280")
    fig.add_vline(x=median_elo, line_dash="dot", line_color="#6b7280")
    fig.update_layout(
        height=620,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0a0e14",
        font=dict(color="#e5e7eb"),
        xaxis=dict(gridcolor="#1f2937"), yaxis=dict(gridcolor="#1f2937"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    # Etiquetas de cuadrante
    fig.add_annotation(x=df["Elo base"].max(), y=df["Club bias"].max(),
                       text="🐺 Top dogs<br>(fuerte por Elo y plantilla)",
                       showarrow=False, font=dict(color=GOOD, size=11), xanchor="right")
    fig.add_annotation(x=df["Elo base"].min(), y=df["Club bias"].max(),
                       text="📈 Infravalorados<br>(plantilla > Elo)",
                       showarrow=False, font=dict(color=ACCENT, size=11), xanchor="left")
    fig.add_annotation(x=df["Elo base"].max(), y=df["Club bias"].min(),
                       text="📉 Sobrevalorados<br>(Elo > plantilla)",
                       showarrow=False, font=dict(color=DANGER, size=11), xanchor="right")
    fig.add_annotation(x=df["Elo base"].min(), y=df["Club bias"].min(),
                       text="🌱 Outsiders<br>(bajos ambos)",
                       showarrow=False, font=dict(color=TEXT_DIM, size=11), xanchor="left")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Cuadrantes respecto a la mediana de cada eje. **Infravalorados** son candidatos "
        "a *sleeper picks* si confías en la fórmula de plantilla. **Sobrevalorados** son "
        "favoritos del Elo histórico que la plantilla actual no respalda."
    )
