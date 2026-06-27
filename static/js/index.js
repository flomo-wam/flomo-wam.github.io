/* FloMo project page — interactive layer (vanilla JS, no deps) */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Rollout clips are rendered at ~3x real time; slow playback so the
  // motion is easy to read. playbackRate is reset by load()/src changes,
  // so re-apply it whenever the media (re)loads or starts playing.
  var SLOW_RATE = 0.5;
  function slow(v) {
    if (!v) return;
    function apply() { try { v.playbackRate = SLOW_RATE; } catch (e) {} }
    apply();
    v.addEventListener('loadedmetadata', apply);
    v.addEventListener('play', apply);
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
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
        video.addEventListener('click', toggle);
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
    var thumbs = [].slice.call(document.querySelectorAll('#taskThumbs .thumb'));

    function select(chip) {
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      thumbs.forEach(function (t) {
        t.classList.toggle('active', t.dataset.task === chip.dataset.task);
      });
      api.reset(chip.dataset.video, chip.dataset.poster);
      status.className = 'vbadge ' + chip.dataset.badge + ' demo-status';
      status.innerHTML = chip.dataset.badgeText;
      caption.textContent = chip.dataset.caption;
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
    thumbs.forEach(function (t) {
      t.addEventListener('click', function () {
        var chip = chips.filter(function (c) { return c.dataset.task === t.dataset.task; })[0];
        if (chip) select(chip);
      });
    });
  }

  /* ---------- scene-flow tokenization gallery ---------- */
  function initFlowGallery() {
    var video = document.getElementById('flowVideo');
    if (!video) return;
    var caption = document.getElementById('flowCaption');
    var chips = [].slice.call(document.querySelectorAll('#flowChips .task-chip'));
    var thumbs = [].slice.call(document.querySelectorAll('#flowThumbs .thumb'));

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
      thumbs.forEach(function (t) {
        t.classList.toggle('active', t.dataset.sample === chip.dataset.sample);
      });
      if (video.getAttribute('src') !== chip.dataset.video) {
        video.setAttribute('src', chip.dataset.video);
        video.setAttribute('poster', chip.dataset.poster);
        video.load();
        if (!reduceMotion) { var p = video.play(); if (p && p.catch) p.catch(function () {}); }
      }
      if (caption) caption.textContent = chip.dataset.caption;
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
    thumbs.forEach(function (t) {
      t.addEventListener('click', function () {
        var chip = chips.filter(function (c) { return c.dataset.sample === t.dataset.sample; })[0];
        if (chip) select(chip);
      });
    });
  }

  /* ---------- OOD axis explorer ---------- */
  function initOod() {
    var stage = document.getElementById('oodStage');
    var table = document.getElementById('oodTable');
    if (!stage || !table) return;
    var api = setupStage(stage);
    var status = document.getElementById('oodStatus');
    var caption = document.getElementById('oodCaption');
    var chips = [].slice.call(document.querySelectorAll('#oodTabs .task-chip'));

    function clearCols() {
      [].forEach.call(table.querySelectorAll('.col-active'), function (c) {
        c.classList.remove('col-active');
      });
    }
    function highlight(chip) {
      clearCols();
      var cells = chip.dataset.cells.split(',').map(Number);
      [].forEach.call(table.tBodies[0].rows, function (r) {
        cells.forEach(function (i) { if (r.cells[i]) r.cells[i].classList.add('col-active'); });
      });
      var th = table.querySelector('thead th[data-group="' + chip.dataset.group + '"]');
      if (th) th.classList.add('col-active');
    }
    function select(chip) {
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('active', on);
        c.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      highlight(chip);
      api.reset(chip.dataset.video, chip.dataset.poster);
      status.className = 'vbadge ' + chip.dataset.badge + ' demo-status';
      status.innerHTML = chip.dataset.badgeText;
      caption.textContent = chip.dataset.caption;
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
    // highlight default column without autoplaying
    if (chips[0]) highlight(chips[0]);
  }

  /* ---------- comparison switcher (FloMo vs baselines) ---------- */
  function initComparison() {
    var root = document.getElementById('cmpSwitcher');
    if (!root) return;
    var single = document.getElementById('cmpSingleWrap');
    var stage = document.getElementById('cmpStage');
    var api = setupStage(stage);
    var result = document.getElementById('cmpResult');
    var seg = [].slice.call(root.querySelectorAll('.cmp-seg button'));
    var syncWrap = document.getElementById('cmpSync');
    var syncToggle = document.getElementById('cmpSyncToggle');
    var masterPlay = document.getElementById('cmpPlay');
    var muteBtn = document.getElementById('cmpMute');
    var syncVideos = [].slice.call(syncWrap.querySelectorAll('video'));

    var muted = true, syncing = false, playing = false, rafId = null;

    function setResult(badge, text) {
      result.innerHTML = '<span class="vbadge ' + badge + '">' + text + '</span>';
    }
    function selectMethod(btn) {
      seg.forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      api.reset(btn.dataset.video, btn.dataset.poster);
      setResult(btn.dataset.badge, btn.dataset.badgeText);
      if (!syncing) masterPlay.textContent = 'Play';
    }
    seg.forEach(function (b) { b.addEventListener('click', function () { selectMethod(b); }); });

    function loadSyncSrc() {
      syncVideos.forEach(function (v) { if (!v.src) v.src = v.dataset.src; v.muted = muted; });
    }
    function syncLoop() {
      if (!syncing) return;
      var leader = syncVideos[0];
      for (var i = 1; i < syncVideos.length; i++) {
        if (Math.abs(syncVideos[i].currentTime - leader.currentTime) > 0.08) {
          syncVideos[i].currentTime = leader.currentTime;
        }
      }
      rafId = requestAnimationFrame(syncLoop);
    }
    syncToggle.addEventListener('click', function () {
      syncing = !syncing;
      syncToggle.classList.toggle('active', syncing);
      syncToggle.setAttribute('aria-pressed', syncing ? 'true' : 'false');
      single.hidden = syncing;
      syncWrap.hidden = !syncing;
      if (syncing) {
        loadSyncSrc();
        if (!reduceMotion) rafId = requestAnimationFrame(syncLoop);
        masterPlay.textContent = 'Play all';
      } else {
        if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
        syncVideos.forEach(function (v) { v.pause(); });
        playing = false;
        masterPlay.textContent = 'Play';
      }
    });
    masterPlay.addEventListener('click', function () {
      if (!syncing) {
        // single mode: master button toggles the selected clip and reflects state
        var nowPlaying = api.toggle();
        masterPlay.textContent = nowPlaying ? 'Pause' : 'Play';
        return;
      }
      playing = !playing;
      if (playing) {
        loadSyncSrc();
        syncVideos.forEach(function (v) { v.currentTime = 0; });
        syncVideos.forEach(function (v) { var p = v.play(); if (p && p.catch) p.catch(function () {}); });
        masterPlay.textContent = 'Pause';
        if (!reduceMotion && !rafId) rafId = requestAnimationFrame(syncLoop);
      } else {
        syncVideos.forEach(function (v) { v.pause(); });
        masterPlay.textContent = 'Play all';
      }
    });
    muteBtn.addEventListener('click', function () {
      muted = !muted;
      syncVideos.forEach(function (v) { v.muted = muted; });
      api.setMuted(muted);
      muteBtn.textContent = muted ? 'Unmute' : 'Mute';
      muteBtn.setAttribute('aria-pressed', muted ? 'false' : 'true');
    });

    // default selection
    if (seg[0]) selectMethod(seg[0]);
  }

  /* ---------- architecture hotspots (tap to toggle on touch) ---------- */
  function initHotspots() {
    var spots = [].slice.call(document.querySelectorAll('.hotspot'));
    if (!spots.length) return;
    spots.forEach(function (h) {
      h.addEventListener('click', function (e) {
        e.stopPropagation();
        spots.forEach(function (o) { if (o !== h) o.classList.remove('show'); });
        h.classList.toggle('show');
      });
    });
    document.addEventListener('click', function () {
      spots.forEach(function (o) { o.classList.remove('show'); });
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
  /* ---------- interactive scene-flow -> RGB color cube ---------- */
  function initFlowCube() {
    var root = document.getElementById('flowCube');
    if (!root) return;
    var pad = document.getElementById('fcPad');
    var knob = document.getElementById('fcKnob');
    var line = document.getElementById('fcArrowLine');
    var zEl = document.getElementById('fcZ');
    var swatch = document.getElementById('fcSwatch');
    var rgbEl = document.getElementById('fcRgb');
    var vx = document.getElementById('fcVx');
    var vy = document.getElementById('fcVy');
    var vz = document.getElementById('fcVz');
    var dx = 0, dy = 0, dz = 0;

    function clamp(v) { return Math.max(-1, Math.min(1, v)); }
    function chan(v) { return Math.round((v + 1) / 2 * 255); } // [-1,1] -> [0,255], 0 -> mid-grey
    function fmt(v) { return (v >= 0 ? '+' : '') + v.toFixed(2); }

    function render() {
      var css = 'rgb(' + chan(dx) + ', ' + chan(dy) + ', ' + chan(dz) + ')';
      swatch.style.background = css;
      rgbEl.textContent = css;
      vx.textContent = fmt(dx); vy.textContent = fmt(dy); vz.textContent = fmt(dz);
      // pad is 200x200, centre (100,100); +dx -> right, +dy -> up
      var cx = 100 + dx * 84, cy = 100 - dy * 84;
      knob.style.left = (cx / 2) + '%';
      knob.style.top = (cy / 2) + '%';
      line.setAttribute('x2', cx.toFixed(1));
      line.setAttribute('y2', cy.toFixed(1));
    }
    function setFromPoint(clientX, clientY) {
      var rect = pad.getBoundingClientRect();
      dx = clamp(((clientX - rect.left) / rect.width - 0.5) * 2);
      dy = clamp((0.5 - (clientY - rect.top) / rect.height) * 2); // invert: up is positive
      render();
    }

    var dragging = false;
    pad.addEventListener('pointerdown', function (e) {
      dragging = true;
      if (pad.setPointerCapture) { try { pad.setPointerCapture(e.pointerId); } catch (err) {} }
      setFromPoint(e.clientX, e.clientY);
      e.preventDefault();
    });
    pad.addEventListener('pointermove', function (e) {
      if (dragging) { setFromPoint(e.clientX, e.clientY); e.preventDefault(); }
    });
    window.addEventListener('pointerup', function () { dragging = false; });

    knob.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 0.2 : 0.05;
      if (e.key === 'ArrowRight') dx = clamp(dx + step);
      else if (e.key === 'ArrowLeft') dx = clamp(dx - step);
      else if (e.key === 'ArrowUp') dy = clamp(dy + step);
      else if (e.key === 'ArrowDown') dy = clamp(dy - step);
      else return;
      e.preventDefault(); render();
    });
    zEl.addEventListener('input', function () { dz = clamp(parseFloat(zEl.value) || 0); render(); });

    render();
  }

  function initBars() {
    var chart = document.getElementById('idBars');
    if (!chart) return;
    var bars = [].slice.call(chart.querySelectorAll('.bar'));
    function fill() { bars.forEach(function (b) { b.style.width = b.dataset.value + '%'; }); }
    if (reduceMotion || !('IntersectionObserver' in window)) { fill(); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { chart.classList.add('in-view'); fill(); io.disconnect(); }
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
    initHotspots();
    initLightbox();
    initBars();
    initCountUp();
    initFlowCube();
    // slow every video already in the DOM (flow gallery, comparison grid,
    // no-JS fallbacks); dynamically created stage videos are handled inline.
    [].forEach.call(document.querySelectorAll('video'), slow);
  });
})();