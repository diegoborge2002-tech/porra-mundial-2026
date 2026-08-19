# 🎬 Prompts de vídeo — "Mi Mundial 2026: la película"

Clips para la retrospectiva scrollytelling. **Guarda cada archivo con el nombre
exacto indicado en `film/assets/`.** La web los detecta sola: si el archivo existe
lo usa, y si no, cae al metraje base que genero yo con ffmpeg. No hay que tocar código.

---

## Dirección de arte (evolución de la tuya, léela antes de generar)

Misma familia visual que los assets actuales, con **un giro**: hasta ahora el cian
era el protagonista y el oro estaba reservado al trofeo. En la película **el oro
pasa a ser el color protagonista** — porque el trofeo ya no es una hipótesis, es
el final de la historia. El cian queda como color del *modelo*, de lo analítico,
de lo que se predijo. Oro = lo que pasó. Cian = lo que se dijo que iba a pasar.

- **Fondo**: negro azulado profundo `#0a0f1e` / `#020617`
- **Cian analítico**: `#4cd7f6` — datos, predicción, frío
- **Oro campeón**: `#f0c14b` / `#e8b64c` — trofeo, título, celebración, cálido
- **Blancos fríos**: `#f8fafc` en luces y destellos
- Luz volumétrica, rim-light sutil, bokeh de partículas, destellos anamórficos,
  profundidad de campo corta, grano de película muy fino, 8K cinematográfico.

**Reglas duras en todos los prompts:**
- ❌ Nunca texto, letras, números, logos, marcas ni marcas de agua.
- ❌ Nunca jugadores reconocibles, caras en primer plano ni escudos reales.
  Si aparecen figuras humanas: siluetas, contraluz, desenfocadas o de espaldas.
- ❌ Nada de branding FIFA/Mundial real. Trofeo genérico, nunca el oficial.
- ✅ Cámara lenta y con intención. Nada de zooms bruscos ni cortes.

---

## LOS 6 CAPÍTULOS

### 0 · `cap0_final.mp4` — El pitido final · 16:9 · **12 s** · sin loop
> Es el plano de apertura a pantalla completa. Avanza con el scroll (scrubbing),
> por eso es más largo: 12 s de movimiento continuo y lento, sin cortes.

```
Slow cinematic push-in across a packed night stadium at the exact moment a world
championship final ends. Golden confetti falls in thick drifting curtains through
volumetric floodlight beams, catching the light like embers. Anonymous player
silhouettes in the far distance, backlit and out of focus, arms raised. A generic
golden trophy glints faintly in the deep background haze, never dominant. Warm gold
(#f0c14b) light floods the frame from the left, deep navy (#020617) shadows hold the
rest. Extremely slow continuous dolly push forward, no cuts, shallow depth of field,
anamorphic lens flares, fine film grain, 8K cinematic. No text, no watermark, no
recognizable faces, no logos.
```

### 1 · `cap1_mayo.mp4` — Lo que dije en mayo · 16:9 · **8 s** · loop
> Frío, vacío, anticipación. Es el estadio *antes* de que existiera la historia.

```
An empty stadium at cold blue-hour dawn, nineteen days before a tournament begins.
Rows of empty seats recede into mist, the pitch immaculate and untouched, faint dew
catching first light. Everything is cold and unresolved: desaturated deep navy
(#020617) with thin electric cyan (#4cd7f6) rim light along the stand edges, no gold
anywhere. A single floodlight tower glows faintly in fog. Very slow lateral drift of
the camera, seamlessly looping, still and expectant mood, volumetric haze, shallow
depth of field, fine film grain, 8K cinematic. No text, no watermark, no people, no
logos.
```

### 2 · `cap2_partidos.mp4` — 104 partidos · 16:9 · **8 s** · loop
> El torneo como maquinaria. Kinético, muchos estadios, ritmo.

```
Abstract kinetic montage evoking an entire month of football compressed into seconds:
overlapping translucent layers of stadium floodlight grids, blurred motion streaks of
a ball crossing frame, pitch line geometry sliding past, rapid parallax of light
towers. Everything abstract and semi-transparent, never a literal match scene. Cyan
(#4cd7f6) data-light dominates with occasional warm gold (#f0c14b) flares punching
through. Continuous fast lateral camera drift with layered parallax, seamlessly
looping, energetic but controlled, volumetric light, fine grain, 8K cinematic. No
text, no watermark, no faces, no logos.
```

### 3 · `cap3_montana.mp4` — La montaña rusa · 16:9 · **8 s** · loop
> La incertidumbre. Curvas de probabilidad que suben, se cruzan y se adelantan.

```
Abstract data-landscape: luminous flowing ribbon curves rising, dipping and crossing
over one another through dark space, like probability lines competing for the lead.
Two ribbons dominate — one electric cyan (#4cd7f6), one warm gold (#f0c14b) — weaving
past each other, trading position, with fainter ribbons trailing behind. Fine
particle dust drifts between them, soft volumetric glow, deep navy (#020617) void.
Slow continuous camera travel along the ribbons, seamlessly looping, elegant and
tense, premium data-visualization aesthetic, 8K. No text, no watermark, no numbers,
no logos.
```

### 4 · `cap4_juicio.mp4` — El juicio al modelo · 16:9 · **12 s** · sin loop
> Segundo plano con scrubbing por scroll. El motor de predicción siendo evaluado.

```
Slow cinematic orbit around a floating machine-intelligence core: a soccer ball
reimagined as a glowing lattice of interconnected nodes and thin light filaments,
suspended in dark space. Translucent probability bars, bell curves and calibration
grids made of pure light drift and rotate around it, some aligning perfectly and some
falling out of register. Electric cyan (#4cd7f6) energy over deep navy (#020617), a
single warm gold (#f0c14b) filament threading through the lattice. Extremely slow
continuous orbit, no cuts, volumetric glow, fine particles, shallow depth of field,
premium sports-tech aesthetic, 8K cinematic. No text, no watermark, no numbers, no
logos.
```

### 5 · `cap5_archivo.mp4` — El archivo · 16:9 · **8 s** · loop
> Cierre. Sereno, memorial, de biblioteca. Aquí baja el pulso.

```
A quiet archival mood piece: dozens of translucent glass panels floating in ordered
rows through dark space, each one a faint luminous rectangle holding indistinct
abstract light patterns, like records suspended in a vault. Dust motes drift slowly
between them. Cold cyan (#4cd7f6) edge light on the glass, one distant warm gold
(#f0c14b) glow far in the background. Very slow forward drift past the panels,
seamlessly looping, calm, reverent, memorial mood, volumetric haze, shallow depth of
field, 8K cinematic. No text, no watermark, no faces, no logos.
```

---

## TRANSICIONES (esto es lo que da el efecto "de película")

Estos NO son fondos: son capas que se funden **encima** entre capítulo y capítulo.
Genéralos sobre **negro puro plano** — yo los mezclo en modo `screen` y el negro
desaparece solo. Son los que hacen que el scroll se sienta cinematográfico.

### 6 · `wipe_light.mp4` — barrido de luz · 16:9 · **2 s** · sobre negro puro
```
A single sweeping blade of bright light travelling fast from left to right across a
pure flat black frame, like an anamorphic lens flare crossing the lens. Warm gold
(#f0c14b) core fading to cyan (#4cd7f6) at the edges, with soft horizontal streaking
and subtle chromatic fringing. Nothing else in frame — pure black background, no
objects, no scene. Fast confident motion, 2 seconds, starts and ends on full black.
No text, no watermark.
```

### 7 · `wipe_confetti.mp4` — cortina de confeti · 16:9 · **2 s** · sobre negro puro
```
A dense curtain of golden and cyan confetti falling fast and filling the frame, then
clearing, against a pure flat black background. Motion-blurred paper flakes catching
light, varied sizes and rotations, natural scatter. Nothing else in frame — no scene,
no background elements. 2 seconds, starts on black and ends on black. No text, no
watermark.
```

### 8 · `wipe_particles.mp4` — disolución de partículas · 16:9 · **2 s** · sobre negro
```
A field of fine glowing particles rushing toward the camera and dispersing outward
past the lens, against pure flat black. Cyan (#4cd7f6) particles with a few warm gold
(#f0c14b) ones mixed in, soft focus falloff and light trails. Nothing else in frame.
2 seconds, starts on black and ends on black. No text, no watermark.
```

---

## Prioridad si andas justo de créditos

El free tier de Higgsfield da para poco. Si solo puedes generar unos pocos, este es
el orden por impacto real en la pieza:

| Orden | Archivo | Por qué |
|---|---|---|
| 1 | `cap0_final.mp4` | Es lo primero que se ve. Si solo generas uno, este. |
| 2 | `wipe_light.mp4` | Una sola transición reutilizada entre los 6 capítulos ya da el efecto. |
| 3 | `cap4_juicio.mp4` | El capítulo con más peso narrativo (el veredicto del modelo). |
| 4 | `cap1_mayo.mp4` | El contraste frío/vacío contra el cap0 es lo que crea el arco. |
| 5 | `cap3_montana.mp4` | Puedo sustituirlo bien con datos animados por ffmpeg. |
| 6 | `cap2_partidos.mp4` | Idem. |
| 7 | `cap5_archivo.mp4` | El más prescindible: cierra bien con un fundido simple. |
| 8-9 | los otros dos `wipe_*` | Solo si sobran créditos. |

**Todo lo que no generes lo cubro yo con ffmpeg**, así que la película está completa
y desplegada tanto si generas nueve clips como si no generas ninguno.

## Especificaciones técnicas
- **Formato**: MP4, H.264, 16:9, mínimo 1920×1080 (mejor 2560×1440)
- **Sin audio** (la web los reproduce en mute; el audio son tus boletines)
- Los marcados **"loop"** deben empezar y acabar en el mismo punto, sin corte visible
- Los de **12 s sin loop** avanzan con el scroll: prioriza movimiento continuo y lento
- Si un clip sale a 24/25 fps, perfecto. Yo lo reencodeo para scrubbing.
