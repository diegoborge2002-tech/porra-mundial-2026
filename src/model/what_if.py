"""Simulador 'What-if': inyecta un resultado hipotético, lanza MC y compara.

Devuelve los top movers de probabilidad de campeón vs el estado actual,
sin tocar el real_results.json en disco.
"""
from __future__ import annotations
from copy import deepcopy

from src.model.tournament_sim import run_monte_carlo
from src.tournament.bracket import R32_FIFA, R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA


_KO_BRACKETS = {
    "r32": R32_FIFA, "r16": R16_FIFA, "qf": QF_FIFA, "sf": SF_FIFA, "final": F_FIFA,
}


def inject_group_result(real_results: dict, team_a: str, team_b: str,
                        score_a: int, score_b: int) -> dict:
    """Devuelve una copia de real_results con el partido de grupo añadido."""
    rr = deepcopy(real_results) if real_results else {
        "group_matches": {},
        "knockout_matches": {"r32": {}, "r16": {}, "qf": {}, "sf": {}, "final": {}},
    }
    # Eliminar versión en orden contrario si existe
    k1 = f"{team_a} vs {team_b}"; k2 = f"{team_b} vs {team_a}"
    if k2 in rr["group_matches"]:
        rr["group_matches"].pop(k2)
    rr["group_matches"][k1] = [int(score_a), int(score_b)]
    return rr


def inject_knockout_result(real_results: dict, round_key: str, match_id: int,
                            home: str, away: str, score_home: int, score_away: int,
                            winner: str | None = None) -> dict:
    """Devuelve copia con el KO inyectado."""
    rr = deepcopy(real_results) if real_results else {
        "group_matches": {},
        "knockout_matches": {"r32": {}, "r16": {}, "qf": {}, "sf": {}, "final": {}},
    }
    if winner is None:
        if score_home > score_away: winner = home
        elif score_away > score_home: winner = away
        else: winner = home  # default penalti
    rr["knockout_matches"].setdefault(round_key, {})[str(match_id)] = {
        "home": home, "away": away,
        "home_score": int(score_home), "away_score": int(score_away),
        "winner": winner,
    }
    return rr


def compute_what_if(
    elo: dict[str, float],
    real_results_now: dict,
    hypothetical_real_results: dict,
    n_sims: int = 4_000,
    seed: int = 42,
) -> dict:
    """Lanza dos MC (actual e hipotético) y devuelve deltas.

    Returns:
        {
          'before': {'champion': {...}, ...},
          'after': {'champion': {...}, ...},
          'movers': [(team, before, after, delta), ...]  # ordenado por |delta| desc
        }
    """
    mc_before = run_monte_carlo(elo, n_sims=n_sims, seed=seed,
                                 real_results=real_results_now)
    mc_after = run_monte_carlo(elo, n_sims=n_sims, seed=seed,
                                real_results=hypothetical_real_results)
    before = mc_before.champion_probs
    after = mc_after.champion_probs
    teams = set(before.keys()) | set(after.keys())
    movers = []
    for t in teams:
        b = before.get(t, 0.0)
        a = after.get(t, 0.0)
        movers.append((t, b, a, a - b))
    movers.sort(key=lambda x: -abs(x[3]))
    return {
        "before": {
            "champion": before,
            "r16": mc_before.r16_probs,
            "quarter": mc_before.quarter_probs,
            "semifinal": mc_before.semifinal_probs,
            "finalist": mc_before.finalist_probs,
        },
        "after": {
            "champion": after,
            "r16": mc_after.r16_probs,
            "quarter": mc_after.quarter_probs,
            "semifinal": mc_after.semifinal_probs,
            "finalist": mc_after.finalist_probs,
        },
        "movers": movers,
    }
