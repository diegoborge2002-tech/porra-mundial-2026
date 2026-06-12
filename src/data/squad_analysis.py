"""Loader del analisis cualitativo por seleccion con lista definitiva.

El JSON vive en data/processed/squad_analysis.json y se genera a partir de
scratch/analisis_rendimiento_listas_definitivas.{md,json}. Solo cubre las
selecciones cuya lista de convocados es ya definitiva; las 15 restantes
("Lista por confirmar") no aparecen aqui.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


_ANALYSIS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "squad_analysis.json"


@dataclass
class TeamAnalysis:
    team: str
    display_name: str
    group: str
    score: float
    tier: str
    key_player: str
    differential_player: str
    club_read: str
    main_strength: str
    main_risk: str


_CACHE: Optional[dict] = None


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        if not _ANALYSIS_PATH.exists():
            _CACHE = {"teams": [], "data_quality_flags": [], "included": [], "excluded_until_final_list": []}
        else:
            _CACHE = json.loads(_ANALYSIS_PATH.read_text(encoding="utf-8"))
    return _CACHE


def get_team_analysis(team: str) -> Optional[TeamAnalysis]:
    """Devuelve el analisis de una seleccion por su nombre canonico
    (el usado en GROUPS, ej. 'Espana', 'R.D. Congo', 'Paises Bajos').
    Devuelve None si la seleccion no tiene lista definitiva todavia."""
    data = _load()
    for t in data.get("teams", []):
        if t.get("team") == team:
            return TeamAnalysis(
                team=t["team"],
                display_name=t.get("display_name", t["team"]),
                group=t.get("group", ""),
                score=float(t.get("score", 0.0)),
                tier=t.get("tier", ""),
                key_player=t.get("key_player", ""),
                differential_player=t.get("differential_player", ""),
                club_read=t.get("club_read", ""),
                main_strength=t.get("main_strength", ""),
                main_risk=t.get("main_risk", ""),
            )
    return None


def all_analyses() -> list[TeamAnalysis]:
    data = _load()
    out: list[TeamAnalysis] = []
    for t in data.get("teams", []):
        out.append(TeamAnalysis(
            team=t["team"],
            display_name=t.get("display_name", t["team"]),
            group=t.get("group", ""),
            score=float(t.get("score", 0.0)),
            tier=t.get("tier", ""),
            key_player=t.get("key_player", ""),
            differential_player=t.get("differential_player", ""),
            club_read=t.get("club_read", ""),
            main_strength=t.get("main_strength", ""),
            main_risk=t.get("main_risk", ""),
        ))
    return out


def data_quality_flags() -> list[str]:
    return list(_load().get("data_quality_flags", []))


def included_teams() -> list[str]:
    return list(_load().get("included", []))


def excluded_teams() -> list[str]:
    return list(_load().get("excluded_until_final_list", []))


def has_definitive_list(team: str) -> bool:
    return get_team_analysis(team) is not None
