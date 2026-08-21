"""Mapeo entre nombres de equipo en el dataset (ingles) y nombres en espanol del Excel."""

# Dataset (ingles) -> Espanol (como aparece en el Excel de la porra)
EN_TO_ES: dict[str, str] = {
    "Mexico": "Mexico",
    "South Africa": "Sudafrica",
    "South Korea": "Corea del Sur",
    "Czech Republic": "Rep. Checa",
    "Canada": "Canada",
    "Bosnia and Herzegovina": "Bosnia Herz.",
    "Qatar": "Catar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haiti",
    "Scotland": "Escocia",
    "United States": "Estados Unidos",
    "Paraguay": "Paraguay",
    "Australia": "Australia",
    "Turkey": "Turquia",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Ivory Coast": "Costa Marfil",
    "Ecuador": "Ecuador",
    "Netherlands": "Paises Bajos",
    "Japan": "Japon",
    "Sweden": "Suecia",
    "Tunisia": "Tunez",
    "Belgium": "Belgica",
    "Egypt": "Egipto",
    "Iran": "Iran",
    "New Zealand": "Nueva Zelanda",
    "Spain": "Espana",
    "Cape Verde": "Cabo Verde",
    "Saudi Arabia": "Arabia Saudi",
    "Uruguay": "Uruguay",
    "France": "Francia",
    "Senegal": "Senegal",
    "Iraq": "Irak",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Algeria": "Argelia",
    "Austria": "Austria",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "DR Congo": "R.D. Congo",
    "Uzbekistan": "Uzbekistan",
    "Colombia": "Colombia",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Ghana": "Ghana",
    "Panama": "Panama",
}

ES_TO_EN: dict[str, str] = {v: k for k, v in EN_TO_ES.items()}


def to_es(name: str) -> str:
    return EN_TO_ES.get(name, name)


def to_en(name: str) -> str:
    return ES_TO_EN.get(name, name)


# ============================================================================
# Nombres para MOSTRAR
# ----------------------------------------------------------------------------
# Las claves internas van sin acentos a propósito ("Espana"): son claves de
# diccionario y de JSON, y tocarlas rompería lookups por todo el repo. Pero lo
# que lee una persona debe estar bien escrito. Esta capa se aplica SOLO al
# pintar, nunca al indexar.
# ============================================================================
DISPLAY_NAMES: dict[str, str] = {
    "Espana": "España",
    "Belgica": "Bélgica",
    "Paises Bajos": "Países Bajos",
    "Arabia Saudi": "Arabia Saudí",
    "Tunez": "Túnez",
    "Turquia": "Turquía",
    "Japon": "Japón",
    "Iran": "Irán",
    "Panama": "Panamá",
    "Sudafrica": "Sudáfrica",
    "Mexico": "México",
    "Canada": "Canadá",
    "Uzbekistan": "Uzbekistán",
    "Haiti": "Haití",
    "Rep. Checa": "Chequia",
    "Bosnia Herz.": "Bosnia y Herz.",
}


def display(name: str | None) -> str:
    """Nombre bien escrito para pintar en pantalla. Nunca para indexar."""
    if not name:
        return ""
    return DISPLAY_NAMES.get(name, name)
