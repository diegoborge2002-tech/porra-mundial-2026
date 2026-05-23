"""Diagnósticos por partido jugado: predicción modelo vs resultado real.

Para cada partido del Mundial ya jugado:
- Elo de cada equipo PRE-partido (walk-forward respetando el orden cronológico)
- Probabilidades 1X2 según el modelo
- Goles esperados (xG estilo simple) por equipo
- Resultado real y outcome (H/D/A)
- Surprise score = 1 - p(outcome real)
- Brier / log-loss / RPS de ese partido
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd

from src.model.elo import (
    expected_score, goal_diff_multiplier, win_draw_loss_probs,
)
from src.model.elo_dynamic import _wc_match_dates, K_WORLD_CUP
from src.model.poisson import elo_to_expected_goals
from src.model.calibration import outcome_from_score, brier_multi, log_loss, rps
from src.tournament.groups import GROUPS, HOST_NATIONS


HOST_ADVANTAGE_ELO = 65.0  # mismo valor que HOME_ADVANTAGE en elo.py


@dataclass
class MatchDiagnostic:
    phase: str            # 'Grupos', 'R32', 'R16', 'QF', 'SF', 'Final'
    match_id: str         # 'Grupo A: España vs Uruguay' o 'R32 #73'
    date: str             # 'YYYY-MM-DD' o ''
    home: str
    away: str
    home_score: int
    away_score: int
    outcome: str          # 'H' / 'D' / 'A'
    elo_home_pre: float
    elo_away_pre: float
    p_home: float
    p_draw: float
    p_away: float
    xg_home: float
    xg_away: float
    surprise: float
    brier: float
    log_loss: float
    rps: float


def _split_match_key(key: str) -> tuple[str, str]:
    parts = key.split(" vs ")
    return parts[0], parts[1]


def _apply_match_inplace(elo: dict[str, float], home: str, away: str,
                         hg: int, ag: int, home_advantage: float = 0.0) -> None:
    r_h = elo.get(home, 1500.0)
    r_a = elo.get(away, 1500.0)
    e_h = expected_score(r_h, r_a, home_advantage)
    e_a = 1.0 - e_h
    if hg > ag: s_h, s_a = 1.0, 0.0
    elif hg < ag: s_h, s_a = 0.0, 1.0
    else: s_h, s_a = 0.5, 0.5
    mult = goal_diff_multiplier(hg - ag)
    elo[home] = r_h + K_WORLD_CUP * mult * (s_h - e_h)
    elo[away] = r_a + K_WORLD_CUP * mult * (s_a - e_a)


def _group_of(team: str) -> str | None:
    for g, teams in GROUPS.items():
        if team in teams:
            return g
    return None


def compute_match_diagnostics(
    base_elo: dict[str, float],
    real_results: dict | None,
) -> list[MatchDiagnostic]:
    """Walk-forward sobre los partidos jugados, devolviendo diagnósticos por partido."""
    if not real_results:
        return []
    elo = base_elo.copy()
    diagnostics: list[MatchDiagnostic] = []

    # 1. Grupos en orden cronológico
    dates_lookup = _wc_match_dates()
    group_matches = real_results.get("group_matches", {})
    sortable = []
    for key, scores in group_matches.items():
        if not scores or len(scores) < 2:
            continue
        h, a = _split_match_key(key)
        date = dates_lookup.get(frozenset({h, a}))
        sortable.append((date or pd.Timestamp("2026-06-01"), key, h, a, int(scores[0]), int(scores[1])))
    sortable.sort(key=lambda x: x[0])

    for date, key, h, a, gh, ga in sortable:
        # Ventaja de anfitrión (mismo criterio que group_sim)
        h_host = h in HOST_NATIONS
        a_host = a in HOST_NATIONS
        ha = HOST_ADVANTAGE_ELO if (h_host and not a_host) else (-HOST_ADVANTAGE_ELO if a_host and not h_host else 0.0)

        r_h = elo.get(h, 1500.0)
        r_a = elo.get(a, 1500.0)
        p_h, p_d, p_aw = win_draw_loss_probs(r_h, r_a, home_advantage=ha)
        xg_h, xg_a = elo_to_expected_goals(r_h, r_a, home_advantage=ha)
        outcome = outcome_from_score(gh, ga)
        probs = (p_h, p_d, p_aw)
        p_outcome = {"H": p_h, "D": p_d, "A": p_aw}[outcome]
        surprise = 1.0 - p_outcome

        g_letter = _group_of(h) or "?"
        diagnostics.append(MatchDiagnostic(
            phase=f"Grupo {g_letter}",
            match_id=key,
            date=date.strftime("%Y-%m-%d") if date is not None else "",
            home=h, away=a, home_score=gh, away_score=ga,
            outcome=outcome,
            elo_home_pre=r_h, elo_away_pre=r_a,
            p_home=p_h, p_draw=p_d, p_away=p_aw,
            xg_home=xg_h, xg_away=xg_a,
            surprise=surprise,
            brier=brier_multi(probs, outcome),
            log_loss=log_loss(probs, outcome),
            rps=rps(probs, outcome),
        ))
        # Update elo
        _apply_match_inplace(elo, h, a, gh, ga, home_advantage=ha)

    # 2. Eliminatorias en orden de ronda
    knockout_matches = real_results.get("knockout_matches", {})
    phase_label = {"r32": "R32", "r16": "R16", "qf": "Cuartos", "sf": "Semis", "final": "Final"}
    for round_key in ("r32", "r16", "qf", "sf", "final"):
        round_data = knockout_matches.get(round_key, {})
        for match_id in sorted(round_data.keys(),
                                key=lambda x: int(x) if str(x).isdigit() else 9999):
            mi = round_data[match_id]
            if not mi or "home" not in mi or "away" not in mi:
                continue
            h = mi["home"]; a = mi["away"]
            gh = int(mi.get("home_score", 0)); ga = int(mi.get("away_score", 0))
            r_h = elo.get(h, 1500.0); r_a = elo.get(a, 1500.0)
            p_h, p_d, p_aw = win_draw_loss_probs(r_h, r_a, home_advantage=0.0)
            xg_h, xg_a = elo_to_expected_goals(r_h, r_a, home_advantage=0.0)
            # En eliminatoria, decidimos outcome final por marcador ó penaltis (winner)
            winner = mi.get("winner")
            if gh > ga:
                outcome = "H"
            elif gh < ga:
                outcome = "A"
            else:
                # Empate en regular -> ganador via penaltis. Asignamos H si gana home, A si visit.
                outcome = "H" if winner == h else "A"
            probs = (p_h, p_d, p_aw)
            p_outcome = {"H": p_h, "D": p_d, "A": p_aw}[outcome]
            surprise = 1.0 - p_outcome
            diagnostics.append(MatchDiagnostic(
                phase=phase_label[round_key],
                match_id=f"{phase_label[round_key]} #{match_id}",
                date="",
                home=h, away=a, home_score=gh, away_score=ga,
                outcome=outcome,
                elo_home_pre=r_h, elo_away_pre=r_a,
                p_home=p_h, p_draw=p_d, p_away=p_aw,
                xg_home=xg_h, xg_away=xg_a,
                surprise=surprise,
                brier=brier_multi(probs, outcome),
                log_loss=log_loss(probs, outcome),
                rps=rps(probs, outcome),
            ))
            _apply_match_inplace(elo, h, a, gh, ga, home_advantage=0.0)

    return diagnostics


def diagnostics_to_dataframe(diagnostics: list[MatchDiagnostic]) -> pd.DataFrame:
    if not diagnostics:
        return pd.DataFrame()
    return pd.DataFrame([asdict(d) for d in diagnostics])
