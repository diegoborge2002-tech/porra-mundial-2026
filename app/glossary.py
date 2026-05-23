"""Glosario de métricas usadas en la app. Útil para tooltips y secciones de ayuda."""
from __future__ import annotations


GLOSSARY: dict[str, str] = {
    "brier": (
        "**Brier score**: error cuadrático medio entre las probabilidades del modelo "
        "y el outcome real (multiclase, rango 0–2). 0 = predicción perfecta. "
        "Cuanto más bajo, mejor calibrado el modelo. "
        "Baseline: predecir 1/3 uniforme → Brier ≈ 0.67."
    ),
    "log_loss": (
        "**Log-loss (cross-entropy)**: −log(prob asignada al outcome real). "
        "0 = perfecto, ∞ si asignas 0% al resultado correcto. Penaliza muy fuerte "
        "estar 'muy seguro y mal'."
    ),
    "rps": (
        "**RPS (Rank Probability Score)**: variante ordinal del Brier — penaliza más "
        "predecir 'victoria local' cuando gana el visitante que cuando empata. "
        "Estándar de oro en quinielas 1X2. Rango 0–1; cuanto más bajo, mejor."
    ),
    "hit_rate": (
        "**Top-1 acierto**: % de veces que el outcome con mayor probabilidad del modelo "
        "coincide con el resultado real."
    ),
    "entropy": (
        "**Entropía (Shannon, bits)**: medida de la 'apertura' del torneo. "
        "0 = un único campeón seguro. log₂(48) ≈ 5.58 = totalmente abierto. "
        "Va bajando a medida que el torneo se decide."
    ),
    "candidatos_efectivos": (
        "**Candidatos efectivos = 2^entropía**: número de equipos equiprobables que "
        "darían la misma entropía. Manera intuitiva de leer la incertidumbre."
    ),
    "surprise": (
        "**Sorpresa = 1 − p(resultado real)**: cuanto más alta, más improbable era el "
        "resultado según el modelo pre-partido. 0 = el modelo lo clavó."
    ),
    "regret": (
        "**Regret**: puntos esperados que dejas sobre la mesa al elegir tu pick en lugar "
        "del favorito del modelo. Alto = porra muy contrarian (puede ser estratégico)."
    ),
    "sharpe": (
        "**Sharpe (porra)**: media de puntos / desviación estándar a lo largo de las "
        "10.000 simulaciones. Más alto = mejor relación retorno-riesgo."
    ),
    "ev": (
        "**EV (Valor Esperado)**: probabilidad × puntos. Si tu pick tiene 30% de éxito "
        "y vale 10 pts, su EV es 3 pts."
    ),
    "xg": (
        "**xG (Expected Goals)**: goles esperados según el modelo Poisson basado en la "
        "diferencia de Elo. No es el xG de StatsBomb (que se calcula tiro a tiro)."
    ),
    "dixon_coles": (
        "**Dixon-Coles**: refinamiento del modelo Poisson independiente que corrige el "
        "sesgo en marcadores 0-0, 1-0, 0-1 y 1-1 con un parámetro tau · rho ≈ −0.10."
    ),
    "host_advantage": (
        "**Host advantage**: anfitriones (USA, Canadá, México) reciben +65 puntos Elo "
        "en sus partidos de grupos por jugar en casa."
    ),
    "half_life": (
        "**Half-life del Elo**: vida media (años) con la que decae el peso de los "
        "partidos antiguos al entrenar el rating. 8 = un partido de hace 8 años pesa la mitad."
    ),
    "p_win_league": (
        "**P(ganar liga)**: probabilidad de ganar la porra de amigos según 10.000 simulaciones."
    ),
    "expected_points": (
        "**Puntos esperados**: suma de prob × puntos sobre todas las casillas de la porra "
        "con las probabilidades actuales del modelo."
    ),
    "elo": (
        "**Elo**: rating dinámico inspirado en eloratings.net. Cada +50 Elo ≈ +20% de "
        "ganar un partido parejo. K base 50–60 para Mundiales."
    ),
}


def help_for(key: str) -> str:
    """Devuelve el texto del glosario para usar como `help=` en widgets de Streamlit."""
    return GLOSSARY.get(key, "")


def short(key: str) -> str:
    """Versión corta (primera oración) para títulos de columnas, etc."""
    full = GLOSSARY.get(key, "")
    if not full: return ""
    return full.split(".")[0].replace("**", "")
