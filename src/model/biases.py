"""Capa de ajuste manual a los ratings Elo.

Los Elo del modelo se entrenan con datos historicos puros (resultados),
pero hay informacion contextual que el modelo no ve: lesiones, estado de
forma reciente, cambios de entrenador, generaciones doradas, factor
psicologico de jugar en casa, motivacion, etc.

Esta capa permite al usuario aplicar ajustes (en puntos Elo) a cada equipo.
Cada +50 puntos Elo ~ +20% de probabilidad de ganar un partido parejo.

Los biases se cargan desde JSON para que la web app pueda editarlos con
sliders y persistir el estado entre sesiones.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, asdict, field


_BIASES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "biases.json"


@dataclass
class TeamBias:
    """Ajuste para un equipo concreto."""
    team: str
    elo_delta: float = 0.0
    reason: str = ""  # nota libre para recordar por que se ajusto


@dataclass
class BiasesConfig:
    """Coleccion de ajustes."""
    team_biases: dict[str, TeamBias] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)  # notas globales, ej "pendiente confirmar convocatorias"
    half_life: float = 8.0
    use_club_performance: bool = False
    weight_market_value: float = 1.0
    weight_club_pedigree: float = 1.0
    weight_recent_form: float = 1.0
    # Peso del modelo de stats (XGBoost) en el ensemble de goles esperados:
    # 0 = solo Elo, 1 = solo stats. Ver src/model/ensemble.py
    stats_weight: float = 0.5

    def get_delta(self, team: str) -> float:
        if team in self.team_biases:
            return self.team_biases[team].elo_delta
        return 0.0

    def set_bias(self, team: str, delta: float, reason: str = "") -> None:
        self.team_biases[team] = TeamBias(team=team, elo_delta=delta, reason=reason)

    def apply_to(self, base_elo: dict[str, float]) -> dict[str, float]:
        """Devuelve un nuevo dict de Elo con los ajustes aplicados y el factor de club si está activo."""
        res = {}
        # Importación dinámica para evitar problemas de dependencias circulares
        from src.data.squad import load_squad, calculate_club_performance_bias
        
        for team, elo in base_elo.items():
            delta = self.get_delta(team)
            
            # Aplicar bias de rendimiento de clubes si está activo
            club_delta = 0.0
            if self.use_club_performance:
                squad = load_squad(team)
                club_delta = calculate_club_performance_bias(
                    squad, 
                    weight_mv=self.weight_market_value, 
                    weight_pedigree=self.weight_club_pedigree,
                    weight_recent_form=self.weight_recent_form
                )
                
            res[team] = elo + delta + club_delta
            
        return res

    def save(self, path: Path = _BIASES_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "team_biases": {t: asdict(b) for t, b in self.team_biases.items()},
            "notes": self.notes,
            "half_life": self.half_life,
            "use_club_performance": self.use_club_performance,
            "weight_market_value": self.weight_market_value,
            "weight_club_pedigree": self.weight_club_pedigree,
            "weight_recent_form": self.weight_recent_form,
            "stats_weight": self.stats_weight,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: Path = _BIASES_PATH) -> "BiasesConfig":
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
        except Exception:
            return cls()
            
        cfg = cls(
            notes=raw.get("notes", []),
            half_life=float(raw.get("half_life", 8.0)),
            use_club_performance=bool(raw.get("use_club_performance", False)),
            weight_market_value=float(raw.get("weight_market_value", 1.0)),
            weight_club_pedigree=float(raw.get("weight_club_pedigree", 1.0)),
            weight_recent_form=float(raw.get("weight_recent_form", 1.0)),
            stats_weight=float(raw.get("stats_weight", 0.5)),
        )
        for t, b in raw.get("team_biases", {}).items():
            cfg.team_biases[t] = TeamBias(**b)
        return cfg


# Biases inciales basados en la primera ronda de input del usuario (sesion del 2026-05-18)
INITIAL_USER_BIASES: list[tuple[str, float, str]] = [
    # Grupo B: Suiza por encima de Canada
    ("Suiza", +50, "Usuario la ve favorita sobre Canada en Grupo B"),
    ("Canada", -10, "Por debajo de Suiza (neto: -30 + 20 anfitrion)"),
    # Grupo E: Ecuador potencia, Alemania tambien
    ("Ecuador", +60, "Usuario la ve potencia ganadora"),
    ("Alemania", +30, "Favorito para Grupo E"),
    # Grupo F: Paises Bajos muy favorito; Suecia segunda opcion; Japon sobrevalorado por Elo
    ("Paises Bajos", +80, "Mucho mas favorito que el modelo, top opcion Grupo F"),
    ("Suecia", +30, "Segunda opcion Grupo F"),
    ("Japon", -40, "Modelo lo sobrevalora segun usuario"),
    # Candidatos al titulo segun usuario: Espana, Francia, Portugal, Alemania
    ("Espana", +50, "Top candidato a campeon"),
    ("Francia", +40, "Top candidato a campeon"),
    ("Portugal", +80, "Infravalorado por el modelo, candidato real a campeon"),
    ("Brasil", -20, "Selecciones mejores aunque en Mundiales nunca se sabe"),
    # Grupo K: Portugal y Colombia pasan, Uzbekistan no
    ("Colombia", +30, "Pasa de grupo seguro segun usuario"),
    ("Uzbekistan", -40, "Usuario lo descarta"),
    # Anfitriones (factor sede)
    ("Mexico", +30, "Anfitrion"),
    ("Estados Unidos", +30, "Anfitrion"),
    # Canada anfitrion +20, ya tiene -30 arriba -> neto -10
]


def build_initial_config() -> BiasesConfig:
    cfg = BiasesConfig()
    cfg.notes.append(
        "Pendiente: confirmar convocatorias oficiales (finales mayo 2026) "
        "para fijar predicciones de Bota de Oro y Balon de Oro."
    )
    cfg.notes.append(
        "Idea inicial del usuario para Bota de Oro: jugador de Argentina "
        "(Messi/Lautaro/Julian Alvarez), Francia (Mbappe/Dembele/Olise) "
        "o Inglaterra (Kane)."
    )
    cfg.notes.append(
        "Idea inicial del usuario para campeon: Espana, Francia, "
        "Portugal o Alemania."
    )
    for team, delta, reason in INITIAL_USER_BIASES:
        cfg.set_bias(team, delta, reason)
    return cfg


if __name__ == "__main__":
    cfg = build_initial_config()
    cfg.save()
    print(f"Guardadas {len(cfg.team_biases)} biases en {_BIASES_PATH}")
    for t, b in sorted(cfg.team_biases.items(), key=lambda x: -x[1].elo_delta):
        print(f"  {t:20s}  {b.elo_delta:+.0f}  ({b.reason})")
