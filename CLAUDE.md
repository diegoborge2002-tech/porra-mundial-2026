# Porra Mundial 2026

Web Streamlit de predicción del Mundial 2026 (11 jun – 19 jul 2026, 48 equipos,
104 partidos). Motor: ensemble Elo dinámico + XGBoost de stats (peso en
`BiasesConfig.stats_weight`), Monte Carlo 10k torneos, Dixon-Coles para marcadores.

## Comandos

- **Lanzar la web**: `/opt/anaconda3/bin/streamlit run app/streamlit_app.py`
  (el `python3` del sistema NO tiene streamlit; el de anaconda sí)
- **Verificación sin browser**: `streamlit.testing.v1.AppTest.from_file(..., default_timeout=300)`
- **Reentrenar modelo XGBoost** (solo si cambian los datos de
  `data/external/simulaciones_mundial/`): `python3 notebooks/04_entrenar_stats_model.py`
  → regenera `data/processed/stats_model.json` (la web NO usa xgboost en runtime)

## 🔁 RUTINA DIARIA (¡importante durante el torneo!)

Cuando el usuario diga "actualiza", "informe del día", pase resultados, o similar:

1. **Buscar los resultados de ayer/hoy en la web** (WebSearch: "resultado <equipos>
   mundial 2026 <fecha>") si el usuario no los da explícitamente.
2. **Registrarlos**:
   - Grupos: `python scripts/dia.py add "Mexico 2-0 Sudafrica" "Corea del Sur 2-1 Chequia"`
   - Eliminatorias: `python scripts/dia.py ko r32 73 "Espana 1-1 Noruega" --ganador Espana`
   - Acepta alias y acentos (Chequia, Holanda, EEUU…). IDs FIFA de KO: 73-104 (ver `src/tournament/bracket.py`).
3. **Generar el informe**: `python scripts/dia.py informe`
   → evalúa el modelo partido a partido (✓/✗, Brier), compara los 3 motores
   (Elo / Ensemble / XGBoost), actualiza probabilidades de campeón con deltas
   vs el snapshot anterior, guarda el snapshot del día y lista los próximos
   partidos con resultado esperado.
4. **Resumir al usuario**: aciertos/fallos del modelo, qué motor va ganando
   (si el Elo rinde peor de forma sostenida, sugerir subir `stats_weight` en
   🎯 Mis ajustes), movimientos grandes en la porra, y partidos clave de hoy.

Todo lo que escribe el script lo lee la web (real_results.json, snapshots/):
no hace falta tocar nada más.

## Deploy

- Repo: https://github.com/diegoborge2002-tech/porra-mundial-2026 (gh CLI autenticado)
- Hosting: **Streamlit Community Cloud** (share.streamlit.io), entry point
  `app/streamlit_app.py`. Vercel NO sirve (Streamlit necesita servidor
  persistente con websockets). Tras `git push origin main` el deploy se
  actualiza solo en ~1 min.
- `.gitignore` excluye `scratch/`, `notebooks/` e `informes_tacticos/` del repo:
  el entrenamiento XGBoost es local; al deploy solo va `stats_model.json`.

## Estructura clave

- `src/model/ensemble.py` — blend Elo+stats; hook central: `expected_goals_ensemble`
  en `src/model/poisson.py` (todo el MC pasa por ahí)
- `src/model/biases.py` — config del usuario (half-life, stats_weight, sesgos por equipo)
- `data/processed/real_results.json` — resultados reales registrados (formato:
  `group_matches: {"A vs B": [gA, gB]}`, `knockout_matches: {r32: {"73": {home, away, ...}}}`)
- `data/processed/stats_model.json` — 1.128 cruces precomputados del XGBoost
- `app/tabs/partidos.py` — pestaña "🔮 Partidos" (resultado esperado de los 104)
- Nombres de equipo: español sin acentos ("Espana", "Rep. Checa", "R.D. Congo",
  "Bosnia Herz.", "Costa Marfil") — ver `src/tournament/groups.py`
