"""Caché en disco del Monte Carlo: lo saca del runtime de la web.

El MC de 10.000 torneos es caro (~5 s) y solo cambia cuando cambian los
resultados o la configuración. La rutina diaria lo precalcula con
`scripts/warm_mc.py` y lo guarda aquí; la web lo carga al instante para la
configuración por defecto (lo que ve casi todo el mundo). Si el usuario toca
'Mis ajustes', la clave cambia y se recalcula en vivo (y se cachea también).

La clave usa los Elo redondeados a 2 decimales para que el hash sea estable
entre la máquina que precalcula y el servidor (evita fallos por epsilon de
coma flotante). 2 decimales de Elo no cambian las probabilidades de forma
perceptible.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MC_DISK_DIR = ROOT / "data" / "processed" / "mc_cache"


def summary_to_dict(summary) -> dict:
    """Serializa un TournamentSummary al dict que consume la web."""
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


def disk_key(elo_frozen, n_sims: int, seed: int,
             real_str: str, porra_str: str, stats_weight: float) -> str:
    rounded = [[t, round(float(e), 2)] for t, e in elo_frozen]
    payload = json.dumps([rounded, n_sims, seed, real_str, porra_str, round(float(stats_weight), 4)],
                         sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def load_cached(key: str) -> dict | None:
    f = MC_DISK_DIR / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_cached(key: str, result: dict) -> None:
    try:
        MC_DISK_DIR.mkdir(parents=True, exist_ok=True)
        (MC_DISK_DIR / f"{key}.json").write_text(json.dumps(result), encoding="utf-8")
    except Exception:
        pass
