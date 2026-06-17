"""Trae cuotas de apuestas del Mundial 2026 desde the-odds-api.com.

Dos mercados:
  - `soccer_fifa_world_cup_winner`  → outrights (ganador del torneo, 48 equipos)
  - `soccer_fifa_world_cup`          → h2h (1X2 de los partidos próximos)

Agrega entre casas de apuestas: por cada resultado guarda la MEJOR cuota
decimal disponible (`best`, para calcular value/EV con el mejor precio real) y
la probabilidad implícita media (`imp` = media de 1/cuota entre casas, para el
consenso del mercado). El cálculo de probabilidad sin vig y la comparación con
el modelo viven en `src/data/odds.py`.

Conservador: por defecto SOLO informa (dry-run). Con --apply escribe
data/processed/odds.json (lo lee la web). Cada refresco gasta ~2 créditos
(1 por mercado); el free tier da 500/mes → de sobra para 2 refrescos/día.

Token (NUNCA en el repo): variable de entorno ODDS_API_TOKEN o el fichero
~/.config/porra/odds_api.token.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    MADRID = ZoneInfo("Europe/Madrid")
except Exception:
    MADRID = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data.team_names import EN_TO_ES          # noqa: E402
from src.tournament.groups import ALL_TEAMS        # noqa: E402

ODDS_PATH = ROOT / "data" / "processed" / "odds.json"
BASE = "https://api.the-odds-api.com/v4/sports"
WINNER_KEY = "soccer_fifa_world_cup_winner"
MATCHES_KEY = "soccer_fifa_world_cup"
REGIONS = "eu"

# Nombres de la API (inglés) -> nombre de la app (español) que EN_TO_ES no clava.
OVERRIDES = {
    "USA": "Estados Unidos",
    "Bosnia & Herzegovina": "Bosnia Herz.",
}


def _token() -> str:
    t = os.environ.get("ODDS_API_TOKEN")
    if t:
        return t.strip()
    f = pathlib.Path.home() / ".config" / "porra" / "odds_api.token"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("❌ Falta el token: define ODDS_API_TOKEN o crea "
             "~/.config/porra/odds_api.token")


def _es(name: str | None) -> str | None:
    """Nombre de equipo de la API → nombre español de la app (o None si no casa)."""
    if not name:
        return None
    if name in OVERRIDES:
        return OVERRIDES[name]
    cand = EN_TO_ES.get(name, name)
    if cand in ALL_TEAMS:
        return cand
    for t in ALL_TEAMS:
        if t.lower() == cand.lower():
            return t
    return None


def _fetch(key: str, markets: str) -> tuple[list, str | None, str | None]:
    tok = _token()
    url = (f"{BASE}/{key}/odds/?apiKey={tok}&regions={REGIONS}"
           f"&markets={markets}&oddsFormat=decimal")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:
        remaining = r.headers.get("x-requests-remaining")
        used = r.headers.get("x-requests-used")
        data = json.load(r)
    return data, remaining, used


def _aggregate(odds_by_outcome: dict[str, list[float]]) -> dict[str, dict]:
    """Para cada resultado: mejor cuota (max) y prob implícita media (media de 1/cuota)."""
    out: dict[str, dict] = {}
    for name, prices in odds_by_outcome.items():
        prices = [p for p in prices if p and p > 1.0]
        if not prices:
            continue
        imp = sum(1.0 / p for p in prices) / len(prices)
        out[name] = {
            "best": round(max(prices), 3),
            "imp": round(imp, 5),
            "n_books": len(prices),
        }
    return out


def _parse_winner(events: list) -> dict[str, dict]:
    """Outrights del campeón → {equipoES: {best, imp, n_books}}."""
    by_team: dict[str, list[float]] = {}
    unmapped: set[str] = set()
    for ev in events:
        for bk in ev.get("bookmakers", []):
            for m in bk.get("markets", []):
                if m.get("key") != "outrights":   # ignora outrights_lay (cuotas de lay)
                    continue
                for o in m.get("outcomes", []):
                    es = _es(o.get("name"))
                    if es is None:
                        unmapped.add(o.get("name", "?"))
                        continue
                    by_team.setdefault(es, []).append(o.get("price"))
    if unmapped:
        print(f"  ⚠ equipos sin mapear (winner): {sorted(unmapped)}")
    return _aggregate(by_team)


def _parse_matches(events: list) -> dict[str, dict]:
    """h2h → {'LocalES vs VisitanteES': {commence_time, home, away, h, x, a, n_books}}."""
    matches: dict[str, dict] = {}
    unmapped: set[str] = set()
    for ev in events:
        home_es = _es(ev.get("home_team"))
        away_es = _es(ev.get("away_team"))
        if home_es is None or away_es is None:
            for n in (ev.get("home_team"), ev.get("away_team")):
                if _es(n) is None:
                    unmapped.add(n or "?")
            continue
        # Recolecta cuotas por resultado (home / draw / away) entre casas.
        buckets: dict[str, list[float]] = {"h": [], "x": [], "a": []}
        n_books = 0
        for bk in ev.get("bookmakers", []):
            book_has = False
            for m in bk.get("markets", []):
                if m.get("key") != "h2h":
                    continue
                for o in m.get("outcomes", []):
                    nm, price = o.get("name"), o.get("price")
                    if nm == "Draw":
                        buckets["x"].append(price); book_has = True
                    elif _es(nm) == home_es:
                        buckets["h"].append(price); book_has = True
                    elif _es(nm) == away_es:
                        buckets["a"].append(price); book_has = True
            if book_has:
                n_books += 1
        agg = _aggregate({k: v for k, v in buckets.items()})
        if not all(k in agg for k in ("h", "x", "a")):
            continue  # mercado incompleto, lo saltamos
        matches[f"{home_es} vs {away_es}"] = {
            "commence_time": ev.get("commence_time"),
            "home": home_es, "away": away_es,
            "h": agg["h"], "x": agg["x"], "a": agg["a"],
            "n_books": n_books,
        }
    if unmapped:
        print(f"  ⚠ equipos sin mapear (matches): {sorted(unmapped)}")
    return matches


def main() -> None:
    apply = "--apply" in sys.argv
    print(f"📈 the-odds-api · región={REGIONS} · {'APLICAR' if apply else 'dry-run (usa --apply para escribir)'}")

    win_events, rem1, used1 = _fetch(WINNER_KEY, "outrights")
    champion = _parse_winner(win_events)
    print(f"  campeón: {len(champion)} equipos con cuota")

    match_events, rem2, used2 = _fetch(MATCHES_KEY, "h2h")
    matches = _parse_matches(match_events)
    print(f"  partidos: {len(matches)} con cuotas 1X2")

    remaining = rem2 or rem1
    used = used2 or used1
    print(f"  créditos → usados:{used} restantes:{remaining}")

    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(MADRID) if MADRID else now_utc
    payload = {
        "fetched_at": now_local.strftime("%Y-%m-%dT%H:%M:%S"),
        "fetched_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regions": REGIONS,
        "requests_remaining": int(remaining) if remaining and remaining.isdigit() else None,
        "requests_used": int(used) if used and used.isdigit() else None,
        "champion": champion,
        "matches": matches,
    }

    # Vista previa: top-8 favoritos del mercado (campeón)
    if champion:
        tot = sum(v["imp"] for v in champion.values()) or 1.0
        top = sorted(champion.items(), key=lambda kv: -kv[1]["imp"])[:8]
        print("  top mercado (campeón, prob sin vig):")
        for t, v in top:
            print(f"    {t:16s} {v['imp']/tot*100:5.1f}%  (mejor cuota {v['best']})")

    if apply:
        ODDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        ODDS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ escrito {ODDS_PATH.relative_to(ROOT)}")
    else:
        print("ℹ️  dry-run: NO se ha escrito nada. Repite con --apply.")


if __name__ == "__main__":
    main()
