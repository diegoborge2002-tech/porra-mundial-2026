"""Ensemble de modelos: Elo dinámico + modelo de stats XGBoost.

El Elo solo ve resultados (quién ganó a quién); el modelo de stats
(entrenado con el pipeline del repo Simulaciones_Mundial) ve CÓMO juega
cada equipo: xG, posesión, remates, forma reciente, ranking FIFA. Son
señales complementarias, así que las mezclamos:

    lambda_final = (1 - w) * lambda_elo  +  w * lambda_stats

donde `w` (peso del modelo de stats) es configurable por el usuario en
"Mis ajustes" (0 = solo Elo, 1 = solo stats; por defecto 0.5).

Las predicciones del modelo de stats vienen precomputadas en
`data/processed/stats_model.json` (generado por
notebooks/04_entrenar_stats_model.py), de modo que la web no necesita
xgboost en runtime. Son xG a sede neutral; la ventaja de anfitrión se
aplica encima con la misma pendiente goles/Elo que usa el modelo Poisson.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

_STATS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "stats_model.json"

# Peso global del modelo de stats en el ensemble. La app lo fija desde la
# config del usuario (BiasesConfig.stats_weight) antes de simular.
_stats_weight: float = 0.5

# Misma pendiente que poisson.elo_to_expected_goals: goles por punto Elo
_GOALS_PER_ELO = 0.0035
_MIN_LAMBDA = 0.15


def set_stats_weight(w: float) -> None:
    global _stats_weight
    _stats_weight = max(0.0, min(1.0, float(w)))


def get_stats_weight() -> float:
    return _stats_weight


@lru_cache(maxsize=1)
def load_stats_model() -> dict:
    """Carga el JSON precomputado. Devuelve {} si no existe (la web degrada a Elo puro)."""
    if not _STATS_PATH.exists():
        return {}
    try:
        return json.loads(_STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def stats_available() -> bool:
    return bool(load_stats_model().get("pairs"))


def get_stats_meta() -> dict:
    return load_stats_model().get("meta", {})


def get_team_stats(team: str) -> dict | None:
    """Snapshot de forma reciente del equipo (xG, posesión, ranking FIFA…)."""
    return load_stats_model().get("teams", {}).get(team)


@lru_cache(maxsize=4096)
def _pair_oriented(team_h: str, team_a: str) -> tuple[float, float, float, float, float] | None:
    """(xg_h, xg_a, p_h, p_x, p_a) orientado, cacheado (hot path del Monte Carlo)."""
    pairs = load_stats_model().get("pairs", {})
    if team_h <= team_a:
        v = pairs.get(f"{team_h}|{team_a}")
        return (v[0], v[1], v[2], v[3], v[4]) if v else None
    v = pairs.get(f"{team_a}|{team_h}")
    return (v[1], v[0], v[4], v[3], v[2]) if v else None


def get_stats_prediction(team_h: str, team_a: str) -> dict | None:
    """Predicción del modelo de stats para el cruce, orientada (home, away).

    Returns dict con xg_h, xg_a, p_h, p_x, p_a (sede neutral) o None si el
    par no está en el modelo.
    """
    v = _pair_oriented(team_h, team_a)
    if v is None:
        return None
    return {"xg_h": v[0], "xg_a": v[1], "p_h": v[2], "p_x": v[3], "p_a": v[4]}


def blended_lambdas(
    lambda_elo_h: float, lambda_elo_a: float,
    team_h: str | None, team_a: str | None,
    home_advantage: float = 0.0,
    weight: float | None = None,
) -> tuple[float, float]:
    """Mezcla las lambdas del Elo con los xG del modelo de stats.

    Si no hay nombres de equipo, peso 0, o el par no existe en el JSON,
    devuelve las lambdas Elo sin tocar.
    """
    w = _stats_weight if weight is None else weight
    if w <= 0 or not team_h or not team_a:
        return lambda_elo_h, lambda_elo_a
    pred = _pair_oriented(team_h, team_a)
    if pred is None:
        return lambda_elo_h, lambda_elo_a
    # Los xG del modelo de stats son a sede neutral: aplicar encima la ventaja
    # de anfitrión con la misma pendiente Elo->goles del modelo Poisson.
    shift = home_advantage * _GOALS_PER_ELO / 2
    xg_h = max(pred[0] + shift, _MIN_LAMBDA)
    xg_a = max(pred[1] - shift, _MIN_LAMBDA)
    lh = (1 - w) * lambda_elo_h + w * xg_h
    la = (1 - w) * lambda_elo_a + w * xg_a
    return max(lh, _MIN_LAMBDA), max(la, _MIN_LAMBDA)
