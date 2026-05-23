"""Analítica avanzada de la liga de amigos.

- Riesgo vs retorno (media y stddev de puntos por participante).
- Overlap entre porras (Jaccard sobre las casillas).
- Diferencial vs el modelo (cuántas casillas se alejan del autofill).
- Regret: cuánto más habrías ganado eligiendo el favorito del modelo.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

from src.tournament.groups import GROUPS


@dataclass
class RiskReturn:
    name: str
    mean: float
    stdev: float
    sharpe: float          # mean / stdev (similar a un Sharpe ratio)
    p10: float
    p50: float
    p90: float


def compute_risk_return(points_by_sim: dict[str, list[int]]) -> list[RiskReturn]:
    out: list[RiskReturn] = []
    for name, pts in points_by_sim.items():
        if not pts:
            continue
        n = len(pts)
        mean = sum(pts) / n
        var = sum((p - mean) ** 2 for p in pts) / n
        std = math.sqrt(var)
        srt = sorted(pts)
        p10 = srt[int(0.10 * n)]
        p50 = srt[int(0.50 * n)]
        p90 = srt[int(0.90 * n)]
        sharpe = mean / std if std > 0 else 0.0
        out.append(RiskReturn(name=name, mean=mean, stdev=std, sharpe=sharpe,
                              p10=p10, p50=p50, p90=p90))
    return sorted(out, key=lambda x: -x.mean)


def porra_to_pick_set(porra: dict) -> set[str]:
    """Convierte una porra a un set de 'fase:equipo' para Jaccard."""
    picks: set[str] = set()
    for g, teams in porra.get("groups", {}).items():
        for pos, t in enumerate(teams):
            if t: picks.add(f"G{g}-{pos+1}:{t}")
    for t in porra.get("r16", []):
        if t: picks.add(f"R16:{t}")
    for t in porra.get("qf", []):
        if t: picks.add(f"QF:{t}")
    for t in porra.get("sf", []):
        if t: picks.add(f"SF:{t}")
    for t in porra.get("final", []):
        if t: picks.add(f"F:{t}")
    if porra.get("champion"):
        picks.add(f"C:{porra['champion']}")
    return picks


def overlap_matrix(porras: dict[str, dict]) -> tuple[list[str], list[list[float]]]:
    """Matriz NxN de Jaccard overlap entre porras."""
    names = list(porras.keys())
    sets = {n: porra_to_pick_set(p) for n, p in porras.items()}
    m: list[list[float]] = []
    for n1 in names:
        row = []
        for n2 in names:
            s1, s2 = sets[n1], sets[n2]
            if not s1 and not s2:
                row.append(1.0)
            else:
                inter = len(s1 & s2)
                union = len(s1 | s2)
                row.append(inter / union if union else 0.0)
        m.append(row)
    return names, m


def differential_vs_model(porra: dict, summary: dict) -> dict[str, int]:
    """Cuántas casillas se desvían del autofill del modelo."""
    diff = {"grupos": 0, "r16": 0, "qf": 0, "sf": 0, "final": 0, "campeon": 0}

    # Modelo: favorito por casilla
    # Grupos: 1.º = argmax(group_winner). 2.º = argmax(top2 - winner). 3.º similar.
    for g in GROUPS:
        gw = summary["group_winner"].get(g, {})
        gtop2 = summary["group_top2"].get(g, {})
        third = summary["third_place"].get(g, {})
        first = max(gw, key=gw.get) if gw else None
        sec_cands = {t: p for t, p in gtop2.items() if t != first}
        second = max(sec_cands, key=sec_cands.get) if sec_cands else None
        third_cands = {t: p for t, p in third.items() if t not in (first, second)}
        third_pick = max(third_cands, key=third_cands.get) if third_cands else None
        model_g = [first, second, third_pick]
        user_g = porra.get("groups", {}).get(g, [None, None, None])
        for mp, up in zip(model_g, user_g):
            if mp and up and mp != up:
                diff["grupos"] += 1

    model_r16 = {t for t, _ in sorted(summary["r16"].items(), key=lambda x: -x[1])[:16]}
    diff["r16"] = len(set(porra.get("r16", [])) - model_r16 - {None})
    model_qf = {t for t, _ in sorted(summary["quarter"].items(), key=lambda x: -x[1])[:8]}
    diff["qf"] = len(set(porra.get("qf", [])) - model_qf - {None})
    model_sf = {t for t, _ in sorted(summary["semifinal"].items(), key=lambda x: -x[1])[:4]}
    diff["sf"] = len(set(porra.get("sf", [])) - model_sf - {None})
    model_f = {t for t, _ in sorted(summary["finalist"].items(), key=lambda x: -x[1])[:2]}
    diff["final"] = len(set(porra.get("final", [])) - model_f - {None})
    model_c = max(summary["champion"], key=summary["champion"].get) if summary["champion"] else None
    diff["campeon"] = 1 if porra.get("champion") and porra.get("champion") != model_c else 0

    diff["TOTAL"] = sum(v for k, v in diff.items() if k != "TOTAL")
    return diff


def porra_expected_points(porra: dict, summary: dict) -> float:
    """Replica del cálculo de porra._compute_expected_points sin importar la app."""
    from src.scoring.porra import (
        POINTS_R32_EXACT, POINTS_R32_WRONG_POS, POINTS_R16,
        POINTS_QF, POINTS_SF, POINTS_FINAL, POINTS_CHAMPION,
    )
    total = 0.0
    for g, picks in porra.get("groups", {}).items():
        gw = summary["group_winner"].get(g, {})
        gtop2 = summary["group_top2"].get(g, {})
        gtop3 = summary["group_top3"].get(g, {})
        third = summary["third_place"].get(g, {})
        gsecond = {t: gtop2.get(t, 0) - gw.get(t, 0) for t in gtop2}
        for pos, team in enumerate(picks):
            if not team: continue
            p_exact = (gw, gsecond, third)[pos].get(team, 0)
            p_in_top3 = gtop3.get(team, 0)
            p_wrong_pos = max(p_in_top3 - p_exact, 0)
            total += p_exact * POINTS_R32_EXACT + p_wrong_pos * POINTS_R32_WRONG_POS
    for t in porra.get("r16", []):
        if t: total += summary["r16"].get(t, 0) * POINTS_R16
    for t in porra.get("qf", []):
        if t: total += summary["quarter"].get(t, 0) * POINTS_QF
    for t in porra.get("sf", []):
        if t: total += summary["semifinal"].get(t, 0) * POINTS_SF
    for t in porra.get("final", []):
        if t: total += summary["finalist"].get(t, 0) * POINTS_FINAL
    if porra.get("champion"):
        total += summary["champion"].get(porra["champion"], 0) * POINTS_CHAMPION
    return total


def regret_analysis(porra: dict, summary: dict) -> dict[str, dict]:
    """Para cada casilla, cuánto perderías frente al favorito del modelo."""
    from src.scoring.porra import (
        POINTS_R32_EXACT, POINTS_R32_WRONG_POS, POINTS_R16, POINTS_QF, POINTS_SF,
        POINTS_FINAL, POINTS_CHAMPION,
    )
    out: dict[str, dict] = {}

    # Champion
    if porra.get("champion"):
        pick = porra["champion"]
        favorite = max(summary["champion"], key=summary["champion"].get) if summary["champion"] else None
        pick_ep = summary["champion"].get(pick, 0) * POINTS_CHAMPION
        fav_ep = summary["champion"].get(favorite, 0) * POINTS_CHAMPION if favorite else 0
        out["campeon"] = {
            "tu_pick": pick, "favorito_modelo": favorite,
            "tu_puntos_esperados": pick_ep, "favorito_puntos_esperados": fav_ep,
            "regret": fav_ep - pick_ep,
        }

    # Finalistas
    finals = porra.get("final", []) or []
    if any(t for t in finals):
        top2 = sorted(summary["finalist"].items(), key=lambda x: -x[1])[:2]
        fav_finals = [t for t, _ in top2]
        pick_ep = sum(summary["finalist"].get(t, 0) * POINTS_FINAL for t in finals if t)
        fav_ep = sum(summary["finalist"].get(t, 0) * POINTS_FINAL for t in fav_finals)
        out["finalistas"] = {
            "tu_pick": ", ".join(t for t in finals if t),
            "favorito_modelo": ", ".join(fav_finals),
            "tu_puntos_esperados": pick_ep,
            "favorito_puntos_esperados": fav_ep,
            "regret": fav_ep - pick_ep,
        }

    # Semis
    sf = porra.get("sf", []) or []
    if any(t for t in sf):
        top4 = sorted(summary["semifinal"].items(), key=lambda x: -x[1])[:4]
        fav_sf = [t for t, _ in top4]
        pick_ep = sum(summary["semifinal"].get(t, 0) * POINTS_SF for t in sf if t)
        fav_ep = sum(summary["semifinal"].get(t, 0) * POINTS_SF for t in fav_sf)
        out["semis"] = {
            "tu_pick": ", ".join(t for t in sf if t),
            "favorito_modelo": ", ".join(fav_sf),
            "tu_puntos_esperados": pick_ep, "favorito_puntos_esperados": fav_ep,
            "regret": fav_ep - pick_ep,
        }

    # Cuartos
    qf = porra.get("qf", []) or []
    if any(t for t in qf):
        top8 = sorted(summary["quarter"].items(), key=lambda x: -x[1])[:8]
        fav_qf = [t for t, _ in top8]
        pick_ep = sum(summary["quarter"].get(t, 0) * POINTS_QF for t in qf if t)
        fav_ep = sum(summary["quarter"].get(t, 0) * POINTS_QF for t in fav_qf)
        out["cuartos"] = {
            "tu_pick": ", ".join(t for t in qf if t),
            "favorito_modelo": ", ".join(fav_qf),
            "tu_puntos_esperados": pick_ep, "favorito_puntos_esperados": fav_ep,
            "regret": fav_ep - pick_ep,
        }

    # Octavos
    r16 = porra.get("r16", []) or []
    if any(t for t in r16):
        top16 = sorted(summary["r16"].items(), key=lambda x: -x[1])[:16]
        fav_r16 = [t for t, _ in top16]
        pick_ep = sum(summary["r16"].get(t, 0) * POINTS_R16 for t in r16 if t)
        fav_ep = sum(summary["r16"].get(t, 0) * POINTS_R16 for t in fav_r16)
        out["octavos"] = {
            "tu_pick": ", ".join(t for t in r16 if t),
            "favorito_modelo": ", ".join(fav_r16),
            "tu_puntos_esperados": pick_ep, "favorito_puntos_esperados": fav_ep,
            "regret": fav_ep - pick_ep,
        }

    # Grupos (sumando regret por grupo)
    grupos_regret = 0.0
    grupos_pick = 0.0
    grupos_fav = 0.0
    from src.tournament.groups import GROUPS as _G
    for g, picks in (porra.get("groups", {}) or {}).items():
        if not picks or not any(picks):
            continue
        gw = summary["group_winner"].get(g, {})
        gtop2 = summary["group_top2"].get(g, {})
        gtop3 = summary["group_top3"].get(g, {})
        third = summary["third_place"].get(g, {})
        gsecond = {t: gtop2.get(t, 0) - gw.get(t, 0) for t in gtop2}
        # Mejor pick por slot
        first_fav = max(gw, key=gw.get) if gw else None
        sec_cands = {t: p for t, p in gsecond.items() if t != first_fav}
        second_fav = max(sec_cands, key=sec_cands.get) if sec_cands else None
        third_cands = {t: p for t, p in third.items()
                       if t not in (first_fav, second_fav)}
        third_fav = max(third_cands, key=third_cands.get) if third_cands else None
        fav_picks = [first_fav, second_fav, third_fav]
        for pos, (t_user, t_fav) in enumerate(zip(picks, fav_picks)):
            ev_user = 0
            if t_user:
                p_exact = (gw, gsecond, third)[pos].get(t_user, 0)
                p_in_top3 = gtop3.get(t_user, 0)
                p_wrong = max(p_in_top3 - p_exact, 0)
                ev_user = p_exact * POINTS_R32_EXACT + p_wrong * POINTS_R32_WRONG_POS
            ev_fav = 0
            if t_fav:
                p_exact = (gw, gsecond, third)[pos].get(t_fav, 0)
                p_in_top3 = gtop3.get(t_fav, 0)
                p_wrong = max(p_in_top3 - p_exact, 0)
                ev_fav = p_exact * POINTS_R32_EXACT + p_wrong * POINTS_R32_WRONG_POS
            grupos_pick += ev_user
            grupos_fav += ev_fav
    if grupos_fav > 0:
        out["grupos"] = {
            "tu_pick": "—", "favorito_modelo": "—",
            "tu_puntos_esperados": grupos_pick,
            "favorito_puntos_esperados": grupos_fav,
            "regret": grupos_fav - grupos_pick,
        }

    return out
