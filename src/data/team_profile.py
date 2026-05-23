"""Perfil enriquecido por seleccion.

Combina varias fuentes publicas gratis:
- Dataset historico Kaggle (resultados, goleadores)
- Codigos ISO de pais para banderas CDN (flagcdn.com)
- Calendario Mundial 2026 ya incluido en el dataset

Todo se cachea en disco para no machacar fuentes externas.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import lru_cache

import pandas as pd

from src.data.team_names import EN_TO_ES, ES_TO_EN


ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"
GOALSCORERS_CSV = ROOT / "data" / "raw" / "goalscorers.csv"
PROFILES_DIR = ROOT / "data" / "processed" / "team_profiles"


# Codigos ISO-2 para flagcdn.com. Mapping ES (nombre Excel) -> codigo
ISO_CODES: dict[str, str] = {
    "Mexico": "mx", "Sudafrica": "za", "Corea del Sur": "kr", "Rep. Checa": "cz",
    "Canada": "ca", "Bosnia Herz.": "ba", "Catar": "qa", "Suiza": "ch",
    "Brasil": "br", "Marruecos": "ma", "Haiti": "ht", "Escocia": "gb-sct",
    "Estados Unidos": "us", "Paraguay": "py", "Australia": "au", "Turquia": "tr",
    "Alemania": "de", "Curazao": "cw", "Costa Marfil": "ci", "Ecuador": "ec",
    "Paises Bajos": "nl", "Japon": "jp", "Suecia": "se", "Tunez": "tn",
    "Belgica": "be", "Egipto": "eg", "Iran": "ir", "Nueva Zelanda": "nz",
    "Espana": "es", "Cabo Verde": "cv", "Arabia Saudi": "sa", "Uruguay": "uy",
    "Francia": "fr", "Senegal": "sn", "Irak": "iq", "Noruega": "no",
    "Argentina": "ar", "Argelia": "dz", "Austria": "at", "Jordania": "jo",
    "Portugal": "pt", "R.D. Congo": "cd", "Uzbekistan": "uz", "Colombia": "co",
    "Inglaterra": "gb-eng", "Croacia": "hr", "Ghana": "gh", "Panama": "pa",
}

# Confederaciones (para mostrar en ficha)
CONFEDERATIONS: dict[str, str] = {
    "Mexico": "CONCACAF", "Sudafrica": "CAF", "Corea del Sur": "AFC", "Rep. Checa": "UEFA",
    "Canada": "CONCACAF", "Bosnia Herz.": "UEFA", "Catar": "AFC", "Suiza": "UEFA",
    "Brasil": "CONMEBOL", "Marruecos": "CAF", "Haiti": "CONCACAF", "Escocia": "UEFA",
    "Estados Unidos": "CONCACAF", "Paraguay": "CONMEBOL", "Australia": "AFC", "Turquia": "UEFA",
    "Alemania": "UEFA", "Curazao": "CONCACAF", "Costa Marfil": "CAF", "Ecuador": "CONMEBOL",
    "Paises Bajos": "UEFA", "Japon": "AFC", "Suecia": "UEFA", "Tunez": "CAF",
    "Belgica": "UEFA", "Egipto": "CAF", "Iran": "AFC", "Nueva Zelanda": "OFC",
    "Espana": "UEFA", "Cabo Verde": "CAF", "Arabia Saudi": "AFC", "Uruguay": "CONMEBOL",
    "Francia": "UEFA", "Senegal": "CAF", "Irak": "AFC", "Noruega": "UEFA",
    "Argentina": "CONMEBOL", "Argelia": "CAF", "Austria": "UEFA", "Jordania": "AFC",
    "Portugal": "UEFA", "R.D. Congo": "CAF", "Uzbekistan": "AFC", "Colombia": "CONMEBOL",
    "Inglaterra": "UEFA", "Croacia": "UEFA", "Ghana": "CAF", "Panama": "CONCACAF",
}

# Mundiales ganados (palmares)
WC_TITLES: dict[str, int] = {
    "Brasil": 5, "Alemania": 4, "Argentina": 3, "Italia": 4, "Francia": 2,
    "Uruguay": 2, "Inglaterra": 1, "Espana": 1,
}


@dataclass
class MatchResult:
    """Resultado de un partido."""
    date: str
    home: str  # nombre en espanol
    away: str
    home_goals: int | None
    away_goals: int | None
    tournament: str
    result: str  # 'W', 'D', 'L', '-' (no jugado)
    is_home: bool


@dataclass
class TeamProfile:
    """Perfil completo de una seleccion."""
    name_es: str
    name_en: str
    iso_code: str
    flag_url: str
    confederation: str
    wc_titles: int
    group: str
    elo_base: float
    last_10_matches: list[MatchResult] = field(default_factory=list)
    upcoming_wc_matches: list[MatchResult] = field(default_factory=list)
    form_streak: str = ""  # ej "WWLDW"
    goals_for_last10: int = 0
    goals_against_last10: int = 0


@lru_cache(maxsize=1)
def _load_results() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _to_es(team_en: str) -> str:
    return EN_TO_ES.get(team_en, team_en)


def _to_en(team_es: str) -> str:
    return ES_TO_EN.get(team_es, team_es)


def _result_label(team_is_home: bool, hg: float, ag: float) -> str:
    if pd.isna(hg) or pd.isna(ag): return "-"
    if hg == ag: return "D"
    if team_is_home:
        return "W" if hg > ag else "L"
    return "W" if ag > hg else "L"


def get_last_n_matches(team_es: str, n: int = 10,
                       up_to: pd.Timestamp | None = None) -> list[MatchResult]:
    """Devuelve los ultimos N partidos jugados del equipo (mas recientes primero)."""
    team_en = _to_en(team_es)
    df = _load_results()
    if up_to is None:
        up_to = pd.Timestamp.now()
    mask = ((df["home_team"] == team_en) | (df["away_team"] == team_en)) & \
           (df["date"] <= up_to) & df["home_score"].notna()
    recent = df[mask].sort_values("date", ascending=False).head(n)
    out = []
    for _, row in recent.iterrows():
        is_home = row["home_team"] == team_en
        out.append(MatchResult(
            date=row["date"].strftime("%Y-%m-%d"),
            home=_to_es(row["home_team"]),
            away=_to_es(row["away_team"]),
            home_goals=int(row["home_score"]),
            away_goals=int(row["away_score"]),
            tournament=row["tournament"],
            result=_result_label(is_home, row["home_score"], row["away_score"]),
            is_home=is_home,
        ))
    return out


def get_upcoming_wc_matches(team_es: str) -> list[MatchResult]:
    """Devuelve los partidos del Mundial 2026 del equipo aun no jugados."""
    team_en = _to_en(team_es)
    df = _load_results()
    today = pd.Timestamp.now()
    mask = ((df["home_team"] == team_en) | (df["away_team"] == team_en)) & \
           (df["date"] >= today) & (df["tournament"] == "FIFA World Cup")
    upcoming = df[mask].sort_values("date").head(10)
    out = []
    for _, row in upcoming.iterrows():
        is_home = row["home_team"] == team_en
        out.append(MatchResult(
            date=row["date"].strftime("%Y-%m-%d"),
            home=_to_es(row["home_team"]),
            away=_to_es(row["away_team"]),
            home_goals=None, away_goals=None,
            tournament=row["tournament"],
            result="-",
            is_home=is_home,
        ))
    return out


def build_profile(team_es: str, group: str, elo_base: float) -> TeamProfile:
    """Construye perfil completo combinando todas las fuentes."""
    iso = ISO_CODES.get(team_es, "un")
    flag_url = f"https://flagcdn.com/w160/{iso}.png"
    confed = CONFEDERATIONS.get(team_es, "?")
    titles = WC_TITLES.get(team_es, 0)
    last10 = get_last_n_matches(team_es, n=10)
    upcoming = get_upcoming_wc_matches(team_es)
    streak = "".join(m.result for m in reversed(last10))  # cronologico mas antiguo->reciente
    gf = sum(m.home_goals if m.is_home else m.away_goals for m in last10 if m.home_goals is not None)
    ga = sum(m.away_goals if m.is_home else m.home_goals for m in last10 if m.home_goals is not None)
    return TeamProfile(
        name_es=team_es,
        name_en=_to_en(team_es),
        iso_code=iso,
        flag_url=flag_url,
        confederation=confed,
        wc_titles=titles,
        group=group,
        elo_base=elo_base,
        last_10_matches=last10,
        upcoming_wc_matches=upcoming,
        form_streak=streak,
        goals_for_last10=gf,
        goals_against_last10=ga,
    )


def serialize_profile(p: TeamProfile) -> dict:
    d = asdict(p)
    return d


def save_all_profiles(profiles: dict[str, TeamProfile]) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for team, p in profiles.items():
        path = PROFILES_DIR / f"{team.replace('.', '').replace(' ', '_')}.json"
        path.write_text(json.dumps(serialize_profile(p), indent=2, ensure_ascii=False))


def build_all_profiles() -> dict[str, TeamProfile]:
    """Construye perfiles para los 48 equipos."""
    from src.tournament.groups import GROUPS
    ratings_df = pd.read_csv(ROOT / "data" / "processed" / "elo_ratings.csv")
    ratings_en = dict(zip(ratings_df["team_en"], ratings_df["elo"]))

    profiles = {}
    for letter, teams in GROUPS.items():
        for team_es in teams:
            elo = ratings_en.get(_to_en(team_es), 1500.0)
            profiles[team_es] = build_profile(team_es, letter, elo)
    return profiles


if __name__ == "__main__":
    print("Construyendo perfiles de los 48 equipos...")
    profiles = build_all_profiles()
    save_all_profiles(profiles)
    print(f"Guardados {len(profiles)} perfiles en {PROFILES_DIR}")
    # Muestra
    p = profiles["Espana"]
    print(f"\nEjemplo: {p.name_es}")
    print(f"  Bandera: {p.flag_url}")
    print(f"  Confederacion: {p.confederation}, Mundiales: {p.wc_titles}")
    print(f"  Forma ultimos 10: {p.form_streak} (GF: {p.goals_for_last10}, GA: {p.goals_against_last10})")
    print(f"  Proximos partidos Mundial:")
    for m in p.upcoming_wc_matches[:3]:
        print(f"    {m.date}: {m.home} vs {m.away}")
