---
title: Porra Mundial 2026
emoji: ⚽
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# ⚽ Porra Mundial 2026

Web app de predicción del Mundial 2026 (USA / Canadá / México) basada en:

- **Ensemble de dos modelos** con peso configurable (slider en 🎯 Mis ajustes):
  - **Elo dinámico** con half-life ajustable y ventaja de campo (+65 Elo anfitriones)
  - **XGBoost de stats** (integrado del repo [Simulaciones_Mundial](https://github.com/jytsss/Simulaciones_Mundial)):
    regresores Tweedie de goles + clasificador 1X2 calibrado, entrenados con
    1.259 partidos 2021-26 de stats scrapeadas (xG, posesión, remates, ranking FIFA)
- **Monte Carlo** 10.000 torneos
- **Dixon-Coles** sobre Poisson para marcadores exactos
- **Resultado esperado por partido** (pestaña 🔮 Partidos): marcador más probable,
  xG y 1X2 de cada partido, con comparación Elo vs XGBoost vs Ensemble
- **Calibración** del modelo (Brier, log-loss, RPS) sobre Mundiales 2010-2022 y Eurocopas 2016-2024
- **Live in-play** probabilities condicionadas a minuto + marcador
- **Análisis de plantillas** con valor Transfermarkt y forma reciente del club 2025-26

> El modelo XGBoost se entrena offline con `python notebooks/04_entrenar_stats_model.py`
> (requiere `xgboost` + `scikit-learn`) y deja las predicciones de los 1.128 cruces
> posibles precomputadas en `data/processed/stats_model.json`, así la web no
> necesita xgboost en runtime.

## Arrancar local

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Abre http://localhost:8501

## Estructura

```
app/
  streamlit_app.py     ← punto de entrada
  tabs/                ← una pestaña por archivo (predicciones, selecciones, …)
  components*.py       ← componentes UI reutilizables
  styles.py            ← tema oscuro custom
src/
  data/                ← carga y persistencia
  model/               ← Elo, MC, Dixon-Coles, calibración…
  tournament/          ← grupos y fases eliminatorias
  scoring/             ← reglas de la porra
data/
  processed/           ← elos, snapshots, plantillas, biases…
```

## Pestañas

| Tab | Qué hace |
|---|---|
| 📊 Predicciones | Resumen MC, top campeón / finalistas / favoritos, evolución longitudinal |
| 🔮 Partidos | Resultado esperado de cada partido: marcador, xG, 1X2, Elo vs XGBoost |
| 🌍 Selecciones | Ficha completa con once probable, scouting, h2h |
| 🆚 Comparador | Radar 2-3 equipos cara a cara |
| 👥 Plantilla | Valor mercado, club performance, impacto Elo |
| 🗓 Calendario | Vista completa + mapa de estadios |
| 🎯 Mis ajustes | Sliders de bias + noticias / lesiones |
| 📋 Mi porra | Apuesta con cálculo de EV |
| 📡 Seguimiento en vivo | Resultados reales + what-if simulator |
| ⚡ En vivo | Probabilidades en vivo con minuto + marcador |
| 📈 Rendimiento del modelo | Backtest, calibración, métricas |

## Deploy

**Hugging Face Spaces** (recomendado — free tier con ~16 GB RAM, aguanta el Monte Carlo):
la cabecera YAML de este README ya configura el Space (`sdk: streamlit`,
`app_file: app/streamlit_app.py`). Crear Space en https://huggingface.co/new-space
(SDK Streamlit, CPU basic), añadir el remoto `hf` y `git push hf main`.

Streamlit Community Cloud (https://share.streamlit.io): funciona pero su free tier
da solo 1 GB de RAM → el MC de 10.000 torneos puede tumbar la app (carga infinita).
