/* FloMo project page — interactive layer (vanilla JS, no deps) */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Rollout clips from the replacement bundle are already encoded at the
  // annotated 5x speed, so keep playback at the media's native rate.
  var SLOW_RATE = 1;
  var FLOW_RATE = 0.7;
  function slow(v) {
    if (!v) return;
    var rate = v.id === 'flowVideo' ? FLOW_RATE : SLOW_RATE;
    function apply() { try { v.playbackRate = rate; } catch (e) {} }
    apply();
    v.addEventListener('loadedmetadata', apply);
    v.addEventListener('play', apply);
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function updateVideoOverlay(root, meta) {
    if (!root || !meta) return;
    var model = root.querySelector('[data-overlay="model"]');
    var speed = root.querySelector('[data-overlay="speed"]');
    var distribution = root.querySelector('[data-overlay="distribution"]');
    var prompt = root.querySelector('[data-overlay="prompt"]');
    if (model && meta.model) model.innerHTML = meta.model;
    if (speed && meta.speed) speed.innerHTML = meta.speed;
    if (distribution && meta.badge) {
      distribution.className = 'ov-pill ' + (meta.badgeClass || '');
      distribution.innerHTML = meta.badge;
    }
    if (prompt && meta.prompt) prompt.textContent = meta.prompt;
  }

  /* ---------- shared: a poster -> click-to-play video stage ---------- */
  function setupStage(stage) {
    var video = null;
    var desiredMuted = true;
    var posterImg = stage.querySelector('.stage-poster');
    var playBtn = stage.querySelector('.stage-play');

    function ensureVideo() {
      if (!video) {
        video = document.createElement('video');
        video.className = 'stage-video';
        video.muted = desiredMuted;
        video.loop = true;
        video.playsInline = true;
        video.setAttribute('playsinline', '');
        video.preload = 'none';
        video.controls = true; // keyboard/AT users can pause, scrub, replay
        video.setAttribute('controls', '');
        video.setAttribute('aria-label', stage.getAttribute('data-label') || 'Rollout video');
        video.src = stage.dataset.video;
        stage.appendChild(video);
        slow(video);
        // keep the overlay state in sync when the native controls are used
        video.addEventListener('pause', function () { stage.classList.remove('is-playing'); });
        video.addEventListener('play', function () { stage.classList.add('is-playing'); });
      }
      return video;
    }
    function play() {
      ensureVideo();
      stage.classList.add('is-playing');
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    }
    function toggle() {
      if (video && !video.paused) {
        video.pause();
        stage.classList.remove('is-playing');
        return false;
      }
      play();
      return true;
    }
    function isPlaying() { return !!(video && !video.paused); }
    function reset(src, poster) {
      if (video) { video.pause(); video.remove(); video = null; }
      stage.classList.remove('is-playing');
      if (src) stage.dataset.video = src;
      if (poster && posterImg) posterImg.src = poster;
    }
    function setMuted(m) { desiredMuted = m; if (video) video.muted = m; }

    if (playBtn) playBtn.addEventListener('click', function (e) { e.stopPropagation(); play(); });
    if (posterImg) posterImg.addEventListener('click', function () {
      if (!stage.classList.contains('is-playing')) play(); else toggle();
    });

    return { play: play, toggle: toggle, reset: reset, setMuted: setMuted, isPlaying: isPlaying };
  }

  /* ---------- sticky nav: smooth scroll + active highlight ---------- */
  function initNav() {
    var links = [].slice.call(document.querySelectorAll('.nav-links a[href^="#"]'));
    if (!links.length) return;
    var map = {};
    var sections = [];
    links.forEach(function (a) {
      var id = a.getAttribute('href').slice(1);
      var sec = document.getElementById(id);
      if (sec) { map[id] = a; sections.push(sec); }
    });
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          links.forEach(function (l) { l.classList.remove('is-active'); });
          var a = map[e.target.id];
          if (a) a.classList.add('is-active');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
    sections.forEach(function (s) { io.observe(s); });
  }

  /* ---------- rollout explorer ---------- */
  function initExplorer() {
    var stage = document.getElementById('demoStage');
    if (!stage) return;
    var api = setupStage(stage);
    var status = document.getElementById('demoStatus');
    var caption = document.getElementById('demoCaption');
    var chips = [].slice.call(document.querySelectorAll('#taskChips .task-chip'));

    function select(chip) {
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      api.reset(chip.dataset.video, chip.dataset.poster);
      status.className = 'vbadge ' + chip.dataset.badge + ' demo-status';
      status.innerHTML = chip.dataset.badgeText;
      caption.textContent = chip.dataset.caption;
      updateVideoOverlay(stage, {
        model: chip.dataset.model,
        speed: chip.dataset.speed,
        badgeClass: chip.dataset.badge,
        badge: chip.dataset.badgeText,
        prompt: chip.dataset.caption
      });
    }

    chips.forEach(function (chip, i) {
      chip.addEventListener('click', function () { select(chip); });
      chip.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          var n = chips[(i + 1) % chips.length]; n.focus(); select(n);
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          var p = chips[(i - 1 + chips.length) % chips.length]; p.focus(); select(p);
        }
      });
    });
  }

  /* ---------- scene-flow tokenization gallery ---------- */
  function initFlowGallery() {
    var video = document.getElementById('flowVideo');
    if (!video) return;
    var chips = [].slice.call(document.querySelectorAll('#flowChips .task-chip'));

    // Kick off playback explicitly: some browsers ignore the `autoplay`
    // attribute but allow a muted .play() call. Setting the muted *property*
    // (not just the attribute) is what unlocks muted autoplay reliably.
    if (reduceMotion) {
      video.removeAttribute('autoplay'); video.pause();
    } else {
      video.muted = true;
      var initPlay = video.play();
      if (initPlay && initPlay.catch) initPlay.catch(function () {});
    }

    function select(chip) {
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      if (video.getAttribute('src') !== chip.dataset.video) {
        video.setAttribute('src', chip.dataset.video);
        video.setAttribute('poster', chip.dataset.poster);
        video.load();
        if (!reduceMotion) { var p = video.play(); if (p && p.catch) p.catch(function () {}); }
      }
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
  }

  /* ---------- OOD rollout carousel (autoplay + autocycle) ---------- */
  function initOod() {
    var table = document.getElementById('oodTable');
    var video = document.getElementById('oodVideo');
    if (!table || !video) return;
    var status = document.getElementById('oodStatus');
    var caption = document.getElementById('oodCaption');
    var prev = document.getElementById('oodPrev');
    var next = document.getElementById('oodNext');
    var carousel = document.getElementById('oodCarousel');
    var tabs = [].slice.call(document.querySelectorAll('#oodTabs .task-chip'));

    // The three OOD axes, in cycle order. cells = the table columns to highlight.
    var items = [
      { cells: [1, 2], group: 'cc', video: 'static/videos/option-compare/door_landscape.mp4', poster: 'static/videos/option-compare/door_landscape.jpg',
        model: 'FloMo', speed: '5&times;', badgeClass: 'ood', badge: 'OOD &middot; unseen primitive',
        caption: 'Push the cabinet door shut.' },
      { cells: [3, 4], group: 'ps', video: 'static/videos/ma10h_yoyo_success.mp4', poster: 'static/images/posters/string.jpg',
        model: 'FloMo', speed: '5&times;', badgeClass: 'ood', badge: 'OOD &middot; unseen task',
        caption: 'Pull the string on the toy in the air.' },
      { cells: [5, 6], group: 'hl', video: 'static/videos/ma10h_highlighter_success2.mp4', poster: 'static/images/posters/highlighter.jpg',
        model: 'FloMo', speed: '5&times;', badgeClass: 'ood', badge: 'OOD &middot; unseen object',
        caption: 'Place the unseen highlighter in the bowl.' }
    ];
    var idx = 0;
    slow(video); // keep replacement clips at their annotated native speed

    function clearCols() {
      [].forEach.call(table.querySelectorAll('.col-active'), function (c) { c.classList.remove('col-active'); });
    }
    function highlight(item) {
      clearCols();
      [].forEach.call(table.tBodies[0].rows, function (r) {
        item.cells.forEach(function (i) { if (r.cells[i]) r.cells[i].classList.add('col-active'); });
      });
      var th = table.querySelector('thead th[data-group="' + item.group + '"]');
      if (th) th.classList.add('col-active');
    }
    function show(i, autoplay) {
      idx = (i % items.length + items.length) % items.length;
      var it = items[idx];
      highlight(it);
      if (status) status.innerHTML = it.badge;
      if (caption) caption.textContent = it.caption;
      updateVideoOverlay(carousel, {
        model: it.model,
        speed: it.speed,
        badgeClass: it.badgeClass,
        badge: it.badge,
        prompt: it.caption
      });
      tabs.forEach(function (tab, k) {
        var active = k === idx;
        tab.classList.toggle('active', active);
        tab.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      video.poster = it.poster;
      video.src = it.video;
      video.load();
      if (autoplay && !reduceMotion) { var p = video.play(); if (p && p.catch) p.catch(function () {}); }
    }
    function go(delta) { show(idx + delta, true); }

    if (prev) prev.addEventListener('click', function () { go(-1); });
    if (next) next.addEventListener('click', function () { go(1); });
    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { show(i, true); });
      tab.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault(); var n = tabs[(i + 1) % tabs.length]; n.focus(); show(i + 1, true);
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault(); var p = tabs[(i - 1 + tabs.length) % tabs.length]; p.focus(); show(i - 1, true);
        }
      });
    });
    // autocycle: advance to the next axis whenever a clip finishes
    video.addEventListener('ended', function () { go(1); });
    if (carousel) {
      carousel.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); }
      });
    }

    show(0, true); // start playing + cycling (no-op autoplay under reduced motion)
  }

  /* ---------- comparison grid (FloMo vs baselines, all autoplay together) ---------- */
  function initComparison() {
    var vids = [].slice.call(document.querySelectorAll('.cmp-video'));
    if (!vids.length) return;
    vids.forEach(function (v) {
      slow(v); // keep replacement clips at their annotated native speed
      if (reduceMotion) { v.removeAttribute('autoplay'); v.pause(); return; }
      v.muted = true; // setting the property (not just the attribute) unlocks muted autoplay
      var p = v.play();
      if (p && p.catch) p.catch(function () {});
    });
  }

  /* ---------- lightbox zoom ---------- */
  function initLightbox() {
    var modal = document.getElementById('lightbox');
    if (!modal) return;
    var img = modal.querySelector('.lightbox-img');
    var closeBtn = modal.querySelector('.lightbox-close');
    var lastFocus = null;
    function open(src, alt, trigger) {
      lastFocus = trigger || null;
      img.src = src; img.alt = alt || '';
      modal.classList.add('is-active');
      if (closeBtn) closeBtn.focus();
    }
    function close() {
      modal.classList.remove('is-active'); img.src = '';
      if (lastFocus && lastFocus.focus) lastFocus.focus();
      lastFocus = null;
    }
    [].forEach.call(document.querySelectorAll('img.lightboxable'), function (im) {
      // make the trigger keyboard-operable
      im.setAttribute('role', 'button');
      im.setAttribute('tabindex', '0');
      if (!im.getAttribute('aria-label')) {
        im.setAttribute('aria-label', 'Zoom figure: ' + (im.getAttribute('alt') || 'figure'));
      }
      im.addEventListener('click', function () { open(im.getAttribute('src'), im.getAttribute('alt'), im); });
      im.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
          e.preventDefault(); open(im.getAttribute('src'), im.getAttribute('alt'), im);
        }
      });
    });
    [].forEach.call(modal.querySelectorAll('.modal-background, .lightbox-close'), function (el) {
      el.addEventListener('click', close);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('is-active')) close();
    });
  }


  /* ---------- ID bar chart animation ---------- */

  function initBars() {
    var chart = document.getElementById('idBars');
    if (!chart) return;
    var bars = [].slice.call(chart.querySelectorAll('.vbar'));
    if (!bars.length) return;
    // Each bar grows to data-value% of its .vbar-plot height, minus the value
    // label that sits above it, so the bars fill the panel and never overflow.
    function fill() {
      bars.forEach(function (b) {
        var plot = b.parentNode;                       // .vbar-plot
        var val = plot.querySelector('.vbar-val');
        var avail = plot.clientHeight - (val ? val.offsetHeight : 0) - 6;
        if (avail <= 0) return;
        b.style.height = Math.round(b.dataset.value / 100 * avail) + 'px';
      });
    }
    function fillSoon() { requestAnimationFrame(fill); }
    // re-measure on resize so the pixel heights track the layout
    var rT;
    window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(fill, 150); });
    if (reduceMotion || !('IntersectionObserver' in window)) { fillSoon(); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { chart.classList.add('in-view'); fillSoon(); io.disconnect(); }
      });
    }, { threshold: 0.4 });
    io.observe(chart);
  }

  /* ---------- stat count-up ---------- */
  function initCountUp() {
    var els = [].slice.call(document.querySelectorAll('[data-target]'));
    if (!els.length) return;
    function run(el) {
      var target = parseFloat(el.dataset.target);
      var suffix = el.dataset.suffix || '';
      if (reduceMotion) { el.textContent = target + suffix; return; }
      var start = null, dur = 1100;
      function step(ts) {
        if (!start) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var val = Math.round(target * (1 - Math.pow(1 - p, 3)));
        el.textContent = val + suffix;
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }
    if (!('IntersectionObserver' in window)) { els.forEach(run); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { run(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    els.forEach(function (el) {
      el.textContent = '0' + (el.dataset.suffix || '');
      io.observe(el);
    });
  }

  ready(function () {
    initNav();
    initExplorer();
    initFlowGallery();
    initOod();
    initComparison();
    initLightbox();
    initBars();
    initCountUp();
    // slow every video already in the DOM (flow gallery, comparison grid,
    // no-JS fallbacks); dynamically created stage videos are handled inline.
    [].forEach.call(document.querySelectorAll('video'), slow);
  });
})();
