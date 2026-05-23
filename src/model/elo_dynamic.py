"""Recalculación de Elo dinámico basada en resultados reales del Mundial."""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd

from src.model.elo import expected_score, goal_diff_multiplier
from src.data.team_names import EN_TO_ES


K_WORLD_CUP = 50.0


@lru_cache(maxsize=1)
def _wc_match_dates() -> dict[frozenset[str], pd.Timestamp]:
    """Mapping {frozenset({equipoA_es, equipoB_es}) -> fecha} para los 72 partidos de grupos."""
    root = Path(__file__).resolve().parent.parent.parent
    df = pd.read_csv(root / "data" / "raw" / "results.csv")
    df["date"] = pd.to_datetime(df["date"])
    wc = df[(df["date"] >= "2026-06-01") & (df["tournament"] == "FIFA World Cup")]
    out: dict[frozenset[str], pd.Timestamp] = {}
    for _, row in wc.iterrows():
        h_es = EN_TO_ES.get(row["home_team"], row["home_team"])
        a_es = EN_TO_ES.get(row["away_team"], row["away_team"])
        out[frozenset({h_es, a_es})] = row["date"]
    return out


def _group_match_date(team_a: str, team_b: str) -> pd.Timestamp:
    key = frozenset({team_a, team_b})
    return _wc_match_dates().get(key, pd.Timestamp("2026-06-01"))


def _apply_match(elo: dict[str, float], team_a: str, team_b: str,
                 score_a: int, score_b: int, k: float) -> None:
    r_a = elo.get(team_a, 1500.0)
    r_b = elo.get(team_b, 1500.0)
    e_a = expected_score(r_a, r_b)
    e_b = 1.0 - e_a
    if score_a > score_b:
        s_a, s_b = 1.0, 0.0
    elif score_a < score_b:
        s_a, s_b = 0.0, 1.0
    else:
        s_a, s_b = 0.5, 0.5
    mult = goal_diff_multiplier(score_a - score_b)
    elo[team_a] = r_a + k * mult * (s_a - e_a)
    elo[team_b] = r_b + k * mult * (s_b - e_b)


def recalculate_elo_with_real(base_elo: dict[str, float], real_results: dict | None) -> dict[str, float]:
    """Toma los Elos base y aplica actualizaciones secuenciales por cada partido jugado.

    Procesa los partidos en orden cronológico (usando el calendario real del Mundial)
    seguido de las eliminatorias por ronda. K = 50 (Mundial).
    """
    if not real_results:
        return base_elo.copy()

    elo = base_elo.copy()

    # 1. Partidos de grupos en orden cronológico real
    group_matches = real_results.get("group_matches", {})
    sortable: list[tuple[pd.Timestamp, str, str, int, int]] = []
    for match_key, scores in group_matches.items():
        if not scores or len(scores) < 2:
            continue
        parts = match_key.split(" vs ")
        if len(parts) != 2:
            continue
        team_a, team_b = parts[0], parts[1]
        sortable.append((_group_match_date(team_a, team_b), team_a, team_b,
                         int(scores[0]), int(scores[1])))
    sortable.sort(key=lambda x: x[0])
    for _, ta, tb, sa, sb in sortable:
        _apply_match(elo, ta, tb, sa, sb, K_WORLD_CUP)

    # 2. Partidos de eliminatorias en orden de ronda
    knockout_matches = real_results.get("knockout_matches", {})
    for round_key in ("r32", "r16", "qf", "sf", "final"):
        round_data = knockout_matches.get(round_key, {})
        for match_id in sorted(round_data.keys(),
                                key=lambda x: int(x) if str(x).isdigit() else 9999):
            match_info = round_data[match_id]
            if not match_info or "home" not in match_info or "away" not in match_info:
                continue
            _apply_match(elo, match_info["home"], match_info["away"],
                         int(match_info.get("home_score", 0)),
                         int(match_info.get("away_score", 0)),
                         K_WORLD_CUP)

    return elo
