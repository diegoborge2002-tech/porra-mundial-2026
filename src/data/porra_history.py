"""Historial timestamped de versiones de la porra del usuario.

Cada vez que se guarda la porra, se añade una versión al archivo de historial.
Mantiene las últimas N versiones por defecto (configurable).
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_PATH = ROOT / "data" / "processed" / "porra_versions.json"

MAX_VERSIONS = 25


def _load_versions() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data.get("versions", [])
    except Exception:
        return []


def _save_versions(versions: list[dict]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps({"versions": versions}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def list_versions() -> list[dict]:
    """Versiones ordenadas de más nueva a más vieja."""
    return _load_versions()


def append_version(porra: dict, note: str = "") -> dict:
    """Añade una versión al historial. Devuelve la versión guardada."""
    versions = _load_versions()
    version = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "note": note,
        "porra": porra,
    }
    versions.insert(0, version)  # más nuevo primero
    versions = versions[:MAX_VERSIONS]
    _save_versions(versions)
    return version


def get_version(timestamp: str) -> dict | None:
    for v in _load_versions():
        if v["timestamp"] == timestamp:
            return v
    return None


def delete_version(timestamp: str) -> None:
    versions = [v for v in _load_versions() if v["timestamp"] != timestamp]
    _save_versions(versions)


def _summary_pick(porra: dict) -> str:
    """Resumen corto de la porra (champion + finalistas)."""
    champ = porra.get("champion") or "—"
    finals = ", ".join(t for t in porra.get("final", []) or [] if t) or "—"
    return f"🏆 {champ} · 🥈 {finals}"


def diff_versions(v_old: dict, v_new: dict) -> list[str]:
    """Devuelve líneas legibles con los cambios entre dos porras."""
    old_p, new_p = v_old.get("porra", {}), v_new.get("porra", {})
    diffs = []
    if old_p.get("champion") != new_p.get("champion"):
        diffs.append(f"Campeón: {old_p.get('champion') or '—'} → {new_p.get('champion') or '—'}")
    for key, label in [("final", "Final"), ("sf", "Semis"), ("qf", "Cuartos"), ("r16", "R16")]:
        ol = set(t for t in (old_p.get(key) or []) if t)
        nw = set(t for t in (new_p.get(key) or []) if t)
        added = nw - ol; removed = ol - nw
        if added or removed:
            diffs.append(f"{label}: +{', '.join(added) or '—'} | -{', '.join(removed) or '—'}")
    for g in (old_p.get("groups") or {}):
        og = old_p["groups"].get(g, [])
        ng = (new_p.get("groups") or {}).get(g, [])
        if og != ng:
            diffs.append(f"Grupo {g}: {og} → {ng}")
    return diffs
