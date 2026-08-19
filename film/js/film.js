/* ============================================================================
   Mi Mundial 2026 · La película — motor de la narración
   ---------------------------------------------------------------------------
   Todo el contenido sale de story.json (horneado por scripts/build_story.py).
   Nada está escrito a mano: si los datos cambian, la película cambia.
   ========================================================================== */
(() => {
  "use strict";

  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const flag = (iso, w = 40) => `https://flagcdn.com/w${w}/${(iso || "un").toLowerCase()}.png`;

  // El repo guarda los equipos sin acentos (convención de src/tournament/groups.py)
  // porque son claves de datos. Aquí se leen, así que se escriben bien.
  const NOMBRE = {
    "Espana": "España", "Belgica": "Bélgica", "Paises Bajos": "Países Bajos",
    "Arabia Saudi": "Arabia Saudí", "Tunez": "Túnez", "Turquia": "Turquía",
    "Japon": "Japón", "Iran": "Irán", "Panama": "Panamá", "Sudafrica": "Sudáfrica",
    "Mexico": "México", "Canada": "Canadá", "Uzbekistan": "Uzbekistán",
    "Haiti": "Haití", "Rep. Checa": "Chequia", "Bosnia Herz.": "Bosnia y Herz.",
  };
  const nm = (t) => NOMBRE[t] || t || "";

  // Formato español: coma decimal y espacio fino antes del %
  const num = (n, d = 1) => n.toFixed(d).replace(".", ",");
  const pct = (n, d = 1) => `${num(n * 100, d)} %`;

  gsap.registerPlugin(ScrollTrigger);

  /* ======================================================================
     1 · CARGA DE DATOS
     ==================================================================== */
  fetch("story.json")
    .then((r) => {
      if (!r.ok) throw new Error(`story.json → HTTP ${r.status}`);
      return r.json();
    })
    .then(build)
    .catch((err) => {
      console.error("[film] no se pudieron cargar los datos:", err);
      // Sin datos, la narración escrita sigue siendo legible: solo avisamos.
      const w = $("#c2 .wrap");
      if (w) {
        const p = document.createElement("p");
        p.className = "lede";
        p.style.color = "#ff8a8a";
        p.textContent = "No se pudieron cargar los datos del torneo (story.json).";
        w.appendChild(p);
      }
      wireMotion();
    });

  /* ======================================================================
     2 · CONSTRUCCIÓN DE CADA CAPÍTULO
     ==================================================================== */
  function build(S) {
    buildPreseason(S);
    buildWall(S);
    buildSurprises(S);
    buildRace(S);
    buildRoad(S);
    buildVerdict(S);
    buildArchive(S);
    stampFooter(S);
    wireMotion(S);
  }

  /* ---------- Cap 01 · las probabilidades de mayo ---------- */
  function buildPreseason(S) {
    const host = $("#preseason");
    const top = (S.preseason && S.preseason.top) || [];
    if (!host || !top.length) return;
    const max = Math.max(...top.map((t) => t.p));
    const champ = S.champion && S.champion.team;

    host.innerHTML = top
      .map(
        (t) => `
      <div class="bar${t.team === champ ? " win" : ""}" data-w="${(t.p / max) * 100}">
        <img class="flag" src="${flag(t.iso)}" alt="" width="26" height="19" loading="lazy">
        <span class="nm">${nm(t.team)}</span>
        <span class="track"><i class="fill"></i></span>
        <span class="pc">${pct(t.p)}</span>
      </div>`
      )
      .join("");
  }

  /* ---------- Cap 02 · el muro de los 104 partidos ---------- */
  function buildWall(S) {
    const host = $("#wall");
    const ms = S.matches || [];
    if (!host || !ms.length) return;

    host.innerHTML = ms
      .map((m) => {
        const said =
          m.outcome === "H" ? m.p_home : m.outcome === "A" ? m.p_away : m.p_draw;
        const tip =
          `${m.phase}\n${nm(m.home)} ${m.gh}–${m.ga} ${nm(m.away)}\n` +
          `el modelo daba ${pct(said, 0)} a ese resultado`;
        return `<div class="cell${m.hit ? " hit" : ""}" data-tip="${tip.replace(/"/g, "&quot;")}" tabindex="0" role="img" aria-label="${nm(m.home)} ${m.gh} ${nm(m.away)} ${m.ga}. ${m.hit ? "Acertado" : "Fallado"}"></div>`;
      })
      .join("");

    const hits = ms.filter((m) => m.hit).length;
    const el = $("#wallHits");
    if (el) el.textContent = hits;
  }

  /* ---------- Cap 02 · las sorpresas ---------- */
  function buildSurprises(S) {
    const host = $("#surprises");
    const sp = (S.surprises || []).slice(0, 5);
    if (!host || !sp.length) return;

    host.innerHTML = sp
      .map((s) => {
        const said =
          s.gh === s.ga
            ? s.p_draw
            : s.gh > s.ga
            ? s.p_home
            : s.p_away;
        return `
      <div class="surp reveal">
        <div class="m">
          <img src="${flag(s.home_iso, 40)}" alt="" width="22" height="16" loading="lazy"><b>${nm(s.home)}</b>
          <span class="sc">${s.gh}–${s.ga}</span>
          <b>${nm(s.away)}</b><img src="${flag(s.away_iso, 40)}" alt="" width="22" height="16" loading="lazy">
          <span class="ph">${s.phase}</span>
          <span class="said">el modelo le daba ${pct(said, 0)} a lo que acabó pasando</span>
        </div>
        <div class="pct">${pct(s.surprise, 0)}<span>sorpresa</span></div>
      </div>`;
      })
      .join("");
  }

  /* ---------- Cap 03 · la carrera de probabilidades ---------- */
  function buildRace(S) {
    const svg = $("#race");
    const race = S.race || {};
    const teams = Object.keys(race);
    if (!svg || !teams.length) return;

    const W = 1000, H = 460;
    const M = { t: 24, r: 90, b: 34, l: 44 };
    const iw = W - M.l - M.r, ih = H - M.t - M.b;

    // eje X por fecha real (no por índice): así el parón entre tomas se ve
    const all = teams.flatMap((t) => race[t]);
    const ts = all.map((d) => Date.parse(d.date));
    const t0 = Math.min(...ts), t1 = Math.max(...ts);
    // techo redondeado al 20 % siguiente: ejes en 0/20/40/60, no en 16/31/47
    const rawMax = Math.max(...all.map((d) => d.p));
    const maxP = Math.min(1, Math.ceil(rawMax / 0.2) * 0.2);

    const X = (d) => M.l + ((Date.parse(d) - t0) / (t1 - t0 || 1)) * iw;
    const Y = (p) => M.t + ih - (p / maxP) * ih;

    const COLORS = { Espana: "#f0c14b", Francia: "#4cd7f6", Argentina: "#9aa7c4" };
    const color = (t, i) => COLORS[t] || ["#c084fc", "#4ade80", "#fb923c"][i % 3];

    let out = "";

    // rejilla horizontal + etiquetas de %
    const steps = Math.round(maxP / 0.2);
    for (let i = 0; i <= steps; i++) {
      const p = 0.2 * i, y = Y(p);
      out += `<line class="grid" x1="${M.l}" y1="${y}" x2="${W - M.r}" y2="${y}"/>`;
      out += `<text class="axlbl" x="${M.l - 10}" y="${y + 4}" text-anchor="end">${Math.round(p * 100)}%</text>`;
    }

    // etiquetas de fecha (primera, el giro, última)
    const fmt = (s) => {
      const d = new Date(s + "T12:00:00");
      return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
    };
    const dates = [...new Set(all.map((d) => d.date))].sort();
    [dates[0], dates[Math.floor(dates.length / 2)], dates[dates.length - 1]].forEach((d) => {
      out += `<text class="axlbl" x="${X(d)}" y="${H - 8}" text-anchor="middle">${fmt(d)}</text>`;
    });

    // una línea por equipo
    const paths = [];
    teams.forEach((team, i) => {
      const pts = race[team].filter((d) => Number.isFinite(d.p));
      if (pts.length < 2) return;
      const d = pts.map((p, j) => `${j ? "L" : "M"}${X(p.date).toFixed(1)},${Y(p.p).toFixed(1)}`).join(" ");
      const c = color(team, i);
      out += `<path class="rline" data-team="${team}" d="${d}" stroke="${c}"/>`;
      const last = pts[pts.length - 1];
      out += `<circle class="rdot" data-team="${team}" cx="${X(last.date).toFixed(1)}" cy="${Y(last.p).toFixed(1)}" r="5" fill="${c}"/>`;
      out += `<text class="axlbl" x="${W - M.r + 12}" y="${Y(last.p) + 4}" fill="${c}" style="font-weight:800">${nm(team)} ${Math.round(last.p * 100)}%</text>`;
      paths.push(team);
    });

    svg.innerHTML = out;

    // leyenda
    const leg = $("#racelegend");
    if (leg) {
      leg.innerHTML = teams
        .map((t, i) => `<span><i style="background:${color(t, i)}"></i>${nm(t)}</span>`)
        .join("");
    }
  }

  /* ---------- Cap 04 · el camino del campeón ---------- */
  function buildRoad(S) {
    const host = $("#road");
    const road = (S.champion && S.champion.road) || [];
    if (!host || !road.length) return;

    host.innerHTML = road
      .map(
        (m) => `
      <li class="reveal">
        <span class="ph">${m.phase}</span>
        <span class="mt">
          <img src="${flag(isoOf(S, m.home), 40)}" alt="" width="22" height="16" loading="lazy">${nm(m.home)}
          <span class="sc">${m.gh}–${m.ga}</span>
          ${nm(m.away)}<img src="${flag(isoOf(S, m.away), 40)}" alt="" width="22" height="16" loading="lazy">
        </span>
        <span class="pw">${Math.round(m.p_win * 100)}%<span>daba el modelo</span></span>
      </li>`
      )
      .join("");
  }

  // el iso de cada equipo ya viene en matches; lo indexamos una vez
  let ISO = null;
  function isoOf(S, team) {
    if (!ISO) {
      ISO = {};
      (S.matches || []).forEach((m) => {
        ISO[m.home] = m.home_iso;
        ISO[m.away] = m.away_iso;
      });
    }
    return ISO[team] || "un";
  }

  /* ---------- Cap 05 · el veredicto ---------- */
  function buildVerdict(S) {
    const v = S.verdict;
    if (!v) return;

    const host = $("#verdict");
    if (host) {
      host.innerHTML = `
        <div class="vcard good reveal">
          <b data-count="${(v.top1 * 100).toFixed(1)}" data-dec="1" data-suffix=" %">0</b>
          <span class="lbl">Aciertos 1X2</span>
          <span class="hint">Acertó el signo en ${Math.round(v.top1 * v.n)} de los ${v.n} partidos.</span>
        </div>
        <div class="vcard reveal">
          <b data-count="${v.brier.toFixed(3)}" data-dec="3">0</b>
          <span class="lbl">Brier medio</span>
          <span class="hint">Error cuadrático de la probabilidad. Cuanto más bajo, mejor calibrado.</span>
        </div>
        <div class="vcard reveal">
          <b data-count="${v.rps.toFixed(3)}" data-dec="3">0</b>
          <span class="lbl">RPS medio</span>
          <span class="hint">Como el Brier, pero castiga más equivocarse «de lejos».</span>
        </div>
        <div class="vcard reveal">
          <b data-count="${v.n}">0</b>
          <span class="lbl">Partidos juzgados</span>
          <span class="hint">Los 104, cada uno predicho antes de jugarse.</span>
        </div>`;
    }

    const eh = $("#engines");
    const engs = v.engines || [];
    if (eh && engs.length) {
      const best = engs.reduce((a, b) => (b.brier < a.brier ? b : a));
      const maxTop = Math.max(...engs.map((e) => e.top1));
      eh.innerHTML = engs
        .map(
          (e) => `
        <div class="eng reveal${e.key === best.key ? " best" : ""}" data-w="${(e.top1 / maxTop) * 100}">
          <span class="nm">${e.label}${e.key === best.key ? "<i>mejor Brier</i>" : ""}</span>
          <span class="track"><i class="fill"></i></span>
          <span class="metrics">
            <div><b>${pct(e.top1)}</b><span>aciertos</span></div>
            <div><b>${num(e.brier, 3)}</b><span>Brier</span></div>
            <div><b>${num(e.rps, 3)}</b><span>RPS</span></div>
          </span>
        </div>`
        )
        .join("");

      const punch = $("#enginePunch");
      if (punch) {
        const elo = engs.find((e) => e.key === "elo");
        const xgb = engs.find((e) => e.key === "xgb");
        const ens = engs.find((e) => e.key === "ensemble");
        if (elo && xgb && ens) {
          const gap = ((elo.brier - xgb.brier) / elo.brier) * 100;
          punch.innerHTML =
            `El veredicto: <b>el XGBoost de estadísticas ganó al Elo puro</b> — ` +
            `${gap.toFixed(0)} % menos de error de Brier sobre los mismos 104 partidos.<br>` +
            `<span class="quiet">La mezcla al 50 % que usé durante el torneo quedó en medio (${num(ens.brier, 3)}). ` +
            `Con los datos en la mano, el peso de las estadísticas debería haber sido mayor.</span>`;
        }
      }
    }
  }

  /* ---------- Cap 06 · el archivo ---------- */
  function buildArchive(S) {
    const a = S.archive || {};
    const host = $("#archive");
    if (host) {
      host.innerHTML = `
        <div class="acard reveal"><b data-count="${a.snapshots || 0}">0</b><span>tomas de probabilidad</span>
          <i>del ${fmtLong(a.first)} al ${fmtLong(a.last)}</i></div>
        <div class="acard reveal"><b data-count="${S.tournament ? S.tournament.matches : 0}">0</b><span>partidos registrados</span>
          <i>verificados contra la API</i></div>
        <div class="acard reveal"><b data-count="${a.audio || 0}">0</b><span>boletines en audio</span>
          <i>uno por jornada grande</i></div>
        <div class="acard reveal"><b data-count="${S.tournament ? S.tournament.goals : 0}">0</b><span>goles</span>
          <i>${S.scorers && S.scorers[0] ? S.scorers[0].player + " máximo goleador" : ""}</i></div>`;
    }

    const bh = $("#boletines");
    const bols = S.boletines || [];
    if (bh && bols.length) {
      bh.innerHTML = bols
        .slice()
        .reverse()
        .map((f) => {
          const d = (f.match(/(\d{4}-\d{2}-\d{2})/) || [])[1] || "";
          return `<div class="bol reveal"><div class="d">${fmtLong(d)}</div>
            <audio controls preload="none" src="audio/${f}"></audio></div>`;
        })
        .join("");
    }
  }

  function fmtLong(s) {
    if (!s) return "";
    const d = new Date(s + "T12:00:00");
    return d.toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" });
  }

  function stampFooter(S) {
    const el = $("#builtAt");
    if (el && S.tournament) {
      el.textContent = `${S.tournament.matches} partidos · ${S.tournament.goals} goles · ${S.tournament.teams} selecciones`;
    }
  }

  /* ======================================================================
     3 · MOVIMIENTO
     ==================================================================== */
  function wireMotion(S) {
    lazyVideos();
    chapterNav();
    progressBar();

    if (REDUCED) {
      // sin movimiento: dejamos todo en su estado final, visible y legible
      $$(".bar").forEach((b) => (b.querySelector(".fill").style.width = b.dataset.w + "%"));
      $$(".eng").forEach((e) => (e.querySelector(".fill").style.width = e.dataset.w + "%"));
      $$("[data-count]").forEach((n) => (n.textContent = num(parseFloat(n.dataset.count), parseInt(n.dataset.dec || "0", 10)) + (n.dataset.suffix || "")));
      $$(".rline").forEach((p) => p.style.strokeDasharray = "none");
      return;
    }

    reveals();
    counters();
    barFills();
    matchWall();
    raceDraw();
    parallax();
    scrubVideos();
    wipes();
  }

  /* ---------- reveals genéricos ---------- */
  function reveals() {
    $$(".reveal").forEach((el) => {
      gsap.to(el, {
        opacity: 1, y: 0, duration: 0.85, ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 88%", once: true },
      });
    });
  }

  /* ---------- contadores ---------- */
  function counters() {
    $$("[data-count]").forEach((el) => {
      const end = parseFloat(el.dataset.count);
      const dec = parseInt(el.dataset.dec || "0", 10);
      const suf = el.dataset.suffix || "";
      const o = { v: 0 };
      gsap.to(o, {
        v: end, duration: 1.6, ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 85%", once: true },
        onUpdate: () => { el.textContent = num(o.v, dec) + suf; },
      });
    });
  }

  /* ---------- barras ---------- */
  function barFills() {
    $$(".bar").forEach((bar, i) => {
      gsap.to(bar.querySelector(".fill"), {
        width: bar.dataset.w + "%", duration: 1.1, ease: "power3.out", delay: i * 0.06,
        scrollTrigger: { trigger: bar, start: "top 90%", once: true },
      });
    });
    $$(".eng").forEach((e, i) => {
      gsap.to(e.querySelector(".fill"), {
        width: e.dataset.w + "%", duration: 1.1, ease: "power3.out", delay: i * 0.12,
        scrollTrigger: { trigger: e, start: "top 88%", once: true },
      });
    });
  }

  /* ---------- muro de partidos: entra en cascada ---------- */
  function matchWall() {
    const wall = $("#wall");
    if (!wall) return;
    gsap.to(wall.children, {
      opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.4)",
      stagger: { each: 0.006, from: "start" },
      scrollTrigger: { trigger: wall, start: "top 85%", once: true },
    });
  }

  /* ---------- la carrera se dibuja con el scroll ---------- */
  function raceDraw() {
    const svg = $("#race");
    if (!svg) return;
    const lines = $$(".rline", svg);
    const dots = $$(".rdot", svg);
    if (!lines.length) return;

    lines.forEach((p) => {
      const L = p.getTotalLength();
      p.style.strokeDasharray = L;
      p.style.strokeDashoffset = L;
    });
    gsap.set(dots, { opacity: 0, scale: 0, transformOrigin: "center" });

    gsap.timeline({
      scrollTrigger: { trigger: ".racewrap", start: "top 78%", end: "bottom 65%", scrub: 0.6 },
    })
      .to(lines, { strokeDashoffset: 0, ease: "none", duration: 1 })
      .to(dots, { opacity: 1, scale: 1, duration: 0.15, stagger: 0.05 }, ">-0.1");
  }

  /* ---------- paralaje de los fondos ---------- */
  function parallax() {
    $$(".bgvid").forEach((box) => {
      const section = box.closest(".chapter");
      if (!section || box.dataset.scrub) return; // los de scrub no se mueven
      gsap.fromTo(
        box.querySelector("video"),
        { yPercent: -6 },
        {
          yPercent: 6, ease: "none",
          scrollTrigger: { trigger: section, start: "top bottom", end: "bottom top", scrub: true },
        }
      );
    });
  }

  /* ---------- vídeo que avanza con el scroll ---------- */
  function scrubVideos() {
    $$(".bgvid[data-scrub]").forEach((box) => {
      const v = box.querySelector("video");
      const section = box.closest(".chapter");
      if (!v || !section) return;

      let ready = false;
      v.addEventListener("loadedmetadata", () => { ready = true; }, { once: true });

      ScrollTrigger.create({
        trigger: section,
        start: "top top",
        end: "bottom top",
        scrub: 0.4,
        onUpdate: (self) => {
          if (!ready || !v.duration || !Number.isFinite(v.duration)) return;
          const t = self.progress * v.duration;
          // evitamos seeks redundantes: el decoder lo agradece
          if (Math.abs(v.currentTime - t) > 0.03) v.currentTime = t;
        },
      });
    });
  }

  /* ---------- transiciones entre capítulos ---------- */
  function wipes() {
    const layer = $(".wipe");
    const vid = $(".wipe-vid");
    if (!layer) return;

    // Los clips de barrido son opcionales. Si no existen, hacemos el barrido
    // con un degradado CSS: el efecto se mantiene con cero assets.
    const CLIPS = ["assets/wipe_light.mp4", "assets/wipe_confetti.mp4", "assets/wipe_particles.mp4"];
    let available = [];
    let checked = 0;

    CLIPS.forEach((src) => {
      const probe = document.createElement("video");
      probe.preload = "metadata";
      probe.muted = true;
      probe.addEventListener("loadedmetadata", () => { available.push(src); done(); }, { once: true });
      probe.addEventListener("error", done, { once: true });
      probe.src = src;
    });
    function done() { if (++checked === CLIPS.length) install(); }

    let busy = false;
    function install() {
      $$(".chapter").forEach((sec, i) => {
        if (i === 0) return;
        ScrollTrigger.create({
          trigger: sec,
          start: "top 65%",
          once: true,
          onEnter: () => fire(i),
        });
      });
    }

    function fire(i) {
      if (busy) return;
      busy = true;
      if (available.length && vid) {
        const src = available[(i - 1) % available.length];
        if (vid.getAttribute("src") !== src) vid.src = src;
        vid.currentTime = 0;
        const p = vid.play();
        if (p && p.catch) p.catch(() => {});
        gsap.timeline({ onComplete: () => { busy = false; vid.pause(); } })
          .set(layer, { opacity: 1 })
          .to(layer, { opacity: 0, duration: 0.5, delay: 1.2, ease: "power2.in" });
      } else {
        cssSweep(() => { busy = false; });
      }
    }

    // barrido de luz puramente CSS: el plan B que nunca falla
    function cssSweep(cb) {
      const el = document.createElement("div");
      el.style.cssText =
        "position:fixed;inset:0;z-index:131;pointer-events:none;" +
        "background:linear-gradient(100deg,transparent 38%,rgba(240,193,75,0.5) 47%," +
        "rgba(255,255,255,0.75) 50%,rgba(76,215,246,0.5) 53%,transparent 62%);" +
        "transform:translateX(-100%)";
      document.body.appendChild(el);
      gsap.to(el, {
        x: "200%", duration: 0.85, ease: "power2.inOut",
        onComplete: () => { el.remove(); cb && cb(); },
      });
    }
  }

  /* ---------- carga diferida de los vídeos de fondo ---------- */
  function lazyVideos() {
    const boxes = $$(".bgvid");
    // el del hero se carga ya: es lo primero que se ve
    const first = boxes[0];
    if (first) load(first);

    if (!("IntersectionObserver" in window)) { boxes.forEach(load); return; }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { load(e.target); io.unobserve(e.target); }
        });
      },
      { rootMargin: "150% 0px" }
    );
    boxes.forEach((b) => { if (b !== first) io.observe(b); });

    function load(box) {
      const v = box.querySelector("video");
      const src = box.dataset.src;
      if (!v || !src || v.dataset.loaded) return;
      v.dataset.loaded = "1";
      // si el clip no existe, el degradado de ::before se queda: no rompe nada
      v.addEventListener("error", () => { v.style.display = "none"; }, { once: true });
      v.addEventListener("loadeddata", () => {
        if (!box.dataset.scrub) { const p = v.play(); if (p && p.catch) p.catch(() => {}); }
        ScrollTrigger.refresh();
      }, { once: true });
      v.src = src;
    }
  }

  /* ---------- navegación de capítulos ---------- */
  function chapterNav() {
    const items = $$(".chapternav li");
    if (!items.length) return;
    $$(".chapter").forEach((sec, i) => {
      ScrollTrigger.create({
        trigger: sec, start: "top 50%", end: "bottom 50%",
        onToggle: (self) => { if (self.isActive) setOn(i); },
      });
    });
    function setOn(i) { items.forEach((li, j) => li.classList.toggle("on", i === j)); }
    setOn(0);
  }

  /* ---------- barra de progreso ---------- */
  function progressBar() {
    const bar = $(".progress i");
    if (!bar) return;
    const update = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + "%";
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
  }
})();
