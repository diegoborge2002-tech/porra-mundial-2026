"""Simulador Poisson de partidos.

Dadas las fortalezas relativas de dos equipos (Elo), estimamos los goles
esperados de cada uno (lambda_home, lambda_away) y simulamos goles como
distribuciones Poisson independientes.

Calibracion:
- Usamos la probabilidad implicita de victoria del Elo para mapear a
  goles esperados via una curva ajustada con datos historicos.
- Goles totales esperados por partido (mediana historica Mundiales): ~2.5
"""

from __future__ import annotations
import numpy as np
from numpy.random import Generator


# Goles esperados totales por partido (Mundial). Calibrar con datos.
EXPECTED_TOTAL_GOALS_WC = 2.6


def elo_to_expected_goals(
    elo_home: float, elo_away: float,
    home_advantage: float = 0.0,
    total_goals: float = EXPECTED_TOTAL_GOALS_WC,
) -> tuple[float, float]:
    """Mapea diferencia de Elo a goles esperados por equipo.

    Estrategia:
    1. Calculamos prob de victoria del local via Elo.
    2. La diferencia de fuerza se traduce en diferencia de goles esperados
       via una funcion lineal acotada (con tope para evitar extremos).
    3. Total goles fijo (~2.6 para Mundial).
    """
    diff = (elo_home + home_advantage) - elo_away
    # Expected goal difference: ~0.0035 goles por punto Elo, con cap
    expected_gd = np.clip(diff * 0.0035, -2.5, 2.5)
    # Reparto: total = lambda_h + lambda_a, gd = lambda_h - lambda_a
    lambda_h = (total_goals + expected_gd) / 2
    lambda_a = (total_goals - expected_gd) / 2
    # Minimo positivo
    lambda_h = max(lambda_h, 0.15)
    lambda_a = max(lambda_a, 0.15)
    return lambda_h, lambda_a


def simulate_match(
    elo_home: float, elo_away: float,
    rng: Generator,
    home_advantage: float = 0.0,
    knockout: bool = False,
) -> tuple[int, int, int, int]:
    """Simula un partido y devuelve (goles_local, goles_visit, pens_local, pens_visit).

    En knockout, si hay empate, simulamos prorroga (+30%) y luego penaltis.
    Penaltis se modelan como prob 50-50 con sesgo leve por Elo.
    """
    lh, la = elo_to_expected_goals(elo_home, elo_away, home_advantage)
    gh = int(rng.poisson(lh))
    ga = int(rng.poisson(la))

    pens_h = pens_a = 0
    if knockout and gh == ga:
        # Prorroga: 30% de tiempo extra -> ~30% mas goles esperados (escalado)
        eg_h = int(rng.poisson(lh * 0.30))
        eg_a = int(rng.poisson(la * 0.30))
        gh += eg_h
        ga += eg_a
        if gh == ga:
            # Penaltis: ligero sesgo por Elo
            diff = elo_home - elo_away
            p_home_pen = 0.5 + np.clip(diff / 2000, -0.15, 0.15)
            if rng.random() < p_home_pen:
                pens_h, pens_a = 4, 3  # marcador simbolico
            else:
                pens_h, pens_a = 3, 4
    return gh, ga, pens_h, pens_a
