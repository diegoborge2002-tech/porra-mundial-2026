# ⚽ Porra Mundial 2026

Web app de predicción del Mundial 2026 (USA / Canadá / México) basada en:

- **Modelo Elo dinámico** con half-life ajustable y ventaja de campo (+65 Elo anfitriones)
- **Monte Carlo** 10.000 torneos
- **Dixon-Coles** sobre Poisson para marcadores exactos
- **Calibración** del modelo (Brier, log-loss, RPS) sobre Mundiales 2010-2022 y Eurocopas 2016-2024
- **Live in-play** probabilities condicionadas a minuto + marcador
- **Análisis de plantillas** con valor Transfermarkt y forma reciente del club 2025-26

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

Streamlit Community Cloud: https://share.streamlit.io → conectar este repo y `app/streamlit_app.py` como entry point.
