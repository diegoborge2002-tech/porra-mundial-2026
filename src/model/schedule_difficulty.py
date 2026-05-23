"""Cálculo de strength-of-schedule (dificultad del calendario) por equipo."""
from __future__ import annotations
from dataclasses import dataclass

from src.tournament.groups import GROUPS


@dataclass
class ScheduleDifficulty:
    team: str
    group: str
    group_opponents: list[tuple[str, float, bool]]  # (rival, elo_rival, jugado?)
    mean_elo_played: float                          # rivales ya jugados (0 si ninguno)
    mean_elo_pending: float                         # rivales por jugar
    expected_ko_opponents: list[tuple[str, float, float]]  # (rival, prob_enfrentarse, elo_rival)
    expected_ko_difficulty: float                   # Elo esperado del rival de Octavos


def _played_set(real_results: dict | None, team: str) -> set[str]:
    if not real_results:
        return set()
    played: set[str] = set()
    for key in real_results.get("group_matches", {}):
        parts = key.split(" vs ")
        if len(parts) != 2:
            continue
        if team in parts:
            other = parts[0] if parts[1] == team else parts[1]
            played.add(other)
    return played


def compute_schedule_difficulty(
    team: str,
    group: str,
    elo: dict[str, float],
    summary: dict,
    real_results: dict | None,
) -> ScheduleDifficulty:
    """Dificultad de grupo + esperada en cruces."""
    teammates = [t for t in GROUPS[group] if t != team]
    played = _played_set(real_results, team)
    group_ops: list[tuple[str, float, bool]] = []
    elos_played, elos_pending = [], []
    for rival in teammates:
        e = elo.get(rival, 1500.0)
        is_played = rival in played
        group_ops.append((rival, e, is_played))
        if is_played:
            elos_played.append(e)
        else:
            elos_pending.append(e)
    mean_played = sum(elos_played) / len(elos_played) if elos_played else 0.0
    mean_pending = sum(elos_pending) / len(elos_pending) if elos_pending else 0.0

    # Cruce más probable en Octavos: equipos del bracket emparejado contra este equipo
    # ponderados por su probabilidad de salir de su grupo en la posición correspondiente.
    # Aproximación: usar la prob de Octavos (r16) de cada equipo y su prob de cruzarse
    # con este. Para una primera versión: top rivales esperados según p(R16) * p(este equipo R16)
    # vs todos los demás de los grupos cruzados.
    # Simplificación: tomar todos los rivales potenciales del lado opuesto del bracket
    # ponderados por p(R16). Si no se tiene la lógica de bracket aquí, usamos como
    # proxy el promedio Elo ponderado por p(R16) de los equipos NO de tu grupo.
    r16_probs = summary.get("r16", {})
    other_teams = [t for t in r16_probs if t not in GROUPS[group]]
    total_w = sum(r16_probs.get(t, 0) for t in other_teams)
    if total_w > 0:
        ko_op_expected = sum(r16_probs.get(t, 0) * elo.get(t, 1500.0)
                              for t in other_teams) / total_w
    else:
        ko_op_expected = 1500.0
    top_ko_ops = sorted(
        [(t, r16_probs.get(t, 0), elo.get(t, 1500.0)) for t in other_teams],
        key=lambda x: -x[2]
    )[:5]
    return ScheduleDifficulty(
        team=team,
        group=group,
        group_opponents=group_ops,
        mean_elo_played=mean_played,
        mean_elo_pending=mean_pending,
        expected_ko_opponents=top_ko_ops,
        expected_ko_difficulty=ko_op_expected,
    )
