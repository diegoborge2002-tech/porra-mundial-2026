"""Tabla FIFA de los 8 mejores terceros del Mundial 2026.

Carga las 495 combinaciones posibles desde data/processed/third_place_table.json
(parseadas de la hoja "Anexo - Terceros" del Excel via parse_third_table.py).

Columnas: 1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L (las 8 cabezas de serie que
enfrentan a un tercero en Dieciseisavos).
"""
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache


_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "third_place_table.json"


@lru_cache(maxsize=1)
def _load_rows() -> list[dict[str, str]]:
    if not _JSON_PATH.exists():
        raise FileNotFoundError(
            f"No existe {_JSON_PATH}. Ejecuta:\n"
            f"  python src/tournament/parse_third_table.py"
        )
    return json.loads(_JSON_PATH.read_text())


@lru_cache(maxsize=1)
def _index() -> dict[frozenset[str], dict[str, str]]:
    """Indice frozenset({grupos terceros clasificados}) -> mapping 1X -> 3X."""
    return {
        frozenset(v[1:] for v in row.values()): row
        for row in _load_rows()
    }


def get_third_place_pairing(qualified_groups: set[str]) -> dict[str, str]:
    """Devuelve mapping 1X -> 3X dado el conjunto de 8 grupos de los mejores terceros."""
    if len(qualified_groups) != 8:
        raise ValueError(f"Se esperaban 8 grupos, recibidos {len(qualified_groups)}")
    key = frozenset(qualified_groups)
    idx = _index()
    if key not in idx:
        raise KeyError(
            f"Combinacion {sorted(qualified_groups)} no encontrada. "
            f"La tabla deberia cubrir las 495 combinaciones posibles."
        )
    return idx[key]
