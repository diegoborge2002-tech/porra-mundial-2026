"""Simulador Monte Carlo del Mundial 2026 completo.

Pipeline de una simulacion:
  1. Simula los 12 grupos (round-robin) -> standings + 8 mejores terceros
  2. Resuelve cruces de Dieciseisavos usando bracket FIFA + tabla de terceros
  3. Simula Dieciseisavos, Octavos, Cuartos, Semis, Final (eliminatoria directa)
  4. Devuelve: campeon, finalistas, semifinalistas, cuartos, octavos, top goleadores

Tras N simulaciones, agregamos probabilidades.
"""
from __future__ import annotations
import numpy as np
from numpy.random import Generator
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from typing import Optional

from src.model.poisson import simulate_match
from src.model.group_sim import simulate_all_groups, TeamGroupStats
from src.tournament.bracket import (
    R32_FIFA, R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA,
    THIRD_PLACE_HEAD_TO_FIFA_MATCH,
)
from src.tournament.third_place_table import get_third_place_pairing
from src.model.pichichi import simulate_goalscorers
from src.scoring.porra import Prediction, ActualResults, score_prediction


@dataclass
class TournamentResult:
    """Resultado de UNA simulacion completa."""
    group_standings: dict[str, list[TeamGroupStats]]
    best_thirds: list[TeamGroupStats]
    r32_winners: dict[int, str]   # FIFA match id -> equipo ganador
    r16_winners: dict[int, str]
    qf_winners: dict[int, str]
    sf_winners: dict[int, str]
    champion: str
    # Clasificados a cada ronda (equipos)
    r16_teams: list[str] = field(default_factory=list)
    qf_teams: list[str] = field(default_factory=list)
    sf_teams: list[str] = field(default_factory=list)
    finalists: list[str] = field(default_factory=list)
    # Goles totales del torneo
    total_goals: int = 0
    # Goles por equipo (para identificar candidatos a Pichichi a nivel de equipo)
    team_goals: dict[str, int] = field(default_factory=dict)
    # Pairings por ronda (match_id -> (home, away)) para reconstruir rivales por equipo
    r32_pairings: dict[int, tuple[str, str]] = field(default_factory=dict)
    r16_pairings: dict[int, tuple[str, str]] = field(default_factory=dict)
    qf_pairings: dict[int, tuple[str, str]] = field(default_factory=dict)
    sf_pairings: dict[int, tuple[str, str]] = field(default_factory=dict)
    final_pairings: dict[int, tuple[str, str]] = field(default_factory=dict)


def _resolve_r32_pairings(
    standings: dict[str, list[TeamGroupStats]],
    thirds: list[TeamGroupStats],
) -> dict[int, tuple[str, str]]:
    """Devuelve dict {fifa_match_id: (home_team, away_team)} para los 16 partidos."""
    # 1) Top 1, top 2 de cada grupo
    p1 = {g: st[0].team for g, st in standings.items()}
    p2 = {g: st[1].team for g, st in standings.items()}
    # 2) Tercero por grupo (entre los 8 mejores)
    third_by_group = {t.group: t.team for t in thirds}
    qualified_third_groups = set(third_by_group)
    # 3) Mapping 1X -> 3X via tabla
    pairing = get_third_place_pairing(qualified_third_groups)  # {"1A": "3E", ...}

    matches: dict[int, tuple[str, str]] = {}
    for fifa_id, (slot_l, slot_r) in R32_FIFA.items():
        home = _resolve_slot(slot_l, p1, p2, third_by_group, pairing)
        away = _resolve_slot(slot_r, p1, p2, third_by_group, pairing)
        matches[fifa_id] = (home, away)
    return matches


def _resolve_slot(
    slot: str,
    p1: dict[str, str], p2: dict[str, str],
    third_by_group: dict[str, str],
    pairing: dict[str, str],
) -> str:
    """Convierte un slot tipo '1A', '2B', '3?E' en el nombre de equipo concreto."""
    if slot.startswith("1"):
        return p1[slot[1]]
    if slot.startswith("2"):
        return p2[slot[1]]
    if slot.startswith("3?"):
        # 3?X significa el tercero asignado a la cabeza de serie 1X
        head = "1" + slot[2]  # '3?E' -> '1E'
        third_slot = pairing[head]  # '3X' donde X es el grupo del tercero
        return third_by_group[third_slot[1]]
    if slot.startswith("3"):
        # Tercero de un grupo concreto (no via tabla)
        return third_by_group[slot[1]]
    raise ValueError(f"Slot desconocido: {slot}")


def _simulate_knockout_round(
    bracket: dict[int, tuple[int, int] | tuple[str, str]],
    prev_winners: dict[int, str] | None,
    teams_elo: dict[str, float],
    rng: Generator,
    team_goals: dict[str, int],
    is_initial: bool = False,
    real_results: dict | None = None,
    round_key: str = "",
) -> tuple[dict[int, str], int]:
    """Simula una ronda eliminatoria.

    Args:
        bracket: dict {match_id: (home, away)} donde home/away son IDs de partido previo
                 o nombres directos de equipo (caso is_initial=True).
        prev_winners: dict {match_id_previo: equipo_ganador}, None si is_initial.
        is_initial: True si es Dieciseisavos (bracket ya tiene nombres de equipos).
        real_results: diccionario de resultados reales cargados.
        round_key: clave de la ronda ('r32', 'r16', 'qf', 'sf', 'final').

    Returns:
        (winners {match_id: equipo}, goles_totales_ronda)
    """
    winners: dict[int, str] = {}
    round_goals = 0
    knockout_matches = real_results.get("knockout_matches", {}).get(round_key, {}) if real_results else {}

    for match_id, (slot_h, slot_a) in bracket.items():
        if is_initial:
            home, away = slot_h, slot_a
        else:
            home = prev_winners[slot_h]
            away = prev_winners[slot_a]

        # Comprobar si hay resultado real
        real_match = knockout_matches.get(str(match_id)) or knockout_matches.get(match_id)
        if real_match and real_match.get("winner"):
            winner = real_match["winner"]
            gh = real_match.get("home_score", 0)
            ga = real_match.get("away_score", 0)
        else:
            gh, ga, ph, pa = simulate_match(
                teams_elo[home], teams_elo[away], rng,
                home_advantage=0.0, knockout=True,
                team_home=home, team_away=away,
            )
            winner = home if (gh > ga or (gh == ga and ph > pa)) else away

        winners[match_id] = winner
        team_goals[home] = team_goals.get(home, 0) + gh
        team_goals[away] = team_goals.get(away, 0) + ga
        round_goals += gh + ga
    return winners, round_goals


def simulate_tournament(
    teams_elo: dict[str, float],
    rng: Generator,
    real_results: dict | None = None,
) -> TournamentResult:
    """Simula un Mundial completo de principio a fin."""
    # === Fase de grupos ===
    standings, thirds = simulate_all_groups(teams_elo, rng, real_results)
    # Goles totales y por equipo en la fase de grupos
    team_goals: dict[str, int] = defaultdict(int)
    group_goals = 0
    for st in standings.values():
        for team_stats in st:
            team_goals[team_stats.team] += team_stats.gf
            group_goals += team_stats.gf
    # group_goals cuenta cada gol UNA vez por equipo, pero hemos sumado todos los GF
    # de los 4 equipos, lo cual da el total real (GF_A + GF_B + GF_C + GF_D = total goles)

    # === Resolver cruces de Dieciseisavos ===
    r32_pairings = _resolve_r32_pairings(standings, thirds)

    # === Eliminatorias ===
    r32_winners, r32_goals = _simulate_knockout_round(
        r32_pairings, None, teams_elo, rng, team_goals, is_initial=True,
        real_results=real_results, round_key="r32"
    )
    r16_winners, r16_goals = _simulate_knockout_round(
        R16_FIFA, r32_winners, teams_elo, rng, team_goals,
        real_results=real_results, round_key="r16"
    )
    qf_winners, qf_goals = _simulate_knockout_round(
        QF_FIFA, r16_winners, teams_elo, rng, team_goals,
        real_results=real_results, round_key="qf"
    )
    sf_winners, sf_goals = _simulate_knockout_round(
        SF_FIFA, qf_winners, teams_elo, rng, team_goals,
        real_results=real_results, round_key="sf"
    )
    f_winners, f_goals = _simulate_knockout_round(
        F_FIFA, sf_winners, teams_elo, rng, team_goals,
        real_results=real_results, round_key="final"
    )

    champion = next(iter(f_winners.values()))
    total_goals = group_goals + r32_goals + r16_goals + qf_goals + sf_goals + f_goals

    # Listas de equipos clasificados a cada ronda
    r16_teams = list(r32_winners.values())
    qf_teams = list(r16_winners.values())
    sf_teams = list(qf_winners.values())
    finalists = list(sf_winners.values())

    # Reconstruir pairings resueltos por ronda (a partir de los winners previos)
    r16_pairings = {mid: (r32_winners.get(s_h), r32_winners.get(s_a))
                    for mid, (s_h, s_a) in R16_FIFA.items()}
    qf_pairings_resolved = {mid: (r16_winners.get(s_h), r16_winners.get(s_a))
                            for mid, (s_h, s_a) in QF_FIFA.items()}
    sf_pairings_resolved = {mid: (qf_winners.get(s_h), qf_winners.get(s_a))
                            for mid, (s_h, s_a) in SF_FIFA.items()}
    final_pairings_resolved = {mid: (sf_winners.get(s_h), sf_winners.get(s_a))
                                for mid, (s_h, s_a) in F_FIFA.items()}

    return TournamentResult(
        group_standings=standings,
        best_thirds=thirds,
        r32_winners=r32_winners,
        r16_winners=r16_winners,
        qf_winners=qf_winners,
        sf_winners=sf_winners,
        champion=champion,
        r16_teams=r16_teams,
        qf_teams=qf_teams,
        sf_teams=sf_teams,
        finalists=finalists,
        total_goals=total_goals,
        team_goals=dict(team_goals),
        r32_pairings=r32_pairings,
        r16_pairings=r16_pairings,
        qf_pairings=qf_pairings_resolved,
        sf_pairings=sf_pairings_resolved,
        final_pairings=final_pairings_resolved,
    )


FINAL_POSITION_BUCKETS = ["Campeón", "Subcampeón", "Semis", "Cuartos", "Octavos", "R32", "Fase grupos"]


@dataclass
class TournamentSummary:
    """Probabilidades agregadas tras N simulaciones."""
    n_sims: int
    champion_probs: dict[str, float]
    finalist_probs: dict[str, float]
    semifinal_probs: dict[str, float]
    quarter_probs: dict[str, float]
    r16_probs: dict[str, float]
    group_winner_probs: dict[str, dict[str, float]]  # grupo -> {team: prob 1.º}
    group_top2_probs: dict[str, dict[str, float]]    # grupo -> {team: prob top 2}
    group_top3_probs: dict[str, dict[str, float]]    # grupo -> {team: prob top 3 (clasif)}
    third_place_probs: dict[str, dict[str, float]]   # grupo -> {team: prob 3.º del grupo}
    qualified_as_best_third_probs: dict[str, float]  # {team: prob ser top-8 tercero}
    expected_total_goals: float
    total_goals_distribution: list[int]              # para histogram
    expected_team_goals: dict[str, float]
    pichichi_probs: dict[str, float] = field(default_factory=dict)
    leaderboard_probs: dict[str, float] = field(default_factory=dict)
    leaderboard_expected_points: dict[str, float] = field(default_factory=dict)
    # Datos por simulación, para análisis de incertidumbre y riesgo
    champion_by_sim: list[str] = field(default_factory=list)
    points_by_sim: dict[str, list[int]] = field(default_factory=dict)
    final_position_by_team: dict[str, dict[str, int]] = field(default_factory=dict)
    # Para "camino al título": {team: {round_label: {opponent: prob}}}
    opponent_probs_per_team: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)


def run_monte_carlo(
    teams_elo: dict[str, float],
    n_sims: int = 10_000,
    seed: int = 42,
    real_results: dict | None = None,
    predictions: dict[str, Prediction] | None = None,
) -> TournamentSummary:
    """Lanza N simulaciones y agrega probabilidades."""
    rng = np.random.default_rng(seed)

    champion_counter = Counter()
    finalist_counter = Counter()
    sf_counter = Counter()
    qf_counter = Counter()
    r16_counter = Counter()
    group_winner_counter: dict[str, Counter] = defaultdict(Counter)
    group_top2_counter: dict[str, Counter] = defaultdict(Counter)
    group_top3_counter: dict[str, Counter] = defaultdict(Counter)
    third_in_group_counter: dict[str, Counter] = defaultdict(Counter)
    best_third_counter: Counter = Counter()
    team_goals_sum: dict[str, float] = defaultdict(float)
    total_goals_list: list[int] = []
    
    pichichi_counter = Counter()
    friend_wins = Counter()
    friend_points_sum = defaultdict(float)
    champion_by_sim: list[str] = []
    points_by_sim: dict[str, list[int]] = defaultdict(list)
    final_position_by_team: dict[str, Counter] = defaultdict(Counter)
    # {team: {round_label: Counter(opponent -> count)}}
    opponents_per_team: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    for _ in range(n_sims):
        res = simulate_tournament(teams_elo, rng, real_results)
        champion_counter[res.champion] += 1
        champion_by_sim.append(res.champion)
        for t in res.finalists: finalist_counter[t] += 1
        for t in res.sf_teams: sf_counter[t] += 1
        for t in res.qf_teams: qf_counter[t] += 1
        for t in res.r16_teams: r16_counter[t] += 1
        for g, st in res.group_standings.items():
            group_winner_counter[g][st[0].team] += 1
            for s in st[:2]: group_top2_counter[g][s.team] += 1
            for s in st[:3]: group_top3_counter[g][s.team] += 1
            third_in_group_counter[g][st[2].team] += 1
        for t in res.best_thirds:
            best_third_counter[t.team] += 1
        for t, g in res.team_goals.items():
            team_goals_sum[t] += g
        total_goals_list.append(res.total_goals)

        # Rivales por equipo en cada ronda (para "camino al título")
        for round_label, pairings in [
            ("R32", res.r32_pairings),
            ("Octavos", res.r16_pairings),
            ("Cuartos", res.qf_pairings),
            ("Semis", res.sf_pairings),
            ("Final", res.final_pairings),
        ]:
            for _mid, (h, a) in pairings.items():
                if h and a:
                    opponents_per_team[h][round_label][a] += 1
                    opponents_per_team[a][round_label][h] += 1

        # Posición final por equipo (etiqueta más profunda alcanzada)
        runner_up = next((t for t in res.finalists if t != res.champion), None)
        sf_set = set(res.sf_teams)
        qf_set = set(res.qf_teams)
        r16_set = set(res.r16_teams)
        r32_set = {s.team for st in res.group_standings.values() for s in st[:2]}
        r32_set.update(t.team for t in res.best_thirds)
        for st in res.group_standings.values():
            for s in st:
                t = s.team
                if t == res.champion:
                    bucket = "Campeón"
                elif t == runner_up:
                    bucket = "Subcampeón"
                elif t in sf_set:
                    bucket = "Semis"
                elif t in qf_set:
                    bucket = "Cuartos"
                elif t in r16_set:
                    bucket = "Octavos"
                elif t in r32_set:
                    bucket = "R32"
                else:
                    bucket = "Fase grupos"
                final_position_by_team[t][bucket] += 1
        
        # 1. Pichichi
        player_goals = simulate_goalscorers(res.team_goals, rng)
        if player_goals:
            max_g = max(player_goals.values())
            top_players = [p for p, g in player_goals.items() if g == max_g]
            for tp in top_players:
                pichichi_counter[tp] += 1.0 / len(top_players)
                
        # 2. Leaderboard (Liga de Amigos)
        if predictions:
            actual_g = {g: [ts.team for ts in res.group_standings[g][:3]] for g in res.group_standings}
            sorted_players = sorted(player_goals.items(), key=lambda x: -x[1])
            top_scorers_ranked = [p[0] for p in sorted_players]
            
            actual_res = ActualResults(
                groups=actual_g,
                r16_teams=res.r16_teams,
                qf_teams=res.qf_teams,
                sf_teams=res.sf_teams,
                finalists=res.finalists,
                champion=res.champion,
                mvp_gold=None, mvp_silver=None, mvp_bronze=None,
                best_eleven=[],
                top_scorers_ranked=top_scorers_ranked,
                total_goals=res.total_goals
            )
            
            scores = {}
            for name, pred in predictions.items():
                pts_breakdown = score_prediction(pred, actual_res)
                pts = pts_breakdown["TOTAL"]
                scores[name] = pts
                friend_points_sum[name] += pts
                points_by_sim[name].append(pts)

            if scores:
                max_score = max(scores.values())
                winners = [name for name, pts in scores.items() if pts == max_score]
                for w in winners:
                    friend_wins[w] += 1.0 / len(winners)

    def to_probs(c: Counter) -> dict[str, float]:
        return {k: v / n_sims for k, v in c.items()}

    def to_probs_dict(d: dict[str, Counter]) -> dict[str, dict[str, float]]:
        return {g: to_probs(c) for g, c in d.items()}

    return TournamentSummary(
        n_sims=n_sims,
        champion_probs=to_probs(champion_counter),
        finalist_probs=to_probs(finalist_counter),
        semifinal_probs=to_probs(sf_counter),
        quarter_probs=to_probs(qf_counter),
        r16_probs=to_probs(r16_counter),
        group_winner_probs=to_probs_dict(group_winner_counter),
        group_top2_probs=to_probs_dict(group_top2_counter),
        group_top3_probs=to_probs_dict(group_top3_counter),
        third_place_probs=to_probs_dict(third_in_group_counter),
        qualified_as_best_third_probs=to_probs(best_third_counter),
        expected_total_goals=float(np.mean(total_goals_list)),
        total_goals_distribution=total_goals_list,
        expected_team_goals={t: g / n_sims for t, g in team_goals_sum.items()},
        pichichi_probs=to_probs(pichichi_counter),
        leaderboard_probs=to_probs(friend_wins),
        leaderboard_expected_points={k: v / n_sims for k, v in friend_points_sum.items()},
        champion_by_sim=champion_by_sim,
        points_by_sim={k: list(v) for k, v in points_by_sim.items()},
        final_position_by_team={t: dict(c) for t, c in final_position_by_team.items()},
        opponent_probs_per_team={
            t: {r: {opp: cnt / n_sims for opp, cnt in c.items()}
                for r, c in rounds.items()}
            for t, rounds in opponents_per_team.items()
        },
    )
