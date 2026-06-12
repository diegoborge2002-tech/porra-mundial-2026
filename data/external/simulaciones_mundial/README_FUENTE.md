# Datos del repo Simulaciones_Mundial

Fuente: https://github.com/jytsss/Simulaciones_Mundial (autor: `@jyts__`)

Datos scrapeados de estadísticas de selecciones (xG, posesión, remates,
córneres, pases, paradas, ranking FIFA…) usados para entrenar el modelo
XGBoost de resultado esperado por partido.

| Archivo | Contenido |
|---|---|
| `datos_historicos.csv` | 1.396 partidos internacionales 2021-2026 con features ya construidas (medias móviles, diffs, prob implícita Elo-FIFA) |
| `datos_mundial.csv` | Snapshot de features por selección (48 equipos) a fecha 11-jun-2026 |
| `ranking_fifa.csv` | Histórico del ranking FIFA |
| `partidos_mundial.csv` | Los 72 partidos de fase de grupos |
| `Grupos_Mundial.csv` | Asignación equipo → grupo |

El entrenamiento y export se hace con `notebooks/04_entrenar_stats_model.py`,
que genera `data/processed/stats_model.json` (consumido por la web sin
necesidad de xgboost en runtime).
