"""Historial Head-to-Head entre dos selecciones."""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.data.team_names import EN_TO_ES, ES_TO_EN

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"


@dataclass
class H2HMatch:
    date: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    tournament: str
    result_for_a: str  # 'W', 'D', 'L' desde la perspectiva de team_a


@dataclass
class H2HSummary:
    team_a: str
    team_b: str
    total: int
    wins_a: int
    draws: int
    wins_b: int
    goals_a: int
    goals_b: int
    last_matches: list[H2HMatch] = field(default_factory=list)
    first_match_date: str = ""
    last_match_date: str = ""


@lru_cache(maxsize=1)
def _all_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["home_score", "away_score"])
    return df


def get_h2h(team_a_es: str, team_b_es: str, max_recent: int = 10) -> H2HSummary:
    a_en = ES_TO_EN.get(team_a_es, team_a_es)
    b_en = ES_TO_EN.get(team_b_es, team_b_es)
    df = _all_results()
    mask = (
        ((df["home_team"] == a_en) & (df["away_team"] == b_en)) |
        ((df["home_team"] == b_en) & (df["away_team"] == a_en))
    )
    h2h = df[mask].sort_values("date", ascending=False)

    wins_a = draws = wins_b = goals_a = goals_b = 0
    matches: list[H2HMatch] = []
    for _, row in h2h.iterrows():
        hg, ag = int(row["home_score"]), int(row["away_score"])
        a_is_home = row["home_team"] == a_en
        if a_is_home:
            a_g, b_g = hg, ag
        else:
            a_g, b_g = ag, hg
        goals_a += a_g; goals_b += b_g
        if a_g > b_g:
            wins_a += 1; result_a = "W"
        elif a_g < b_g:
            wins_b += 1; result_a = "L"
        else:
            draws += 1; result_a = "D"
        matches.append(H2HMatch(
            date=row["date"].strftime("%Y-%m-%d"),
            home=EN_TO_ES.get(row["home_team"], row["home_team"]),
            away=EN_TO_ES.get(row["away_team"], row["away_team"]),
            home_goals=hg, away_goals=ag,
            tournament=row["tournament"],
            result_for_a=result_a,
        ))
    return H2HSummary(
        team_a=team_a_es, team_b=team_b_es,
        total=len(h2h), wins_a=wins_a, draws=draws, wins_b=wins_b,
        goals_a=goals_a, goals_b=goals_b,
        last_matches=matches[:max_recent],
        first_match_date=h2h["date"].min().strftime("%Y-%m-%d") if not h2h.empty else "",
        last_match_date=h2h["date"].max().strftime("%Y-%m-%d") if not h2h.empty else "",
    )
