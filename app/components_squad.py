"""Componente visual: once probable de una seleccion sobre un campo de futbol.

Renderiza un mini-campo en HTML/CSS con los `starter=True` de la `Squad`
colocados segun la `formation` declarada (4-3-3, 4-4-2, 4-2-3-1, 3-5-2, 5-3-2, 3-4-3).
"""
from __future__ import annotations
from src.data.squad import Squad, Player


# Coordenadas (x, y) en porcentajes [0, 100]. x=horizontal, y=vertical desde arriba.
# El portero esta abajo (y=88) y los delanteros arriba (y=15-25).
LAYOUTS: dict[str, dict[str, list[tuple[float, float]]]] = {
    "4-3-3": {
        "POR": [(50, 88)],
        "DEF": [(15, 70), (38, 73), (62, 73), (85, 70)],
        "MED": [(28, 50), (50, 48), (72, 50)],
        "DEL": [(20, 22), (50, 16), (80, 22)],
    },
    "4-4-2": {
        "POR": [(50, 88)],
        "DEF": [(15, 72), (38, 70), (62, 70), (85, 72)],
        "MED": [(15, 48), (38, 50), (62, 50), (85, 48)],
        "DEL": [(35, 22), (65, 22)],
    },
    "4-2-3-1": {
        "POR": [(50, 88)],
        "DEF": [(15, 72), (38, 70), (62, 70), (85, 72)],
        "MED": [(35, 58), (65, 58), (22, 38), (50, 35), (78, 38)],
        "DEL": [(50, 16)],
    },
    "3-5-2": {
        "POR": [(50, 88)],
        "DEF": [(25, 70), (50, 72), (75, 70)],
        "MED": [(10, 48), (30, 50), (50, 48), (70, 50), (90, 48)],
        "DEL": [(35, 20), (65, 20)],
    },
    "5-3-2": {
        "POR": [(50, 88)],
        "DEF": [(10, 70), (30, 72), (50, 70), (70, 72), (90, 70)],
        "MED": [(28, 50), (50, 48), (72, 50)],
        "DEL": [(35, 20), (65, 20)],
    },
    "3-4-3": {
        "POR": [(50, 88)],
        "DEF": [(25, 72), (50, 70), (75, 72)],
        "MED": [(15, 50), (38, 52), (62, 52), (85, 50)],
        "DEL": [(20, 22), (50, 16), (80, 22)],
    },
}


def _surname(name: str) -> str:
    if not name:
        return "?"
    parts = name.replace(".", "").split()
    return parts[-1][:14] if parts else "?"


def render_lineup_html(squad: Squad) -> str:
    """Devuelve el HTML del campo con los titulares colocados.

    - Si la formacion no esta en LAYOUTS, cae a 4-3-3.
    - Si faltan jugadores en una posicion, dibuja huecos vacios (?).
    - Hover muestra nombre completo, club, valor, forma.
    """
    formation = (squad.formation or "4-3-3").strip()
    layout = LAYOUTS.get(formation, LAYOUTS["4-3-3"])

    by_pos: dict[str, list[Player]] = {"POR": [], "DEF": [], "MED": [], "DEL": []}
    for p in squad.players:
        if p.starter and p.position in by_pos:
            by_pos[p.position].append(p)

    # Ordenamos cada grupo: titulares mas valiosos al centro / mejor numerados primero
    for pos in by_pos:
        by_pos[pos].sort(
            key=lambda pl: (-(pl.market_value or 0.0), pl.number or 99)
        )

    parts = ['<div class="pitch">']
    # Lineas del campo
    parts.append('<div class="pitch-line pitch-midline"></div>')
    parts.append('<div class="pitch-circle"></div>')
    parts.append('<div class="pitch-box pitch-box-top"></div>')
    parts.append('<div class="pitch-box pitch-box-bottom"></div>')

    for pos, coords in layout.items():
        players = by_pos.get(pos, [])
        for i, (x, y) in enumerate(coords):
            if i < len(players):
                p = players[i]
                name = _surname(p.name)
                num = p.number if p.number else ""
                club = (p.club or "—").replace('"', "'")
                full_name = (p.name or "?").replace('"', "'")
                form = p.recent_form if p.recent_form is not None else 6.0
                mv = p.market_value or 0.0
                tooltip = f"{full_name} · {club} · Valor {mv:.0f}M€ · Forma {form:.1f}"
                # Color del jersey segun forma reciente
                if form >= 7.5:
                    js_class = "jersey-hot"
                elif form >= 6.5:
                    js_class = "jersey-good"
                elif form >= 5.5:
                    js_class = "jersey-mid"
                else:
                    js_class = "jersey-cold"
                parts.append(
                    f'<div class="pitch-player" style="left:{x}%;top:{y}%;" title="{tooltip}">'
                    f'<div class="jersey {js_class}">{num}</div>'
                    f'<div class="player-label">{name}</div>'
                    f'</div>'
                )
            else:
                parts.append(
                    f'<div class="pitch-player pitch-player-empty" style="left:{x}%;top:{y}%;">'
                    f'<div class="jersey jersey-empty">?</div>'
                    f'</div>'
                )

    parts.append('</div>')
    return "".join(parts)


def lineup_summary(squad: Squad) -> dict:
    """Stats rapidos sobre el once probable."""
    starters = [p for p in squad.players if p.starter]
    if not starters:
        return {"n_starters": 0, "total_mv": 0.0, "mean_form": 0.0, "formation": squad.formation}
    total_mv = sum(p.market_value or 0.0 for p in starters)
    mean_form = sum((p.recent_form or 6.0) for p in starters) / len(starters)
    return {
        "n_starters": len(starters),
        "total_mv": total_mv,
        "mean_form": mean_form,
        "formation": squad.formation or "4-3-3",
    }
