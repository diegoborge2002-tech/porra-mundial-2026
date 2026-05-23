"""Backtest del modelo Elo sobre partidos históricos.

Para cada torneo del backtest:
1. Entrena Elo con todos los partidos anteriores al kickoff del torneo.
2. Para cada partido del torneo, predice probabilidades 1X2 a partir del Elo.
3. Acumula métricas (Brier, log-loss, RPS, hit-rate, reliability) sobre todos
   los partidos del torneo.

El Elo se va actualizando dinámicamente partido a partido dentro del torneo
para emular cómo se hubiera ido afinando el modelo si tuviéramos las predicciones
en tiempo real (walk-forward).
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd

from src.model.elo import (
    train_elo, expected_score, goal_diff_multiplier,
    win_draw_loss_probs, TOURNAMENT_K, DEFAULT_K, HOME_ADVANTAGE,
)
from src.model.calibration import (
    aggregate_metrics, reliability_bins, outcome_from_score, CalibrationStats,
)


ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"
BACKTEST_JSON = ROOT / "data" / "processed" / "backtest_summary.json"


# Torneos a backtestear. (name, tournament_string, year_start)
DEFAULT_TOURNAMENTS = [
    ("Mundial 2010", "FIFA World Cup", 2010),
    ("Mundial 2014", "FIFA World Cup", 2014),
    ("Eurocopa 2016", "UEFA Euro", 2016),
    ("Mundial 2018", "FIFA World Cup", 2018),
    ("Eurocopa 2020", "UEFA Euro", 2020),
    ("Mundial 2022", "FIFA World Cup", 2022),
    ("Eurocopa 2024", "UEFA Euro", 2024),
]


@dataclass
class BacktestTournament:
    name: str
    n_matches: int
    brier: float
    log_loss: float
    rps: float
    hit_rate_top1: float
    accuracy_by_confidence: dict[str, tuple[int, float]]
    reliability: list[dict]


def _predict_and_update_one(elo: dict[str, float], home: str, away: str,
                            hg: int, ag: int, tournament: str, neutral: bool,
                            decay_k: float = 1.0) -> tuple[float, float, float]:
    """Predice probabilidades 1X2 y luego actualiza los Elos con el resultado real.

    Returns: (p_home, p_draw, p_away) basados en el Elo PRE-partido.
    """
    r_h = elo.get(home, 1500.0)
    r_a = elo.get(away, 1500.0)
    ha = 0.0 if neutral else HOME_ADVANTAGE
    p_h, p_d, p_a = win_draw_loss_probs(r_h, r_a, home_advantage=ha)
    # Update Elo
    e_h = expected_score(r_h, r_a, ha)
    e_a = 1.0 - e_h
    if hg > ag: s_h, s_a = 1.0, 0.0
    elif hg < ag: s_h, s_a = 0.0, 1.0
    else: s_h, s_a = 0.5, 0.5
    k = TOURNAMENT_K.get(tournament, DEFAULT_K) * decay_k
    mult = goal_diff_multiplier(hg - ag)
    elo[home] = r_h + k * mult * (s_h - e_h)
    elo[away] = r_a + k * mult * (s_a - e_a)
    return p_h, p_d, p_a


def backtest_tournament(df: pd.DataFrame, name: str, tournament_str: str,
                        year_start: int, half_life: float = 8.0) -> BacktestTournament:
    """Backtestea un torneo concreto con la calibración temporal (half-life) configurada."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    tourn_mask = (df["tournament"] == tournament_str) & (df["date"].dt.year == year_start)
    tourn_df = df[tourn_mask].sort_values("date").reset_index(drop=True)
    if tourn_df.empty:
        # Algunos torneos cruzan año (Eurocopa 2020 jugada en 2021)
        tourn_mask = (df["tournament"] == tournament_str) & (
            (df["date"].dt.year == year_start) | (df["date"].dt.year == year_start + 1)
        )
        # Filtrar por fechas del torneo (mes 6-7 típicamente)
        tourn_df = df[tourn_mask].copy()
        tourn_df = tourn_df[
            tourn_df["date"].dt.month.isin([5, 6, 7])
        ].sort_values("date").reset_index(drop=True)

    if tourn_df.empty:
        return BacktestTournament(name, 0, 0, 0, 0, 0, {}, [])

    tourn_start = tourn_df["date"].min()
    # Entrenar con todo lo PREVIO al kickoff
    train_df = df[df["date"] < tourn_start]
    elo = train_elo(train_df, decay_old_matches=True, half_life=half_life)

    # Predecir partido a partido y actualizar
    preds: list[tuple[tuple[float, float, float], str]] = []
    for _, row in tourn_df.iterrows():
        if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
            continue
        home, away = row["home_team"], row["away_team"]
        hg, ag = int(row["home_score"]), int(row["away_score"])
        neutral = bool(row.get("neutral", False))
        p = _predict_and_update_one(elo, home, away, hg, ag,
                                     row["tournament"], neutral)
        outcome = outcome_from_score(hg, ag)
        preds.append((p, outcome))

    stats = aggregate_metrics(preds)
    rel = reliability_bins(preds, n_bins=10)
    return BacktestTournament(
        name=name,
        n_matches=stats.n,
        brier=stats.mean_brier,
        log_loss=stats.mean_log_loss,
        rps=stats.mean_rps,
        hit_rate_top1=stats.hit_rate_top1,
        accuracy_by_confidence=stats.accuracy_by_confidence,
        reliability=rel,
    )


def run_full_backtest(tournaments: list[tuple[str, str, int]] = None, half_life: float = 8.0) -> dict:
    """Ejecuta backtest sobre todos los torneos con la vida media dada y genera el resumen."""
    if tournaments is None:
        tournaments = DEFAULT_TOURNAMENTS
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])

    results = []
    for name, t_str, year in tournaments:
        res = backtest_tournament(df, name, t_str, year, half_life=half_life)
        results.append(asdict(res))

    # Agregado global
    all_preds_n = sum(r["n_matches"] for r in results)
    overall = {
        "n_matches": all_preds_n,
        "weighted_brier": (
            sum(r["brier"] * r["n_matches"] for r in results) / all_preds_n
            if all_preds_n else 0
        ),
        "weighted_log_loss": (
            sum(r["log_loss"] * r["n_matches"] for r in results) / all_preds_n
            if all_preds_n else 0
        ),
        "weighted_rps": (
            sum(r["rps"] * r["n_matches"] for r in results) / all_preds_n
            if all_preds_n else 0
        ),
        "weighted_hit_rate": (
            sum(r["hit_rate_top1"] * r["n_matches"] for r in results) / all_preds_n
            if all_preds_n else 0
        ),
    }

    summary = {"tournaments": results, "overall": overall}
    # Solo persistir en el JSON por defecto si es el baseline estándar (8.0 años)
    if half_life == 8.0:
        BACKTEST_JSON.parent.mkdir(parents=True, exist_ok=True)
        BACKTEST_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def load_backtest_summary() -> dict | None:
    if not BACKTEST_JSON.exists():
        return None
    try:
        return json.loads(BACKTEST_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    print("Lanzando backtest sobre todos los torneos…")
    summary = run_full_backtest()
    for t in summary["tournaments"]:
        print(f"  {t['name']:18s} | n={t['n_matches']:3d} | "
              f"Brier={t['brier']:.3f} | RPS={t['rps']:.3f} | "
              f"hit={t['hit_rate_top1']*100:.1f}%")
    o = summary["overall"]
    print(f"\nGlobal: n={o['n_matches']} | Brier={o['weighted_brier']:.3f} | "
          f"RPS={o['weighted_rps']:.3f} | hit={o['weighted_hit_rate']*100:.1f}%")
