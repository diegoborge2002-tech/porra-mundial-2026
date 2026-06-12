"""Componente visual: once probable de una seleccion sobre un campo de futbol.

Renderiza un mini-campo en HTML/CSS con los `starter=True` de la `Squad`
colocados segun la `formation` declarada (4-3-3, 4-4-2, 4-2-3-1, 3-5-2, 5-3-2, 3-4-3).
"""
from __future__ import annotations
from src.data.squad import Squad, Player


# Cada slot del once: (x, y, banda POR/DEF/MED/DEL, roles que encajan en él).
# x,y en porcentajes; portero abajo (y=88), delanteros arriba. El primer rol
# de la tupla es el "natural" del hueco; el resto son compatibles.
Slot = tuple[float, float, str, tuple[str, ...]]

LAYOUTS: dict[str, list[Slot]] = {
    "4-3-3": [
        (50, 88, "POR", ("POR",)),
        (15, 70, "DEF", ("LI",)), (38, 73, "DEF", ("CT",)),
        (62, 73, "DEF", ("CT",)), (85, 70, "DEF", ("LD",)),
        (28, 50, "MED", ("MC", "MI", "MCO")), (50, 48, "MED", ("MCD", "MC")),
        (72, 50, "MED", ("MC", "MD", "MCO")),
        (20, 22, "DEL", ("EI", "SD", "MI")), (50, 16, "DEL", ("DC",)),
        (80, 22, "DEL", ("ED", "SD", "MD")),
    ],
    "4-4-2": [
        (50, 88, "POR", ("POR",)),
        (15, 72, "DEF", ("LI",)), (38, 70, "DEF", ("CT",)),
        (62, 70, "DEF", ("CT",)), (85, 72, "DEF", ("LD",)),
        (15, 48, "MED", ("MI", "EI")), (38, 50, "MED", ("MC", "MCD")),
        (62, 50, "MED", ("MC", "MCD")), (85, 48, "MED", ("MD", "ED")),
        (35, 22, "DEL", ("DC", "SD")), (65, 22, "DEL", ("DC", "SD")),
    ],
    "4-2-3-1": [
        (50, 88, "POR", ("POR",)),
        (15, 72, "DEF", ("LI",)), (38, 70, "DEF", ("CT",)),
        (62, 70, "DEF", ("CT",)), (85, 72, "DEF", ("LD",)),
        (35, 58, "MED", ("MCD", "MC")), (65, 58, "MED", ("MC", "MCD")),
        (50, 35, "MED", ("MCO", "SD", "MC")),
        # Los extremos del 4-2-3-1 son banda DEL (así están clasificados en los datos)
        (22, 38, "DEL", ("EI", "MI", "MCO")), (78, 38, "DEL", ("ED", "MD", "MCO")),
        (50, 16, "DEL", ("DC",)),
    ],
    "3-5-2": [
        (50, 88, "POR", ("POR",)),
        (25, 70, "DEF", ("CT",)), (50, 72, "DEF", ("CT",)), (75, 70, "DEF", ("CT",)),
        (10, 48, "MED", ("LI", "MI", "EI")), (30, 50, "MED", ("MC",)),
        (50, 48, "MED", ("MCD", "MC")), (70, 50, "MED", ("MC", "MCO")),
        (90, 48, "MED", ("LD", "MD", "ED")),
        (35, 20, "DEL", ("DC", "SD")), (65, 20, "DEL", ("DC", "SD")),
    ],
    "5-3-2": [
        (50, 88, "POR", ("POR",)),
        (10, 70, "DEF", ("LI",)), (30, 72, "DEF", ("CT",)), (50, 70, "DEF", ("CT",)),
        (70, 72, "DEF", ("CT",)), (90, 70, "DEF", ("LD",)),
        (28, 50, "MED", ("MC", "MI")), (50, 48, "MED", ("MCD", "MC")),
        (72, 50, "MED", ("MC", "MD")),
        (35, 20, "DEL", ("DC", "SD")), (65, 20, "DEL", ("DC", "SD")),
    ],
    "3-4-3": [
        (50, 88, "POR", ("POR",)),
        (25, 72, "DEF", ("CT",)), (50, 70, "DEF", ("CT",)), (75, 72, "DEF", ("CT",)),
        (15, 50, "MED", ("LI", "MI", "EI")), (38, 52, "MED", ("MC", "MCD")),
        (62, 52, "MED", ("MC", "MCD")), (85, 50, "MED", ("LD", "MD", "ED")),
        (20, 22, "DEL", ("EI", "SD", "MI")), (50, 16, "DEL", ("DC",)),
        (80, 22, "DEL", ("ED", "SD", "MD")),
    ],
    "3-4-2-1": [
        (50, 88, "POR", ("POR",)),
        (25, 72, "DEF", ("CT",)), (50, 70, "DEF", ("CT",)), (75, 72, "DEF", ("CT",)),
        (12, 50, "MED", ("LI", "MI", "EI")), (38, 54, "MED", ("MC", "MCD")),
        (62, 54, "MED", ("MC", "MCD")), (88, 50, "MED", ("LD", "MD", "ED")),
        (32, 30, "DEL", ("MCO", "SD", "EI", "MC")), (68, 30, "DEL", ("MCO", "SD", "ED", "MC")),
        (50, 14, "DEL", ("DC",)),
    ],
}


def _surname(name: str) -> str:
    if not name:
        return "?"
    parts = name.replace(".", "").split()
    return parts[-1][:14] if parts else "?"


def _assign_players_to_slots(starters: list[Player], layout: list[Slot]) -> dict[int, Player]:
    """Asigna titulares a los huecos del once respetando su demarcación (role).

    Pasadas, de más estricta a más laxa:
      1. Rol del jugador == rol natural del hueco (primero de la tupla), misma banda.
      2. Rol del jugador en los roles compatibles del hueco, misma banda.
      3. Sin rol (o sin hueco de su rol): huecos libres de su banda, por valor.
      4. Sobrantes (p.ej. 4 defensas en una formación de 3): cualquier hueco libre
         donde su rol sea compatible (carrileros LI/LD encajan en bandas de 3-X-X),
         y si no, cualquier hueco libre.
    """
    assignment: dict[int, Player] = {}
    free = set(range(len(layout)))
    pool = list(starters)

    def place(idx: int, player: Player) -> None:
        assignment[idx] = player
        free.discard(idx)
        pool.remove(player)

    # Pasada 1: rol exacto en su banda
    for i, (_, _, band, roles) in enumerate(layout):
        if i not in free:
            continue
        for p in sorted(pool, key=lambda pl: -(pl.market_value or 0.0)):
            if p.position == band and p.role == roles[0]:
                place(i, p)
                break

    # Pasada 2: rol compatible en su banda
    for i, (_, _, band, roles) in enumerate(layout):
        if i not in free:
            continue
        for p in sorted(pool, key=lambda pl: -(pl.market_value or 0.0)):
            if p.position == band and p.role in roles:
                place(i, p)
                break

    # Pasada 3: misma banda, sin exigir rol (jugadores sin role o atípicos)
    for i, (_, _, band, _) in enumerate(layout):
        if i not in free:
            continue
        candidates = [p for p in pool if p.position == band]
        if candidates:
            place(i, max(candidates, key=lambda pl: pl.market_value or 0.0))

    # Pasada 4: sobrantes a huecos libres (rol compatible primero)
    for p in sorted(pool, key=lambda pl: -(pl.market_value or 0.0)):
        target = next((i for i in sorted(free) if p.role in layout[i][3]), None)
        if target is None:
            target = next(iter(sorted(free)), None)
        if target is not None:
            place(target, p)

    return assignment


def render_lineup_html(squad: Squad) -> str:
    """Devuelve el HTML del campo con los titulares colocados por demarcación.

    - Si la formacion no esta en LAYOUTS, cae a 4-3-3.
    - Si faltan jugadores en una posicion, dibuja huecos vacios (?).
    - Hover muestra nombre completo, demarcación, club, valor, forma.
    """
    from src.data.squad import ROLE_LABELS

    formation = (squad.formation or "4-3-3").strip()
    layout = LAYOUTS.get(formation, LAYOUTS["4-3-3"])
    starters = [p for p in squad.players if p.starter]
    assignment = _assign_players_to_slots(starters, layout)

    parts = ['<div class="pitch">']
    # Lineas del campo
    parts.append('<div class="pitch-line pitch-midline"></div>')
    parts.append('<div class="pitch-circle"></div>')
    parts.append('<div class="pitch-box pitch-box-top"></div>')
    parts.append('<div class="pitch-box pitch-box-bottom"></div>')

    for i, (x, y, _band, _roles) in enumerate(layout):
        p = assignment.get(i)
        if p is not None:
            name = _surname(p.name)
            num = p.number if p.number else ""
            club = (p.club or "—").replace('"', "'")
            full_name = (p.name or "?").replace('"', "'")
            role_lbl = ROLE_LABELS.get(p.role or "", "")
            role_part = f" · {role_lbl}" if role_lbl else ""
            form = p.recent_form if p.recent_form is not None else 6.0
            mv = p.market_value or 0.0
            tooltip = f"{full_name}{role_part} · {club} · Valor {mv:.0f}M€ · Forma {form:.1f}"
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
