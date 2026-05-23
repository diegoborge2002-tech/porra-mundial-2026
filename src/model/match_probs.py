"""Probabilidades de partido: Poisson clásico + corrección Dixon-Coles.

El modelo Poisson independiente sobre-estima 0-0, 1-0, 0-1 y 1-1
porque empareja ambos goleadores como independientes. Dixon-Coles (1997)
añade una función tau que reescala estos cuatro cuadrantes con un parámetro
rho ≈ -0.10 calibrable.

Funciones públicas:
- exact_score_matrix(lh, la, max_goals, use_dc, rho) -> dict (h,a) -> prob
- top_exact_scores(lh, la, n, use_dc, rho) -> list[((h,a), prob)]
- match_outcome_probs(lh, la, use_dc, rho) -> (p_home, p_draw, p_away)
- live_outcome_probs(lh, la, minute_played, home_score, away_score, ...)
"""
from __future__ import annotations
import math


DEFAULT_RHO = -0.10
DEFAULT_MAX_GOALS = 8


def _poisson_pmf(lmbda: float, k: int) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)


def _dc_tau(h: int, a: int, lh: float, la: float, rho: float) -> float:
    """Función tau de Dixon-Coles. Solo afecta (0,0), (1,0), (0,1), (1,1)."""
    if h == 0 and a == 0:
        return 1.0 - lh * la * rho
    if h == 0 and a == 1:
        return 1.0 + lh * rho
    if h == 1 and a == 0:
        return 1.0 + la * rho
    if h == 1 and a == 1:
        return 1.0 - rho
    return 1.0


def exact_score_matrix(
    lh: float, la: float,
    max_goals: int = DEFAULT_MAX_GOALS,
    use_dc: bool = True,
    rho: float = DEFAULT_RHO,
) -> dict[tuple[int, int], float]:
    """Probabilidad de cada marcador exacto (h,a) con 0 <= h,a <= max_goals.

    Renormaliza al final para que la suma sea 1.0 (la cola truncada importa poco
    para lambdas típicas <3 pero al menos no produce probabilidades sesgadas).
    """
    probs: dict[tuple[int, int], float] = {}
    total = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = _poisson_pmf(lh, h) * _poisson_pmf(la, a)
            if use_dc and h <= 1 and a <= 1:
                tau = _dc_tau(h, a, lh, la, rho)
                # Guard contra valores muy negativos (rho mal calibrado)
                tau = max(tau, 0.0)
                p *= tau
            probs[(h, a)] = p
            total += p
    if total > 0:
        for k in probs:
            probs[k] /= total
    return probs


def top_exact_scores(
    lh: float, la: float, n: int = 5,
    use_dc: bool = True, rho: float = DEFAULT_RHO,
    max_goals: int = 6,
) -> list[tuple[tuple[int, int], float]]:
    """Top-N marcadores más probables."""
    m = exact_score_matrix(lh, la, max_goals=max_goals, use_dc=use_dc, rho=rho)
    return sorted(m.items(), key=lambda x: -x[1])[:n]


def match_outcome_probs(
    lh: float, la: float,
    use_dc: bool = True, rho: float = DEFAULT_RHO,
    max_goals: int = DEFAULT_MAX_GOALS,
) -> tuple[float, float, float]:
    """Probabilidad de (victoria local, empate, victoria visit) sumando la matriz."""
    m = exact_score_matrix(lh, la, max_goals=max_goals, use_dc=use_dc, rho=rho)
    p_h = sum(p for (h, a), p in m.items() if h > a)
    p_d = sum(p for (h, a), p in m.items() if h == a)
    p_a = sum(p for (h, a), p in m.items() if h < a)
    # Normalizar minúscula deriva por floats
    s = p_h + p_d + p_a
    if s > 0:
        return p_h / s, p_d / s, p_a / s
    return 1 / 3, 1 / 3, 1 / 3


def live_outcome_probs(
    lh_full: float, la_full: float,
    minute_played: int,
    home_score: int, away_score: int,
    use_dc: bool = True, rho: float = DEFAULT_RHO,
    max_extra_goals: int = 6,
    total_minutes: int = 90,
) -> dict:
    """Probabilidades 1X2 en VIVO condicionadas al minuto actual y al marcador.

    lh_full / la_full son las lambdas de goles esperados a 90 minutos (modelo pre-partido).
    Calculamos la lambda restante proporcional al tiempo restante y sumamos
    la distribución de goles futuros con el marcador actual.

    Returns:
        {
            'p_home': float, 'p_draw': float, 'p_away': float,
            'remaining_minutes': int,
            'lambda_home_remaining': float,
            'lambda_away_remaining': float,
            'expected_final_home': float, 'expected_final_away': float,
            'top_final_scores': [((h,a), prob), ...],
        }
    """
    minute_played = max(0, min(minute_played, total_minutes))
    rem = total_minutes - minute_played
    factor = rem / total_minutes
    lh_rem = lh_full * factor
    la_rem = la_full * factor

    # Distribución de goles RESTANTES (sin DC porque los lambdas pueden ser muy
    # pequeños y la corrección de los cuadrantes bajos pierde sentido).
    p_h = p_d = p_a = 0.0
    score_grid: dict[tuple[int, int], float] = {}
    for hg in range(max_extra_goals + 1):
        for ag in range(max_extra_goals + 1):
            p = _poisson_pmf(lh_rem, hg) * _poisson_pmf(la_rem, ag)
            final_h = home_score + hg
            final_a = away_score + ag
            score_grid[(final_h, final_a)] = score_grid.get((final_h, final_a), 0.0) + p
            if final_h > final_a:
                p_h += p
            elif final_h < final_a:
                p_a += p
            else:
                p_d += p
    s = p_h + p_d + p_a
    if s > 0:
        p_h /= s; p_d /= s; p_a /= s
    top = sorted(score_grid.items(), key=lambda x: -x[1])[:5]
    return {
        "p_home": p_h, "p_draw": p_d, "p_away": p_a,
        "remaining_minutes": rem,
        "lambda_home_remaining": lh_rem,
        "lambda_away_remaining": la_rem,
        "expected_final_home": home_score + lh_rem,
        "expected_final_away": away_score + la_rem,
        "top_final_scores": top,
    }
