"""Goleadores reales del Mundial 2026 + tracker de Pichichi en vivo."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
SCORERS_PATH = ROOT / "data" / "processed" / "scorers.json"


def load_scorers() -> dict:
    """Estructura: {"matches": {"match_key": [{"player","team","minute","penalty"}]}}"""
    if not SCORERS_PATH.exists():
        return {"matches": {}}
    try:
        return json.loads(SCORERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"matches": {}}


def save_scorers(data: dict) -> None:
    SCORERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORERS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def add_scorer(data: dict, match_key: str, player: str, team: str,
               minute: int, penalty: bool = False) -> None:
    matches = data.setdefault("matches", {})
    matches.setdefault(match_key, []).append({
        "player": player.strip(),
        "team": team,
        "minute": int(minute),
        "penalty": bool(penalty),
    })


def remove_scorer(data: dict, match_key: str, index: int) -> None:
    matches = data.get("matches", {})
    if match_key in matches and 0 <= index < len(matches[match_key]):
        matches[match_key].pop(index)


def pichichi_live(data: dict) -> list[tuple[str, str, int, int]]:
    """Devuelve [(player, team, goals, penalty_goals), ...] ordenado por goles desc."""
    goals: Counter = Counter()
    pens: Counter = Counter()
    teams: dict[str, str] = {}
    for match_key, scorers in data.get("matches", {}).items():
        for s in scorers:
            key = s["player"]
            goals[key] += 1
            if s.get("penalty"):
                pens[key] += 1
            teams[key] = s.get("team", "")
    out = []
    for player, g in goals.most_common():
        out.append((player, teams.get(player, ""), g, pens.get(player, 0)))
    return out


def total_goals_logged(data: dict) -> int:
    total = 0
    for scorers in data.get("matches", {}).values():
        total += len(scorers)
    return total
