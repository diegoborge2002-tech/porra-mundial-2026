"""Snapshots diarios de probabilidades del modelo.

Cada dia se guarda un JSON con los `champion_probs` y `finalist_probs` calculados.
Esto permite ver la evolucion longitudinal de la probabilidad de cada seleccion
a medida que va avanzando el torneo y se ajustan los biases.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import date, datetime


SNAP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "snapshots"


def take_snapshot(summary: dict, force: bool = False) -> Path | None:
    """Guarda un snapshot del dia actual si no existe ya (idempotente).

    Devuelve el path del archivo creado, o None si ya existia.
    """
    today = date.today().isoformat()
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    fpath = SNAP_DIR / f"{today}.json"
    if fpath.exists() and not force:
        return None

    snap = {
        "date": today,
        "datetime": datetime.now().isoformat(timespec="seconds"),
        "champion": {k: float(v) for k, v in (summary.get("champion") or {}).items()},
        "finalist": {k: float(v) for k, v in (summary.get("finalist") or {}).items()},
        "semifinal": {k: float(v) for k, v in (summary.get("semifinal") or {}).items()},
    }
    fpath.write_text(json.dumps(snap, indent=2, ensure_ascii=False))
    return fpath


def list_snapshots() -> list[dict]:
    """Devuelve todos los snapshots ordenados por fecha asc."""
    if not SNAP_DIR.exists():
        return []
    out: list[dict] = []
    for p in sorted(SNAP_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def history_for_team(team: str, metric: str = "champion") -> list[dict]:
    """Serie temporal {date, p} para un equipo en una métrica concreta.

    `metric` puede ser: champion | finalist | semifinal.
    """
    return [
        {"date": s["date"], "p": float(s.get(metric, {}).get(team, 0.0))}
        for s in list_snapshots()
    ]


def history_top_teams(n: int = 8, metric: str = "champion") -> dict[str, list[dict]]:
    """{equipo: serie} para los top-N del snapshot mas reciente."""
    snaps = list_snapshots()
    if not snaps:
        return {}
    last = snaps[-1].get(metric, {})
    top = sorted(last.items(), key=lambda x: -x[1])[:n]
    out: dict[str, list[dict]] = {}
    for team, _ in top:
        out[team] = history_for_team(team, metric)
    return out


def count_snapshots() -> int:
    return len(list(SNAP_DIR.glob("*.json"))) if SNAP_DIR.exists() else 0
