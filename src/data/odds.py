"""Cuotas de apuestas: carga data/processed/odds.json y deriva probabilidades.

El JSON lo genera `scripts/fetch_odds.py` (the-odds-api). Aquí calculamos la
probabilidad implícita del mercado SIN vig (margen de la casa), normalizando, y
el helper de value/EV para comparar con el modelo.

Devig por normalización proporcional: prob_i = imp_i / Σ imp. `imp` es la media
entre casas de 1/cuota. Para el campeón Σ corre sobre los 48 equipos; para un
partido sobre {local, empate, visitante}.

Value de una apuesta a la MEJOR cuota disponible `o` con prob real `p` (modelo):
EV de 1€ apostado = p·o − 1. Si EV > 0 el modelo dice que la apuesta es rentable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ODDS_PATH = ROOT / "data" / "processed" / "odds.json"


def load_odds() -> dict | None:
    """Lee odds.json crudo (o None si no existe / está corrupto)."""
    if not ODDS_PATH.exists():
        return None
    try:
        return json.loads(ODDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _mtime() -> float:
    try:
        return ODDS_PATH.stat().st_mtime
    except OSError:
        return 0.0


def has_odds() -> bool:
    data = load_odds()
    return bool(data and (data.get("champion") or data.get("matches")))


def freshness(now: datetime | None = None) -> dict | None:
    """Metadatos de frescura: fecha de captura, antigüedad en horas, cuota restante."""
    data = load_odds()
    if not data:
        return None
    age_h = None
    stamp = data.get("fetched_at_utc")
    if stamp:
        try:
            t = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            now = now or datetime.now(timezone.utc)
            age_h = (now - t).total_seconds() / 3600.0
        except Exception:
            age_h = None
    return {
        "fetched_at": data.get("fetched_at"),
        "fetched_at_utc": stamp,
        "age_hours": age_h,
        "regions": data.get("regions"),
        "requests_remaining": data.get("requests_remaining"),
        "n_champion": len(data.get("champion") or {}),
        "n_matches": len(data.get("matches") or {}),
    }


# ── caché por mtime: recalcula solo si el fichero cambió ───────────────────
@lru_cache(maxsize=4)
def _champion_cached(_mtime_key: float) -> dict[str, dict]:
    data = load_odds() or {}
    champ = data.get("champion") or {}
    total = sum(v.get("imp", 0.0) for v in champ.values()) or 1.0
    out: dict[str, dict] = {}
    for team, v in champ.items():
        imp = v.get("imp", 0.0)
        out[team] = {
            "p_market": imp / total,          # prob sin vig (normalizada entre los 48)
            "best": v.get("best"),            # mejor cuota decimal disponible
            "n_books": v.get("n_books", 0),
        }
    return out


def market_champion_probs() -> dict[str, dict]:
    """{equipoES: {p_market, best, n_books}} — prob de campeón del mercado, sin vig."""
    return _champion_cached(_mtime())


@lru_cache(maxsize=4)
def _matches_cached(_mtime_key: float) -> dict[str, dict]:
    data = load_odds() or {}
    out: dict[str, dict] = {}
    for key, m in (data.get("matches") or {}).items():
        try:
            ih, ix, ia = m["h"]["imp"], m["x"]["imp"], m["a"]["imp"]
        except (KeyError, TypeError):
            continue
        s = (ih + ix + ia) or 1.0
        out[key] = {
            "home": m.get("home"), "away": m.get("away"),
            "commence_time": m.get("commence_time"),
            "n_books": m.get("n_books", 0),
            "p_h": ih / s, "p_x": ix / s, "p_a": ia / s,    # 1X2 sin vig
            "best_h": m["h"].get("best"), "best_x": m["x"].get("best"),
            "best_a": m["a"].get("best"),
            "vig": s - 1.0,                                  # margen de la casa
        }
    return out


def market_match_probs() -> dict[str, dict]:
    """{'LocalES vs VisitanteES': {home, away, p_h/p_x/p_a (sin vig), best_*, vig, ...}}."""
    return _matches_cached(_mtime())


def match_by_pair() -> dict[frozenset, dict]:
    """Igual que market_match_probs pero indexado por {local, visitante} (orden-agnóstico)."""
    out: dict[frozenset, dict] = {}
    for m in market_match_probs().values():
        if m.get("home") and m.get("away"):
            out[frozenset((m["home"], m["away"]))] = m
    return out


def ev(model_p: float, best_odds: float | None) -> float | None:
    """Valor esperado de 1€ apostado a `best_odds` con prob real `model_p`: p·o − 1."""
    if not best_odds or best_odds <= 1.0:
        return None
    return model_p * best_odds - 1.0
