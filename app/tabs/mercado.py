"""Pestaña 💰 Mercado vs Modelo.

Compara las probabilidades del modelo (ensemble Elo+XGBoost → Monte Carlo para el
campeón, Dixon-Coles para el 1X2) con las que implican las cuotas de las casas de
apuestas (the-odds-api.com), una vez quitado el margen de la casa (vig).

Donde el modelo da MÁS probabilidad que el mercado a la mejor cuota disponible,
hay *value*: EV = prob_modelo · cuota − 1 > 0. Las cuotas las trae
`scripts/fetch_odds.py` a data/processed/odds.json (la web solo lo lee).
"""
from __future__ import annotations
from datetime import datetime, timezone

import streamlit as st

from app.utils import get_elo_with_biases, get_biases, run_simulation_with_real
from app.styles import PRIMARY, ACCENT, GOOD, DANGER, TEXT, TEXT_DIM, BG_CARD
from app.components import render_table, table_flag
from src.data import odds as odds_mod
from src.tournament.groups import ALL_TEAMS

try:
    from zoneinfo import ZoneInfo
    _MADRID = ZoneInfo("Europe/Madrid")
except Exception:
    _MADRID = None


def _fmt_kick(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if _MADRID:
            t = t.astimezone(_MADRID)
        return t.strftime("%d %b · %H:%M")
    except Exception:
        return ""


def _trio(p_h: float, p_x: float, p_a: float) -> str:
    """1X2 coloreado (1=cian, X=gris, 2=violeta), como la leyenda de Partidos."""
    return (f'<span style="font-variant-numeric:tabular-nums;white-space:nowrap;">'
            f'<b style="color:{PRIMARY};">{p_h*100:.0f}</b>'
            f'<span style="color:{TEXT_DIM};"> / </span>'
            f'<b style="color:{TEXT_DIM};">{p_x*100:.0f}</b>'
            f'<span style="color:{TEXT_DIM};"> / </span>'
            f'<b style="color:{ACCENT};">{p_a*100:.0f}</b></span>')


def _value_chip(code: str, odds: float, evv: float, is_value: bool) -> str:
    if is_value:
        return (f'<span style="background:rgba(78,222,163,.16);color:{GOOD};font-weight:800;'
                f'border-radius:6px;padding:2px 9px;white-space:nowrap;font-variant-numeric:tabular-nums;">'
                f'{code} @{odds:.2f} · EV {evv*100:+.0f}%</span>')
    return (f'<span style="color:{TEXT_DIM};white-space:nowrap;font-variant-numeric:tabular-nums;">'
            f'{code} {evv*100:+.0f}%</span>')


def _kelly(evv: float | None, odds: float | None) -> float:
    """Fracción de Kelly = EV / (cuota − 1): qué % del bankroll apostaría Kelly."""
    if evv is None or not odds or odds <= 1.0:
        return 0.0
    return evv / (odds - 1.0)


def _headline_card(tag: str, title_html: str, pick: str, odds: float,
                   evv: float, mp: float, kp: float, books: int, kelly: float) -> str:
    return (
        f'<div style="background:{BG_CARD};border:1px solid rgba(78,222,163,.35);'
        f'border-radius:14px;padding:13px 15px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">'
        f'<span style="font-size:.6rem;font-weight:800;letter-spacing:.06em;color:{TEXT_DIM};">{tag}</span>'
        f'<span style="background:rgba(78,222,163,.18);color:{GOOD};font-weight:800;'
        f'border-radius:7px;padding:2px 9px;font-size:.82rem;">EV {evv*100:+.0f}%</span></div>'
        f'<div style="font-weight:700;font-size:.92rem;margin-bottom:5px;">{title_html}</div>'
        f'<div style="font-size:.82rem;color:{TEXT};">Apuesta <b style="color:{GOOD};">{pick}</b> '
        f'· cuota <b style="font-variant-numeric:tabular-nums;">{odds:.2f}</b></div>'
        f'<div style="font-size:.72rem;color:{TEXT_DIM};margin-top:5px;">'
        f'Modelo {mp*100:.0f}% · Mercado {kp*100:.0f}% · Kelly {kelly*100:.1f}% · {books} casa(s)</div>'
        f'</div>'
    )


def _calibration(match_rows: list[dict]) -> dict | None:
    """Cuánto más (o menos) confía el modelo que el mercado en el favorito del mercado."""
    gaps, lower = [], 0
    for r in match_rows:
        mdl, mkt = r.get("_mdl"), r.get("_mkt")
        if not mdl or not mkt:
            continue
        fav = max(range(3), key=lambda i: mkt[i])   # 0/1/2 = local/empate/visitante
        gaps.append(mkt[fav] - mdl[fav])            # >0 ⇒ el mercado da más al favorito
        if mdl[fav] < mkt[fav]:
            lower += 1
    if not gaps:
        return None
    return {"gap": sum(gaps) / len(gaps), "lower_pct": lower / len(gaps), "n": len(gaps)}


def render() -> None:
    st.header("💰 Mercado vs Modelo")
    st.caption(
        "El pulso entre **lo que dice el modelo** y **lo que pagan las casas**. "
        "Quitando el margen del corredor (vig), donde el modelo ve más probabilidad "
        "que el mercado aparece *value*."
    )

    if not odds_mod.has_odds():
        st.info(
            "Todavía no hay cuotas cargadas. Genera el fichero con:\n\n"
            "```\npython scripts/fetch_odds.py --apply\n```\n\n"
            "(necesita la API key de the-odds-api.com en `~/.config/porra/odds_api.token`)."
        )
        return

    fr = odds_mod.freshness() or {}
    age = fr.get("age_hours")
    age_txt = "ahora mismo" if (age is not None and age < 1) else (
        f"hace {age:.0f} h" if age is not None else "—")
    rem = fr.get("requests_remaining")
    st.caption(
        f"🕒 Cuotas capturadas **{age_txt}** ({fr.get('fetched_at', '—')}, hora ES) · "
        f"región {fr.get('regions', 'eu')} · {fr.get('n_matches', 0)} partidos · "
        f"campeón {fr.get('n_champion', 0)} equipos"
        + (f" · {rem} peticiones/mes restantes" if rem is not None else "")
    )

    with st.expander("ℹ️ Cómo se calcula el value", expanded=False):
        st.markdown(
            "- **Probabilidad implícita del mercado**: `1 / cuota`, promediada entre casas. "
            "Esa suma supera el 100% por el margen de la casa (*vig*); la **normalizamos** "
            "para repartir ese margen y obtener la probabilidad *justa* del mercado.\n"
            "- **Edge** = prob. del modelo − prob. justa del mercado (en puntos porcentuales).\n"
            "- **EV** (valor esperado de 1 € apostado a la **mejor cuota** disponible) = "
            "`prob_modelo × cuota − 1`. Si es positivo, el modelo cree que la apuesta es rentable.\n"
            "- **Kelly** = `EV / (cuota − 1)`: la fracción del bankroll que apostaría el criterio de "
            "Kelly. Castiga las cuotas altas, así que tempera el EV: un +1000% a cuota 1000 es "
            "calderilla en Kelly. Lo prudente es media-Kelly.\n"
            "- Se descartan las **colas larguísimas** (campeón con prob. de modelo <4%, partidos con "
            "lado <12%): a cuotas enormes el EV explota por ruido del modelo, no por value real.\n"
            "- Las cuotas de campeón salen de un mercado *de futuros* (pocas casas, margen alto): "
            "trátalas como señal a largo plazo, no como certeza."
        )

    thr_pct = st.slider("Umbral de value (EV mínimo)", 0, 25, 5, step=1, format="+%d%%",
                        key="mkt_thr",
                        help="Solo se marcan como value las apuestas con EV por encima de este umbral.")
    thr = thr_pct / 100.0
    MIN_BOOKS_MATCH = 4       # liquidez mínima para fiarte de un 1X2
    MIN_CHAMP_P = 0.04        # campeón: ignora colas larguísimas (ruido del modelo a cuota 1000)
    MIN_MATCH_P = 0.15        # partido: el lado tiene que ser plausible para el modelo
    MAX_MATCH_ODDS = 8.0      # no marcamos value en longshots (cuota ≤ 8 ⇒ ~12%+ implícito)

    elo = get_elo_with_biases()
    w = get_biases().stats_weight
    from app.tabs.partidos import _predict_match  # misma fuente de verdad que 🔮 Partidos

    market_champ = odds_mod.market_champion_probs()
    market_matches = odds_mod.market_match_probs()

    # ── Modelo: campeón (Monte Carlo) ──────────────────────────────────────
    try:
        summary = run_simulation_with_real(elo, n_sims=10_000, seed=42)
        model_champ = summary.get("champion", {}) or {}
    except Exception:
        model_champ = {}

    # ── Recolectar oportunidades de value (campeón + partidos) ─────────────
    opps: list[dict] = []

    # Campeón
    champ_rows = []
    for team in sorted(set(model_champ) | set(market_champ)):
        mp = float(model_champ.get(team, 0.0))
        mk = market_champ.get(team)
        kp = mk["p_market"] if mk else 0.0
        best = mk["best"] if mk else None
        books = mk["n_books"] if mk else 0
        evv = odds_mod.ev(mp, best) if best else None
        is_val = evv is not None and evv >= thr and mp >= MIN_CHAMP_P
        if mk:
            champ_rows.append({
                "team": team, "model": mp * 100, "market": kp * 100,
                "edge": (mp - kp) * 100, "odds": best or 0.0,
                "ev": (evv * 100 if evv is not None else 0.0),
                "kelly": _kelly(evv, best) * 100, "_value": is_val,
            })
        if is_val:
            opps.append({
                "tag": "🏆 CAMPEÓN", "sort_ev": evv,
                "title": f"{table_flag(team)} {team}", "pick": f"{team} campeón",
                "odds": best, "ev": evv, "mp": mp, "kp": kp, "books": books,
                "kelly": _kelly(evv, best),
            })

    # Partidos: 1X2 del modelo (orientación de la API) vs mercado
    match_rows = []
    for key, mk in market_matches.items():
        home, away = mk.get("home"), mk.get("away")
        if home not in ALL_TEAMS or away not in ALL_TEAMS:
            continue
        pred = _predict_match(home, away, elo, w)
        sides = []
        for code, mp, o, kp, label in [
            ("1", pred["p_h"], mk["best_h"], mk["p_h"], f'1 · {home}'),
            ("X", pred["p_x"], mk["best_x"], mk["p_x"], "X · Empate"),
            ("2", pred["p_a"], mk["best_a"], mk["p_a"], f'2 · {away}'),
        ]:
            evv = odds_mod.ev(mp, o)
            if evv is not None:
                sides.append({"code": code, "mp": mp, "odds": o, "kp": kp,
                              "label": label, "ev": evv})
        enough = mk.get("n_books", 0) >= MIN_BOOKS_MATCH
        # Lados "apostables": cuota sensata y prob plausible (descarta longshots,
        # donde el modelo plano infla el EV por ruido). El value real vive ahí.
        qual = [s for s in sides if s["odds"] <= MAX_MATCH_ODDS and s["mp"] >= MIN_MATCH_P]
        best_qual = max(qual, key=lambda s: s["ev"]) if qual else None
        is_val = bool(best_qual and best_qual["ev"] >= thr and enough)
        match_rows.append({
            "_key": key, "home": home, "away": away,
            "ct": mk.get("commence_time") or "",
            "model": _trio(pred["p_h"], pred["p_x"], pred["p_a"]),
            "market": _trio(mk["p_h"], mk["p_x"], mk["p_a"]),
            # Solo mostramos «Mejor value» si es apostable de verdad; si no, «—».
            # La discrepancia entera ya se ve en las columnas Modelo vs Mercado.
            "value": (_value_chip(best_qual["code"], best_qual["odds"], best_qual["ev"], True)
                      if is_val else f'<span style="color:{TEXT_DIM};">—</span>'),
            "_value": is_val, "_ev": best_qual["ev"] if best_qual else -9,
            "_mdl": (pred["p_h"], pred["p_x"], pred["p_a"]),
            "_mkt": (mk["p_h"], mk["p_x"], mk["p_a"]),
        })
        if is_val:
            opps.append({
                "tag": "⚽ PARTIDO", "sort_ev": best_qual["ev"],
                "title": f'{table_flag(home)} {home} <span style="color:{TEXT_DIM}">vs</span> {away} {table_flag(away)}',
                "pick": best_qual["label"], "odds": best_qual["odds"],
                "ev": best_qual["ev"], "mp": best_qual["mp"], "kp": best_qual["kp"],
                "books": mk.get("n_books", 0),
                "kelly": _kelly(best_qual["ev"], best_qual["odds"]),
            })

    # ── KPIs ────────────────────────────────────────────────────────────────
    vigs = [m["vig"] for m in market_matches.values() if m.get("vig") is not None]
    avg_vig = sum(vigs) / len(vigs) if vigs else 0.0
    best_ev = max((o["ev"] for o in opps), default=0.0)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Partidos con cuotas", len(match_rows))
    k2.metric("Value bets detectados", len(opps), help=f"Con EV ≥ {thr_pct}%")
    k3.metric("Vig medio del mercado", f"{avg_vig*100:.1f}%",
              help="Margen medio de la casa en los 1X2 (cuanto menor, más eficiente).")
    k4.metric("Mejor value (EV)", f"{best_ev*100:+.0f}%" if opps else "—")

    st.divider()

    # ── Calibración: ¿el modelo es más plano o más agudo que el mercado? ──────
    cal = _calibration(match_rows)
    if cal and cal["n"] >= 8:
        gap_pp = cal["gap"] * 100
        if gap_pp >= 4:
            st.warning(
                f"📐 **Calibración modelo vs mercado** · De media tu modelo da **{gap_pp:+.0f} pp** "
                f"al favorito del mercado (es decir, **menos**): le pasa en el {cal['lower_pct']*100:.0f}% "
                f"de los partidos. Por eso casi todo el *value* cae en el no-favorito. El mercado (24 casas, "
                f"incluida Pinnacle) suele ir muy afinado, así que esto delata sobre todo **infraconfianza "
                f"del modelo**, no dinero gratis: léelo como *dónde discrepa* tu modelo."
            )
        elif gap_pp <= -4:
            st.warning(
                f"📐 **Calibración modelo vs mercado** · Tu modelo es de media **{-gap_pp:.0f} pp más agresivo** "
                f"que el mercado con los favoritos. Revisa que no esté sobreajustando a los resultados ya jugados."
            )
        else:
            st.success(
                f"📐 **Calibración modelo vs mercado** · Tu modelo y el mercado están muy alineados "
                f"(gap medio en el favorito {gap_pp:+.0f} pp). El *value* que aparezca es disagreement fino, "
                f"más interesante."
            )

    # ── Titular: top value bets ──────────────────────────────────────────────
    st.subheader("🎯 Mejores value bets (según el modelo)")
    if opps:
        opps.sort(key=lambda o: -o["sort_ev"])
        cards = "".join(
            _headline_card(o["tag"], o["title"], o["pick"], o["odds"], o["ev"],
                           o["mp"], o["kp"], o["books"], o["kelly"])
            for o in opps[:8]
        )
        st.markdown(
            f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));'
            f'gap:11px;margin-bottom:6px;">{cards}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "El modelo paga más que el mercado en estas apuestas. No es una recomendación: "
            "el modelo puede equivocarse y el mercado suele ir bien informado. Apuesta con cabeza."
        )
    else:
        st.success(
            f"No hay apuestas con EV ≥ {thr_pct}% ahora mismo: el modelo y el mercado están "
            "muy de acuerdo. Baja el umbral para ver las diferencias más finas."
        )

    st.divider()

    # ── Campeón: Mercado vs Modelo ───────────────────────────────────────────
    st.subheader("🏆 Campeón · Mercado vs Modelo")
    if champ_rows:
        champ_rows.sort(key=lambda r: -r["model"])
        render_table(
            champ_rows[:24],
            [
                {"label": "Selección", "key": "team", "kind": "team"},
                {"label": "Modelo", "key": "model", "kind": "bar", "champ": True},
                {"label": "Mercado", "key": "market", "kind": "num", "fmt": "{:.1f}", "suffix": "%"},
                {"label": "Edge (pp)", "key": "edge", "kind": "grad", "diverge": True,
                 "fmt": "{:+.1f}", "max": 8},
                {"label": "Mejor cuota", "key": "odds", "kind": "num", "fmt": "{:.1f}"},
                {"label": "Kelly %", "key": "kelly", "kind": "grad", "diverge": True,
                 "fmt": "{:+.1f}", "max": 4},
            ],
            highlight=lambda r: r.get("_value", False),
        )
        st.caption(
            "Probabilidad de levantar la Copa. **Kelly** = fracción del bankroll a apostar (ya descuenta "
            "el riesgo de la cuota): fíjate en que hasta el mejor value es un mordisco pequeño. "
            "Mercado de futuros (2 casas, margen alto): señal a largo plazo, no certeza."
        )
    else:
        st.caption("Sin datos de campeón en el mercado.")

    st.divider()

    # ── Partidos: 1X2 Mercado vs Modelo + value ──────────────────────────────
    st.subheader("⚽ Próximos partidos · 1X2 Mercado vs Modelo")
    only_value = st.toggle("Solo partidos con value", value=False, key="mkt_only_value")
    rows = sorted(match_rows, key=lambda r: r["ct"])
    if only_value:
        rows = [r for r in rows if r["_value"]]
    if rows:
        for r in rows:
            r["partido"] = (f'{table_flag(r["home"])} {r["home"]} '
                            f'<span style="color:{TEXT_DIM};font-weight:400;">vs</span> '
                            f'{r["away"]} {table_flag(r["away"])}')
            r["fecha"] = _fmt_kick(r["ct"])
        render_table(
            rows,
            [
                {"label": "Partido", "key": "partido", "kind": "text"},
                {"label": "Fecha", "key": "fecha", "kind": "text"},
                {"label": "Modelo 1/X/2", "key": "model", "kind": "text"},
                {"label": "Mercado 1/X/2", "key": "market", "kind": "text"},
                {"label": "Mejor value", "key": "value", "kind": "text"},
            ],
            highlight=lambda r: r.get("_value", False),
            max_height="620px",
        )
        st.caption(
            f"Modelo y mercado en % (1=local / X=empate / 2=visitante). «Mejor value» marca el resultado "
            f"apostable con EV ≥ +{thr_pct}% (cuota ≤ {int(MAX_MATCH_ODDS)}, prob. del modelo ≥ 15%, "
            f"≥{MIN_BOOKS_MATCH} casas); «—» si no lo hay. La discrepancia completa la ves comparando las "
            f"columnas Modelo y Mercado."
        )
    else:
        st.caption("No hay partidos que cumplan el filtro.")
