"""Media enriquecida: banner, fondo de estadio, boletín de jornada y banners de pestaña.

Assets fijos y reutilizables (Nano Banana Pro / Higgsfield) en app/assets/custom/.
Los boletines de audio diarios en app/assets/recaps/ (boletin_YYYY-MM-DD.wav).
"""
from __future__ import annotations

import base64
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "app" / "assets"
CUSTOM = ASSETS / "custom"
RECAP_DIR = ASSETS / "recaps"


def _first(*paths: Path) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def render_banner() -> None:
    """Vídeo (o imagen) cinematográfico a todo lo ancho, en lo alto de la página."""
    vid = _first(CUSTOM / "hero.mp4", CUSTOM / "intro.mp4")
    if vid:
        st.video(str(vid), loop=True, autoplay=True, muted=True)
        return
    p = _first(CUSTOM / "banner.png", ASSETS / "banner_mundial.png")
    if p:
        st.image(str(p), use_container_width=True)


@lru_cache(maxsize=1)
def _hero_bg_uri() -> str:
    p = _first(CUSTOM / "banner_hero.jpg", CUSTOM / "banner.png", ASSETS / "banner_mundial.png")
    if not p:
        return ""
    mime = "jpeg" if p.suffix in (".jpg", ".jpeg") else "png"
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def render_hero() -> None:
    """Hero cinematográfico: imagen/vídeo de fondo con el título superpuesto.

    El vídeo se sirve en /hero.mp4 (lo copia patch_index.py al deploy); si no
    carga, queda la imagen de fondo (banner_hero.jpg en base64) con el título.
    """
    bg = _hero_bg_uri()
    st.markdown(
        f"""
        <div class="hero-cine" style="background-image:url('{bg}');">
          <video class="hero-vid" autoplay muted loop playsinline>
            <source src="/hero.mp4" type="video/mp4">
          </video>
          <div class="hero-scrim"></div>
          <div class="hero-text">
            <h1 class="wc-title"><span class="ball">⚽</span> Porra Mundial 2026
                <span class="hosts">🇺🇸 🇨🇦 🇲🇽</span></h1>
            <p class="sub">Ensemble Elo + XGBoost · Monte Carlo 10.000 torneos · 48 equipos · 104 partidos · 11 jun → 19 jul</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@lru_cache(maxsize=1)
def _bg_data_uri() -> str:
    p = _first(CUSTOM / "bg_texture_min.jpg", CUSTOM / "bg_texture.png")
    if not p:
        return ""
    mime = "jpeg" if p.suffix == ".jpg" else "png"
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def render_background() -> None:
    """Textura de estadio fija y muy atenuada detrás de toda la app (legible)."""
    uri = _bg_data_uri()
    if not uri:
        return
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(rgba(2,6,23,0.90), rgba(2,6,23,0.95)),
                url('{uri}');
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_tab_banner(filename: str, caption: str = "") -> None:
    """Imagen-cabecera decorativa al principio de una pestaña."""
    p = CUSTOM / filename
    if p.exists():
        st.image(str(p), use_container_width=True, caption=caption or None)


def _latest(pattern: str) -> Path | None:
    if not RECAP_DIR.exists():
        return None
    files = sorted(RECAP_DIR.glob(pattern))
    return files[-1] if files else None


def _nice_date(path: Path) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not m:
        return ""
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return m.group(1)


def render_matchday_brief() -> None:
    """Boletín de la jornada: imagen fija (estudio) + locución del informe del día.

    La imagen es un asset reutilizable (engine.png), NO se regenera por partido;
    lo que cambia cada día es la locución (boletin_*.wav).
    """
    _aud = (list(RECAP_DIR.glob("boletin_*.wav")) + list(RECAP_DIR.glob("boletin_*.mp3"))
            if RECAP_DIR.exists() else [])
    audio = max(_aud, key=lambda p: p.stat().st_mtime) if _aud else None
    img = _first(CUSTOM / "engine.png")
    if not img and not audio:
        return

    fecha = _nice_date(audio) if audio else ""
    titulo = "📻 Boletín de la jornada" + (f" · {fecha}" if fecha else "")
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:700;margin:.3rem 0 .5rem;">{titulo}</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([3, 2])
    if img:
        cols[0].image(str(img), use_container_width=True)
    with cols[1]:
        if audio:
            st.audio(str(audio))
            st.caption("🔊 Resumen del día narrado · voz IA")
        st.caption("Se actualiza cada jornada con los resultados del día.")
