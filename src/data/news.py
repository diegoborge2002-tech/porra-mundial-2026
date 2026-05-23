"""Sistema de noticias / lesiones / cambios de plantilla para el Mundial.

Cada noticia: {id, fecha, equipo, tipo, texto, elo_delta, expires_at, active}

- `tipo`: lesion | baja | cambio_tecnico | alineacion | positivo | otro
- `elo_delta`: ajuste temporal (puntos Elo) sumado mientras la noticia este activa
- `expires_at`: fecha ISO (YYYY-MM-DD) hasta la que aplica el delta; None = sin expirar
- `active`: el usuario puede desactivar sin borrar
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime, date


NEWS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "news.json"

NEWS_TYPES: dict[str, tuple[str, str]] = {
    "lesion": ("🤕", "Lesión"),
    "baja": ("❌", "Baja confirmada"),
    "cambio_tecnico": ("👔", "Cambio técnico"),
    "alineacion": ("📋", "Convocatoria / Once"),
    "positivo": ("⭐", "Refuerzo / Buenas noticias"),
    "otro": ("📰", "Otro"),
}


@dataclass
class NewsItem:
    id: str
    fecha: str  # YYYY-MM-DD HH:MM
    equipo: str
    tipo: str
    texto: str
    elo_delta: float = 0.0
    expires_at: str | None = None  # YYYY-MM-DD o None
    active: bool = True


def _load_raw() -> list[dict]:
    if not NEWS_PATH.exists():
        return []
    try:
        return json.loads(NEWS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_raw(items: list[dict]) -> None:
    NEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEWS_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False))


def _is_expired(item: dict) -> bool:
    exp = item.get("expires_at")
    if not exp:
        return False
    return exp < date.today().isoformat()


def list_news(only_active: bool = False, only_team: str | None = None) -> list[NewsItem]:
    """Devuelve noticias ordenadas por fecha desc."""
    out: list[NewsItem] = []
    for raw in _load_raw():
        item = NewsItem(
            id=raw.get("id", ""),
            fecha=raw.get("fecha", ""),
            equipo=raw.get("equipo", ""),
            tipo=raw.get("tipo", "otro"),
            texto=raw.get("texto", ""),
            elo_delta=float(raw.get("elo_delta", 0.0) or 0.0),
            expires_at=raw.get("expires_at"),
            active=bool(raw.get("active", True)),
        )
        if only_active and (not item.active or _is_expired(raw)):
            continue
        if only_team and item.equipo != only_team:
            continue
        out.append(item)
    out.sort(key=lambda i: i.fecha, reverse=True)
    return out


def add_news(equipo: str, tipo: str, texto: str,
             elo_delta: float = 0.0, expires_at: str | None = None) -> NewsItem:
    items = _load_raw()
    item = NewsItem(
        id=str(uuid.uuid4())[:8],
        fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
        equipo=equipo, tipo=tipo, texto=texto,
        elo_delta=float(elo_delta),
        expires_at=expires_at, active=True,
    )
    items.append(asdict(item))
    _save_raw(items)
    return item


def delete_news(news_id: str) -> bool:
    items = _load_raw()
    new_items = [i for i in items if i.get("id") != news_id]
    if len(new_items) != len(items):
        _save_raw(new_items)
        return True
    return False


def toggle_active(news_id: str) -> bool:
    items = _load_raw()
    for i in items:
        if i.get("id") == news_id:
            i["active"] = not i.get("active", True)
            _save_raw(items)
            return True
    return False


def get_active_deltas() -> dict[str, float]:
    """Devuelve {equipo: suma de elo_deltas de noticias activas no expiradas}."""
    out: dict[str, float] = {}
    for n in list_news(only_active=True):
        if n.elo_delta:
            out[n.equipo] = out.get(n.equipo, 0.0) + n.elo_delta
    return out
