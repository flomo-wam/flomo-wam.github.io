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
    var dots = [].slice.call(document.querySelectorAll('#oodDots .ood-dot'));

    // The three OOD axes, in cycle order. cells = the table columns to highlight.
    var items = [
      { cells: [1, 2], group: 'cc', video: 'static/videos/door.mp4', poster: 'static/images/posters/door.jpg',
        badge: 'OOD &middot; unseen primitive', caption: 'Push the cabinet door shut.' },
      { cells: [3, 4], group: 'ps', video: 'static/videos/string.mp4', poster: 'static/images/posters/string.jpg',
        badge: 'OOD &middot; unseen task', caption: 'Pull the hanging string, a primitive seen only in human video.' },
      { cells: [5, 6], group: 'hl', video: 'static/videos/highlighter.mp4', poster: 'static/images/posters/highlighter.jpg',
        badge: 'OOD &middot; unseen object', caption: 'Place the unseen highlighter in the bowl.' }
    ];
    var idx = 0;
    slow(video); // 3x-real-time clips: play at half speed (listeners persist across src changes)

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
      dots.forEach(function (d, k) { d.classList.toggle('active', k === idx); });
      video.poster = it.poster;
      video.src = it.video;
      video.load();
      if (autoplay && !reduceMotion) { var p = video.play(); if (p && p.catch) p.catch(function () {}); }
    }
    function go(delta) { show(idx + delta, true); }

    if (prev) prev.addEventListener('click', function () { go(-1); });
    if (next) next.addEventListener('click', function () { go(1); });
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
  /* ---------- interactive scene-flow -> RGB colour on a live 3D cube ----------
     The motion vector is set by dragging its tip directly in the cube: a screen-plane
     drag moves the tip in the plane facing the camera, and orbiting the cube lets that
     drag reach any depth — so all of (dX, dY, dZ) are set in 3D, with no separate slider. */
  function initFlowCube() {
    var root = document.getElementById('flowCube');
    if (!root) return;
    var swatch = document.getElementById('fcSwatch');
    var rgbEl = document.getElementById('fcRgb');
    var vx = document.getElementById('fcVx');
    var vy = document.getElementById('fcVy');
    var vz = document.getElementById('fcVz');
    var cube = document.getElementById('fc3dCube');
    var scene = document.getElementById('fc3dScene');
    var point = document.getElementById('fc3dPoint');
    var vec = document.getElementById('fc3dVec');
    var dx = 0, dy = 0, dz = 0;
    var H = 100; // cube half-extent in px (matches CSS .fc3d-cube = 200x200)

    function clamp(v) { return Math.max(-1, Math.min(1, v)); }
    function chan(v) { return Math.round((v + 1) / 2 * 255); } // [-1,1] -> [0,255], 0 -> mid-grey
    function fmt(v) { return (v >= 0 ? '+' : '') + v.toFixed(2); }
    // cube-local CSS coords: +X right, +Y up (CSS y is down, so negate), +Z toward viewer
    function pos3d(x, y, z) { return 'translate3d(' + (x * H) + 'px,' + (-y * H) + 'px,' + (z * H) + 'px)'; }

    // ----- 3x3 rotation helpers (R = Rx(ax)·Ry(ay), CSS coords) -----
    function rad(d) { return d * Math.PI / 180; }
    function rotMat(ax, ay) {
      var cx = Math.cos(rad(ax)), sx = Math.sin(rad(ax));
      var cy = Math.cos(rad(ay)), sy = Math.sin(rad(ay));
      return [
        [cy,       0,   sy],
        [sx * sy,  cx, -sx * cy],
        [-cx * sy, sx,  cx * cy]
      ];
    }
    function mulVec(m, v) {
      return [m[0][0]*v[0] + m[0][1]*v[1] + m[0][2]*v[2],
              m[1][0]*v[0] + m[1][1]*v[1] + m[1][2]*v[2],
              m[2][0]*v[0] + m[2][1]*v[1] + m[2][2]*v[2]];
    }
    function mulVecT(m, v) { // m^T · v  (R is orthonormal, so this is R^-1·v)
      return [m[0][0]*v[0] + m[1][0]*v[1] + m[2][0]*v[2],
              m[0][1]*v[0] + m[1][1]*v[1] + m[2][1]*v[2],
              m[0][2]*v[0] + m[1][2]*v[1] + m[2][2]*v[2]];
    }

    var rotX = -22, rotY = 32; // current cube orientation (read by the tip-drag math)

    // build the 8 colour-coded corners of the RGB cube once
    if (cube && !cube.dataset.built) {
      cube.dataset.built = '1';
      [-1, 1].forEach(function (sx) {
        [-1, 1].forEach(function (sy) {
          [-1, 1].forEach(function (sz) {
            var c = document.createElement('span');
            c.className = 'fc3d-corner';
            c.style.background = 'rgb(' + chan(sx) + ',' + chan(sy) + ',' + chan(sz) + ')';
            c.style.transform = pos3d(sx, sy, sz);
            cube.insertBefore(c, vec); // corners behind the vector + tip
          });
        });
      });
    }

    function render() {
      var css = 'rgb(' + chan(dx) + ', ' + chan(dy) + ', ' + chan(dz) + ')';
      if (swatch) swatch.style.background = css;
      if (rgbEl) rgbEl.textContent = css;
      if (vx) vx.textContent = fmt(dx);
      if (vy) vy.textContent = fmt(dy);
      if (vz) vz.textContent = fmt(dz);
      if (point) { point.style.background = css; point.style.transform = pos3d(dx, dy, dz); }
      if (vec) {
        // arrow from origin to the tip: orient a unit-length bar along the tip direction
        var ex = dx * H, ey = -dy * H, ez = dz * H, L = Math.sqrt(ex*ex + ey*ey + ez*ez);
        if (L < 1) { vec.style.opacity = '0'; }
        else {
          var ux = ex/L, uy = ey/L, uz = ez/L;            // x-axis = tip direction
          var ref = Math.abs(uy) > 0.92 ? [0,0,1] : [0,1,0];
          var d = ref[0]*ux + ref[1]*uy + ref[2]*uz;
          var yx = ref[0]-d*ux, yy = ref[1]-d*uy, yz = ref[2]-d*uz;
          var yl = Math.sqrt(yx*yx + yy*yy + yz*yz) || 1; yx/=yl; yy/=yl; yz/=yl;
          var zx = uy*yz-uz*yy, zy = uz*yx-ux*yz, zz = ux*yy-uy*yx; // z = x × y
          vec.style.opacity = '1';
          vec.style.width = L + 'px';
          vec.style.background = css;
          vec.style.transform = 'matrix3d(' + ux+','+uy+','+uz+',0,' +
            yx+','+yy+','+yz+',0,' + zx+','+zy+','+zz+',0, 0,0,0,1)';
        }
      }
    }

    // ----- drag the tip: screen-plane motion mapped back into cube-local axes -----
    var tipDrag = false, tLastX = 0, tLastY = 0;
    if (point) {
      point.addEventListener('pointerdown', function (e) {
        tipDrag = true; auto = false; tLastX = e.clientX; tLastY = e.clientY;
        if (point.setPointerCapture) { try { point.setPointerCapture(e.pointerId); } catch (err) {} }
        e.preventDefault(); e.stopPropagation();
      });
      point.addEventListener('pointermove', function (e) {
        if (!tipDrag) return;
        var sdx = (e.clientX - tLastX) / H, sdy = (e.clientY - tLastY) / H;
        tLastX = e.clientX; tLastY = e.clientY;
        var R = rotMat(rotX, rotY);
        var world = mulVec(R, [dx, -dy, dz]); // tip in screen space
        world[0] += sdx; world[1] += sdy;     // slide in the screen plane (keep depth)
        var loc = mulVecT(R, world);          // back to cube-local
        dx = clamp(loc[0]); dy = clamp(-loc[1]); dz = clamp(loc[2]);
        render(); e.preventDefault();
      });
      point.addEventListener('pointerup', function () { tipDrag = false; });
      point.addEventListener('lostpointercapture', function () { tipDrag = false; });
      point.addEventListener('keydown', function (e) {
        var s = 0.08;
        if (e.shiftKey && e.key === 'ArrowUp') dz = clamp(dz + s);
        else if (e.shiftKey && e.key === 'ArrowDown') dz = clamp(dz - s);
        else if (e.key === 'ArrowRight') dx = clamp(dx + s);
        else if (e.key === 'ArrowLeft') dx = clamp(dx - s);
        else if (e.key === 'ArrowUp') dy = clamp(dy + s);
        else if (e.key === 'ArrowDown') dy = clamp(dy - s);
        else return;
        e.preventDefault(); render();
      });
    }

    // ----- orbit the cube (drag the scene background); gentle auto-spin until touched -----
    var orbiting = false, lastX = 0, lastY = 0, auto = !reduceMotion;
    function applyOrbit() { if (cube) cube.style.transform = 'rotateX(' + rotX + 'deg) rotateY(' + rotY + 'deg)'; }
    if (scene) {
      scene.addEventListener('pointerdown', function (e) {
        if (e.target === point) return; // the tip handles its own drag
        orbiting = true; auto = false; lastX = e.clientX; lastY = e.clientY;
        if (scene.setPointerCapture) { try { scene.setPointerCapture(e.pointerId); } catch (err) {} }
        e.preventDefault();
      });
      scene.addEventListener('pointermove', function (e) {
        if (!orbiting) return;
        rotY += (e.clientX - lastX) * 0.4;
        rotX = Math.max(-85, Math.min(85, rotX - (e.clientY - lastY) * 0.4));
        lastX = e.clientX; lastY = e.clientY; applyOrbit();
      });
      window.addEventListener('pointerup', function () { orbiting = false; tipDrag = false; });
    }
    applyOrbit();
    if (auto && cube && window.requestAnimationFrame) {
      (function spin() {
        if (auto && !orbiting && !tipDrag) { rotY += 0.22; applyOrbit(); }
        requestAnimationFrame(spin);
      })();
    }

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