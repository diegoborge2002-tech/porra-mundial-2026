"""Media enriquecida con Higgsfield: banner cinematográfico + boletín de jornada.

Los recaps diarios se guardan como ficheros DATADOS en app/assets/recaps/:
    recap_YYYY-MM-DD.png    -> imagen cinematográfica de la jornada
    boletin_YYYY-MM-DD.mp3  -> locución del informe del día (voz IA)

La web muestra SIEMPRE el más reciente. Para añadir uno nuevo basta con dejar
los ficheros con la fecha del día (los genera Higgsfield al actualizar resultados),
sin tocar código: `render_matchday_brief()` coge el último por nombre.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
BANNER = ROOT / "app" / "assets" / "banner_mundial.png"
RECAP_DIR = ROOT / "app" / "assets" / "recaps"


def render_banner() -> None:
    """Banner cinematográfico a todo lo ancho, en lo alto de la página."""
    if BANNER.exists():
        st.image(str(BANNER), use_container_width=True)


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
    """Boletín de la jornada: imagen cinematográfica + locución del informe del día."""
    img = _latest("recap_*.png")
    audio = _latest("boletin_*.wav") or _latest("boletin_*.mp3")
    if not img and not audio:
        return

    fecha = _nice_date(img or audio)
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
            st.caption("🔊 Resumen del día narrado · voz IA (Higgsfield)")
        st.caption("Imagen generada con Higgsfield a partir de los resultados del día.")
