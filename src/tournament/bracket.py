"""Bracket eliminatorio del Mundial 2026.

Datos del cuadro oficial publicado por FIFA. Los Dieciseisavos enfrentan a
cabezas de serie (1.X) contra terceros (3.X) en 8 partidos, y a clasificados
directos (1.X vs 2.X o 2.X vs 2.X) en los otros 8.

NOTACION:
- "1X", "2X", "3X" = primero/segundo/tercero del grupo X
- "3?H" = tercero a determinar via tabla de 8 mejores terceros, posicion H
- Ganadores se referencian por su numero de partido FIFA (P73-P102, P104).

Numeracion:
- FIFA usa P1-P72 para fase de grupos y P73-P104 para eliminatorias
  (P101=semi, P102=semi, P103=3er puesto, P104=final)
- Tu Excel renumera las eliminatorias del 1 al 31 (1-16=R32, 17-24=R16,
  25-28=QF, 29-30=SF, 31=F).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# DIECISEISAVOS (Round of 32) - 16 partidos
# Numeracion FIFA: P73-P88. Numeracion Excel: 1-16.
# ============================================================================

# Cada partido = (slot_left, slot_right)
# Los slots "3?{position}" indican tercero a resolver via tabla; el {position}
# es la columna en la tabla de terceros: A, B, D, E, G, I, K, L.
R32_FIFA: dict[int, tuple[str, str]] = {
    73: ("2A", "2B"),
    74: ("1E", "3?E"),    # 3 de uno entre A,B,C,D,F
    75: ("1F", "2C"),
    76: ("1C", "2F"),
    77: ("1I", "3?I"),    # 3 de uno entre C,D,F,G,H
    78: ("1L", "3?L"),    # 3 de uno entre E,H,I,J,K
    79: ("2E", "2I"),
    80: ("1A", "3?A"),    # 3 de uno entre C,E,F,H,I
    81: ("1G", "3?G"),    # 3 de uno entre B,E,F,I,J
    82: ("1B", "3?B"),    # 3 de uno entre A,E,H,I,J
    83: ("2K", "2L"),
    84: ("1H", "2J"),
    85: ("1D", "3?D"),    # 3 de uno entre E,F,G,I,J
    86: ("1K", "3?K"),    # 3 de uno entre D,E,I,J,L
    87: ("1J", "2H"),
    88: ("2D", "2G"),
}


# ============================================================================
# OCTAVOS (Round of 16) - 8 partidos
# ============================================================================
R16_FIFA: dict[int, tuple[int, int]] = {
    89: (74, 77),
    90: (73, 75),
    91: (76, 78),
    92: (79, 80),
    93: (83, 84),
    94: (81, 82),
    95: (86, 88),
    96: (85, 87),
}


# ============================================================================
# CUARTOS (Quarter-finals) - 4 partidos
# ============================================================================
QF_FIFA: dict[int, tuple[int, int]] = {
    97: (89, 90),
    98: (93, 94),
    99: (91, 92),
    100: (95, 96),
}


# ============================================================================
# SEMIFINALES - 2 partidos
# ============================================================================
SF_FIFA: dict[int, tuple[int, int]] = {
    101: (97, 98),
    102: (99, 100),
}


# ============================================================================
# FINAL
# ============================================================================
F_FIFA: dict[int, tuple[int, int]] = {
    104: (101, 102),
}


# ============================================================================
# MAPEO Excel <-> FIFA
# El Excel numera del 1 al 31. Asumimos un orden top-down, left-right.
# La asignacion exacta de los 16 Dieciseisavos se confirma con el usuario.
# ============================================================================

# Por ahora mapeamos el orden visual del Excel (1-16 leyendo arriba-abajo,
# izquierda-derecha como aparece en la imagen del Excel) al P73-P88 FIFA.
# ESTO DEBE SER VERIFICADO con el Excel real.
EXCEL_TO_FIFA_R32: dict[int, int] = {
    # Excel num -> FIFA num
    1: 80,   # P1 Excel: ?? vs 3A/B/C/D/F -> P80 FIFA: 1A vs 3?A
    2: 77,   # P2 Excel: ?? vs 3C/D/F/G/H -> P77 FIFA: 1I vs 3?I
    7: 81,   # P7 Excel: ?? vs 3B/E/F/I/J -> P81 FIFA: 1G vs 3?G
    8: 82,   # P8 Excel: ?? vs 3A/E/H/I/J -> P82 FIFA: 1B vs 3?B
    11: 74,  # P11 Excel: ?? vs 3C/E/F/H/I -> P74 FIFA: 1E vs 3?E
    12: 78,  # P12 Excel: ?? vs 3E/H/I/J/K -> P78 FIFA: 1L vs 3?L
    15: 85,  # P15 Excel: ?? vs 3E/F/G/I/J -> P85 FIFA: 1D vs 3?D
    16: 86,  # P16 Excel: ?? vs 3D/E/I/J/L -> P86 FIFA: 1K vs 3?K
    # Los 8 partidos sin tercero (3, 4, 5, 6, 9, 10, 13, 14) -> P73, P75, P76, P79, P83, P84, P87, P88
    # El orden exacto necesita verificacion con el Excel.
}


# Mapping de letra de columna en la tabla de terceros -> posicion 3? en el bracket
# Esto nos dice donde colocar el tercero del grupo X en los Dieciseisavos.
# Por ejemplo, si la tabla dice "1A -> 3E", entonces en el partido P80 (que es 1A vs ?)
# el rival es el tercero del grupo E.
THIRD_PLACE_HEAD_TO_FIFA_MATCH: dict[str, int] = {
    "1A": 80,
    "1B": 82,
    "1D": 85,
    "1E": 74,
    "1G": 81,
    "1I": 77,
    "1K": 86,
    "1L": 78,
}


@dataclass
class Match:
    """Un partido del torneo."""
    fifa_id: int
    round_name: str  # 'R32', 'R16', 'QF', 'SF', 'F'
    excel_id: Optional[int] = None
    home: Optional[str] = None
    away: Optional[str] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    home_pens: Optional[int] = None
    away_pens: Optional[int] = None
    winner: Optional[str] = None
