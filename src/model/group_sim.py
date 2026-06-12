"""Simulador Monte Carlo de la fase de grupos.

Para cada grupo de 4 equipos:
1. Simula los 6 partidos round-robin con el modelo Poisson basado en Elo.
2. Calcula puntos, diferencia de goles, goles a favor.
3. Devuelve la clasificacion (1.º, 2.º, 3.º, 4.º).

Tras simular los 12 grupos, identifica los 8 mejores terceros segun:
1. Puntos
2. Diferencia de goles
3. Goles a favor
4. (Fair play y FIFA ranking no los modelamos, usamos Elo como desempate)

Ventaja de anfitrión: USA, Canadá y México juegan sus 3 partidos de grupos
en casa (verificado en el dataset oficial). Aplicamos +HOME_ADVANTAGE Elo al
anfitrión si está en el partido.
"""
from __future__ import annotations
import numpy as np
from numpy.random import Generator
from dataclasses import dataclass, field
from itertools import combinations

from src.model.poisson import simulate_match
from src.model.elo import HOME_ADVANTAGE
from src.tournament.groups import GROUPS, HOST_NATIONS


@dataclass
class TeamGroupStats:
    team: str
    group: str
    points: int = 0
    gd: int = 0
    gf: int = 0
    ga: int = 0
    elo: float = 1500.0


def _host_advantage_for(team_a: str, team_b: str) -> float:
    """Devuelve el bonus Elo a favor de team_a (negativo si team_b es anfitrión)."""
    a_host = team_a in HOST_NATIONS
    b_host = team_b in HOST_NATIONS
    if a_host and not b_host:
        return HOME_ADVANTAGE
    if b_host and not a_host:
        return -HOME_ADVANTAGE
    return 0.0


def simulate_group(
    group_letter: str,
    teams_elo: dict[str, float],
    rng: Generator,
    real_results: dict | None = None,
) -> list[TeamGroupStats]:
    """Simula un grupo round-robin y devuelve la clasificacion ordenada."""
    teams = GROUPS[group_letter]
    stats = {t: TeamGroupStats(team=t, group=group_letter, elo=teams_elo[t]) for t in teams}

    group_matches = real_results.get("group_matches", {}) if real_results else {}

    for ta, tb in combinations(teams, 2):
        score = None
        if f"{ta} vs {tb}" in group_matches:
            gh, ga = group_matches[f"{ta} vs {tb}"]
            score = (gh, ga)
        elif f"{tb} vs {ta}" in group_matches:
            ga, gh = group_matches[f"{tb} vs {ta}"]
            score = (gh, ga)

        if score is not None:
            gh, ga = score
        else:
            ha = _host_advantage_for(ta, tb)
            gh, ga, _, _ = simulate_match(
                stats[ta].elo, stats[tb].elo, rng,
                home_advantage=ha, knockout=False,
                team_home=ta, team_away=tb,
            )

        stats[ta].gf += gh; stats[ta].ga += ga
        stats[tb].gf += ga; stats[tb].ga += gh
        stats[ta].gd = stats[ta].gf - stats[ta].ga
        stats[tb].gd = stats[tb].gf - stats[tb].ga
        if gh > ga:
            stats[ta].points += 3
        elif gh < ga:
            stats[tb].points += 3
        else:
            stats[ta].points += 1
            stats[tb].points += 1

    # Ordenar: puntos, diferencia goles, goles a favor, elo (desempate suave)
    ranking = sorted(
        stats.values(),
        key=lambda s: (s.points, s.gd, s.gf, s.elo),
        reverse=True,
    )
    return ranking


def best_third_places(
    all_groups_standings: dict[str, list[TeamGroupStats]],
) -> list[TeamGroupStats]:
    """Devuelve los 8 mejores terceros."""
    thirds = [standings[2] for standings in all_groups_standings.values()]
    thirds_sorted = sorted(
        thirds,
        key=lambda s: (s.points, s.gd, s.gf, s.elo),
        reverse=True,
    )
    return thirds_sorted[:8]


def simulate_all_groups(
    teams_elo: dict[str, float],
    rng: Generator,
    real_results: dict | None = None,
) -> tuple[dict[str, list[TeamGroupStats]], list[TeamGroupStats]]:
    """Simula los 12 grupos. Devuelve (standings_por_grupo, 8_mejores_terceros)."""
    standings = {g: simulate_group(g, teams_elo, rng, real_results) for g in GROUPS}
    thirds = best_third_places(standings)
    return standings, thirds
