/* FloMo — "Tactile Compare Engine" additive interactions.
   Signature widgets:
     1. cwWipe  — before/after wipe between RGB observation and scene-flow colour.
     2. duels   — head-to-head metric duels (in-distribution + human-video ablation).
   Everything no-ops gracefully if its DOM is absent, and honours reduced motion.
   index.js continues to drive: rollout explorer, OOD explorer, comparison switcher,
   architecture hotspots, lightbox, #idBars, count-ups, and the #flowCube colour pad. */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var SLOW_RATE = 0.5;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  /* easing count-up shared by the duel scores */
  function animateNumber(el, from, to, suffix, done) {
    suffix = suffix || '';
    if (reduceMotion) { el.textContent = Math.round(to) + suffix; if (done) done(); return; }
    var start = null, dur = 650;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(from + (to - from) * eased) + suffix;
      if (p < 1) requestAnimationFrame(step); else if (done) done();
    }
    requestAnimationFrame(step);
  }

  /* ============================ 1. BEFORE / AFTER WIPE ===================== */
  function initWipe() {
    var root = document.getElementById('cwWipe');
    if (!root) return;
    var win = document.getElementById('cwWindow');
    var before = document.getElementById('cwBefore');
    var after = document.getElementById('cwAfter');
    var range = document.getElementById('cwRange');
    var caption = document.getElementById('cwCaption');
    var chips = [].slice.call(document.querySelectorAll('#cwChips .task-chip'));
    if (!win || !before || !after || !range) return;

    // keyboard stays on the range; pointer wiping is handled on the window
    range.style.pointerEvents = 'none';

    function mkVideo() {
      var v = document.createElement('video');
      v.muted = true; v.loop = true; v.playsInline = true;
      v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
      v.preload = 'auto';
      v.addEventListener('loadedmetadata', function () { try { v.playbackRate = SLOW_RATE; } catch (e) {} });
      return v;
    }
    var vBefore = mkVideo(), vAfter = mkVideo();
    before.appendChild(vBefore); after.appendChild(vAfter);

    var rafId = null;
    function syncLoop() {
      if (Math.abs(vAfter.currentTime - vBefore.currentTime) > 0.06) {
        try { vAfter.currentTime = vBefore.currentTime; } catch (e) {}
      }
      rafId = requestAnimationFrame(syncLoop);
    }
    function startSync() {
      if (reduceMotion || rafId) return;
      rafId = requestAnimationFrame(syncLoop);
    }

    function load(video, poster, cap) {
      vBefore.poster = poster; vAfter.poster = poster;
      vBefore.src = video; vAfter.src = video;
      vBefore.load(); vAfter.load();
      if (caption && cap) caption.innerHTML = cap;
      if (!reduceMotion) {
        var pb = vBefore.play(); if (pb && pb.catch) pb.catch(function () {});
        var pa = vAfter.play(); if (pa && pa.catch) pa.catch(function () {});
        startSync();
      }
    }

    function setSplit(v) {
      v = clamp(v, 0, 100);
      root.style.setProperty('--split', v);
      if (Number(range.value) !== Math.round(v)) range.value = Math.round(v);
    }
    function fromClientX(x) {
      var r = win.getBoundingClientRect();
      setSplit((x - r.left) / r.width * 100);
    }

    var dragging = false;
    win.addEventListener('pointerdown', function (e) {
      dragging = true;
      if (win.setPointerCapture) { try { win.setPointerCapture(e.pointerId); } catch (err) {} }
      fromClientX(e.clientX); e.preventDefault();
    });
    win.addEventListener('pointermove', function (e) { if (dragging) { fromClientX(e.clientX); } });
    window.addEventListener('pointerup', function () { dragging = false; });
    range.addEventListener('input', function () { setSplit(Number(range.value)); });

    // chip switching (re-implements the scene-flow sample selector)
    function select(chip) {
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      load(chip.dataset.video, chip.dataset.poster, chip.dataset.caption);
    }
    chips.forEach(function (chip, i) {
      chip.addEventListener('click', function () { select(chip); });
      chip.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault(); var n = chips[(i + 1) % chips.length]; n.focus(); select(n);
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault(); var p = chips[(i - 1 + chips.length) % chips.length]; p.focus(); select(p);
        }
      });
    });

    // initial state from the markup defaults
    setSplit(Number(range.value) || 52);
    load(root.dataset.video, root.dataset.poster,
      chips[0] ? chips[0].dataset.caption : null);
  }

  /* ============================ 2. HEAD-TO-HEAD DUELS ===================== */
  function initDuels() {
    var duels = [].slice.call(document.querySelectorAll('.duel'));
    if (!duels.length) return;

    duels.forEach(function (duel) {
      var max = parseFloat(duel.getAttribute('data-max')) || 100;
      var unit = duel.getAttribute('data-unit') || '';
      var fillA = duel.querySelector('[data-role="fill-a"]');
      var fillB = duel.querySelector('[data-role="fill-b"]');
      var sideA = duel.querySelector('.duel-side[data-side="a"]');
      var sideB = duel.querySelector('.duel-side[data-side="b"]');
      if (!fillA || !fillB) return;

      var isStatic = duel.hasAttribute('data-static');

      // reveal fills when the duel scrolls into view (or instantly w/ reduced motion)
      function paintFills(a, b) {
        fillA.style.width = (clamp(a, 0, max) / max * 100) + '%';
        fillB.style.width = (clamp(b, 0, max) / max * 100) + '%';
      }

      if (isStatic) {
        var sa = parseFloat(fillA.getAttribute('data-score')) || 0;
        var sb = parseFloat(fillB.getAttribute('data-score')) || 0;
        var reveal = function () { paintFills(sa, sb); };
        if (reduceMotion || !('IntersectionObserver' in window)) { reveal(); }
        else {
          paintFills(0, 0);
          var io = new IntersectionObserver(function (ents) {
            ents.forEach(function (e) { if (e.isIntersecting) { reveal(); io.disconnect(); } });
          }, { threshold: 0.4 });
          io.observe(duel);
        }
        return; // scores animated by index.js count-up; verdict is static markup
      }

      // ----- interactive duel -----
      var selA = duel.querySelector('.duel-pick[data-side="a"]');
      var selB = duel.querySelector('.duel-pick[data-side="b"]');
      var scoreA = duel.querySelector('[data-role="score-a"]');
      var scoreB = duel.querySelector('[data-role="score-b"]');
      var verdict = duel.querySelector('[data-role="verdict"]');
      if (!selA || !selB) return;

      var curA = parseFloat(scoreA.textContent) || 0;
      var curB = parseFloat(scoreB.textContent) || 0;

      function optScore(sel) {
        var o = sel.options[sel.selectedIndex];
        return parseFloat(o.getAttribute('data-score')) || 0;
      }
      function render() {
        var a = optScore(selA), b = optScore(selB);
        var nameA = selA.value, nameB = selB.value;
        animateNumber(scoreA, curA, a, '', null); curA = a;
        animateNumber(scoreB, curB, b, '', null); curB = b;
        paintFills(a, b);

        if (sideA) sideA.classList.toggle('is-winner', a > b);
        if (sideB) sideB.classList.toggle('is-winner', b > a);

        if (verdict) {
          if (a === b) {
            verdict.innerHTML = nameA === nameB
              ? 'Same method &mdash; ' + a + unit + ' either way.'
              : 'Dead even at ' + a + unit + '.';
          } else {
            var win = a > b ? nameA : nameB;
            var diff = Math.abs(a - b);
            verdict.innerHTML = '<b>' + win + '</b> leads by ' + diff + ' points (' +
              Math.max(a, b) + unit + ' vs ' + Math.min(a, b) + unit + ').';
          }
        }
      }
      selA.addEventListener('change', render);
      selB.addEventListener('change', render);

      // first paint: animate from zero on view, else render directly
      if (reduceMotion || !('IntersectionObserver' in window)) { render(); }
      else {
        paintFills(0, 0);
        var io2 = new IntersectionObserver(function (ents) {
          ents.forEach(function (e) { if (e.isIntersecting) { render(); io2.disconnect(); } });
        }, { threshold: 0.35 });
        io2.observe(duel);
      }
    });
  }

  ready(function () {
    initWipe();
    initDuels();
  });
})();
