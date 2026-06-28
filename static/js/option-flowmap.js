/* ============================================================
   FloMo — "FLOW MAP" additive interactions
   Three NEW pieces, all degrade gracefully and honor
   prefers-reduced-motion:
     1) flow-progress + vertical rail  (where am I along
        video -> motion -> action)
     2) hero scene-flow vector field   (canvas particles,
        coloured by the dx,dy,dz -> RGB rule, biased to palette)
     3) embodiment-agnostic motion morph (signature: a hand
        motion field morphs into a gripper motion field while
        the motion / colour token stays identical)
   index.js still drives the standard widgets; this file only
   adds and never overrides them.
   ============================================================ */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function lerp(a, b, t) { return a + (b - a) * t; }

  /* palette anchors (the locked tokens) */
  var ORANGE = [240, 144, 24];
  var TEAL = [48, 120, 144];

  /* ============================================================
     1) FLOW PROGRESS + VERTICAL RAIL
     ============================================================ */
  function initFlowProgress() {
    var marker = document.getElementById('fpMarker');
    var railMarker = document.getElementById('frMarker');
    var stations = [].slice.call(document.querySelectorAll('.fp-station'));
    var phases = ['video', 'motion', 'action'];

    // map each phase to the first section that declares it
    var sectionsByPhase = {};
    phases.forEach(function (p) {
      sectionsByPhase[p] = [].slice.call(
        document.querySelectorAll('section[data-phase="' + p + '"]'));
    });

    if (!marker && !railMarker && !stations.length) return;

    function currentPhase() {
      // phase of the section whose top is nearest above mid-viewport
      var probe = window.scrollY + window.innerHeight * 0.42;
      var best = 'video', bestTop = -Infinity;
      [].forEach.call(document.querySelectorAll('section[data-phase]'), function (s) {
        var top = s.getBoundingClientRect().top + window.scrollY;
        if (top <= probe && top > bestTop) { bestTop = top; best = s.dataset.phase; }
      });
      return best;
    }

    function update() {
      var doc = document.documentElement;
      var max = (doc.scrollHeight - window.innerHeight) || 1;
      var p = clamp(window.scrollY / max, 0, 1);
      if (marker) marker.style.left = (p * 100) + '%';
      if (railMarker) railMarker.style.top = (p * 100) + '%';

      var phase = currentPhase();
      var reached = true;
      // light current phase, mark prior phases done
      var idx = phases.indexOf(phase);
      stations.forEach(function (st) {
        var i = phases.indexOf(st.dataset.phase);
        st.classList.toggle('active', i === idx);
        st.classList.toggle('done', i < idx);
      });
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { update(); ticking = false; });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  }

  /* ============================================================
     2) HERO SCENE-FLOW VECTOR FIELD
     Particles advect through a smooth flow field. Each particle
     is coloured by its velocity using the paper's mapping
     (vx,vy,vz -> R,G,B), then biased toward the brand palette so
     the field reads orange/teal rather than full-spectrum.
     ============================================================ */
  function initHeroField() {
    var canvas = document.getElementById('heroField');
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var parts = [];
    var t = 0;
    var running = false, rafId = null;

    function resize() {
      var r = canvas.getBoundingClientRect();
      W = Math.max(1, r.width); H = Math.max(1, r.height);
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // smooth pseudo-curl field -> (vx, vy); a 3rd "depth" channel
    // is derived for the blue channel of the colour mapping.
    function field(x, y, time) {
      var nx = x * 0.0042, ny = y * 0.0042;
      var vx = Math.sin(ny + time * 0.45) + 0.55 * Math.cos(nx * 1.7 - time * 0.3);
      var vy = Math.cos(nx + time * 0.4) - 0.55 * Math.sin(ny * 1.6 + time * 0.25);
      return [vx, vy];
    }

    function colorFor(vx, vy) {
      // direction -> blend between teal and orange (the two brand hues)
      var ang = Math.atan2(vy, vx);            // -pi..pi
      var mix = (Math.sin(ang) + 1) / 2;       // 0..1
      var depth = (Math.cos(ang) + 1) / 2;     // pseudo dz -> brightness
      var r = lerp(TEAL[0], ORANGE[0], mix);
      var g = lerp(TEAL[1], ORANGE[1], mix);
      var b = lerp(TEAL[2], ORANGE[2], mix);
      // gentle depth lift so the field has air, never muddy
      var lift = 0.12 + depth * 0.18;
      r = clamp(r + (255 - r) * lift, 0, 255);
      g = clamp(g + (255 - g) * lift, 0, 255);
      b = clamp(b + (255 - b) * lift, 0, 255);
      return 'rgba(' + (r | 0) + ',' + (g | 0) + ',' + (b | 0) + ',';
    }

    function makeParticle() {
      return { x: Math.random() * W, y: Math.random() * H, life: 40 + Math.random() * 90, age: Math.random() * 120 };
    }
    function seed() {
      var n = Math.round(clamp(W / 9, 60, 150));
      parts = [];
      for (var i = 0; i < n; i++) parts.push(makeParticle());
    }

    function step() {
      // fade trails instead of clearing -> soft flow lines
      ctx.fillStyle = 'rgba(255,255,255,0.10)';
      ctx.fillRect(0, 0, W, H);
      ctx.lineWidth = 1.4;
      ctx.lineCap = 'round';
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        var f = field(p.x, p.y, t);
        var vx = f[0], vy = f[1];
        var nx = p.x + vx * 1.5;
        var ny = p.y + vy * 1.5;
        ctx.strokeStyle = colorFor(vx, vy) + '0.42)';
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(nx, ny);
        ctx.stroke();
        p.x = nx; p.y = ny; p.age++;
        if (p.age > p.life || p.x < -5 || p.x > W + 5 || p.y < -5 || p.y > H + 5) {
          parts[i] = makeParticle();
        }
      }
      t += 0.016;
    }

    function loop() {
      if (!running) return;
      step();
      rafId = window.requestAnimationFrame(loop);
    }

    function drawStatic() {
      // calm single frame: a grid of short coloured flow arrows
      ctx.clearRect(0, 0, W, H);
      var gap = 46;
      for (var y = gap / 2; y < H; y += gap) {
        for (var x = gap / 2; x < W; x += gap) {
          var f = field(x, y, 0.6);
          var vx = f[0], vy = f[1];
          var m = Math.sqrt(vx * vx + vy * vy) || 1;
          var len = 13;
          ctx.strokeStyle = colorFor(vx, vy) + '0.30)';
          ctx.lineWidth = 1.6; ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + (vx / m) * len, y + (vy / m) * len);
          ctx.stroke();
        }
      }
    }

    function start() {
      if (running) return;
      running = true;
      loop();
    }
    function stop() {
      running = false;
      if (rafId) { window.cancelAnimationFrame(rafId); rafId = null; }
    }

    resize(); seed();
    if (reduceMotion) { drawStatic(); }
    else {
      // paint white base so first frames aren't black
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
      start();
      // pause when hero scrolls out of view (save CPU)
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) { if (e.isIntersecting) start(); else stop(); });
        }, { threshold: 0 });
        io.observe(canvas);
      }
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) stop(); else if (isOnScreen()) start();
      });
    }

    function isOnScreen() {
      var r = canvas.getBoundingClientRect();
      return r.bottom > 0 && r.top < window.innerHeight;
    }

    var rt = null;
    window.addEventListener('resize', function () {
      if (rt) clearTimeout(rt);
      rt = setTimeout(function () {
        resize(); seed();
        if (reduceMotion) drawStatic();
        else { ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H); }
      }, 160);
    });
  }

  /* ============================================================
     3) SIGNATURE — embodiment-agnostic motion morph
     A two-pronged grasper morphs hand <-> gripper. The motion
     field (arrows) and the encoded colour token never change:
     "swap the body, keep the motion."
     ============================================================ */
  function initMorph() {
    var root = document.getElementById('morphField');
    if (!root) return;
    var canvas = root.querySelector('.morph-canvas');
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var slider = document.getElementById('morphSlider');
    var playBtn = document.getElementById('morphPlay');
    var tagHuman = root.querySelector('.morph-tag.human');
    var tagRobot = root.querySelector('.morph-tag.robot');

    var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var m = 0;          // 0 = human hand, 1 = robot gripper
    var auto = !reduceMotion;
    var phase = 0;
    var rafId = null;

    function resize() {
      var r = canvas.getBoundingClientRect();
      W = Math.max(1, r.width); H = Math.max(1, r.height);
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // a two-prong grasper outline, parameterised so the same path
    // describes a pinching hand (curved, tapered) and a parallel
    // gripper (straight, boxy). cx,cy = base anchor; s = scale.
    function grasperPath(t, cx, cy, s, open) {
      // interpolated shape params
      var baseW = lerp(0.30, 0.40, t) * s;     // mount width
      var baseH = lerp(0.16, 0.20, t) * s;
      var prongLen = lerp(0.92, 0.86, t) * s;
      var outerW = lerp(0.30, 0.30, t) * s;    // half outer span
      var gap = lerp(0.10, 0.13, t) * s + open * s; // inner gap (grasp opening)
      var tipTaper = lerp(0.55, 0.04, t);      // hand tapers, gripper barely
      var bend = lerp(0.10, 0.0, t) * s;       // hand curls inward
      var pw = lerp(0.14, 0.13, t) * s;        // prong thickness

      // build right half (then mirror) as a poly-line up the outside,
      // across the tip, down the inside.
      function side(sign) {
        var pts = [];
        var bx = sign * baseW / 2;
        // base corners
        pts.push([cx + sign * 0.02 * s, cy]);             // near gap bottom
        pts.push([cx + bx, cy]);                           // base outer bottom
        pts.push([cx + bx, cy - baseH]);                   // base outer top
        // up the outer edge of the prong (slight inward bend for hand)
        var ox = sign * (gap / 2 + pw);
        pts.push([cx + ox + sign * (outerW - gap / 2 - pw) * 0.25, cy - baseH]);
        pts.push([cx + ox + sign * bend, cy - baseH - prongLen * 0.5]);
        pts.push([cx + ox + sign * bend * 1.4, cy - baseH - prongLen]);
        // tip (taper pulls inner-top toward gap for the hand)
        var tipOuter = cx + ox + sign * bend * 1.4;
        var tipInner = cx + sign * (gap / 2) + sign * (1 - tipTaper) * pw + sign * bend * 1.4 * tipTaper;
        pts.push([tipInner, cy - baseH - prongLen]);
        // down the inner edge back to gap bottom
        pts.push([cx + sign * (gap / 2) + sign * bend, cy - baseH - prongLen * 0.45]);
        pts.push([cx + sign * (gap / 2), cy - baseH * 0.4]);
        return pts;
      }
      var right = side(1);
      var left = side(-1).reverse();
      return left.concat(right);
    }

    function strokeFillPath(pts, fill, stroke) {
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.closePath();
      if (fill) { ctx.fillStyle = fill; ctx.fill(); }
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.stroke(); }
    }

    // the constant motion token: a down-left "pull" (the Pull-String
    // primitive). dx,dy,dz are chosen so the encoded colour lands on a
    // locked brand token: (-0.72,-0.27,-0.12) -> rgb(36,93,112) = teal-dark.
    var MOT = { dx: -0.72, dy: -0.27, dz: -0.12 };
    function chan(v) { return Math.round((v + 1) / 2 * 255); }
    var motRGB = 'rgb(' + chan(MOT.dx) + ',' + chan(MOT.dy) + ',' + chan(MOT.dz) + ')';
    // the encoded token swatch is constant across the morph
    var mtSwatch = document.getElementById('mtSwatch');
    if (mtSwatch) mtSwatch.style.background = motRGB;

    function drawArrow(x, y, ang, len, col) {
      var ex = x + Math.cos(ang) * len, ey = y + Math.sin(ang) * len;
      ctx.strokeStyle = col; ctx.lineWidth = 3; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ex, ey); ctx.stroke();
      var a1 = ang + 2.5, a2 = ang - 2.5, hl = len * 0.34;
      ctx.beginPath();
      ctx.moveTo(ex, ey); ctx.lineTo(ex + Math.cos(a1) * hl, ey + Math.sin(a1) * hl);
      ctx.moveTo(ex, ey); ctx.lineTo(ex + Math.cos(a2) * hl, ey + Math.sin(a2) * hl);
      ctx.stroke();
    }

    function draw(pull) {
      ctx.clearRect(0, 0, W, H);
      var s = Math.min(W, H) * 0.78;
      var cx = W * 0.5;
      var cy = H * 0.86;

      // ---- the string (the grasped object), pulled along motion dir
      var graspX = cx, graspY = cy - s * 0.86;
      var pullAng = Math.atan2(-MOT.dy, MOT.dx); // screen: dy up-positive
      var pullMag = (reduceMotion ? 0.5 : pull) * s * 0.16;
      // anchor at top bar
      ctx.strokeStyle = 'rgba(91,102,117,0.5)';
      ctx.lineWidth = 6; ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.34, H * 0.10);
      ctx.lineTo(cx + s * 0.34, H * 0.10);
      ctx.stroke();
      var sx = cx + Math.cos(pullAng) * pullMag;
      var sy = (graspY) + Math.sin(pullAng) * pullMag;
      ctx.strokeStyle = 'rgba(91,102,117,0.85)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(cx, H * 0.10);
      ctx.lineTo(sx, sy);
      ctx.stroke();
      // string end bead
      ctx.fillStyle = 'rgba(91,102,117,0.9)';
      ctx.beginPath(); ctx.arc(sx, sy, 5, 0, Math.PI * 2); ctx.fill();

      // ---- the grasper (morphs hand <-> gripper), follows the pull
      var gx = sx, gy = sy + s * 0.04;
      var pts = grasperPath(m, gx, gy, s, 0.0);

      // colour shifts subtly with embodiment but stays in-palette
      var fillH = 'rgba(48,120,144,0.16)', strokeH = 'rgba(36,93,112,0.9)';
      var fillR = 'rgba(91,102,117,0.18)', strokeR = 'rgba(31,39,51,0.92)';
      var fill = m < 0.5 ? fillH : fillR;
      var stroke = m < 0.5 ? strokeH : strokeR;
      strokeFillPath(pts, fill, stroke);
      // wrist / mount accent
      ctx.fillStyle = m < 0.5 ? 'rgba(48,120,144,0.9)' : 'rgba(31,39,51,0.9)';
      ctx.beginPath(); ctx.arc(gx, gy + s * 0.02, s * 0.05, 0, Math.PI * 2); ctx.fill();

      // ---- the CONSTANT motion field: arrows in the brand-mapped
      // colour, identical regardless of embodiment.
      var motCol = motRGB;
      drawArrow(sx, sy, pullAng, s * 0.26, motCol);
      drawArrow(gx - s * 0.16, gy - s * 0.5, pullAng, s * 0.18, motCol);
      drawArrow(gx + s * 0.16, gy - s * 0.5, pullAng, s * 0.18, motCol);
    }

    function setLit() {
      if (tagHuman) tagHuman.classList.toggle('lit', m < 0.5);
      if (tagRobot) tagRobot.classList.toggle('lit', m >= 0.5);
    }

    function frame() {
      if (auto) {
        phase += 0.006;
        // ease-in-out triangle between 0 and 1, with dwell at ends
        var tri = (Math.sin(phase) + 1) / 2;
        m = tri;
        if (slider) slider.value = String(Math.round(m * 100));
      }
      var pull = reduceMotion ? 0.5 : (Math.sin(phase * 1.0) * 0.5 + 0.5);
      draw(pull);
      setLit();
      rafId = window.requestAnimationFrame(frame);
    }

    function renderOnce() {
      draw(0.5); setLit();
    }

    if (slider) {
      slider.addEventListener('input', function () {
        auto = false;
        if (playBtn) { playBtn.classList.remove('active'); playBtn.textContent = 'Auto-morph'; playBtn.setAttribute('aria-pressed', 'false'); }
        m = clamp(parseFloat(slider.value) / 100, 0, 1);
        if (reduceMotion) renderOnce();
      });
    }
    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (reduceMotion) return; // no auto animation under reduced motion
        auto = !auto;
        playBtn.classList.toggle('active', auto);
        playBtn.textContent = auto ? 'Pause' : 'Auto-morph';
        playBtn.setAttribute('aria-pressed', auto ? 'true' : 'false');
        if (auto) { phase = Math.asin(m * 2 - 1) || 0; }
      });
      if (!reduceMotion) { playBtn.classList.add('active'); playBtn.textContent = 'Pause'; playBtn.setAttribute('aria-pressed', 'true'); }
    }

    resize();
    if (reduceMotion) { renderOnce(); }
    else {
      // run only while on screen
      var active = false;
      function go() { if (!active) { active = true; frame(); } }
      function halt() { active = false; if (rafId) { window.cancelAnimationFrame(rafId); rafId = null; } }
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) { if (e.isIntersecting) go(); else halt(); });
        }, { threshold: 0.15 });
        io.observe(canvas);
      } else { go(); }
    }

    var rt = null;
    window.addEventListener('resize', function () {
      if (rt) clearTimeout(rt);
      rt = setTimeout(function () { resize(); if (reduceMotion) renderOnce(); }, 160);
    });
  }

  ready(function () {
    try { initFlowProgress(); } catch (e) {}
    try { initHeroField(); } catch (e) {}
    try { initMorph(); } catch (e) {}
  });
})();
