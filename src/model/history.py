"""Historial de snapshots de la simulación tras cada cambio de resultado real.

Cada vez que el usuario guarda resultados nuevos, registramos:
- timestamp
- número de partidos jugados hasta el momento
- probabilidades de campeón por equipo (top 10)
- entropía
- top-1 pick (campeón más probable)

Sirve para dibujar cómo evolucionan las probabilidades durante el Mundial.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_PATH = ROOT / "data" / "processed" / "history.json"

MAX_TEAMS_TRACKED = 12  # top-12 campeones siempre


def _count_played(real_results: dict | None) -> int:
    if not real_results:
        return 0
    n = len(real_results.get("group_matches", {}))
    for r in ("r32", "r16", "qf", "sf", "final"):
        n += len(real_results.get("knockout_matches", {}).get(r, {}))
    return n


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_snapshot(
    real_results: dict | None,
    champion_probs: dict[str, float],
    entropy_bits: float,
) -> None:
    history = load_history()
    top = sorted(champion_probs.items(), key=lambda x: -x[1])[:MAX_TEAMS_TRACKED]
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "matches_played": _count_played(real_results),
        "entropy_bits": entropy_bits,
        "top_pick": top[0][0] if top else None,
        "top_pick_prob": top[0][1] if top else 0.0,
        "top_probs": {t: p for t, p in top},
    }
    # Si ya hay un snapshot con el mismo matches_played y mismo top, no duplicar.
    if history and history[-1]["matches_played"] == snapshot["matches_played"]:
        history[-1] = snapshot
    else:
        history.append(snapshot)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def clear_history() -> None:
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()
