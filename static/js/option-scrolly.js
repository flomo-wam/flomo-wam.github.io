/* FloMo — "Scrolly Walkthrough" signature interaction (additive, vanilla JS).
 *
 * Drives the sticky visual STAGE from the scrolling narrative steps:
 *   - crossfades scenes (hero -> self-building architecture -> motion->RGB -> results)
 *   - cumulatively reveals the architecture pipeline as build steps scroll past
 *   - updates the act step counter
 *
 * Fully additive: the reused widgets (index.js) are untouched. This no-ops
 * gracefully if the stage is missing, if IntersectionObserver is unavailable,
 * and it honours prefers-reduced-motion (scenes still switch, but without the
 * heavy transitions — those are disabled in CSS).
 */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function initScrolly() {
    var stage = document.getElementById('scrollyStage');
    var steps = [].slice.call(document.querySelectorAll('.scrolly-step'));
    if (!stage || !steps.length) return; // no-op if structure missing

    var scenes = {};
    [].forEach.call(stage.querySelectorAll('.scene'), function (s) {
      scenes[s.getAttribute('data-scene')] = s;
    });
    var archScene = scenes.arch || null;
    var counter = document.getElementById('stepCount');
    var total = steps.length;

    // Track the deepest architecture build reached so the pipeline reveals
    // cumulatively while scrolling down, and folds back when scrolling up.
    function setScene(name) {
      Object.keys(scenes).forEach(function (k) {
        scenes[k].classList.toggle('is-active', k === name);
      });
    }

    function setBuild(level) {
      if (!archScene) return;
      var lvl = parseInt(level, 10) || 0;
      for (var i = 1; i <= 4; i++) {
        archScene.classList.toggle('built-' + i, i <= lvl);
        archScene.classList.toggle('step-' + i, i === lvl);
      }
      archScene.setAttribute('data-build', String(lvl));
    }

    function activate(step, index) {
      steps.forEach(function (s) { s.classList.toggle('is-active', s === step); });
      var scene = step.getAttribute('data-scene') || 'hero';
      setScene(scene);
      if (scene === 'arch') {
        setBuild(step.getAttribute('data-build') || '1');
      }
      if (counter) {
        var n = index + 1;
        counter.textContent = (n < 10 ? '0' : '') + n;
      }
    }

    // Default fully-assembled state so the stage reads well before any
    // step has been observed and on browsers without IntersectionObserver.
    function showDefault() {
      activate(steps[0], 0);
    }

    if (!('IntersectionObserver' in window)) {
      // Static fallback: assemble the pipeline and show the architecture.
      setScene('arch'); setBuild(4);
      if (counter) counter.textContent = '01';
      return;
    }

    showDefault();

    var current = 0;
    var io = new IntersectionObserver(function (entries) {
      // pick the most centered intersecting step
      var best = null, bestRatio = 0;
      entries.forEach(function (e) {
        if (e.isIntersecting && e.intersectionRatio >= bestRatio) {
          best = e.target; bestRatio = e.intersectionRatio;
        }
      });
      if (!best) return;
      var idx = steps.indexOf(best);
      if (idx === current) return;
      current = idx;
      activate(best, idx);
    }, {
      // a step is "active" when it sits in the vertical middle band
      rootMargin: '-42% 0px -42% 0px',
      threshold: [0, 0.25, 0.5, 0.75, 1]
    });

    steps.forEach(function (s) { io.observe(s); });
  }

  ready(initScrolly);
})();
