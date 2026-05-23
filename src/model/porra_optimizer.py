"""Optimizador de porra: dado un objetivo, sugiere cambios a los picks."""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy

from src.tournament.groups import GROUPS, ALL_TEAMS
from src.scoring.porra import (
    POINTS_R32_EXACT, POINTS_R32_WRONG_POS, POINTS_R16, POINTS_QF, POINTS_SF,
    POINTS_FINAL, POINTS_CHAMPION,
)


@dataclass
class Suggestion:
    category: str          # 'champion', 'final', 'sf', 'qf', 'r16', 'grupos'
    position: str          # descripción del slot ('Campeón', 'Finalista #2', 'Grupo A 1.º', etc.)
    current_pick: str | None
    suggested_pick: str
    current_ev: float
    suggested_ev: float
    delta: float           # ganancia esperada


def _ev_champion(team: str, summary: dict) -> float:
    return summary["champion"].get(team, 0) * POINTS_CHAMPION


def _ev_final(team: str, summary: dict) -> float:
    return summary["finalist"].get(team, 0) * POINTS_FINAL


def _ev_sf(team: str, summary: dict) -> float:
    return summary["semifinal"].get(team, 0) * POINTS_SF


def _ev_qf(team: str, summary: dict) -> float:
    return summary["quarter"].get(team, 0) * POINTS_QF


def _ev_r16(team: str, summary: dict) -> float:
    return summary["r16"].get(team, 0) * POINTS_R16


def _ev_group_pick(team: str, group: str, position: int, summary: dict) -> float:
    """EV de un pick en grupos para una posición 0=1.º, 1=2.º, 2=3.º."""
    gw = summary["group_winner"].get(group, {})
    gtop2 = summary["group_top2"].get(group, {})
    gtop3 = summary["group_top3"].get(group, {})
    third = summary["third_place"].get(group, {})
    gsecond = {t: gtop2.get(t, 0) - gw.get(t, 0) for t in gtop2}
    p_exact = (gw, gsecond, third)[position].get(team, 0)
    p_in_top3 = gtop3.get(team, 0)
    p_wrong = max(p_in_top3 - p_exact, 0)
    return p_exact * POINTS_R32_EXACT + p_wrong * POINTS_R32_WRONG_POS


def _best_for_slot(summary: dict, category: str, group: str | None,
                    position: int | None, already_picked: set[str],
                    eliminated: set[str], available_teams: list[str] | None = None) -> tuple[str | None, float]:
    """Devuelve (mejor_equipo, su_EV) para esta casilla, excluyendo eliminados y ya usados."""
    teams = available_teams or ALL_TEAMS
    best_team = None
    best_ev = -1
    for t in teams:
        if t in eliminated or t in already_picked:
            continue
        if category == "champion":
            ev = _ev_champion(t, summary)
        elif category == "final":
            ev = _ev_final(t, summary)
        elif category == "sf":
            ev = _ev_sf(t, summary)
        elif category == "qf":
            ev = _ev_qf(t, summary)
        elif category == "r16":
            ev = _ev_r16(t, summary)
        elif category == "grupos":
            ev = _ev_group_pick(t, group, position, summary)
        else:
            ev = 0
        if ev > best_ev:
            best_ev = ev
            best_team = t
    return best_team, best_ev


def suggest_changes(
    porra: dict, summary: dict, eliminated_teams: set[str],
    objective: str = "max_points",  # 'max_points' | 'contrarian' | 'safe'
) -> list[Suggestion]:
    """Sugiere cambios concretos al porra. Devuelve sólo cambios que ganan EV.

    - max_points: maximiza EV deterministico (ignora ranking liga)
    - contrarian: penaliza picks "de consenso" (los más probables son menos diferenciadores)
    - safe: prefiere picks de consenso para mantener ventaja
    """
    suggestions: list[Suggestion] = []

    # Champion
    current_champ = porra.get("champion")
    cur_ev = _ev_champion(current_champ, summary) if current_champ else 0
    best, best_ev = _best_for_slot(summary, "champion", None, None,
                                    set(), eliminated_teams)
    if objective == "contrarian":
        # Penalizar al favorito del modelo si es el mismo que ya tienes
        if current_champ and current_champ == best:
            best, best_ev = _second_best(summary, "champion", current_champ, eliminated_teams)
    elif objective == "safe":
        # Sólo cambiar si la diferencia es muy grande (>4 pts EV)
        if best_ev - cur_ev < 4 and current_champ:
            best = current_champ; best_ev = cur_ev
    if best and best != current_champ and best_ev > cur_ev:
        suggestions.append(Suggestion(
            category="champion", position="Campeón",
            current_pick=current_champ, suggested_pick=best,
            current_ev=cur_ev, suggested_ev=best_ev, delta=best_ev - cur_ev,
        ))

    # Finalistas
    current_finals = [t for t in porra.get("final", []) if t]
    for idx in range(2):
        cur = current_finals[idx] if idx < len(current_finals) else None
        cur_ev = _ev_final(cur, summary) if cur else 0
        already = set(porra.get("final", []) or [])
        already.discard(cur)
        best, best_ev = _best_for_slot(summary, "final", None, None, already,
                                        eliminated_teams)
        if best and best != cur and best_ev > cur_ev + 0.5:
            suggestions.append(Suggestion(
                category="final", position=f"Finalista #{idx+1}",
                current_pick=cur, suggested_pick=best,
                current_ev=cur_ev, suggested_ev=best_ev, delta=best_ev - cur_ev,
            ))

    # Semis (4) - sólo mostrar si mejoras EV en al menos 1 pt
    current_sf = list(porra.get("sf", []) or [])
    for idx in range(4):
        cur = current_sf[idx] if idx < len(current_sf) else None
        cur_ev = _ev_sf(cur, summary) if cur else 0
        already = set(current_sf)
        already.discard(cur)
        best, best_ev = _best_for_slot(summary, "sf", None, None, already,
                                        eliminated_teams)
        if best and best != cur and best_ev > cur_ev + 1:
            suggestions.append(Suggestion(
                category="sf", position=f"Semis slot #{idx+1}",
                current_pick=cur, suggested_pick=best,
                current_ev=cur_ev, suggested_ev=best_ev, delta=best_ev - cur_ev,
            ))

    # Cuartos (8)
    current_qf = list(porra.get("qf", []) or [])
    for idx in range(8):
        cur = current_qf[idx] if idx < len(current_qf) else None
        cur_ev = _ev_qf(cur, summary) if cur else 0
        already = set(current_qf)
        already.discard(cur)
        best, best_ev = _best_for_slot(summary, "qf", None, None, already,
                                        eliminated_teams)
        if best and best != cur and best_ev > cur_ev + 1:
            suggestions.append(Suggestion(
                category="qf", position=f"QF slot #{idx+1}",
                current_pick=cur, suggested_pick=best,
                current_ev=cur_ev, suggested_ev=best_ev, delta=best_ev - cur_ev,
            ))

    # Octavos (16)
    current_r16 = list(porra.get("r16", []) or [])
    for idx in range(16):
        cur = current_r16[idx] if idx < len(current_r16) else None
        cur_ev = _ev_r16(cur, summary) if cur else 0
        already = set(current_r16)
        already.discard(cur)
        best, best_ev = _best_for_slot(summary, "r16", None, None, already,
                                        eliminated_teams)
        if best and best != cur and best_ev > cur_ev + 1:
            suggestions.append(Suggestion(
                category="r16", position=f"R16 slot #{idx+1}",
                current_pick=cur, suggested_pick=best,
                current_ev=cur_ev, suggested_ev=best_ev, delta=best_ev - cur_ev,
            ))

    suggestions.sort(key=lambda s: -s.delta)
    return suggestions


def _second_best(summary: dict, category: str, exclude: str,
                  eliminated: set[str]) -> tuple[str | None, float]:
    best = None; best_ev = -1
    for t in ALL_TEAMS:
        if t == exclude or t in eliminated:
            continue
        if category == "champion":
            ev = _ev_champion(t, summary)
        elif category == "final":
            ev = _ev_final(t, summary)
        else:
            ev = 0
        if ev > best_ev:
            best_ev = ev; best = t
    return best, best_ev
