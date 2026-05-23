"""Worst-nightmare detector: para cada participante, qué resultado pendiente
le hace más daño en puntos esperados.

Estrategia (heurística pero útil):
- Para cada pick aún VIVO del participante (no eliminado), su valor esperado
  remanente = puntos_si_acierta * p(que_siga_avanzando_segun_modelo).
- El "nightmare" de un participante es el pick con mayor valor esperado en
  riesgo: si ese equipo cae en el próximo partido pendiente, perderá esos puntos.
"""
from __future__ import annotations
from dataclasses import dataclass

from src.scoring.porra import (
    POINTS_R32_EXACT, POINTS_R32_WRONG_POS, POINTS_R16, POINTS_QF, POINTS_SF,
    POINTS_FINAL, POINTS_CHAMPION,
)
from src.tournament.groups import GROUPS


# Mapping pick category -> (puntos por acierto exacto, prob_key del summary)
CATEGORY_INFO: dict[str, tuple[int, str]] = {
    "r16": (POINTS_R16, "r16"),
    "qf": (POINTS_QF, "quarter"),
    "sf": (POINTS_SF, "semifinal"),
    "final": (POINTS_FINAL, "finalist"),
    "champion": (POINTS_CHAMPION, "champion"),
}


@dataclass
class NightmareItem:
    participant: str
    team: str
    category: str          # 'r16', 'qf', 'sf', 'final', 'champion'
    points_at_risk: int    # puntos si el equipo acierta el avance
    expected_value: float  # points_at_risk * p(actual)
    current_prob: float    # probabilidad de que la pick siga avanzando

    @property
    def label_category(self) -> str:
        return {"r16": "Octavos", "qf": "Cuartos", "sf": "Semis",
                 "final": "Final", "champion": "Campeón"}.get(self.category, self.category)


def _team_eliminated(team: str, eliminated: set[str]) -> bool:
    return team in eliminated


def collect_at_risk(
    porra: dict, summary: dict, eliminated_teams: set[str],
) -> list[NightmareItem]:
    """Por cada pick vivo, devuelve un NightmareItem con su EV en riesgo."""
    out: list[NightmareItem] = []
    for cat, (pts, key) in CATEGORY_INFO.items():
        picks = porra.get(cat, [])
        if cat == "champion":
            picks = [porra.get("champion")] if porra.get("champion") else []
        for t in picks:
            if not t:
                continue
            if _team_eliminated(t, eliminated_teams):
                continue
            p = summary.get(key, {}).get(t, 0)
            out.append(NightmareItem(
                participant="", team=t, category=cat,
                points_at_risk=pts,
                expected_value=p * pts,
                current_prob=p,
            ))
    # Picks de grupos (también en riesgo si pierde el partido)
    for g, teams in porra.get("groups", {}).items():
        for pos, t in enumerate(teams):
            if not t or _team_eliminated(t, eliminated_teams):
                continue
            # En grupos las probabilidades por posición se aproximan a las top3 + exacta
            gw = summary.get("group_winner", {}).get(g, {})
            gtop2 = summary.get("group_top2", {}).get(g, {})
            third = summary.get("third_place", {}).get(g, {})
            gtop3 = summary.get("group_top3", {}).get(g, {})
            gsecond = {team: gtop2.get(team, 0) - gw.get(team, 0) for team in gtop2}
            p_exact = (gw, gsecond, third)[pos].get(t, 0)
            p_in_top3 = gtop3.get(t, 0)
            p_wrong = max(p_in_top3 - p_exact, 0)
            ev = p_exact * POINTS_R32_EXACT + p_wrong * POINTS_R32_WRONG_POS
            if ev > 0:
                out.append(NightmareItem(
                    participant="", team=t, category="grupo",
                    points_at_risk=POINTS_R32_EXACT,
                    expected_value=ev, current_prob=p_in_top3,
                ))
    return out


def compute_nightmares(
    porras: dict[str, dict],
    summary: dict,
    eliminated_teams: set[str],
) -> dict[str, list[NightmareItem]]:
    """Para cada participante, lista ordenada de sus picks vivos por EV descendente.

    El primer elemento de la lista es su 'worst nightmare': el equipo que más
    le dolería ver caer.
    """
    out: dict[str, list[NightmareItem]] = {}
    for name, p in porras.items():
        items = collect_at_risk(p, summary, eliminated_teams)
        for it in items:
            it.participant = name
        items.sort(key=lambda x: -x.expected_value)
        out[name] = items
    return out
