"""Utilidades compartidas por las pestanas de la web app."""
from __future__ import annotations
import sys
import json
import hashlib
from pathlib import Path

# Permite importar src.* desde la app
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.data.team_names import EN_TO_ES
from src.tournament.groups import ALL_TEAMS, GROUPS, HOST_NATIONS
from src.model.biases import BiasesConfig
from src.model.tournament_sim import run_monte_carlo, TournamentSummary
from src.model.elo_dynamic import recalculate_elo_with_real
from src.scoring.porra import Prediction


ELO_RATINGS_CSV = ROOT / "data" / "processed" / "elo_ratings.csv"
REAL_RESULTS_PATH = ROOT / "data" / "processed" / "real_results.json"
AMIGOS_DIR = ROOT / "data" / "processed" / "porras_amigos"
USER_PORRA_PATH = ROOT / "data" / "processed" / "porra_usuario.json"


def load_base_elo() -> dict[str, float]:
    """Carga los Elo entrenados usando el half-life definido en los ajustes."""
    cfg = get_biases()
    return load_base_elo_with_half_life(cfg.half_life)


@st.cache_data(show_spinner="Retrenando modelo Elo con nueva ponderación...")
def load_base_elo_with_half_life(half_life: float) -> dict[str, float]:
    """Entrena y devuelve los Elo base indexados por nombre en espanol, usando la vida media indicada."""
    results_path = ROOT / "data" / "raw" / "results.csv"
    if not results_path.exists():
        # Fallback si no existe results.csv (usar el CSV procesado por defecto)
        df = pd.read_csv(ELO_RATINGS_CSV)
        ratings_en = dict(zip(df["team_en"], df["elo"]))
        es_to_en = {v: k for k, v in EN_TO_ES.items()}
        return {t: ratings_en.get(es_to_en[t], 1500.0) for t in ALL_TEAMS}
        
    results = pd.read_csv(results_path)
    from src.model.elo import train_elo
    
    # Filtrar solo partidos reales hasta la actualidad del Mundial 2026
    results["date"] = pd.to_datetime(results["date"])
    today = pd.Timestamp("2026-05-21")
    train_set = results[results["date"] < today].copy()
    train_set = train_set.dropna(subset=["home_score", "away_score"])
    
    # Entrenar Elo en tiempo real usando el valor de vida media personalizado
    ratings = train_elo(train_set, decay_old_matches=True, half_life=half_life)
    
    es_to_en = {v: k for k, v in EN_TO_ES.items()}
    return {t: ratings.get(es_to_en.get(t, t), 1500.0) for t in ALL_TEAMS}


def load_real_results() -> dict:
    if REAL_RESULTS_PATH.exists():
        try:
            return json.loads(REAL_RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "group_matches": {},
        "knockout_matches": {
            "r32": {},
            "r16": {},
            "qf": {},
            "sf": {},
            "final": {}
        }
    }


def save_real_results(results: dict) -> None:
    REAL_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REAL_RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def _dict_to_prediction(d: dict) -> Prediction:
    return Prediction(
        groups=d.get("groups", {}),
        r16_teams=d.get("r16", []),
        qf_teams=d.get("qf", []),
        sf_teams=d.get("sf", []),
        finalists=d.get("final", []),
        champion=d.get("champion"),
        mvp_gold=d.get("mvp_gold"),
        mvp_silver=d.get("mvp_silver"),
        mvp_bronze=d.get("mvp_bronze"),
        top_scorer=d.get("top_scorer"),
        total_goals=d.get("total_goals"),
    )


def load_all_predictions(user_porra_dict: dict | None = None) -> dict[str, Prediction]:
    predictions: dict[str, Prediction] = {}

    if user_porra_dict:
        predictions["Tú"] = _dict_to_prediction(user_porra_dict)
    else:
        if USER_PORRA_PATH.exists():
            try:
                predictions["Tú"] = _dict_to_prediction(json.loads(USER_PORRA_PATH.read_text(encoding="utf-8")))
            except Exception:
                pass

    return predictions


def _amigos_fingerprint() -> str:
    """Simplificado para Porra Única de un jugador."""
    return "no-amigos"


@st.cache_data(show_spinner="Simulando 10.000 torneos…")
def run_simulation(
    elo_dict_frozen: tuple[tuple[str, float], ...],
    n_sims: int,
    seed: int,
    real_results_str: str = "",
    porra_str: str = "",
    amigos_fingerprint: str = "",  # part of cache key, no use inside
) -> dict:
    """Ejecuta Monte Carlo. Cacheado por elos+resultados+porra propia+huella amigos."""
    elo = dict(elo_dict_frozen)
    real_results = json.loads(real_results_str) if real_results_str else None
    user_porra = json.loads(porra_str) if porra_str else None
    predictions = load_all_predictions(user_porra)

    summary = run_monte_carlo(elo, n_sims=n_sims, seed=seed,
                              real_results=real_results, predictions=predictions)

    return {
        "n_sims": summary.n_sims,
        "champion": summary.champion_probs,
        "finalist": summary.finalist_probs,
        "semifinal": summary.semifinal_probs,
        "quarter": summary.quarter_probs,
        "r16": summary.r16_probs,
        "group_winner": summary.group_winner_probs,
        "group_top2": summary.group_top2_probs,
        "group_top3": summary.group_top3_probs,
        "third_place": summary.third_place_probs,
        "best_third": summary.qualified_as_best_third_probs,
        "expected_total_goals": summary.expected_total_goals,
        "total_goals_distribution": summary.total_goals_distribution,
        "expected_team_goals": summary.expected_team_goals,
        "pichichi": summary.pichichi_probs,
        "leaderboard": summary.leaderboard_probs,
        "leaderboard_expected_points": summary.leaderboard_expected_points,
        "champion_by_sim": summary.champion_by_sim,
        "points_by_sim": summary.points_by_sim,
        "final_position_by_team": summary.final_position_by_team,
        "opponent_probs_per_team": summary.opponent_probs_per_team,
    }


def run_simulation_with_real(elo: dict[str, float], n_sims: int = 10_000, seed: int = 42) -> dict:
    """Wrapper no cacheado que serializa real_results y porra del usuario para la cache."""
    real_results = load_real_results()
    real_results_str = json.dumps(real_results, sort_keys=True)

    porra_dict = None
    if "porra" in st.session_state:
        porra_dict = st.session_state.porra
    else:
        if USER_PORRA_PATH.exists():
            try:
                porra_dict = json.loads(USER_PORRA_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

    porra_str = json.dumps(porra_dict, sort_keys=True) if porra_dict else ""
    result = run_simulation(freeze_elo(elo), n_sims, seed, real_results_str, porra_str,
                            _amigos_fingerprint())
    # Snapshot diario de probabilidades (idempotente: 1/día)
    try:
        from src.data.snapshots import take_snapshot
        take_snapshot(result)
    except Exception:
        pass
    return result


def get_biases() -> BiasesConfig:
    """Lee los biases del session_state (o los carga del disco si no estan)."""
    if "biases" not in st.session_state:
        st.session_state.biases = BiasesConfig.load()
    
    # Robustez defensiva: asegurar que todos los nuevos campos existan en el objeto
    # (evita el AttributeError por objetos obsoletos en st.session_state durante recargas en vivo)
    b = st.session_state.biases
    if not hasattr(b, "half_life"):
        b.half_life = 8.0
    if not hasattr(b, "use_club_performance"):
        b.use_club_performance = False
    if not hasattr(b, "weight_market_value"):
        b.weight_market_value = 1.0
    if not hasattr(b, "weight_club_pedigree"):
        b.weight_club_pedigree = 1.0
        
    return b


@st.cache_data(show_spinner=False)
def _recalc_elo_cached(
    biased_elo_frozen: tuple[tuple[str, float], ...],
    real_results_str: str,
) -> tuple[tuple[str, float], ...]:
    """Cacheado: aplica resultados reales sobre Elo+sesgos."""
    biased = dict(biased_elo_frozen)
    real_results = json.loads(real_results_str) if real_results_str else None
    final = recalculate_elo_with_real(biased, real_results)
    return tuple(sorted(final.items()))


def get_elo_with_biases() -> dict[str, float]:
    """Carga Elo base, aplica sesgos (manuales + club + noticias) y actualiza con resultados reales."""
    base = load_base_elo()
    cfg = get_biases()
    biased_elo = cfg.apply_to(base)
    # Sumar deltas activos del newsfeed (lesiones, bajas, refuerzos…)
    try:
        from src.data.news import get_active_deltas
        for team, d in get_active_deltas().items():
            if team in biased_elo:
                biased_elo[team] += d
    except Exception:
        pass
    real_results = load_real_results()
    real_str = json.dumps(real_results, sort_keys=True)
    final_tuple = _recalc_elo_cached(freeze_elo(biased_elo), real_str)
    return dict(final_tuple)


def freeze_elo(elo: dict[str, float]) -> tuple[tuple[str, float], ...]:
    """Convierte dict a tuple ordenada para usar como clave de cache."""
    return tuple(sorted(elo.items()))


def fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"
