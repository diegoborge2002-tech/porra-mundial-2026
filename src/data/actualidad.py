"""Datos de 'actualidad' del Mundial: goleadores, MVPs y storylines.

Dos tipos de dato:
  • Externos (goleadores, MVP) → no vienen en la API gratuita; se cotejan por
    web en cada 'actualiza' y se guardan en data/processed/actualidad.json.
  • Derivados (en forma, movimientos de la porra, titulares automáticos) → se
    calculan al vuelo desde real_results.json y los snapshots, sin fuente externa,
    así que siempre son de calidad y están al día.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.tournament.groups import GROUPS, HOST_NATIONS
from src.model.elo import HOME_ADVANTAGE
from src.model.poisson import expected_goals_ensemble
from src.model.match_probs import match_outcome_probs

ROOT = Path(__file__).resolve().parent.parent.parent
ACTUALIDAD_PATH = ROOT / "data" / "processed" / "actualidad.json"
SNAP_DIR = ROOT / "data" / "processed" / "snapshots"


# ---------------------------------------------------------------- externos ---
def load_actualidad() -> dict:
    if ACTUALIDAD_PATH.exists():
        try:
            return json.loads(ACTUALIDAD_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"updated": "", "scorers": [], "mvps": []}


def top_scorers(limit: int = 20) -> list[dict]:
    data = load_actualidad().get("scorers", [])
    return sorted(data, key=lambda s: (-s.get("goals", 0), s.get("player", "")))[:limit]


def recent_mvps(limit: int = 8) -> list[dict]:
    data = load_actualidad().get("mvps", [])
    return sorted(data, key=lambda m: m.get("date", ""), reverse=True)[:limit]


# --------------------------------------------------------------- derivados ---
def _team_group(team: str) -> str:
    for g, teams in GROUPS.items():
        if team in teams:
            return g
    return "?"


def _host_adv(home: str, away: str) -> float:
    h, a = home in HOST_NATIONS, away in HOST_NATIONS
    if h and not a:
        return HOME_ADVANTAGE
    if a and not h:
        return -HOME_ADVANTAGE
    return 0.0


def _played(real_results: dict) -> list[tuple[str, str, int, int]]:
    """Lista (home, away, gh, ga) de los partidos de grupos ya jugados."""
    out = []
    for key, score in (real_results.get("group_matches") or {}).items():
        if score and len(score) == 2 and " vs " in key:
            h, a = key.split(" vs ", 1)
            out.append((h, a, int(score[0]), int(score[1])))
    return out


def form_table(elo: dict[str, float], real_results: dict, limit: int = 6) -> dict:
    """Rendimiento real vs esperado: puntos sacados menos los esperados por el
    modelo en los partidos jugados. Positivo = está rindiendo por encima.

    Devuelve {'risers': [...], 'fallers': [...]} con dicts
    {team, group, played, points, expected, delta}.
    """
    agg: dict[str, dict] = {}
    for home, away, gh, ga in _played(real_results):
        ha = _host_adv(home, away)
        lh, la = expected_goals_ensemble(
            elo.get(home, 1500.0), elo.get(away, 1500.0), home, away, home_advantage=ha)
        p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
        pts_h = 3 if gh > ga else (1 if gh == ga else 0)
        pts_a = 3 if ga > gh else (1 if gh == ga else 0)
        for team, pts, exp in ((home, pts_h, 3 * p_h + p_d), (away, pts_a, 3 * p_a + p_d)):
            d = agg.setdefault(team, {"team": team, "group": _team_group(team),
                                      "played": 0, "points": 0, "expected": 0.0})
            d["played"] += 1
            d["points"] += pts
            d["expected"] += exp
    rows = []
    for d in agg.values():
        d["delta"] = d["points"] - d["expected"]
        rows.append(d)
    rows.sort(key=lambda r: r["delta"], reverse=True)
    return {"risers": rows[:limit], "fallers": rows[::-1][:limit]}


def group_standings(real_results: dict, elo: dict[str, float]) -> dict[str, list[dict]]:
    """Clasificación en vivo de los 12 grupos desde los marcadores reales.

    Cada grupo → lista ordenada (puntos, dif. goles, goles a favor, Elo) de
    dicts {team, played, won, drawn, lost, gf, ga, gd, points}.
    """
    out: dict[str, list[dict]] = {}
    gm = real_results.get("group_matches") or {}
    for g, teams in GROUPS.items():
        stats = {t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                     "gf": 0, "ga": 0, "gd": 0, "points": 0} for t in teams}
        for i, ta in enumerate(teams):
            for tb in teams[i + 1:]:
                if f"{ta} vs {tb}" in gm:
                    (gh, ga), th, taw = gm[f"{ta} vs {tb}"], ta, tb
                elif f"{tb} vs {ta}" in gm:
                    (gh, ga), th, taw = gm[f"{tb} vs {ta}"], tb, ta
                else:
                    continue
                stats[th]["played"] += 1; stats[taw]["played"] += 1
                stats[th]["gf"] += gh; stats[th]["ga"] += ga
                stats[taw]["gf"] += ga; stats[taw]["ga"] += gh
                if gh > ga:
                    stats[th]["won"] += 1; stats[th]["points"] += 3; stats[taw]["lost"] += 1
                elif gh < ga:
                    stats[taw]["won"] += 1; stats[taw]["points"] += 3; stats[th]["lost"] += 1
                else:
                    stats[th]["drawn"] += 1; stats[taw]["drawn"] += 1
                    stats[th]["points"] += 1; stats[taw]["points"] += 1
        for s in stats.values():
            s["gd"] = s["gf"] - s["ga"]
        out[g] = sorted(stats.values(),
                        key=lambda s: (s["points"], s["gd"], s["gf"], elo.get(s["team"], 1500.0)),
                        reverse=True)
    return out


def champion_movers(limit: int = 6) -> dict | None:
    """Compara las probabilidades de campeón de los dos últimos snapshots.

    Devuelve {'date_prev','date_now','up':[(team,now,delta)],'down':[...]} o None.
    """
    if not SNAP_DIR.exists():
        return None
    snaps = sorted(SNAP_DIR.glob("*.json"))
    if len(snaps) < 2:
        return None
    prev = (json.loads(snaps[-2].read_text()).get("champion") or {})
    now = (json.loads(snaps[-1].read_text()).get("champion") or {})
    if not now:
        return None
    deltas = [(t, p, p - prev.get(t, 0.0)) for t, p in now.items()]
    up = sorted([d for d in deltas if d[2] > 0.0005], key=lambda x: -x[2])[:limit]
    down = sorted([d for d in deltas if d[2] < -0.0005], key=lambda x: x[2])[:limit]
    return {"date_prev": snaps[-2].stem, "date_now": snaps[-1].stem, "up": up, "down": down}


def auto_storylines(elo: dict[str, float], real_results: dict, limit: int = 6) -> list[dict]:
    """Titulares calculados desde los resultados: goleadas, festivales de goles y
    sorpresones (favorito que pincha). Cada uno: {emoji, text}.
    """
    played = _played(real_results)
    if not played:
        return []
    items: list[tuple[float, dict]] = []

    # Mayor goleada (diferencia de goles)
    h, a, gh, ga = max(played, key=lambda m: abs(m[2] - m[3]))
    if abs(gh - ga) >= 3:
        win, lose, gw, gl = (h, a, gh, ga) if gh > ga else (a, h, ga, gh)
        items.append((abs(gh - ga), {"emoji": "💥",
                      "text": f"Goleada de la jornada: {win} {gw}-{gl} {lose}."}))

    # Festival de goles (más goles totales)
    h, a, gh, ga = max(played, key=lambda m: m[2] + m[3])
    if gh + ga >= 5:
        items.append((gh + ga, {"emoji": "🎆",
                      "text": f"Festival de goles: {h} {gh}-{ga} {a} ({gh + ga} goles)."}))

    # Sorpresones: favorito (por Elo) que no ganó
    for home, away, gh, ga in played:
        ha = _host_adv(home, away)
        lh, la = expected_goals_ensemble(
            elo.get(home, 1500.0), elo.get(away, 1500.0), home, away, home_advantage=ha)
        p_h, p_d, p_a = match_outcome_probs(lh, la, use_dc=True)
        # favorito claro que pinchó
        if p_h >= 0.55 and gh <= ga:
            items.append((p_h, {"emoji": "😱",
                          "text": f"Sorpresón: {home} solo pudo {gh}-{ga} ante {away} "
                                  f"(era favorito al {p_h*100:.0f}%)."}))
        elif p_a >= 0.55 and ga <= gh:
            items.append((p_a, {"emoji": "😱",
                          "text": f"Sorpresón: {away} no pasó del {gh}-{ga} ante {home} "
                                  f"(era favorito al {p_a*100:.0f}%)."}))

    # ordenar por relevancia y deduplicar texto
    items.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, it in items:
        if it["text"] in seen:
            continue
        seen.add(it["text"])
        out.append(it)
        if len(out) >= limit:
            break
    return out
