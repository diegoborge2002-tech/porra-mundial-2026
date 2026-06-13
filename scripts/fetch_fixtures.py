"""Trae fixtures y resultados del Mundial 2026 desde football-data.org.

Conservador: por defecto SOLO informa (dry-run). Con --apply escribe los horarios
en hora de España en data/processed/kickoff_times.json (merge). Los resultados se
imprimen para revisión; registrarlos sigue siendo cosa de scripts/dia.py.

Token (NUNCA en el repo): variable de entorno FOOTBALL_DATA_TOKEN o el fichero
~/.config/porra/football_data.token.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    MADRID = ZoneInfo("Europe/Madrid")
except Exception:
    MADRID = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data.team_names import EN_TO_ES          # noqa: E402
from src.tournament.groups import ALL_TEAMS        # noqa: E402

KICKOFF_PATH = ROOT / "data" / "processed" / "kickoff_times.json"
API = "https://api.football-data.org/v4/competitions/WC/matches"

# API (inglés) -> nombre de la app (español) para los que EN_TO_ES no clava
OVERRIDES = {
    "United States": "Estados Unidos", "Korea Republic": "Corea del Sur",
    "Czechia": "Rep. Checa", "Netherlands": "Paises Bajos", "IR Iran": "Iran",
    "Côte d'Ivoire": "Costa Marfil", "Cape Verde Islands": "Cabo Verde",
    "Congo DR": "R.D. Congo", "Bosnia-Herzegovina": "Bosnia Herz.",
    "Qatar": "Catar", "Saudi Arabia": "Arabia Saudi", "Curaçao": "Curazao",
    "Türkiye": "Turquia", "South Africa": "Sudafrica", "New Zealand": "Nueva Zelanda",
}


def _token() -> str:
    t = os.environ.get("FOOTBALL_DATA_TOKEN")
    if t:
        return t.strip()
    f = pathlib.Path.home() / ".config" / "porra" / "football_data.token"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("❌ Falta el token: define FOOTBALL_DATA_TOKEN o crea "
             "~/.config/porra/football_data.token")


def _es(name: str | None) -> str | None:
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


def main() -> None:
    apply = "--apply" in sys.argv
    req = urllib.request.Request(API, headers={"X-Auth-Token": _token()})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    matches = data.get("matches", [])
    print(f"{len(matches)} partidos devueltos por la API")

    kickoffs: dict[str, str] = {}
    finished: list[tuple] = []
    unmapped: set[str] = set()

    for m in matches:
        hn, an = m["homeTeam"]["name"], m["awayTeam"]["name"]
        h, a = _es(hn), _es(an)
        if hn and not h:
            unmapped.add(hn)
        if an and not a:
            unmapped.add(an)
        utc = m.get("utcDate")
        if utc and h and a and MADRID:
            dt = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(MADRID)
            kickoffs[f"{h} vs {a}"] = dt.strftime("%Y-%m-%dT%H:%M")
        if m.get("status") == "FINISHED":
            sc = m["score"]["fullTime"]
            finished.append((h or hn, sc.get("home"), sc.get("away"), a or an))

    print(f"Horarios (hora ES) mapeados: {len(kickoffs)}")
    if unmapped:
        print("⚠️  Equipos sin mapear (añadir a OVERRIDES):", sorted(unmapped))
    print(f"\nPartidos FINISHED ({len(finished)}):")
    for h, gh, ga, a in finished:
        print(f"  {h} {gh}-{ga} {a}")

    if apply and kickoffs:
        existing = json.loads(KICKOFF_PATH.read_text()) if KICKOFF_PATH.exists() else {}
        existing.update(kickoffs)
        KICKOFF_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        print(f"\n✓ kickoff_times.json actualizado ({len(existing)} entradas)")
    elif kickoffs:
        print("\n(dry-run — añade --apply para escribir los horarios)")


if __name__ == "__main__":
    main()
