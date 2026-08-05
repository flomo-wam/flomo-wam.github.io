(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var status = document.getElementById("copy-status");
  var resetTimers = new WeakMap();

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
    var message = result === "copied" ? "Copied" : "Ready to copy";

    button.dataset.originalLabel = original;
    button.textContent = message;
    status.textContent = result === "copied" ? "Copied to clipboard." : "Copy text shown in a dialog.";

    if (resetTimers.has(button)) {
      window.clearTimeout(resetTimers.get(button));
    }

    resetTimers.set(button, window.setTimeout(function () {
      button.textContent = original;
      resetTimers.delete(button);
    }, 1800));
  }

  function getThreadText() {
    return Array.from(document.querySelectorAll("[data-post-body]"))
      .map(function (post) {
        return post.textContent.trim();
      })
      .join("\n\n---\n\n");
  }

  document.addEventListener("click", async function (event) {
    var button = event.target.closest("[data-copy-post], [data-copy-thread]");

    if (!button) {
      return;
    }

    var text;
    if (button.hasAttribute("data-copy-thread")) {
      text = getThreadText();
    } else {
      text = button.closest(".thread-post").querySelector("[data-post-body]").textContent.trim();
    }

    button.disabled = true;
    try {
      showResult(button, await copyText(text));
    } finally {
      button.disabled = false;
    }
  });

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("video[autoplay]").forEach(function (video) {
      video.removeAttribute("autoplay");
      video.pause();
    });
  }
}());
