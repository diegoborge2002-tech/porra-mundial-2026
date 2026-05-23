"""Información de sedes del Mundial 2026 y utilidades de descanso entre partidos."""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import pandas as pd

from src.data.team_names import EN_TO_ES, ES_TO_EN

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"


# Altitud (metros sobre el nivel del mar) por ciudad sede del Mundial 2026.
# Aproximada a partir de fuentes públicas. La altitud puede impactar el rendimiento
# en aerobios; Ciudad de México y Guadalajara son las más altas.
VENUE_ALTITUDE: dict[str, int] = {
    "Mexico City": 2240,
    "Guadalajara": 1566,
    "Zapopan": 1566,
    "Monterrey": 540,
    "Atlanta": 320,
    "Boston": 43,
    "Dallas": 131,
    "Houston": 13,
    "Kansas City": 277,
    "Los Angeles": 93,
    "Miami": 2,
    "New York City": 10,
    "Philadelphia": 12,
    "San Francisco Bay Area": 5,
    "Santa Clara": 5,
    "Seattle": 53,
    "Toronto": 76,
    "Vancouver": 0,
    "East Rutherford": 12,
    "Inglewood": 35,
    "Foxborough": 60,
    "Arlington": 165,
    "Cincinnati": 150,
}

VENUE_COUNTRY: dict[str, str] = {
    "Mexico City": "México",
    "Guadalajara": "México",
    "Zapopan": "México",
    "Monterrey": "México",
    "Toronto": "Canadá",
    "Vancouver": "Canadá",
    # Resto: USA
}


# Coordenadas aproximadas (lat, lon) por sede del Mundial 2026.
VENUE_COORDS: dict[str, tuple[float, float]] = {
    "Mexico City": (19.3030, -99.1503),    # Estadio Azteca
    "Guadalajara": (20.6817, -103.4633),
    "Zapopan": (20.6810, -103.4630),       # Estadio Akron
    "Monterrey": (25.6694, -100.2444),     # Estadio BBVA
    "Atlanta": (33.7553, -84.4006),        # Mercedes-Benz Stadium
    "Boston": (42.3601, -71.0589),         # Foxborough next
    "Foxborough": (42.0909, -71.2643),     # Gillette
    "Dallas": (32.7767, -96.7970),
    "Arlington": (32.7479, -97.0935),      # AT&T Stadium
    "Houston": (29.6847, -95.4107),        # NRG Stadium
    "Kansas City": (39.0489, -94.4839),    # Arrowhead
    "Los Angeles": (34.0522, -118.2437),
    "Inglewood": (33.9534, -118.3387),     # SoFi
    "Miami": (25.9580, -80.2389),          # Hard Rock
    "New York City": (40.7128, -74.0060),
    "East Rutherford": (40.8136, -74.0746),  # MetLife
    "Philadelphia": (39.9008, -75.1675),
    "San Francisco Bay Area": (37.4030, -121.9700),
    "Santa Clara": (37.4030, -121.9700),    # Levi's
    "Seattle": (47.5952, -122.3316),        # Lumen Field
    "Toronto": (43.6532, -79.3832),
    "Vancouver": (49.2767, -123.1119),      # BC Place
    "Cincinnati": (39.1031, -84.5120),
}


@dataclass
class TeamSchedule:
    team: str
    matches: list[dict]   # {date, opponent, city, country, played, rest_days_prev, altitude}
    avg_rest: float
    min_rest: int | None
    cities_visited: list[str]


@lru_cache(maxsize=1)
def _wc_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df[df["date"] >= "2026-06-01"].copy()


def get_team_schedule(team_es: str) -> TeamSchedule:
    team_en = ES_TO_EN.get(team_es, team_es)
    df = _wc_results()
    mask = (df["home_team"] == team_en) | (df["away_team"] == team_en)
    team_df = df[mask].sort_values("date").reset_index(drop=True)

    matches = []
    rest_days = []
    prev_date = None
    cities: list[str] = []
    for _, row in team_df.iterrows():
        opponent_en = row["away_team"] if row["home_team"] == team_en else row["home_team"]
        opponent = EN_TO_ES.get(opponent_en, opponent_en)
        city = row.get("city")
        if pd.isna(city):
            city = ""
        else:
            cities.append(str(city))
        played = pd.notna(row["home_score"])
        rest = (row["date"] - prev_date).days if prev_date is not None else None
        if rest is not None:
            rest_days.append(rest)
        matches.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "opponent": opponent,
            "city": city,
            "country": row.get("country", ""),
            "played": played,
            "home_score": int(row["home_score"]) if played else None,
            "away_score": int(row["away_score"]) if played else None,
            "rest_days_prev": rest,
            "altitude": VENUE_ALTITUDE.get(str(city), 0),
            "is_home": row["home_team"] == team_en,
        })
        prev_date = row["date"]

    avg_rest = sum(rest_days) / len(rest_days) if rest_days else 0.0
    min_rest = min(rest_days) if rest_days else None
    return TeamSchedule(
        team=team_es, matches=matches,
        avg_rest=avg_rest, min_rest=min_rest,
        cities_visited=cities,
    )
