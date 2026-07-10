"""Detección de partidos próximos y cálculo de impacto en la porra."""
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import pandas as pd

from src.data.team_names import EN_TO_ES
from src.data.venues import VENUE_ALTITUDE
from src.tournament.groups import GROUPS, HOST_NATIONS
from src.model.elo import HOME_ADVANTAGE
from src.model.poisson import expected_goals_ensemble
from src.model.match_probs import top_exact_scores, match_outcome_probs

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"
REAL_RESULTS = ROOT / "data" / "processed" / "real_results.json"


@dataclass
class UpcomingMatch:
    date: pd.Timestamp
    home: str       # español
    away: str       # español
    city: str
    altitude: int
    group: str      # 'A'.. o 'KO'
    is_played: bool
    home_score: int | None
    away_score: int | None
    lambda_home: float
    lambda_away: float
    p_home: float
    p_draw: float
    p_away: float
    top_scores: list[tuple[tuple[int, int], float]]


KICKOFF_TIMES = ROOT / "data" / "processed" / "kickoff_times.json"


@lru_cache(maxsize=1)
def _kickoff_overrides() -> dict[str, str]:
    """Horas de inicio en hora ESPAÑOLA (Europe/Madrid, ISO naive).

    Clave: 'Local vs Visitante' en español. El CSV solo trae fecha; esto le
    pone la hora real. Lo rellena la rutina diaria escribiendo este JSON.
    """
    if KICKOFF_TIMES.exists():
        try:
            return json.loads(KICKOFF_TIMES.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


@lru_cache(maxsize=1)
def _wc_schedule() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= "2026-06-01"].copy().reset_index(drop=True)
    ko = _kickoff_overrides()
    if ko:
        def _with_time(row):
            h = EN_TO_ES.get(row["home_team"], row["home_team"])
            a = EN_TO_ES.get(row["away_team"], row["away_team"])
            iso = ko.get(f"{h} vs {a}")
            return pd.to_datetime(iso) if iso else row["date"]
        df["date"] = df.apply(_with_time, axis=1)
    return df


def _team_group(team_es: str) -> str:
    for g, teams in GROUPS.items():
        if team_es in teams:
            return g
    return "?"


def _host_advantage(team_h_es: str, team_a_es: str) -> float:
    h = team_h_es in HOST_NATIONS
    a = team_a_es in HOST_NATIONS
    if h and not a: return HOME_ADVANTAGE
    if a and not h: return -HOME_ADVANTAGE
    return 0.0


def _build_upcoming(row, elo: dict[str, float], use_host: bool = True) -> UpcomingMatch:
    home_es = EN_TO_ES.get(row["home_team"], row["home_team"])
    away_es = EN_TO_ES.get(row["away_team"], row["away_team"])
    city = row.get("city")
    if pd.isna(city): city = ""
    altitude = VENUE_ALTITUDE.get(str(city), 0)
    is_played = pd.notna(row["home_score"])
    elo_h = elo.get(home_es, 1500.0)
    elo_a = elo.get(away_es, 1500.0)
    ha = _host_advantage(home_es, away_es) if use_host and not row.get("neutral", True) else 0.0
    lh, la = expected_goals_ensemble(elo_h, elo_a, home_es, away_es, home_advantage=ha)
    p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
    top = top_exact_scores(lh, la, n=5, use_dc=True)
    g_letter = _team_group(home_es)
    return UpcomingMatch(
        date=row["date"], home=home_es, away=away_es,
        city=str(city), altitude=altitude, group=g_letter,
        is_played=is_played,
        home_score=int(row["home_score"]) if is_played else None,
        away_score=int(row["away_score"]) if is_played else None,
        lambda_home=lh, lambda_away=la,
        p_home=p_h, p_draw=p_d, p_away=p_a,
        top_scores=top,
    )


def _played_pairs() -> set[frozenset]:
    """Pares {local, visitante} (en español) ya registrados en real_results.json.

    Los resultados se guardan ahí, NO en results.csv, así que el `home_score`
    del calendario sigue vacío aunque el partido se haya jugado. Sin esto, un
    partido recién registrado aparece como "próximo" (su hora de inicio cae
    dentro de la ventana). No se cachea: cambia al registrar cada resultado.
    """
    pairs: set[frozenset] = set()
    if not REAL_RESULTS.exists():
        return pairs
    try:
        data = json.loads(REAL_RESULTS.read_text(encoding="utf-8"))
    except Exception:
        return pairs
    for key, score in (data.get("group_matches") or {}).items():
        if score and " vs " in key:
            h, a = key.split(" vs ", 1)
            pairs.add(frozenset((h, a)))
    for rnd in (data.get("knockout_matches") or {}).values():
        for m in (rnd or {}).values():
            if isinstance(m, dict) and m.get("home") and m.get("away"):
                pairs.add(frozenset((m["home"], m["away"])))
    return pairs


def _dynamic_knockout_matches(elo: dict[str, float]) -> list[UpcomingMatch]:
    """Partidos KO ya resueltos por el cuadro, con horario y pronóstico únicos.

    El CSV oficial contiene plazas genéricas (W95, W96...) hasta que se conoce el
    cruce. Esta capa los sustituye por equipos reales para que portada,
    Selecciones y Actualidad no discrepen durante las eliminatorias.
    """
    if not REAL_RESULTS.exists():
        return []
    try:
        real = json.loads(REAL_RESULTS.read_text(encoding="utf-8"))
        from src.data.bracket_view import build_bracket
        bracket = build_bracket(real, elo)
    except Exception:
        return []
    if not bracket:
        return []

    kickoffs = _kickoff_overrides()
    out: list[UpcomingMatch] = []
    for match in bracket["matches"].values():
        home, away = match.get("home"), match.get("away")
        if not (match.get("expected") and home and away):
            continue
        when = kickoffs.get(f"{home} vs {away}")
        if not when:
            continue
        exp = match["expected"]
        lh, la = exp["xg_home"], exp["xg_away"]
        out.append(UpcomingMatch(
            date=pd.Timestamp(when), home=home, away=away, city="",
            altitude=0, group="KO", is_played=False, home_score=None,
            away_score=None, lambda_home=lh, lambda_away=la,
            p_home=exp["p_home"], p_draw=exp["p_draw"], p_away=exp["p_away"],
            top_scores=top_exact_scores(lh, la, n=5, use_dc=True),
        ))
    return out


def find_upcoming_matches(
    elo: dict[str, float],
    now: datetime | None = None,
    window_hours: int = 36,
    fallback_days: int = 7,
) -> list[UpcomingMatch]:
    """Devuelve los partidos no jugados que arrancan en las próximas window_hours.

    Si no hay ningún partido en esa ventana, amplía a fallback_days para no
    devolver lista vacía cuando el Mundial está parado (días sin fixtures).
    """
    now = now or datetime.now()
    df = _wc_schedule()
    pending = df[df["home_score"].isna()].copy()
    # Excluir los ya registrados en real_results.json (el CSV no los conoce)
    played = _played_pairs()
    if played and not pending.empty:
        pending = pending[~pending.apply(
            lambda r: frozenset((
                EN_TO_ES.get(r["home_team"], r["home_team"]),
                EN_TO_ES.get(r["away_team"], r["away_team"]),
            )) in played, axis=1)]
    scheduled = [] if pending.empty else [_build_upcoming(row, elo) for _, row in pending.iterrows()]
    # Los KO dinámicos tienen prioridad sobre los placeholders del CSV oficial.
    dynamic = _dynamic_knockout_matches(elo)
    known_pairs = {frozenset((m.home, m.away)) for m in dynamic}
    candidates = [m for m in scheduled if frozenset((m.home, m.away)) not in known_pairs] + dynamic
    if not candidates:
        return []
    candidates.sort(key=lambda m: m.date)
    timed = [(m, (m.date - pd.Timestamp(now)).total_seconds()) for m in candidates]
    # Solo futuros y dentro de ventana
    in_window = [m for m, secs in timed if -3600 * 3 <= secs <= window_hours * 3600]
    if not in_window:
        # Fallback: el siguiente partido por jugar
        in_window = [m for m, secs in timed if 0 <= secs <= fallback_days * 86400][:3]
    return in_window


def find_recently_played(
    elo: dict[str, float],
    real_results: dict | None,
    window_hours: int = 36,
    now: datetime | None = None,
) -> list[UpcomingMatch]:
    """Partidos cuyo kickoff fue en las últimas 36h y que tienen resultado real."""
    if not real_results:
        return []
    now = now or datetime.now()
    df = _wc_schedule()
    cutoff = pd.Timestamp(now) - pd.Timedelta(hours=window_hours)
    candidates = df[(df["date"] >= cutoff) & (df["date"] <= pd.Timestamp(now))]
    out = []
    group_real = real_results.get("group_matches", {})
    for _, row in candidates.iterrows():
        h_es = EN_TO_ES.get(row["home_team"], row["home_team"])
        a_es = EN_TO_ES.get(row["away_team"], row["away_team"])
        key1 = f"{h_es} vs {a_es}"; key2 = f"{a_es} vs {h_es}"
        if key1 in group_real or key2 in group_real:
            # Sí jugado; sintetizar fila como jugada
            row = row.copy()
            scores = group_real.get(key1) or group_real.get(key2)
            if scores:
                if key1 in group_real:
                    row["home_score"], row["away_score"] = scores
                else:
                    row["home_score"], row["away_score"] = scores[1], scores[0]
            out.append(_build_upcoming(row, elo))
    return out


def days_to_next_match(now: datetime | None = None) -> int:
    """Días hasta el siguiente partido pendiente."""
    now = now or datetime.now()
    # Reutiliza la misma fuente unificada que el resto de la aplicación.
    from app.utils import get_elo_with_biases
    upcoming = find_upcoming_matches(get_elo_with_biases(), now=now,
                                     window_hours=24 * 21, fallback_days=21)
    if not upcoming:
        return 999
    next_match = min(m.date for m in upcoming)
    return max(0, (next_match - pd.Timestamp(now)).days)


def time_to_kickoff(date: pd.Timestamp, now: datetime | None = None) -> dict:
    """Tiempo restante hasta el partido en una tupla legible (d, h, m)."""
    now = now or datetime.now()
    delta = date - pd.Timestamp(now)
    total_s = int(delta.total_seconds())
    return {
        "negative": total_s < 0,
        "days": abs(total_s) // 86400,
        "hours": (abs(total_s) % 86400) // 3600,
        "minutes": (abs(total_s) % 3600) // 60,
        "total_seconds": total_s,
    }
