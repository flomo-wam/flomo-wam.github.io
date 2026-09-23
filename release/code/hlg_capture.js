// FloMo release v3: SDR intermediates for the HLG website clips, rendered by Chrome.
//
// The site plays ma10h_yoyo_success.mp4 / ma10h_highlighter_success2.mp4 (HLG, bt.2020)
// through the browser, so the browser's rendering is the reference look. ffmpeg's
// tone-map chains land far from it (measured: hable/npl=1000 table patch 115 vs 215).
// This module seeks every frame in a headless Chrome tab, screenshots the <video>
// at 1:1 and encodes the PNGs to bt.709 mp4 intermediates that footage_figs.py
// consumes like any SDR source.
//
// Runs inside the omp JS eval kernel (needs its `browser` global):
//   const m = await import("<repo>/video/release/v3/hlg_capture.js");
//   await m.main(browser);           // ~10 min for 710 frames, login node
// Outputs: MEDIA/src/{yoyo,highlighter}_sdr.mp4 + MEDIA/src/manifest.json
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "fs";
import { spawnSync } from "child_process";

const SITE = `${import.meta.dir}/../../static/videos`;
const MEDIA = `${import.meta.dir}/../media`;
const FFMPEG = "/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/lib/python3.10/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2";
const TMP = "/tmp/hlg_cap";
const FPS = 30;
export const SOURCES = {
  yoyo: `${SITE}/ma10h_yoyo_success.mp4`,
  highlighter: `${SITE}/ma10h_highlighter_success2.mp4`,
};

function run(args) {
  const p = spawnSync(FFMPEG, args, { stdio: ["ignore", "inherit", "inherit"] });
  if (p.status !== 0) throw new Error(`ffmpeg failed (${p.status}): ${args.join(" ")}`);
}

// All-intra copy so per-frame seeks are cheap (0.5 s/frame instead of 2 s). CRF 4: visually lossless.
export function intra(name, src) {
  mkdirSync(`${TMP}/src`, { recursive: true });
  const dst = `${TMP}/src/${name}.mp4`;
  run(["-v", "error", "-y", "-i", src, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "4", "-g", "1",
    "-pix_fmt", "yuv420p", "-colorspace", "bt2020nc", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67",
    "-movflags", "+faststart", dst]);
  return dst;
}

// Seek frame k to (k + 0.5) / FPS, wait for `seeked`, screenshot the element 1:1. (No rAF wait: a
// backgrounded tab never fires it, and captureScreenshot composites the decoded frame itself.)
export async function capture(browser, name, src) {
  const dir = `${TMP}/${name}`;
  mkdirSync(dir, { recursive: true });
  // persist: the harness freezes non-persistent idle tabs when the calling turn settles, stalling a background capture
  const tab = await browser.open({ name: `hlg_${name}`, url: "about:blank", viewport: { width: 1920, height: 1080 }, persist: true });
  try {
    return await tab.run(async ({ page }, [src, dir, fps]) => {
      const fs = require("fs");
      await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
      // a file:// document: an about:blank page (setContent) may not load file:// media (MEDIA_ERR_SRC_NOT_SUPPORTED)
      fs.writeFileSync(`${dir}.html`, `<!doctype html><body style="margin:0;background:#000"><video id="v" src="file://${src}" muted playsinline preload="auto" style="display:block;width:1920px;height:1080px"></video></body>`);
      await page.goto(`file://${dir}.html`, { waitUntil: "load" });
      const st = await page.evaluate(() => new Promise((r) => {
        const v = document.getElementById("v");
        const done = (tag) => () => r({ tag, code: v.error && v.error.code });
        if (v.readyState >= 2) return done("ready")();
        v.addEventListener("loadeddata", done("ready"), { once: true });
        v.addEventListener("error", done("error"), { once: true });
      }));
      if (st.tag !== "ready") throw new Error(`video failed to load: MediaError ${st.code}`);
      const dur = await page.evaluate(() => document.getElementById("v").duration);
      const n = Math.round(dur * fps);
      const times = [];
      for (let k = 0; k < n; k++) {
        const ct = await page.evaluate(async (t) => {
          const v = document.getElementById("v");
          v.currentTime = t;
          await new Promise((r) => v.addEventListener("seeked", r, { once: true }));
          return v.currentTime;
        }, (k + 0.5) / fps);
        const buf = await page.screenshot({ type: "png", optimizeForSpeed: true, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
        fs.writeFileSync(`${dir}/${String(k).padStart(5, "0")}.png`, buf);
        times.push(ct);
      }
      const distinct = new Set(times.map((t) => t.toFixed(4))).size;
      if (distinct !== n) throw new Error(`${n} seeks landed on ${distinct} distinct frames`);
      return { dur, n, chrome: await page.browser().version() };
    }, { args: [[src, dir, FPS]], timeout: 1800000 });
  } finally {
    await tab.close();
  }
}

// PNG sequence -> bt.709 SDR mp4, CRF 6 (visually lossless), same frame count as the source.
export function encode(name, n) {
  mkdirSync(`${MEDIA}/src`, { recursive: true });
  const pngs = readdirSync(`${TMP}/${name}`).filter((f) => f.endsWith(".png")).length;
  if (pngs !== n) throw new Error(`${name}: ${pngs} PNGs, expected ${n}`);
  const dst = `${MEDIA}/src/${name}_sdr.mp4`;
  run(["-v", "error", "-y", "-framerate", String(FPS), "-i", `${TMP}/${name}/%05d.png`, "-frames:v", String(n),
    "-c:v", "libx264", "-preset", "medium", "-crf", "6", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", dst]);
  return dst;
}

export async function main(browser) {
  const manifest = { provenance: "Chrome rendering of the website HLG mp4, one screenshot per frame at 1:1, encoded bt.709 CRF 6", fps: FPS, clips: {} };
  for (const [name, src] of Object.entries(SOURCES)) {
    const fast = existsSync(`${TMP}/src/${name}.mp4`) ? `${TMP}/src/${name}.mp4` : intra(name, src);
    const cap = await capture(browser, name, fast);
    const dst = encode(name, cap.n);
    manifest.clips[name] = { source: src, frames: cap.n, duration_s: cap.dur, chrome: cap.chrome, output: dst };
    console.log(`[hlg] ${name}: ${cap.n} frames -> ${dst}`);
  }
  writeFileSync(`${MEDIA}/src/manifest.json`, JSON.stringify(manifest, null, 2));
  return manifest;
}
