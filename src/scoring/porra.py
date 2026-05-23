"""Sistema de puntuacion de la porra del Mundial 2026.

Reglas extraidas del Excel (hoja "Instrucciones - Reglas"):

DIECISEISAVOS (clasificacion de grupos):
- 3 puntos: acertar el clasificado en su posicion exacta (1.º como 1.º, etc.)
- 2 puntos: acertar el clasificado pero en otra posicion

OCTAVOS:
- 5 puntos por cada seleccion clasificada para Octavos

CUARTOS:
- 8 puntos por cada seleccion clasificada para Cuartos

SEMIFINALES:
- 12 puntos por cada seleccion clasificada para Semis

FINAL:
- 20 puntos por cada finalista

CAMPEON:
- 40 puntos por acertar el campeon

BALON DE ORO (MVP):
- Oro:  25 si Oro / 15 si Plata / 8 si Bronce / 5 si en Once Ideal
- Plata:18 si Plata / 10 si Oro / 5 si Bronce / 3 si en Once Ideal
- Bronce:12 si Bronce / 7 si Oro / 4 si Plata / 2 si en Once Ideal

BOTA DE ORO (Pichichi):
- 25 si exacto / 15 si Top-3 / 10 si Top-5 / 5 si Top-10 / 0 resto

TOTAL GOLES:
- 30 - |goles_real - goles_predicho|, minimo 0
- Si te alejas >= 30 goles -> 0 puntos
"""

from dataclasses import dataclass, field
from typing import Optional


# --- Puntuaciones por seleccion clasificada ---
POINTS_R32_EXACT = 3   # acertar 1/2/3 en su posicion
POINTS_R32_WRONG_POS = 2  # acertar 1/2/3 pero en otra posicion
POINTS_R16 = 5
POINTS_QF = 8
POINTS_SF = 12
POINTS_FINAL = 20
POINTS_CHAMPION = 40


@dataclass
class Prediction:
    """Apuesta del usuario para toda la porra."""
    # Grupos: dict[grupo_letra] -> lista de 3 equipos en orden [1.º, 2.º, 3.º]
    groups: dict[str, list[str]] = field(default_factory=dict)
    # Equipos que clasifican a Octavos (16 equipos)
    r16_teams: list[str] = field(default_factory=list)
    # Equipos que clasifican a Cuartos (8 equipos)
    qf_teams: list[str] = field(default_factory=list)
    # Semifinalistas (4 equipos)
    sf_teams: list[str] = field(default_factory=list)
    # Finalistas (2 equipos)
    finalists: list[str] = field(default_factory=list)
    # Campeon
    champion: Optional[str] = None
    # MVPs
    mvp_gold: Optional[str] = None
    mvp_silver: Optional[str] = None
    mvp_bronze: Optional[str] = None
    # Pichichi
    top_scorer: Optional[str] = None
    # Total goles del Mundial
    total_goals: Optional[int] = None


@dataclass
class ActualResults:
    """Resultados reales del Mundial."""
    groups: dict[str, list[str]] = field(default_factory=dict)
    r16_teams: list[str] = field(default_factory=list)
    qf_teams: list[str] = field(default_factory=list)
    sf_teams: list[str] = field(default_factory=list)
    finalists: list[str] = field(default_factory=list)
    champion: Optional[str] = None
    mvp_gold: Optional[str] = None
    mvp_silver: Optional[str] = None
    mvp_bronze: Optional[str] = None
    best_eleven: list[str] = field(default_factory=list)
    top_scorers_ranked: list[str] = field(default_factory=list)  # ordenados del 1 al N
    total_goals: int = 0


def score_groups(pred: dict[str, list[str]], actual: dict[str, list[str]]) -> int:
    """Puntua la fase de grupos."""
    total = 0
    for group, pred_teams in pred.items():
        actual_teams = actual.get(group, [])
        for pos, team in enumerate(pred_teams):
            if team in actual_teams:
                if actual_teams[pos] == team:
                    total += POINTS_R32_EXACT
                else:
                    total += POINTS_R32_WRONG_POS
    return total


def _set_overlap_points(pred: list[str], actual: list[str], pts_per_hit: int) -> int:
    return len(set(pred) & set(actual)) * pts_per_hit


def score_mvp(pred: Prediction, actual: ActualResults) -> int:
    """Puntua los 3 Balones segun la matriz del Excel."""
    total = 0
    # Oro
    if pred.mvp_gold:
        if pred.mvp_gold == actual.mvp_gold: total += 25
        elif pred.mvp_gold == actual.mvp_silver: total += 15
        elif pred.mvp_gold == actual.mvp_bronze: total += 8
        elif pred.mvp_gold in actual.best_eleven: total += 5
    # Plata
    if pred.mvp_silver:
        if pred.mvp_silver == actual.mvp_silver: total += 18
        elif pred.mvp_silver == actual.mvp_gold: total += 10
        elif pred.mvp_silver == actual.mvp_bronze: total += 5
        elif pred.mvp_silver in actual.best_eleven: total += 3
    # Bronce
    if pred.mvp_bronze:
        if pred.mvp_bronze == actual.mvp_bronze: total += 12
        elif pred.mvp_bronze == actual.mvp_gold: total += 7
        elif pred.mvp_bronze == actual.mvp_silver: total += 4
        elif pred.mvp_bronze in actual.best_eleven: total += 2
    return total


def score_top_scorer(pred_player: Optional[str], ranked: list[str]) -> int:
    if not pred_player or not ranked: return 0
    if pred_player not in ranked: return 0
    pos = ranked.index(pred_player) + 1
    if pos == 1: return 25
    if pos <= 3: return 15
    if pos <= 5: return 10
    if pos <= 10: return 5
    return 0


def score_total_goals(pred: Optional[int], actual: int) -> int:
    if pred is None: return 0
    diff = abs(pred - actual)
    if diff >= 30: return 0
    return 30 - diff


def score_prediction(pred: Prediction, actual: ActualResults) -> dict[str, int]:
    """Calcula el desglose completo de puntos."""
    breakdown = {
        "grupos": score_groups(pred.groups, actual.groups),
        "octavos": _set_overlap_points(pred.r16_teams, actual.r16_teams, POINTS_R16),
        "cuartos": _set_overlap_points(pred.qf_teams, actual.qf_teams, POINTS_QF),
        "semis": _set_overlap_points(pred.sf_teams, actual.sf_teams, POINTS_SF),
        "final": _set_overlap_points(pred.finalists, actual.finalists, POINTS_FINAL),
        "campeon": POINTS_CHAMPION if pred.champion and pred.champion == actual.champion else 0,
        "mvp": score_mvp(pred, actual),
        "pichichi": score_top_scorer(pred.top_scorer, actual.top_scorers_ranked),
        "total_goles": score_total_goals(pred.total_goals, actual.total_goals),
    }
    breakdown["TOTAL"] = sum(breakdown.values())
    return breakdown
