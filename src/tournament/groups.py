"""Grupos del Mundial 2026 según la plantilla de la porra.

El Mundial 2026 tiene 48 equipos en 12 grupos (A-L) de 4 equipos.
Clasifican a la siguiente ronda los 2 primeros de cada grupo + los 8 mejores terceros.
La ronda inicial se llama "Dieciseisavos" (Round of 32) y consta de 16 partidos.
"""

from dataclasses import dataclass, field


GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "Sudafrica", "Corea del Sur", "Rep. Checa"],
    "B": ["Canada", "Bosnia Herz.", "Catar", "Suiza"],
    "C": ["Brasil", "Marruecos", "Haiti", "Escocia"],
    "D": ["Estados Unidos", "Paraguay", "Australia", "Turquia"],
    "E": ["Alemania", "Curazao", "Costa Marfil", "Ecuador"],
    "F": ["Paises Bajos", "Japon", "Suecia", "Tunez"],
    "G": ["Belgica", "Egipto", "Iran", "Nueva Zelanda"],
    "H": ["Espana", "Cabo Verde", "Arabia Saudi", "Uruguay"],
    "I": ["Francia", "Senegal", "Irak", "Noruega"],
    "J": ["Argentina", "Argelia", "Austria", "Jordania"],
    "K": ["Portugal", "R.D. Congo", "Uzbekistan", "Colombia"],
    "L": ["Inglaterra", "Croacia", "Ghana", "Panama"],
}

ALL_TEAMS: list[str] = [team for teams in GROUPS.values() for team in teams]

HOST_NATIONS: set[str] = {"Mexico", "Canada", "Estados Unidos"}


@dataclass
class GroupStanding:
    """Estado de un equipo en la fase de grupos."""

    team: str
    group: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    yellow_cards: int = 0
    red_cards: int = 0

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def fair_play_score(self) -> int:
        """Puntuación de juego limpio FIFA: -1 por amarilla, -3 por roja directa.
        En la práctica no tendremos esto al simular, así que será 0."""
        return -(self.yellow_cards + 3 * self.red_cards)
