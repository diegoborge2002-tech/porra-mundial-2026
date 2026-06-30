"""Construye el cuadro de eliminatorias (R32 → Final) desde los resultados reales.

Resuelve los cruces de Dieciseisavos a partir de las clasificaciones reales —
determinista cuando la fase de grupos está completa — y propaga los ganadores
registrados (`real_results.knockout_matches`) por las rondas siguientes. Para los
partidos aún por jugar con ambos equipos ya definidos, adjunta el resultado
esperado del ensemble (mismo motor que 🔮 Partidos).

La web no toca código para actualizar el cuadro: basta con registrar los KO con
`scripts/dia.py ko ...` y el bracket se rellena solo.
"""
from __future__ import annotations

from numpy.random import default_rng

from src.tournament.groups import HOST_NATIONS
from src.tournament.bracket import R16_FIFA, QF_FIFA, SF_FIFA, F_FIFA
from src.model.group_sim import simulate_all_groups
from src.model.tournament_sim import _resolve_r32_pairings
from src.model.elo import HOME_ADVANTAGE
from src.model.poisson import expected_goals_ensemble
from src.model.match_probs import match_outcome_probs, representative_score

ROUND_ORDER = ["r32", "r16", "qf", "sf", "final"]
ROUND_LABEL = {"r32": "Dieciseisavos", "r16": "Octavos", "qf": "Cuartos",
               "sf": "Semifinales", "final": "Final"}
ROUND_SHORT = {"r32": "16avos", "r16": "8vos", "qf": "Cuartos",
               "sf": "Semis", "final": "Final"}
FEEDERS = {"r16": R16_FIFA, "qf": QF_FIFA, "sf": SF_FIFA, "final": F_FIFA}


def _host_adv(home: str, away: str) -> float:
    h, a = home in HOST_NATIONS, away in HOST_NATIONS
    if h and not a:
        return HOME_ADVANTAGE
    if a and not h:
        return -HOME_ADVANTAGE
    return 0.0


def group_stage_complete(real: dict) -> bool:
    gm = real.get("group_matches") or {}
    return sum(1 for v in gm.values() if v) >= 72


def _expected(home: str, away: str, elo: dict) -> dict:
    ha = _host_adv(home, away)
    lh, la = expected_goals_ensemble(
        elo.get(home, 1500.0), elo.get(away, 1500.0), home, away, home_advantage=ha)
    p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
    (bh, ba), _ = representative_score(lh, la)
    return {"exp_home": bh, "exp_away": ba, "xg_home": lh, "xg_away": la,
            "p_home": p_h, "p_draw": p_d, "p_away": p_a}


def _leaf_order(fid: int, rnd: str) -> list[int]:
    """IDs de R32 (hojas) bajo un nodo, en orden vertical top→down del árbol."""
    if rnd == "r32":
        return [fid]
    fa, fb = FEEDERS[rnd][fid]
    prev = ROUND_ORDER[ROUND_ORDER.index(rnd) - 1]
    return _leaf_order(fa, prev) + _leaf_order(fb, prev)


def _side_layout(sf_id: int) -> dict[str, list[int]]:
    """Para una de las dos mitades (semifinal sf_id), los IDs de cada ronda en
    orden vertical coherente con el árbol."""
    layout: dict[str, list[int]] = {"sf": [sf_id]}
    # QF que alimentan esa semi
    qfs = list(SF_FIFA[sf_id])
    layout["qf"] = qfs
    r16s: list[int] = []
    for q in qfs:
        r16s.extend(QF_FIFA[q])
    layout["r16"] = r16s
    r32s: list[int] = []
    for fid in r16s:
        r32s.extend(R16_FIFA[fid])
    layout["r32"] = r32s
    return layout


# Mitades del cuadro (104 = Final → 101 izquierda, 102 derecha)
LEFT_SF, RIGHT_SF = F_FIFA[104]
LAYOUT_LEFT = _side_layout(LEFT_SF)
LAYOUT_RIGHT = _side_layout(RIGHT_SF)


def build_bracket(real: dict, elo: dict) -> dict | None:
    """Devuelve el cuadro completo o None si la fase de grupos no ha terminado.

    {
      'matches': {fifa_id: match_dict},
      'layout_left': {round: [ids]}, 'layout_right': {...}, 'final': 104,
      'champion': team|None,
    }
    match_dict: {fifa_id, round, home, away, home_goals, away_goals, winner,
                 pens(bool), played(bool), expected(dict|None)}
    """
    if not group_stage_complete(real):
        return None

    standings, thirds = simulate_all_groups(elo, default_rng(0), real)
    r32_pairings = _resolve_r32_pairings(standings, thirds)
    ko = real.get("knockout_matches") or {}

    matches: dict[int, dict] = {}
    winners: dict[int, str] = {}

    def make(fid: int, rnd: str, home, away) -> None:
        e = (ko.get(rnd) or {}).get(str(fid))
        m = {"fifa_id": fid, "round": rnd, "home": home, "away": away,
             "home_goals": None, "away_goals": None, "winner": None,
             "pens": False, "played": False, "expected": None}
        if e:
            m["home_goals"] = e.get("home_score")
            m["away_goals"] = e.get("away_score")
            m["winner"] = e.get("winner")
            m["played"] = m["home_goals"] is not None
            if m["played"] and m["home_goals"] == m["away_goals"] and m["winner"]:
                m["pens"] = True
            if m["winner"]:
                winners[fid] = m["winner"]
        elif home and away:
            m["expected"] = _expected(home, away, elo)
        matches[fid] = m

    for fid, (h, a) in r32_pairings.items():
        make(fid, "r32", h, a)
    for rnd in ("r16", "qf", "sf", "final"):
        for fid, (fa, fb) in FEEDERS[rnd].items():
            make(fid, rnd, winners.get(fa), winners.get(fb))

    champion = winners.get(104)
    return {"matches": matches, "layout_left": LAYOUT_LEFT,
            "layout_right": LAYOUT_RIGHT, "final": 104, "champion": champion,
            "r32_pairings": r32_pairings}


def bracket_progress(real: dict) -> dict:
    """Resumen para cabeceras: nº jugados/total por ronda + equipos eliminados."""
    ko = real.get("knockout_matches") or {}
    totals = {"r32": 16, "r16": 8, "qf": 4, "sf": 2, "final": 1}
    played = {r: len(ko.get(r) or {}) for r in totals}
    return {"played": played, "totals": totals}
