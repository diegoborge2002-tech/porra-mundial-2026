"""Portada del Mundial terminado: TODO en una sola pantalla.

Premisa de diseño: la gente entra desde un enlace de WhatsApp y le dedica
**treinta segundos**. En ese tiempo tiene que quedarle todo:

  1. España campeona (el hecho)
  2. Que el modelo la puso primera el 23 de mayo (el gancho: lo único que
     no saben ya)
  3. 64,4 % de acierto en 104 partidos (la prueba de que no fue suerte)

Por eso no hay scroll obligatorio: si solo ven el primer pantallazo, ya lo
han visto todo. Lo demás (las 10 pestañas, la película) es para el que se queda.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
CUSTOM = ROOT / "app" / "assets" / "custom"

# Foto de la peña celebrando. Es opcional: si no está, la portada funciona
# igual y sencillamente no aparece el marco.
FOTO_CANDIDATAS = ("campeones.jpg", "campeones.jpeg", "campeones.png",
                   "campeones.webp", "campeones.HEIC")


@lru_cache(maxsize=1)
def _foto_campeones() -> str:
    for name in FOTO_CANDIDATAS:
        p = CUSTOM / name
        if p.exists():
            mime = "jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else p.suffix.lower().lstrip(".")
            return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return ""


@lru_cache(maxsize=1)
def _poster() -> str:
    """Fotograma fijo del hero. Es el suelo del diseño: si el vídeo no llega a
    reproducirse (reduced-motion, autoplay bloqueado, red lenta) la portada
    tiene que verse exactamente igual, solo que quieta."""
    p = CUSTOM / "hero_champion_poster.jpg"
    if not p.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


@lru_cache(maxsize=1)
def _preseason() -> list[tuple[str, float]]:
    """Top-2 de la primerísima foto del modelo, antes de que empezara nada."""
    try:
        from src.data.snapshots import list_snapshots
        snaps = list_snapshots()
        if not snaps:
            return []
        champ = snaps[0].get("champion") or {}
        return sorted(champ.items(), key=lambda x: -x[1])[:2]
    except Exception:
        return []


@lru_cache(maxsize=1)
def _preseason_date() -> str:
    try:
        from src.data.snapshots import list_snapshots
        snaps = list_snapshots()
        if not snaps:
            return ""
        from datetime import date as _d
        y, m, dd = (int(x) for x in snaps[0]["date"].split("-"))
        meses = ["ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "sep", "oct", "nov", "dic"]
        return f"{dd} {meses[m-1]}"
    except Exception:
        return ""


from src.data.team_names import display as D  # noqa: E402


def _flag(team: str, w: int = 80) -> str:
    from src.data.team_profile import ISO_CODES
    return f'https://flagcdn.com/w{w}/{ISO_CODES.get(team, "un")}.png'


def render_champion_hero(champion: str, hit_rate: str, n_played: int,
                         film_url: str) -> bool:
    """Portada del torneo terminado. Devuelve False si aún no hay campeón."""
    if not champion:
        return False
    try:
        from app.utils import load_real_results
        real = load_real_results() or {}
        ko = real.get("knockout_matches") or {}
        fin = next(iter((ko.get("final") or {}).values()), None)
        if not fin:
            return False
    except Exception:
        return False

    runner = fin["away"] if fin["winner"] == fin["home"] else fin["home"]
    pre = _preseason()
    foto = _foto_campeones()

    # --- bloque del gancho: lo que dijo el modelo antes de que rodara el balón
    claim = ""
    if pre and pre[0][0] == champion:
        (t1, p1), rest = pre[0], pre[1:]
        t2, p2 = rest[0] if rest else ("—", 0.0)
        w2 = (p2 / p1 * 100) if p1 else 0
        pc1 = f"{p1*100:.1f}".replace(".", ",") + " %"
        pc2 = f"{p2*100:.1f}".replace(".", ",") + " %"
        claim = (
'<div class="hc-claim">'
'<div class="hc-claim-h">◆ Y lo tenía escrito desde mayo</div>'
f'<div class="hc-claim-sub">{_preseason_date()} · 19 días antes del primer partido, '
'el modelo repartió el título entre las 48 selecciones</div>'
'<div class="hc-bars">'
'<div class="hc-bar win">'
f'<img src="{_flag(t1, 40)}" alt="">'
f'<span class="nm">{D(t1)}</span>'
'<span class="tr"><i style="width:100%"></i></span>'
f'<span class="pc">{pc1}</span>'
'</div>'
'<div class="hc-bar">'
f'<img src="{_flag(t2, 40)}" alt="">'
f'<span class="nm">{D(t2)}</span>'
f'<span class="tr"><i style="width:{w2:.0f}%"></i></span>'
f'<span class="pc">{pc2}</span>'
'</div>'
'</div>'
'<div class="hc-claim-foot">La puso primera. Más del doble que la segunda.</div>'
'</div>'
        )

    foto_html = ""
    if foto:
        foto_html = (
'<figure class="hc-foto">'
f'<img src="{foto}" alt="Celebrando el título">'
'<figcaption>🏆 Campeones · 19 de julio de 2026</figcaption>'
'</figure>'
        )

    poster = _poster()
    bg = f' style="background-image:url({poster})"' if poster else ""

    st.markdown(
f'<section class="hc"{bg}>'
'<video class="hc-vid" autoplay muted loop playsinline>'
'<source src="/hero_champion.mp4" type="video/mp4"></video>'
'<div class="hc-scrim"></div>'
'<div class="hc-inner">'
'<div class="hc-left">'
'<p class="hc-eyebrow">Mundial 2026 · terminado</p>'
f'<h1 class="hc-title"><span>{D(champion)}</span><em>campeona del mundo</em></h1>'
'<div class="hc-score">'
f'<span class="t"><img src="{_flag(fin["home"])}" alt="">{D(fin["home"])}</span>'
f'<span class="s">{fin["home_score"]}<i>–</i>{fin["away_score"]}</span>'
f'<span class="t r">{D(fin["away"])}<img src="{_flag(fin["away"])}" alt=""></span>'
'</div>'
f'<p class="hc-sub">Final · 19 de julio · {D(runner)} subcampeona</p>'
'<div class="hc-nums">'
f'<div><b>{hit_rate}</b><span>acierto del modelo</span></div>'
f'<div><b>{n_played}</b><span>partidos predichos</span></div>'
'<div><b>10.000</b><span>torneos por noche</span></div>'
'</div>'
'<div class="hc-ctas">'
f'<a class="hc-cta primary" href="{film_url}" target="_blank" rel="noopener">'
'▶ Ver la película <span class="ar">→</span></a>'
'<a class="hc-cta ghost" href="#explorar">Explorar los datos ↓</a>'
'</div>'
'</div>'
'<div class="hc-right">'
f'{foto_html}{claim}'
'</div>'
'</div>'
'</section>',
        unsafe_allow_html=True,
    )
    return True


# ============================================================================
# LOS TRES GOLPES
# ----------------------------------------------------------------------------
# La película entera son 5 minutos de scroll y vive en otra URL. Aquí abajo va
# comprimida a tres pantallas con el metraje bueno de fondo: el que baja del
# hero se lleva el torneo contado, sin salir de la web que le pasaron.
# ============================================================================

def _beat_poster(name: str) -> str:
    p = CUSTOM / f"beat_{name}_poster.jpg"
    if not p.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def _beat(name: str, eyebrow: str, big: str, unit: str, title: str,
          body: str, side: str = "left") -> str:
    poster = _beat_poster(name)
    bg = f' style="background-image:url({poster})"' if poster else ""
    return (
f'<section class="beat beat-{side}"{bg}>'
f'<video class="beat-vid" autoplay muted loop playsinline preload="none" data-src="/beat_{name}.mp4"></video>'
'<div class="beat-scrim"></div>'
'<div class="beat-inner">'
f'<p class="beat-eyebrow">{eyebrow}</p>'
f'<p class="beat-big">{big}<span class="u">{unit}</span></p>'
f'<h3 class="beat-title">{title}</h3>'
f'<p class="beat-body">{body}</p>'
'</div>'
'</section>'
    )


def render_beats(hit_rate: str, engines: list[dict] | None = None) -> None:
    """Tres pantallas de cine: lo que dijo, lo que dudó, lo que acertó."""
    pre = _preseason()
    p1 = f"{pre[0][1]*100:.1f}".replace(".", ",") if pre else "19,4"
    t1 = D(pre[0][0]) if pre else "España"

    veredicto = ""
    if engines:
        best = min(engines, key=lambda e: e["brier"])
        elo = next((e for e in engines if e["key"] == "elo"), None)
        if elo and best["key"] != "elo":
            gap = (elo["brier"] - best["brier"]) / elo["brier"] * 100
            veredicto = (f' El <b>{best["label"]}</b> le sacó un {gap:.0f} % de ventaja '
                         'al Elo clásico sobre los mismos partidos.')

    st.markdown(
        _beat("mayo", "23 de mayo · 19 días antes del primer partido",
              p1, " %",
              f"{t1}, la más probable de las 48",
              "El estadio todavía estaba vacío. El modelo corrió diez mil torneos "
              "y le dio a España más del doble de opciones que a la segunda. "
              "No se movió de ahí en las cinco tomas siguientes.", "left")
        + _beat("montana", "1 de julio · fin de la fase de grupos",
                "12,4", " %",
                "Y entonces dejó de creérselo",
                "Francia arrasaba en grupos y el modelo se bajó del carro: España "
                "cayó al 12,4 % y Francia se puso líder con el 24,5 %. Siguió por "
                "delante el 10 y el 13 de julio. Después jugaron la semifinal.", "right")
        + _beat("juicio", "104 partidos · el veredicto",
                hit_rate.replace(" %", ""), " %",
                "de acierto, partido a partido",
                "Acertar al campeón es fácil de contar y fácil de tener suerte. "
                f"Esto son los 104, cada uno predicho antes de jugarse.{veredicto}", "left"),
        unsafe_allow_html=True,
    )
