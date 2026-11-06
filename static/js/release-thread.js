(function () {
  "use strict";

  var LIMIT = 280;
  var status = document.getElementById("copy-status");
  var resetTimers = new WeakMap();

  // ---------- X weighted length: links count 23, CJK and emoji count 2 ----------
  var URL_RE = /(https?:\/\/\S+|\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|io|org|ai|net|edu|dev)\b(\/\S*)?)/gi;
  var EMOJI_RE = /[\u{1F000}-\u{1FAFF}☀-➿][️‍\u{1F3FB}-\u{1F3FF}]*/gu;

  function xlen(s) {
    var n = 0;
    s = s.normalize("NFC");
    s = s.replace(URL_RE, function () { n += 23; return ""; });
    s = s.replace(EMOJI_RE, function () { n += 2; return ""; });
    for (var c of s) {
      var o = c.codePointAt(0);
      n += (o <= 0x10FF || (o >= 0x2000 && o <= 0x200D) || (o >= 0x2010 && o <= 0x201F) || (o >= 0x2032 && o <= 0x2037)) ? 1 : 2;
    }
    return n;
  }

  // ---------- post text as X shows it: placeholders, links without the scheme, "Show more" past 280 ----------
  var TOK = /(\[(?!\d+\/\d+\])[^\]]+\])|(@\w+)|((?:https?:\/\/)?\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|io|org|ai|net|edu|dev)\b(?:\/\S*)?)/gi;

  function rich(el, s) {
    var i = 0;
    for (var m of s.matchAll(TOK)) {
      el.append(s.slice(i, m.index));
      var sp = document.createElement("span");
      sp.className = m[1] ? "ph" : "lk";
      sp.textContent = m[3] ? m[3].replace(/^https?:\/\//, "").replace(/\/$/, "") : m[0];
      el.append(sp);
      i = m.index + m[0].length;
    }
    el.append(s.slice(i));
  }

  function cut(s) { // longest prefix ending at whitespace that fits with the ellipsis
    var best = 0;
    for (var m of s.matchAll(/\s+/g)) {
      if (xlen(s.slice(0, m.index)) <= LIMIT - 1) best = m.index;
    }
    return s.slice(0, best);
  }

  function count(s) {
    var c = xlen(s);
    return '<span class="' + (c > LIMIT ? "over" : "") + '">' + c + "/" + LIMIT + "</span>";
  }

  // ---------- browser storage: per-viewer only; the page works when it is blocked ----------
  function load(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null; // blocked storage holds nothing for this viewer
    }
  }

  function store(key, val) {
    try {
      if (val === null) localStorage.removeItem(key);
      else localStorage.setItem(key, val);
      return true;
    } catch (error) {
      return false;
    }
  }

  // ---------- posts: published text lives in [data-post-body]; a local edit is {base, text} ----------
  var posts = Array.from(document.querySelectorAll(".post")).map(function (art, k) {
    var txt = art.querySelector("[data-post-body]");
    var pub = txt.textContent.trim();
    var key = "flomo-thread:post-" + (k + 1);
    var raw = load(key);
    var edit = raw === null ? null : JSON.parse(raw);
    return {
      art: art, txt: txt, key: key, pub: pub,
      cur: edit === null ? pub : edit.text,
      base: edit === null ? null : edit.base,
      saved: true,
      cnt: art.querySelector(".note .cnt"),
    };
  });

  function noteState(p, s) {
    var h = " · " + count(s);
    if (p.base !== null) {
      h += ' · edited · <button type="button" data-reset>Reset</button>';
      if (p.base !== p.pub) h += ' · <span class="warn">published text changed since your edit</span>';
    }
    if (!p.saved) h += ' · <span class="over">not saved: browser storage is blocked</span>';
    p.cnt.innerHTML = h;
  }

  function paint(p, open) {
    p.txt.replaceChildren();
    if (xlen(p.cur) <= LIMIT || open) {
      rich(p.txt, p.cur);
    } else {
      rich(p.txt, cut(p.cur) + "…");
      var more = document.createElement("span");
      more.className = "more";
      more.textContent = "\nShow more";
      more.onclick = function (event) {
        event.stopPropagation();
        paint(p, true);
      };
      p.txt.append(more);
    }
    noteState(p, p.cur);
  }

  function commit(p, text) {
    p.cur = text;
    if (text === p.pub) {
      p.base = null;
      p.saved = store(p.key, null);
    } else {
      if (p.base === null) p.base = p.pub;
      p.saved = store(p.key, JSON.stringify({ base: p.base, text: text }));
    }
  }

  function setupEditor(p, k) {
    var ed = document.createElement("textarea");
    var bar = document.createElement("output");
    ed.className = "ed";
    bar.className = "edbar";
    ed.hidden = bar.hidden = true;
    ed.setAttribute("aria-label", "Edit post " + (k + 1) + " of " + posts.length);
    p.txt.after(ed, bar);
    p.txt.tabIndex = 0;
    p.txt.title = "Click to edit";

    var fit = function () {
      ed.style.height = "auto";
      ed.style.height = ed.scrollHeight + 2 + "px";
    };
    var bar_ = function () {
      var msg = !p.saved ? '<span class="over">NOT SAVED: browser storage is blocked</span>'
        : p.base === null ? "matches the published text" : "saved in this browser";
      bar.innerHTML = count(ed.value) + " · " + msg;
      noteState(p, ed.value);
    };
    var open = function () {
      ed.value = p.cur;
      p.txt.hidden = true;
      ed.hidden = bar.hidden = false;
      fit();
      bar_();
      ed.focus();
    };

    p.txt.addEventListener("click", open);
    p.txt.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        open();
      }
    });
    ed.addEventListener("input", function () {
      fit();
      commit(p, ed.value);
      bar_();
    });
    ed.addEventListener("keydown", function (event) {
      if (event.key === "Escape" || (event.key === "Enter" && (event.metaKey || event.ctrlKey))) ed.blur();
    });
    ed.addEventListener("blur", function () {
      ed.hidden = bar.hidden = true;
      p.txt.hidden = false;
      paint(p, false);
    });
  }

  // ---------- copying the current (edited) text ----------
  function legacyCopy(text) {
    var field = document.createElement("textarea");
    var copied = false;

    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.top = "0";
    field.style.left = "-9999px";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.focus();
    field.select();
    field.setSelectionRange(0, field.value.length);

    try {
      copied = document.execCommand("copy");
    } catch (error) {
      copied = false;
    }

    document.body.removeChild(field);
    return copied;
  }

  async function copyText(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        await navigator.clipboard.writeText(text);
        return "copied";
      } catch (error) {
        // file:// commonly denies the async API; continue to the local fallback.
      }
    }

    if (legacyCopy(text)) {
      return "copied";
    }

    window.prompt("Copy this text:", text);
    return "prompt";
  }

  function showResult(button, result) {
    var original = button.dataset.originalLabel || button.textContent;

    button.dataset.originalLabel = original;
    button.textContent = result === "copied" ? "Copied" : "Ready to copy";
    status.textContent = result === "copied" ? "Copied to clipboard." : "Copy text shown in a dialog.";

    if (resetTimers.has(button)) {
      window.clearTimeout(resetTimers.get(button));
    }

    resetTimers.set(button, window.setTimeout(function () {
      button.textContent = original;
      resetTimers.delete(button);
    }, 1800));
  }

  function postOf(el) {
    return posts.find(function (p) { return p.art.contains(el); });
  }

  document.addEventListener("click", async function (event) {
    var reset = event.target.closest("[data-reset]");
    if (reset) {
      var p = postOf(reset);
      commit(p, p.pub);
      paint(p, false);
      return;
    }

    var button = event.target.closest("[data-copy-post], [data-copy-thread]");
    if (!button) {
      return;
    }

    var text = button.hasAttribute("data-copy-thread")
      ? posts.map(function (q) { return q.cur; }).join("\n\n---\n\n")
      : postOf(button).cur;

    button.disabled = true;
    try {
      showResult(button, await copyText(text));
    } finally {
      button.disabled = false;
    }
  });

  // ---------- page chrome: decorative X icons, notes toggle, theme ----------
  var ICONS = '<div class="icons" aria-hidden="true">' + [
    "M4.5 11.5c0-3.9 3.2-7 7.2-7h.6c4 0 7.2 3.1 7.2 7s-3.2 7-7.2 7h-1.1l-4.7 3v-3.9a6.9 6.9 0 0 1-2-6.1z",
    "M4 8.5l3-3 3 3M7 5.8V15a3 3 0 0 0 3 3h4.5M20 15.5l-3 3-3-3M17 18.2V9a3 3 0 0 0-3-3H9.5",
    "M12 20s-7.5-4.5-7.5-10a4.2 4.2 0 0 1 7.5-2.6A4.2 4.2 0 0 1 19.5 10c0 5.5-7.5 10-7.5 10z",
    "M5 20v-6M10 20V5M15 20v-9M20 20V8",
    "M6.5 4.5h11v16l-5.5-4-5.5 4z",
    "M12 15V4.5M7.5 9L12 4.5 16.5 9M5 14v5.5h14V14",
  ].map(function (d) { return '<svg viewBox="0 0 24 24"><path d="' + d + '"/></svg>'; }).join("") + "</div>";

  posts.forEach(function (p, k) {
    p.art.querySelector(".note").insertAdjacentHTML("beforebegin", ICONS);
    setupEditor(p, k);
    paint(p, false);
  });

  var root = document.documentElement;
  var theme = load("flomo-thread:theme");
  if (theme !== null) root.dataset.theme = theme;
  document.getElementById("theme-btn").addEventListener("click", function () {
    var dark = root.dataset.theme ? root.dataset.theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    store("flomo-thread:theme", root.dataset.theme);
  });

  var notesBtn = document.getElementById("notes-btn");
  var setNotes = function (on) {
    document.body.classList.toggle("notes-off", !on);
    notesBtn.setAttribute("aria-pressed", String(on));
    notesBtn.textContent = on ? "Notes on" : "Notes off";
  };
  setNotes(load("flomo-thread:notes") !== "off");
  notesBtn.addEventListener("click", function () {
    var on = notesBtn.getAttribute("aria-pressed") !== "true";
    setNotes(on);
    store("flomo-thread:notes", on ? "on" : "off");
  });

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("video[autoplay]").forEach(function (video) {
      video.removeAttribute("autoplay");
      video.pause();
    });
  }
}());
