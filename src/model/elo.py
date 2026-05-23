"""Sistema Elo dinamico para selecciones nacionales.

Inspirado en el sistema World Football Elo Ratings (eloratings.net), con
adaptaciones para entrenarlo desde un historico de resultados.

Parametros clave:
- K base: factor de aprendizaje. Mas alto para partidos importantes.
- Ventaja de campo: ~+65 pts (eloratings.net usa 100, pero 65 ajusta mejor para selecciones)
- Margen de victoria: multiplicador segun diferencia de goles
- Tipo de torneo: K se escala (amistosos = 20, clasificatorios = 35, World Cup = 60)
"""

from __future__ import annotations
import math
import pandas as pd
from collections import defaultdict


# Multiplicadores de K segun importancia del torneo (estilo eloratings.net)
TOURNAMENT_K: dict[str, float] = {
    "Friendly": 20,
    "FIFA World Cup": 60,
    "FIFA World Cup qualification": 35,
    "UEFA Euro": 50,
    "UEFA Euro qualification": 35,
    "Copa America": 50,
    "African Cup of Nations": 50,
    "AFC Asian Cup": 50,
    "Gold Cup": 40,
    "Confederations Cup": 45,
    "UEFA Nations League": 40,
    "CONCACAF Nations League": 35,
    "FIFA Series": 25,
}
DEFAULT_K = 30.0

HOME_ADVANTAGE = 65.0  # puntos Elo
INITIAL_RATING = 1500.0


def expected_score(rating_a: float, rating_b: float, home_advantage: float = 0.0) -> float:
    """Probabilidad de que A gane contra B usando logistica Elo."""
    diff = (rating_a + home_advantage) - rating_b
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def goal_diff_multiplier(goal_diff: int) -> float:
    """Multiplicador estilo eloratings.net por margen de victoria."""
    gd = abs(goal_diff)
    if gd <= 1: return 1.0
    if gd == 2: return 1.5
    if gd == 3: return 1.75
    return 1.75 + (gd - 3) / 8.0


def actual_score(home_goals: int, away_goals: int) -> tuple[float, float]:
    """Resultado real: 1 victoria, 0.5 empate, 0 derrota."""
    if home_goals > away_goals: return 1.0, 0.0
    if home_goals < away_goals: return 0.0, 1.0
    return 0.5, 0.5


def train_elo(
    results: pd.DataFrame,
    initial_rating: float = INITIAL_RATING,
    home_advantage: float = HOME_ADVANTAGE,
    decay_old_matches: bool = True,
    half_life: float = 8.0,
) -> dict[str, float]:
    """Entrena Elo iterando sobre todos los partidos historicos.

    Args:
        results: DataFrame con columnas ['date','home_team','away_team',
                 'home_score','away_score','tournament','neutral']
        initial_rating: Elo inicial para equipos no vistos.
        home_advantage: bonus Elo del equipo local (0 si neutral=True).
        decay_old_matches: si True, reduce K para partidos muy antiguos
                          para que el rating final refleje mas la actualidad.
        half_life: vida media en anos para el decaimiento exponencial de la importancia de partidos.

    Returns:
        dict equipo -> Elo final.
    """
    ratings: dict[str, float] = defaultdict(lambda: initial_rating)
    results = results.copy()
    results["date"] = pd.to_datetime(results["date"])
    results = results.sort_values("date").reset_index(drop=True)
    # Solo partidos con resultado real
    results = results.dropna(subset=["home_score", "away_score"])

    max_date = results["date"].max()

    for _, row in results.iterrows():
        home, away = row["home_team"], row["away_team"]
        hg, ag = int(row["home_score"]), int(row["away_score"])
        tournament = row["tournament"]
        neutral = bool(row.get("neutral", False))

        ra, rb = ratings[home], ratings[away]
        ha = 0.0 if neutral else home_advantage
        ea = expected_score(ra, rb, ha)
        eb = 1 - ea
        sa, sb = actual_score(hg, ag)

        k = TOURNAMENT_K.get(tournament, DEFAULT_K)
        mult = goal_diff_multiplier(hg - ag)

        if decay_old_matches:
            years_ago = (max_date - row["date"]).days / 365.25
            # Half-life de ~half_life anos
            decay = 0.5 ** (years_ago / half_life)
            k *= decay

        delta_a = k * mult * (sa - ea)
        delta_b = k * mult * (sb - eb)

        ratings[home] = ra + delta_a
        ratings[away] = rb + delta_b

    return dict(ratings)


def win_draw_loss_probs(
    elo_home: float, elo_away: float,
    home_advantage: float = 0.0,
    draw_alpha: float = 1/3,
) -> tuple[float, float, float]:
    """Convierte Elo a probabilidades de victoria/empate/derrota.

    Modelo simple: el empate "come" una fraccion de la probabilidad
    en funcion de lo parejo del partido. Cuanto mas cerrado, mas empate.
    """
    p_home_raw = expected_score(elo_home, elo_away, home_advantage)
    p_away_raw = 1 - p_home_raw
    # Probabilidad de empate proporcional a lo parejo
    closeness = 1 - 2 * abs(p_home_raw - 0.5)  # 1 si 50-50, 0 si 100-0
    p_draw = draw_alpha * closeness
    # Reparte el resto proporcional a las probabilidades crudas
    rest = 1 - p_draw
    p_home = rest * p_home_raw
    p_away = rest * p_away_raw
    return p_home, p_draw, p_away
