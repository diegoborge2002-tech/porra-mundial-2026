"""Base de datos y simulador probabilístico de goleadores (Pichichi)."""

from __future__ import annotations
import numpy as np

PLAYERS_DB: dict[str, dict[str, float]] = {
    "Mexico": {"Santi Gimenez": 0.50, "Hirving Lozano": 0.30, "Edson Alvarez": 0.20},
    "Sudafrica": {"Lyle Foster": 0.50, "Percy Tau": 0.30, "Teboho Mokoena": 0.20},
    "Corea del Sur": {"Heung-min Son": 0.60, "Hee-chan Hwang": 0.25, "Kang-in Lee": 0.15},
    "Rep. Checa": {"Patrik Schick": 0.55, "Tomas Soucek": 0.25, "Adam Hlozek": 0.20},
    "Canada": {"Jonathan David": 0.50, "Alphonso Davies": 0.30, "Cyle Larin": 0.20},
    "Bosnia Herz.": {"Edin Dzeko": 0.50, "Ermedin Demirovic": 0.30, "Miralem Pjanic": 0.20},
    "Catar": {"Akram Afif": 0.50, "Almoez Ali": 0.35, "Hassan Al-Haydos": 0.15},
    "Suiza": {"Breel Embolo": 0.40, "Zeki Amdouni": 0.35, "Xherdan Shaqiri": 0.25},
    "Brasil": {"Vinicius Jr": 0.45, "Rodrygo": 0.35, "Neymar Jr": 0.20},
    "Marruecos": {"Youssef En-Nesyri": 0.45, "Hakim Ziyech": 0.30, "Brahim Diaz": 0.25},
    "Haiti": {"Frantzdy Pierrot": 0.50, "Duckens Nazon": 0.35, "Louicius Don Deedson": 0.15},
    "Escocia": {"Scott McTominay": 0.45, "Che Adams": 0.35, "John McGinn": 0.20},
    "Estados Unidos": {"Christian Pulisic": 0.45, "Folarin Balogun": 0.35, "Timothy Weah": 0.20},
    "Paraguay": {"Antonio Sanabria": 0.45, "Julio Enciso": 0.30, "Miguel Almiron": 0.25},
    "Australia": {"Mitchell Duke": 0.45, "Craig Goodwin": 0.30, "Jackson Irvine": 0.25},
    "Turquia": {"Arda Güler": 0.40, "Baris Alper Yilmaz": 0.35, "Kerem Akturkoglu": 0.25},
    "Alemania": {"Kai Havertz": 0.40, "Niclas Füllkrug": 0.35, "Florian Wirtz": 0.25},
    "Curazao": {"Rangelo Janga": 0.50, "Juninho Bacuna": 0.30, "Kenji Gorre": 0.20},
    "Costa Marfil": {"Sebastian Haller": 0.45, "Simon Adingra": 0.30, "Oumar Diakite": 0.25},
    "Ecuador": {"Enner Valencia": 0.50, "Kendry Paez": 0.30, "Jordy Caicedo": 0.20},
    "Paises Bajos": {"Memphis Depay": 0.40, "Cody Gakpo": 0.35, "Xavi Simons": 0.25},
    "Japon": {"Ayase Ueda": 0.45, "Takumi Minamino": 0.30, "Kaoru Mitoma": 0.25},
    "Suecia": {"Viktor Gyökeres": 0.45, "Alexander Isak": 0.35, "Dejan Kulusevski": 0.20},
    "Tunez": {"Youssef Msakni": 0.45, "Elias Achouri": 0.30, "Haythem Jouini": 0.25},
    "Belgica": {"Romelu Lukaku": 0.50, "Lois Openda": 0.30, "Leandro Trossard": 0.20},
    "Egipto": {"Mohamed Salah": 0.55, "Mostafa Mohamed": 0.30, "Omar Marmoush": 0.15},
    "Iran": {"Mehdi Taremi": 0.45, "Sardar Azmoun": 0.40, "Alireza Jahanbakhsh": 0.15},
    "Nueva Zelanda": {"Chris Wood": 0.55, "Ben Waine": 0.25, "Kosta Barbarouses": 0.20},
    "Espana": {"Lamine Yamal": 0.35, "Nico Williams": 0.30, "Alvaro Morata": 0.35},
    "Cabo Verde": {"Ryan Mendes": 0.45, "Garry Rodrigues": 0.35, "Bebé": 0.20},
    "Arabia Saudi": {"Salem Al-Dawsari": 0.45, "Firas Al-Buraikan": 0.35, "Saleh Al-Shehri": 0.20},
    "Uruguay": {"Darwin Nuñez": 0.50, "Federico Valverde": 0.25, "Luis Suarez": 0.25},
    "Francia": {"Kylian Mbappé": 0.55, "Antoine Griezmann": 0.25, "Olivier Giroud": 0.20},
    "Senegal": {"Sadio Mané": 0.45, "Nicolas Jackson": 0.35, "Ismaila Sarr": 0.20},
    "Irak": {"Aymen Hussein": 0.50, "Mohanad Ali": 0.30, "Ali Jasim": 0.20},
    "Noruega": {"Erling Haaland": 0.65, "Martin Ødegaard": 0.20, "Alexander Sørloth": 0.15},
    "Argentina": {"Lionel Messi": 0.45, "Lautaro Martinez": 0.35, "Julian Alvarez": 0.20},
    "Argelia": {"Baghdad Bounedjah": 0.45, "Riyad Mahrez": 0.35, "Amine Gouiri": 0.20},
    "Austria": {"Michael Gregoritsch": 0.45, "Marcel Sabitzer": 0.35, "Christoph Baumgartner": 0.20},
    "Jordania": {"Musa Al-Taamari": 0.45, "Yazan Al-Naimat": 0.35, "Ali Olwan": 0.20},
    "Portugal": {"Cristiano Ronaldo": 0.45, "Bruno Fernandes": 0.35, "Rafael Leão": 0.20},
    "R.D. Congo": {"Yoane Wissa": 0.45, "Cedric Bakambu": 0.35, "Meschack Elia": 0.20},
    "Uzbekistan": {"Eldor Shomurodov": 0.50, "Oston Urunov": 0.30, "Abbosbek Fayzullaev": 0.20},
    "Colombia": {"Luis Diaz": 0.45, "Jhon Duran": 0.30, "James Rodriguez": 0.25},
    "Inglaterra": {"Harry Kane": 0.45, "Jude Bellingham": 0.30, "Bukayo Saka": 0.25},
    "Croacia": {"Andrej Kramaric": 0.45, "Bruno Petkovic": 0.30, "Luka Modric": 0.25},
    "Ghana": {"Mohammed Kudus": 0.45, "Inaki Williams": 0.35, "Jordan Ayew": 0.20},
    "Panama": {"Ismael Diaz": 0.45, "José Fajardo": 0.35, "Cecilio Waterman": 0.20},
}

def simulate_goalscorers(team_goals_dict: dict[str, int], rng) -> dict[str, int]:
    """Distribuye los goles marcados por cada equipo entre sus jugadores estrella.
    
    Devuelve dict {jugador: goles}.
    """
    player_goals: dict[str, int] = {}
    for team, goals in team_goals_dict.items():
        if goals <= 0:
            continue
        
        # Si el equipo no está en nuestra DB, usamos un fallback genérico
        players_info = PLAYERS_DB.get(team)
        if not players_info:
            players_info = {f"Delantero {team}": 1.0}
            
        players = list(players_info.keys())
        weights = list(players_info.values())
        
        # Normalizar pesos
        total_w = sum(weights)
        if total_w > 0:
            pvals = [w / total_w for w in weights]
        else:
            pvals = [1.0 / len(players)] * len(players)
            
        # Muestreo multinomial
        goals_dist = rng.multinomial(goals, pvals)
        for player, g in zip(players, goals_dist):
            if g > 0:
                player_goals[player] = player_goals.get(player, 0) + int(g)
                
    return player_goals
