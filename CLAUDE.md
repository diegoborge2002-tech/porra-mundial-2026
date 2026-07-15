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

> **Automatizada:** existe una tarea programada `porra-mundial-auto-update`
> (10:00 y 23:00 hora España) que ejecuta este ciclo sola — busca resultados +
> horarios, registra, `informe` y redespliega. Corre mientras la app de Claude
> esté abierta (si está cerrada, en el próximo arranque). El flujo manual de abajo
> sigue valiendo para forzarlo cuando el usuario diga "actualiza"/"ejecuta los
> nuevos partidos". Horarios de inicio en hora ES: `data/processed/kickoff_times.json`,
> rellenado por `python scripts/fetch_fixtures.py --apply` (API football-data.org;
> token local en `~/.config/porra/football_data.token`, NO en el repo). Ese script
> también imprime los partidos FINISHED de la API como fuente fiable de resultados.
> La rutina además: regenera el **boletín de audio** gratis con `scripts/make_boletin_audio.py`
> (TTS de macOS `say`, voz Mónica → `app/assets/recaps/boletin_<fecha>.mp3`; la web
> muestra el más reciente), y manda el resumen a **Telegram** con `scripts/notify_telegram.py`
> (token y chat id en `~/.config/porra/telegram.token` y `telegram_chat_id`).

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
3b. **Refrescar Actualidad** (pestaña 🔥): busca en la web los **máximos
   goleadores**, las **máximas asistencias** y el **jugador del partido / MVP** de
   los partidos nuevos y escríbelos en `data/processed/actualidad.json`. Campos
   editables a mano:
   - `scorers` — tabla acumulada de goleadores (la pestaña muestra el top 15).
   - `assists` — tabla acumulada de asistencias (`{player, team, assists}`; la
     pestaña muestra el top 15 en "🅰️ Rey de las asistencias", junto a goleadores).
     La API/prensa gratis da datos fragmentados y a veces de fases pasadas: fíjate
     bien en el top (ej. Olise, Messi) y cotéjalo con varias fuentes; el tramo bajo
     es aproximado. Súmale a cada asistente los pases de gol de los partidos nuevos.
   - `mvps` — jugador del partido (la pestaña muestra los 8 más recientes).
   - `match_scorers` — **goleadores por partido** (lista `{home, away, goals:[{player, team, minute}]}`),
     para el desglose "Resultados al detalle". Añade los partidos nuevos; cotéjalos
     con el marcador (los goles deben sumar). Empareja por los dos equipos.
   - `unavailable` — **bajas y sancionados** (`{player, team, reason, detail}`),
     para la sección "🚑 Bajas y sancionados". Búscalos en web (lesiones/sanciones);
     ojo: las amarillas se borran tras la fase de grupos, así que en R32 casi no hay
     arrastre de sanciones.
   - `updated` — fecha del refresco.
   Coteja siempre los goles con los marcadores registrados (deben sumar por
   partido) — eso garantiza la calidad. El resto de la pestaña (en forma,
   movimientos de la porra, clasificaciones, titulares, **desglose modelo-vs-realidad**,
   **avisos de próximos**) se calcula solo desde los resultados; no hay que tocar nada.
   El **🏆 Cuadro** (bracket de eliminatorias) también es automático: se rellena solo
   con cada KO que registras con `dia.py ko`. La API gratuita NO da goleadores ni
   bajas, por eso van por búsqueda web.
3c. **Refrescar cuotas** (pestaña 💰 Mercado): `python scripts/fetch_odds.py --apply`
   → reescribe `data/processed/odds.json` con las cuotas de the-odds-api (campeón
   + 1X2 de los próximos partidos). ~2 créditos/llamada (free tier 500/mes; token
   en `~/.config/porra/odds_api.token`, NO en el repo). La web compara modelo vs
   mercado y marca *value bets* (EV + Kelly). OJO: el modelo es ~10 pp más plano
   que el mercado, así que casi todo el value es infraconfianza del modelo, no
   ineficiencia — la propia pestaña lo avisa con un banner de calibración.
4. **Recap visual + boletín (Higgsfield)** — opcional, gasta créditos (~2/img,
   ~2/audio; free tier ≈10): generar con Higgsfield una imagen `recap_<fecha>.png`
   y una locución `boletin_<fecha>.wav` (modelo `inworld_text_to_speech`, voz
   **"Diego (es)"**) y descargarlas a `app/assets/recaps/`. La web muestra SIEMPRE
   el par más reciente por nombre (`app/components_media.py` → `render_matchday_brief`),
   no hay que tocar código. El banner fijo está en `app/assets/banner_mundial.png`.
5. **Desplegar**: primero **`python scripts/warm_mc.py`** (precalcula el Monte
   Carlo con los resultados nuevos → `data/processed/mc_cache/`, para que la web
   cargue al instante; gitignored, lo sube el deploy). Luego
   `git add -A && git commit -m "..." && git push origin main` y
   **`python scripts/deploy_hf.py "..."`** (HF por API; `git push hf` rechaza los
   binarios de los recaps). HF rebuildea en ~40 s. El caché es seguro: la clave
   incluye los resultados, así que si se te olvida `warm_mc` la web recalcula en
   vivo (más lento) pero **nunca sirve datos viejos**.
6. **Resumir al usuario**: aciertos/fallos del modelo, qué motor va ganando
   (si el Elo rinde peor de forma sostenida, sugerir subir `stats_weight` en
   🎯 Mis ajustes), movimientos grandes en la porra, y partidos clave de hoy.

Todo lo que escribe el script lo lee la web (real_results.json, snapshots/):
el código no hace falta tocarlo, solo registrar resultados y desplegar.

## Deploy

- Repo: https://github.com/diegoborge2002-tech/porra-mundial-2026 (gh CLI autenticado)
- Hosting: **Hugging Face Spaces** (Docker SDK) —
  https://huggingface.co/spaces/diegoborge/porra-mundial-2026 ·
  app live: **https://diegoborge-porra-mundial-2026.hf.space**
  - El `Dockerfile` corre `streamlit run app/streamlit_app.py` en el puerto 7860;
    la cabecera YAML del README configura el Space (`sdk: docker`, `app_port: 7860`).
  - Free tier ~16 GB RAM → aguanta el MC. (Streamlit Community Cloud daba 1 GB y
    lo tumbaba: "carga y no se ve nada". Vercel tampoco sirve.)
  - **Deploy: `python scripts/deploy_hf.py "mensaje"`** (sube por API/Xet y
    rebuildea en ~40 s). OJO: `git push hf main` RECHAZA binarios (banner y los
    recaps png/wav) si no van por LFS — por eso el deploy va por la API.
    Login HF: `hf auth login` (token Write, queda cacheado).
- `git push origin main` actualiza GitHub (fuente de verdad, sí acepta binarios).
  Para que el deploy online refleje cambios, además: `python scripts/deploy_hf.py`.
- `.gitignore` excluye `scratch/`, `notebooks/` e `informes_tacticos/` del repo:
  el entrenamiento XGBoost es local; al deploy solo va `stats_model.json`.

## Estructura clave

- `src/model/ensemble.py` — blend Elo+stats; hook central: `expected_goals_ensemble`
  en `src/model/poisson.py` (todo el MC pasa por ahí)
- `src/model/biases.py` — config del usuario (half-life, stats_weight, sesgos por equipo)
- `data/processed/real_results.json` — resultados reales registrados (formato:
  `group_matches: {"A vs B": [gA, gB]}`, `knockout_matches: {r32: {"73": {home, away, ...}}}`)
- `data/processed/stats_model.json` — 1.128 cruces precomputados del XGBoost
- `data/processed/actualidad.json` — goleadores + asistencias + MVP + goleadores por partido
  (`match_scorers`) + bajas (`unavailable`), datos externos vía web; los lee
  `src/data/actualidad.py` (que además deriva en forma / movimientos /
  clasificaciones / titulares / **desglose modelo-vs-realidad por partido** vía
  `recent_match_breakdowns` / **avisos de próximos** vía `upcoming_watchouts`) y
  los pinta `app/tabs/actualidad.py` (pestaña 🔥)
- `src/data/bracket_view.py` — construye el cuadro de eliminatorias (R32→Final)
  desde `real_results.json`: resuelve los cruces de R32 con `_resolve_r32_pairings`
  (clasificaciones reales) y propaga ganadores; marcador esperado del ensemble en
  los pendientes. Lo pinta `app/tabs/cuadro.py` (pestaña 🏆 Cuadro, árbol clásico de
  mitades). 100% automático: solo registrar KO con `dia.py ko`.
- `data/processed/odds.json` — cuotas de apuestas (the-odds-api, vía
  `scripts/fetch_odds.py`; mejor cuota + prob implícita media por casa). Las lee
  `src/data/odds.py` (devig por normalización + helpers EV/Kelly) y las pinta
  `app/tabs/mercado.py` (pestaña 💰 Mercado vs Modelo: campeón y 1X2 modelo vs
  mercado + value bets). El modelo del 1X2 sale del MISMO `_predict_match` que
  🔮 Partidos, así que los números cuadran entre pestañas.
- `app/tabs/partidos.py` — pestaña "🔮 Partidos" (resultado esperado de los 104 +
  mapa de sedes). **Navegación**: `app/streamlit_app.py` usa `st.segmented_control`
  (lazy: solo renderiza la pestaña activa), 10 pestañas (incl. 🏆 Cuadro y 💰 Mercado
  vs Modelo). Retiradas: Comparador
  (ahora toggle dentro de Selecciones), Calendario (su mapa está en Partidos) y
  "En vivo" (calculadora minuto a minuto). Deep-link `?goto=<clave>` para saltar.
- Nombres de equipo: español sin acentos ("Espana", "Rep. Checa", "R.D. Congo",
  "Bosnia Herz.", "Costa Marfil") — ver `src/tournament/groups.py`
