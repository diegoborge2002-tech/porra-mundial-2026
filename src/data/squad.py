"""Gestion de plantillas (squads) por seleccion.

Cada equipo tiene su propio JSON en data/processed/squads/<equipo>.json
con la siguiente estructura:

{
  "team": "Espana",
  "coach": "Luis de la Fuente",
  "captain": "Alvaro Morata",
  "formation": "4-3-3",
  "star_player": "Lamine Yamal",
  "notes": "Generacion dorada, candidata clara al titulo...",
  "ratings": {            # tu rating subjetivo 1-10 en cada eje
      "attack": 9, "defense": 8, "midfield": 9,
      "bench_depth": 8, "experience": 7, "motivation": 9
  },
  "players": [
      {"name": "Unai Simon", "position": "POR", "club": "Athletic", "number": 1, "market_value": 25, "starter": true},
      ...
  ],
  "updated_at": "2026-05-18"
}
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


SQUADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "squads"

POSITIONS = ["POR", "DEF", "MED", "DEL"]
POSITION_LABELS = {"POR": "Portero", "DEF": "Defensa", "MED": "Mediocampo", "DEL": "Delantero"}

RATING_AXES = {
    "attack": "Ataque",
    "defense": "Defensa",
    "midfield": "Mediocampo",
    "bench_depth": "Banquillo",
    "experience": "Experiencia",
    "motivation": "Motivacion",
}


@dataclass
class Player:
    name: str
    position: str = "MED"  # POR/DEF/MED/DEL
    club: str = ""
    number: Optional[int] = None
    market_value: Optional[float] = None  # en millones de euros
    starter: bool = False
    notes: str = ""
    recent_form: float = 6.0  # de 1.0 a 10.0 (por defecto 6.0)


@dataclass
class Squad:
    team: str
    coach: str = ""
    captain: str = ""
    formation: str = "4-3-3"
    star_player: str = ""
    notes: str = ""
    ratings: dict[str, int] = field(default_factory=lambda: {k: 5 for k in RATING_AXES})
    players: list[Player] = field(default_factory=list)
    updated_at: str = ""

    def avg_rating(self) -> float:
        if not self.ratings: return 0.0
        return sum(self.ratings.values()) / len(self.ratings)

    def player_count_by_position(self) -> dict[str, int]:
        out = {p: 0 for p in POSITIONS}
        for p in self.players:
            out[p.position] = out.get(p.position, 0) + 1
        return out


def _path(team: str) -> Path:
    safe = team.replace(".", "").replace(" ", "_").replace("/", "_")
    return SQUADS_DIR / f"{safe}.json"


def load_squad(team: str) -> Squad:
    p = _path(team)
    if not p.exists():
        return Squad(team=team)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        players_raw = raw.pop("players", [])
        players = []
        for pl in players_raw:
            # Construcción segura para evitar KeyErrors por campos incompletos
            players.append(Player(
                name=pl.get("name", ""),
                position=pl.get("position", "MED"),
                club=pl.get("club", ""),
                number=pl.get("number"),
                market_value=pl.get("market_value"),
                starter=bool(pl.get("starter", False)),
                notes=pl.get("notes", ""),
                recent_form=float(pl.get("recent_form", 6.0))
            ))
        return Squad(
            team=raw.get("team", team),
            coach=raw.get("coach", ""),
            captain=raw.get("captain", ""),
            formation=raw.get("formation", "4-3-3"),
            star_player=raw.get("star_player", ""),
            notes=raw.get("notes", ""),
            ratings=raw.get("ratings", {k: 5 for k in RATING_AXES}),
            players=players,
            updated_at=raw.get("updated_at", "")
        )
    except Exception:
        # Retorno seguro si el archivo JSON está malformado
        return Squad(team=team)


def save_squad(squad: Squad) -> None:
    SQUADS_DIR.mkdir(parents=True, exist_ok=True)
    squad.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = asdict(squad)
    _path(squad.team).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def squad_exists(team: str) -> bool:
    return _path(team).exists()


def squad_completeness(squad: Squad) -> int:
    """Devuelve un porcentaje de completitud (0-100) basado en cuanta info hay rellena."""
    score = 0
    if squad.coach: score += 10
    if squad.captain: score += 10
    if squad.formation: score += 5
    if squad.star_player: score += 10
    if squad.notes: score += 5
    if squad.ratings and any(v != 5 for v in squad.ratings.values()): score += 10
    # Jugadores: 50 puntos repartidos
    if squad.players:
        score += min(50, len(squad.players) * 2)
    return score


def ratings_to_elo_bias(squad: Squad) -> float:
    """Convierte los ratings subjetivos (1-10) a un bias Elo aproximado.

    La media de los 6 ejes representa la 'fuerza percibida' del equipo.
    Mapeamos:
        - rating 5 (neutral) -> 0 puntos Elo
        - rating 10 (top)    -> +100 puntos Elo
        - rating 1 (malisimo) -> -100 puntos Elo
    """
    if not squad.ratings: return 0.0
    avg = squad.avg_rating()
    return (avg - 5) * 20  # cada punto sobre 5 vale +20 Elo


def calculate_club_performance_bias(
    squad: Squad,
    weight_mv: float = 1.0,
    weight_pedigree: float = 1.0,
    weight_recent_form: float = 1.0,
) -> float:
    """Calcula un bias Elo basado en el valor de mercado total, la presencia de jugadores en clubs de elite y la forma de los ultimos 3 meses.

    - Valor de mercado: escala logarítmica respecto a un valor base de 50M€.
    - Pedigrí de club: jugadores titulares en equipos top ponderan 1.5, suplentes 0.5.
    - Rendimiento reciente (ultimos 3 meses): sumatorio del delta de forma respecto a 6.0 neutro.
      Titulares ponderan x2.0, suplentes x0.5. Impacto en Elo escalado por factor 2.5.
    """
    if not squad.players:
        return 0.0

    total_mv = sum(p.market_value for p in squad.players if p.market_value is not None)

    # Conjunto de palabras clave de clubes de élite (Champions / top 5 ligas europeas)
    elite_keywords = {
        "real madrid", "madrid", "bayern", "munich", "münchen", "man city", "manchester city",
        "liverpool", "arsenal", "psg", "paris saint", "barcelona", "barca", "inter",
        "juventus", "milan", "chelsea", "tottenham", "spurs", "atletico", "atlético",
        "dortmund", "leverkusen", "bayer", "aston villa", "newcastle", "lazio", "napoli", "roma"
    }

    elite_count = 0.0
    form_delta_sum = 0.0
    
    for p in squad.players:
        # Calcular pedigri de club elite
        if p.club:
            club_lower = p.club.lower()
            if any(kw in club_lower for kw in elite_keywords):
                elite_count += 1.5 if p.starter else 0.5
        
        # Calcular delta de forma reciente (ultimos 3 meses) respecto a 6.0 (neutro)
        p_form = p.recent_form if p.recent_form is not None else 6.0
        delta = p_form - 6.0
        weight = 2.0 if p.starter else 0.5
        form_delta_sum += delta * weight

    # Cálculo logarítmico para el valor de mercado
    if total_mv > 0:
        # Capping inferior para evitar valores extremos
        ratio = max(0.1, total_mv / 50.0)
        mv_bias = 25.0 * math.log(ratio)
    else:
        mv_bias = -30.0  # penalización por ausencia de datos de plantilla

    # El pedigrí de club añade puntos directamente por cada estrella en élite
    pedigree_bias = elite_count * 5.0
    
    # Impacto de forma de los ultimos 3 meses (escalado por factor 2.5)
    form_bias = form_delta_sum * 2.5

    # Ponderar y sumar
    total_bias = (mv_bias * weight_mv) + (pedigree_bias * weight_pedigree) + (form_bias * weight_recent_form)

    # Limitar el bias entre -200 y +200 para preservar la estabilidad de la escala Elo
    return max(-200.0, min(200.0, total_bias))
