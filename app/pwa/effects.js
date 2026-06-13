/* Efectos visuales de la Porra Mundial 2026 (se inyecta en el index.html).
   - Confeti cian/dorado una vez al cargar.
   - Scroll-reveal: las secciones aparecen al entrar en pantalla.
   Failsafe: si algo falla, revela todo a los 2.5s (nunca deja contenido oculto). */
(function () {
  "use strict";

  function confetti() {
    try {
      var c = document.createElement("canvas");
      c.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:99999";
      document.body.appendChild(c);
      var ctx = c.getContext("2d");
      function size() { c.width = innerWidth; c.height = innerHeight; }
      size(); addEventListener("resize", size);
      var colors = ["#06b6d4", "#22d3ee", "#a5f3fc", "#f0c14b", "#ffffff"];
      var P = [];
      for (var i = 0; i < 150; i++) {
        P.push({ x: Math.random() * c.width, y: -20 - Math.random() * c.height * 0.4,
          r: 4 + Math.random() * 5, col: colors[i % colors.length],
          vx: (Math.random() - 0.5) * 3, vy: 3 + Math.random() * 4,
          rot: Math.random() * 6.28, vr: (Math.random() - 0.5) * 0.3 });
      }
      var t0 = performance.now();
      (function frame(t) {
        var dt = t - t0;
        ctx.clearRect(0, 0, c.width, c.height);
        for (var i = 0; i < P.length; i++) {
          var p = P[i];
          p.x += p.vx; p.y += p.vy; p.vy += 0.045; p.rot += p.vr;
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
          ctx.globalAlpha = Math.max(0, 1 - dt / 4200); ctx.fillStyle = p.col;
          ctx.fillRect(-p.r / 2, -p.r / 2, p.r, p.r * 0.6); ctx.restore();
        }
        if (dt < 4200) requestAnimationFrame(frame); else c.remove();
      })(t0);
    } catch (e) {}
  }

  var SEL = ".hero-cine, .next-match, .news-banner, [data-testid='stTabs'], [data-testid='stImage'], [data-testid='stVideo']";

  function reveal() {
    try {
      if (!("IntersectionObserver" in window)) return;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { en.target.classList.add("reveal-in"); io.unobserve(en.target); }
        });
      }, { threshold: 0.08 });
      function scan() {
        document.querySelectorAll(SEL).forEach(function (el) {
          if (!el.classList.contains("reveal-init") && !el.classList.contains("reveal-in")) {
            el.classList.add("reveal-init"); io.observe(el);
          }
        });
      }
      scan();
      new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
      setTimeout(function () {
        document.querySelectorAll(".reveal-init").forEach(function (el) { el.classList.add("reveal-in"); });
      }, 2500);
    } catch (e) {
      document.querySelectorAll(".reveal-init").forEach(function (el) { el.classList.add("reveal-in"); });
    }
  }

  function init() { reveal(); setTimeout(confetti, 900); }
  if (document.readyState !== "loading") setTimeout(init, 400);
  else addEventListener("DOMContentLoaded", function () { setTimeout(init, 400); });
})();
