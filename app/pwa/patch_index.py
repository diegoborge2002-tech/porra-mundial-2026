"""Inyecta PWA (manifest + service worker + iconos) y meta OG en el index.html
de Streamlit. Se ejecuta UNA vez en el build de Docker (ver Dockerfile).

Copia los assets de app/pwa/ y og_image al directorio static/ de Streamlit (se
sirven en la raiz) y anade las etiquetas <head>. Idempotente.
"""
from __future__ import annotations

import pathlib
import shutil

import streamlit

BASE_URL = "https://diegoborge-porra-mundial-2026.hf.space"

static = pathlib.Path(streamlit.__file__).parent / "static"
pwa = pathlib.Path(__file__).parent

# 1) Copiar assets PWA (+ OG image) al static de Streamlit -> servidos en "/"
for p in pwa.glob("*"):
    if p.suffix in {".png", ".js", ".webmanifest"}:
        shutil.copy(p, static / p.name)

og = pathlib.Path("app/assets/custom/og_image.png")
if og.exists():
    shutil.copy(og, static / "og_image.png")

# Video hero -> servido en /hero.mp4 (lo usa render_hero)
hero = pathlib.Path("app/assets/custom/hero.mp4")
if hero.exists():
    shutil.copy(hero, static / "hero.mp4")

HEAD = f"""
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#020617">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:title" content="Mi Mundial 2026">
<meta property="og:description" content="Predicciones del Mundial 2026 con IA: Elo + XGBoost + Monte Carlo de 10.000 torneos.">
<meta property="og:image" content="{BASE_URL}/og_image.png">
<meta property="og:url" content="{BASE_URL}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<script>if("serviceWorker" in navigator){{window.addEventListener("load",function(){{navigator.serviceWorker.register("/sw.js")}})}}</script>
<script src="/effects.js" defer></script>
"""

idx = static / "index.html"
html = idx.read_text(encoding="utf-8")
if "manifest.webmanifest" not in html:
    html = html.replace("</head>", HEAD + "</head>", 1)
    idx.write_text(html, encoding="utf-8")
    print("[patch_index] index.html parcheado con PWA + OG")
else:
    print("[patch_index] index.html ya estaba parcheado")
