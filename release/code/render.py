"""v3 video renderer: story.BEATS -> per-beat PNG frames (Pool) -> per-beat mp4
-> concat master -> audit -> stills. Layout mirrors deck.py (same numbers) so
the deck and the video are one design. Reuses v2 theme + ClipReader.

  python render.py --smoke 3                # login: 3 frames per beat + sheet
  sbatch release_v3.sbatch                  # full master + X + ICRA encodes
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # story shadows v2/story
import theme  # noqa: E402  (v2 design system)
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("render_v2", HERE / "render_v2.py")
render_v2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_v2)
ClipReader, FFMPEG, frame_count, probe, run = (render_v2.ClipReader, render_v2.FFMPEG, render_v2.frame_count,
                                               render_v2.probe, render_v2.run)
from story import BEATS, MEDIA, X_CUT_DROP  # noqa: E402

WORK = HERE.parent / "work"
FRAMES, BEAT_DIR, LOGS = WORK / "frames", WORK / "beats", WORK / "work"
OUT = HERE.parent / "videos"
FPS = theme.FPS
W, H, M = theme.W, theme.H, theme.MARGIN
INK, MUTED, ORANGE, TEAL_D, LINE, PANEL = theme.INK, theme.MUTED, theme.ORANGE, theme.TEAL_DARK, theme.LINE, theme.PANEL
HL = 60  # headline px (html .hl)
CTX = None

os.environ.setdefault("OMP_NUM_THREADS", "1")


# ----------------------------------------------------------------- media ---
class Ctx:
    def __init__(self):
        self.clips = {}
        self.durs = {}

    def frame(self, key, t):
        """Looping frame of MEDIA/<key> at beat-local time t."""
        if key not in self.clips:
            self.clips[key] = ClipReader(MEDIA / key)
            self.durs[key] = frame_count(MEDIA / key) / FPS
        return self.clips[key].frame_at(t % (self.durs[key] - 1 / FPS))


def ctx():
    global CTX
    if CTX is None:
        CTX = Ctx()
    return CTX


@lru_cache(maxsize=16)
def image(key):
    return Image.open(MEDIA / key).convert("RGBA")


@lru_cache(maxsize=1)
def boxes():
    return json.loads((MEDIA / "figures/arch_boxes.json").read_text())


# ------------------------------------------------------------------ text ---
def wrap(text, weight, size, max_w, tracking=0.0):
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if cur and theme.text_len(cand, weight, size, tracking) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    lines.append(cur)
    return lines


def text_block(img, x, y, text, weight, size, color, max_w, t, t0, tracking=0.0, lh=1.3, align="left"):
    """Wrapped block with the design-system entrance; returns bottom y."""
    a, dy = theme.rise_in(t, t0)
    for ln in wrap(text, weight, size, max_w, tracking):
        if a > 0:
            xx = x if align == "left" else x - theme.text_len(ln, weight, size, tracking) / 2
            theme.draw_text(img, (xx, y + dy), ln, weight, size, color, tracking=tracking, alpha=a)
        y += round(size * lh)
    return y


def headline(img, b, t, center=False):
    x = W // 2 if center else M
    y = text_block(img, x, M, b["headline"], "semibold", HL, INK, 1560, t, 0.1, -0.02, 1.12,
                   "center" if center else "left")
    if "sub" in b:
        y = text_block(img, x, y + 18, b["sub"], "medium", 34, MUTED, 1500, t, 0.3, 0, 1.3,
                       "center" if center else "left")
    return y


def caption(img, b, t, t0=0.9, max_w=1728):
    if "caption" not in b:
        return
    a, dy = theme.rise_in(t, t0)
    if a <= 0:
        return
    lines = wrap(b["caption"], "medium", 27, max_w - 52)
    lh = round(27 * 1.35)
    h = len(lines) * lh + 40
    w = max(theme.text_len(s, "medium", 27) for s in lines) + 52
    y = H - 72 - h + dy
    theme.card(img, [M, y, M + round(w), y + h], alpha=1.0)
    for i, s in enumerate(lines):
        theme.draw_text(img, (M + 26, y + 20 + i * lh), s, "medium", 27, INK, alpha=a)


def label(img, cx, y, text, t, t0, size=24, color=MUTED):
    a, dy = theme.rise_in(t, t0)
    txt = text.upper()
    theme.draw_text(img, (cx - theme.text_len(txt, "semibold", size, 0.06) / 2, y + dy), txt, "semibold",
                    size, color, tracking=0.06, alpha=a)


def wordmark(img, alpha=1.0):
    wm = theme.wordmark(150)
    theme.paste_faded(img, wm, (W - M - 150, 56), alpha)


def vpane(img, box, key, t, t0=0.0):
    """Pane with a looping clip; 400 ms dissolve in from PANEL."""
    a = theme.ease_out((t - t0) / 0.4)
    if a <= 0:
        theme.pane(img, box)
        return
    fr = theme.cover(ctx().frame(key, max(t - t0, 0.0)), box)
    if a < 0.999:
        fr = Image.blend(Image.new("RGB", fr.size, theme.rgb(PANEL)[:3]), fr, a)
    theme.pane(img, box, fr)


def ipane(img, box, key, t, t0=0.0, fit=True):
    """Pane with a still image, contain-fit on white."""
    a = theme.ease_out((t - t0) / 0.4)
    theme.pane(img, box, None, fill=True)
    if a <= 0:
        return
    im = image(key)
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = min((bw - 24) / im.width, (bh - 24) / im.height) if fit else max(bw / im.width, bh / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    ImageDraw.Draw(img).rounded_rectangle(box, radius=12, fill=(255, 255, 255))
    theme.paste_faded(img, im, (box[0] + (bw - im.width) // 2, box[1] + (bh - im.height) // 2), a)
    ImageDraw.Draw(img).rounded_rectangle(box, radius=12, outline=theme.rgb(LINE), width=1)


def badge(img, box, kind, t, t0):
    a, _ = theme.rise_in(t, t0)
    if a <= 0:
        return
    col = "#2A8A4F" if kind == "success" else "#B23A48"
    txt = kind.upper()
    w = theme.text_len(txt, "semibold", 22, 0.04) + 28
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([box[0] + 16, box[1] + 16, box[0] + 16 + w, box[1] + 16 + 40], radius=8, fill=theme.rgb(col, a))
    theme.draw_text(img, (box[0] + 30, box[1] + 22), txt, "semibold", 22, "#FFFFFF", tracking=0.04, alpha=a)


# ----------------------------------------------------------- vertical rule ---
def header_bottom(b):
    y = M + len(wrap(b["headline"], "semibold", HL, 1560, -0.02)) * round(HL * 1.12)
    if "sub" in b:
        y += 18 + len(wrap(b["sub"], "medium", 34, 1500)) * round(34 * 1.3)
    return y


def cap_top(b, max_w=1728):
    if "caption" not in b:
        return H - 72
    return H - 72 - (len(wrap(b["caption"], "medium", 27, max_w - 52)) * round(27 * 1.35) + 40)


def content_y(b, h, max_w=1728):
    """Top of a content block of height h, centred between header (+44) and caption (-18) = deck .body."""
    top, bot = header_bottom(b) + 44, cap_top(b, max_w) - 18
    return top + max(0, bot - top - h) // 2


LAB = 44  # label block under a pane: 14 px gap + 24 px uppercase label (deck .lab)


# ----------------------------------------------------------------- kinds ---
def k_title(img, b, t):
    """Title card = deck .title: wordmark / title / accent bar / credits, one group centred vertically."""
    wm = theme.wordmark(760)
    hl = len(wrap(b["headline"], "semibold", 60, 1400, -0.02)) * round(60 * 1.12)
    total = wm.height + 44 + hl + 40 + 4 + ((40 + 34) if b["credits"] else 0)
    y = (H - total) // 2
    a, dy = theme.rise_in(t, 0.0)
    theme.paste_faded(img, wm, ((W - 760) // 2, y + dy), a)
    y = text_block(img, W // 2, y + wm.height + 44, b["headline"], "semibold", 60, INK, 1400, t, 0.3, -0.02, 1.12, "center")
    a, _ = theme.rise_in(t, 0.7)
    half = round(60 * theme.ease_out((t - 0.7) / 0.5))  # bar grows out of its centre
    if half > 0:
        ImageDraw.Draw(img, "RGBA").rounded_rectangle([W // 2 - half, y + 40, W // 2 + half, y + 44], radius=2,
                                                      fill=theme.rgb(ORANGE, a))
    if b["credits"]:
        text_block(img, W // 2, y + 44 + 40, b["credits"], "medium", 26, MUTED, 1400, t, 1.0, 0, 1.3, "center")


def k_figure(img, b, t):
    headline(img, b, t)
    wordmark(img)
    ipane(img, [M, header_bottom(b) + 44, W - M, cap_top(b) - 18], b["media"]["figure"], t, 0.5)
    caption(img, b, t)


def k_pair(img, b, t):
    headline(img, b, t)
    wordmark(img)
    m = b["media"]
    keys = [m["left"], m["right"]]
    w, h = (852, 479) if keys[0].startswith("footage/") else (660, 495)
    y = content_y(b, h + LAB)
    for i, (k, lab) in enumerate(zip(keys, b["labels"])):
        x = (W - 2 * w - 24) // 2 + i * (w + 24)
        box = [x, y, x + w, y + h]
        vpane(img, box, k, t, 0.5 + 0.15 * i)
        if "badges" in b:
            badge(img, box, b["badges"][i], t, 1.0 + 0.15 * i)
        label(img, x + w // 2, y + h + 14, lab, t, 0.7 + 0.15 * i)
    caption(img, b, t)


def k_triptych(img, b, t):
    headline(img, b, t)
    wordmark(img)
    y = content_y(b, 420 + LAB)
    for i, (k, lab) in enumerate(zip(b["media"]["panes"], b["labels"])):
        x = M + i * (560 + 24)  # 3 x 560 + 2 x 24 = 1728 = centred row
        vpane(img, [x, y, x + 560, y + 420], k, t, 0.5 + 0.2 * i)
        label(img, x + 280, y + 420 + 14, lab, t, 0.7 + 0.2 * i)
    caption(img, b, t)


SPOT_PAD = 20  # = deck.SPOT_PAD


def spot_geom(crop):
    """= deck.spot_geom: crop at <= native scale inside a SPOT_PAD margin, left-aligned; step list fills the rest."""
    bw, bh = crop[2] - crop[0], crop[3] - crop[1]
    s = min(1000 / bw, 720 / bh, 1.0)
    pw, ph = round(bw * s) + 2 * SPOT_PAD, round(bh * s) + 2 * SPOT_PAD
    ox = SPOT_PAD - crop[0] * s
    oy = SPOT_PAD - crop[1] * s
    lx = M + pw + 40
    return s, pw, ph, ox, oy, lx, W - M - lx


def k_spotlight(img, b, t):
    headline(img, b, t)
    wordmark(img)
    bx = boxes()
    crop = bx[b["crop"]]
    s, pw, ph, ox, oy, lx, lw = spot_geom(crop)
    x0, y0 = M, 260
    fig = image(b["media"]["figure"])
    if s != 1.0:
        fig = fig.resize((round(fig.width * s), round(fig.height * s)), Image.LANCZOS)
    part = fig.crop(tuple(round(c * s) for c in crop))  # only the crop shows; the SPOT_PAD margin stays white (deck .fig)
    plate = Image.new("RGB", (pw, ph), (255, 255, 255))
    plate.paste(part, (SPOT_PAD, SPOT_PAD), part)
    steps = b["steps"]
    n = len(steps) + 1  # + final full-figure state
    per = (b["dur"] - 1.0) / n
    si = min(n - 1, int(max(t - 1.0, 0) / per))
    if si < len(steps):
        holes = [nm for _, reveal, _ in steps[:si + 1] for nm in reveal]  # dim holes = reveal boxes so far
        ov = Image.new("RGBA", (pw, ph), (255, 255, 255, int(255 * 0.82)))
        od = ImageDraw.Draw(ov)
        for nm in holes:
            bb = bx[nm]
            od.rounded_rectangle([ox + bb[0] * s - 6, oy + bb[1] * s - 6, ox + bb[2] * s + 6, oy + bb[3] * s + 6],
                                 radius=10, fill=(0, 0, 0, 0))
        plate = Image.alpha_composite(plate.convert("RGBA"), ov).convert("RGB")
        pd = ImageDraw.Draw(plate)
        for nm in steps[si][0]:  # rings = the current step's components
            bb = bx[nm]
            pd.rounded_rectangle([ox + bb[0] * s - 10, oy + bb[1] * s - 10, ox + bb[2] * s + 10, oy + bb[3] * s + 10],
                                 radius=14, outline=theme.rgb(ORANGE), width=4)
    theme.pane(img, [x0, y0, x0 + pw, y0 + ph], plate)
    # step list: revealed items accumulate; current = orange chip + ink text; earlier = muted (deck .si)
    items = [(str(i + 1), txt) for i, (_, _, txt) in enumerate(steps)]
    d = ImageDraw.Draw(img, "RGBA")
    yy = y0
    for k, (chip_txt, txt) in enumerate(items[:si + 1]):
        a, dy = theme.rise_in(t, 1.0 + k * per)
        cur = k == si
        cwid = max(40, theme.text_len(chip_txt, "semibold", 22) + 24)
        d.rounded_rectangle([lx, yy + dy, lx + cwid, yy + 40 + dy], radius=10,
                            fill=theme.rgb(theme.SOFT_ORANGE if cur else "#FFFFFF", a),
                            outline=theme.rgb("#F4C98A" if cur else LINE, a))
        theme.draw_text(img, (lx + (cwid - theme.text_len(chip_txt, "semibold", 22)) / 2, yy + 7 + dy), chip_txt,
                        "semibold", 22, theme.ORANGE_DARK if cur else MUTED, alpha=a)
        lines = wrap(txt, "medium", 26, lw - cwid - 16)
        ty = yy + 5
        for ln in lines:
            theme.draw_text(img, (lx + cwid + 16, ty + dy), ln, "medium", 26, INK if cur else MUTED, alpha=a)
            ty += 34
        yy += max(40, 5 + len(lines) * 34) + 18


def k_pair_cards(img, b, t):
    headline(img, b, t)
    wordmark(img)
    m = b["media"]
    y = content_y(b, 465 + LAB)
    for i, (k, lab) in enumerate(zip([m["left"], m["right"]], b["labels"])):
        x = M + i * (620 + 28)
        vpane(img, [x, y, x + 620, y + 465], k, t, 0.5 + 0.15 * i)
        label(img, x + 310, y + 465 + 14, lab, t, 0.7 + 0.15 * i, size=21)
    x = M + 2 * 648
    for i, ((v, l), col) in enumerate(zip(b["cards"], [TEAL_D, ORANGE])):
        a, dy = theme.rise_in(t, 1.0 + 0.2 * i)
        cy = y + i * (220 + 24) + dy
        d = ImageDraw.Draw(img, "RGBA")
        d.rounded_rectangle([x, cy, x + 420, cy + 220], radius=12, fill=theme.rgb(PANEL, a), outline=theme.rgb(LINE, a))
        theme.draw_text(img, (x + 30, cy + 22), v, "bold", 64, col, tracking=-0.02, alpha=a)
        yy = cy + 104
        for ln in wrap(l, "medium", 25, 360):
            theme.draw_text(img, (x + 30, yy), ln, "medium", 25, MUTED, alpha=a)
            yy += 33
    caption(img, b, t, t0=1.5)


def k_tasks(img, b, t):
    headline(img, b, t)
    wordmark(img)
    descs = [wrap(desc, "medium", 25, 560) for _, desc in b["tasks"]]
    h = 44 + 20 + 400 + 18 + 38 + 6 + max(len(d) for d in descs) * 34  # chip, gap, pane, name, desc (deck .task)
    y = content_y(b, h)
    a, dy = theme.rise_in(t, 0.4)
    ct = b["chip"].upper()
    d = ImageDraw.Draw(img, "RGBA")
    cw = theme.text_len(ct, "semibold", 22, 0.06) + 28
    d.rounded_rectangle([M, y + dy, M + cw, y + 44 + dy], radius=10, fill=theme.rgb(theme.SOFT_ORANGE, a),
                        outline=theme.rgb("#F4C98A", a))
    theme.draw_text(img, (M + 14, y + 9 + dy), ct, "semibold", 22, theme.ORANGE_DARK, tracking=0.06, alpha=a)
    py = y + 44 + 20
    for i, (k, (name, _)) in enumerate(zip(b["media"]["clips"], b["tasks"])):
        x = M + i * (560 + 24)
        vpane(img, [x, py, x + 560, py + 400], k, t, 0.6 + 0.2 * i)
        a, dy = theme.rise_in(t, 0.8 + 0.2 * i)
        theme.draw_text(img, (x, py + 400 + 18 + dy), name, "semibold", 32, INK, alpha=a)
        yy = py + 400 + 18 + 38 + 6
        for ln in descs[i]:
            theme.draw_text(img, (x, yy + dy), ln, "medium", 25, MUTED, alpha=a)
            yy += 34
    caption(img, b, t, t0=1.6)


def fig_pane(key):
    """Figure pane size: 520 tall for landscape figures, 680 for portrait; width follows the aspect (= deck.fig_pane)."""
    fw, fh = image(key).size
    h = 680 if fh > fw else 520
    return min(1000, round(h * fw / fh)), h


def k_chart_fig(img, b, t):
    headline(img, b, t)
    wordmark(img)
    pw, ph = fig_pane(b["media"]["figure"])
    y = content_y(b, ph)
    x0 = (W - pw - 40 - 640) // 2
    ipane(img, [x0, y, x0 + pw, y + ph], b["media"]["figure"], t, 0.5)
    x = x0 + pw + 40
    a, dy = theme.rise_in(t, 0.8)
    n = len(b["stats"])
    yy = y + (ph - (40 + n * 100)) // 2  # stats column vertically centred on the pane
    theme.draw_text(img, (x, yy + dy), b["stat_label"].upper(), "semibold", 22, MUTED, tracking=0.06, alpha=a)
    yy += 50
    for i, (v, l, hexcol) in enumerate(b["stats"]):
        a, dy = theme.rise_in(t, 1.0 + 0.15 * i)
        p = theme.ease_out((t - (1.0 + 0.15 * i)) / 0.6)
        shown = f"{float(v) * p:.1f}" if "." in v else str(round(int(v) * p))
        vw = theme.text_len(shown, "bold", 72, -0.02)
        theme.draw_text(img, (x + 200 - vw, yy + dy), shown, "bold", 72, hexcol, tracking=-0.02, alpha=a)
        theme.draw_text(img, (x + 218, yy + 34 + dy), l, "medium", 28, INK if i == 0 else MUTED, alpha=a)
        yy += 100
    caption(img, b, t, t0=1.6)


def k_table(img, b, t):
    headline(img, b, t)
    wordmark(img)
    cols = ["Method"] + b["columns"]
    widths = [430, 230, 230, 230, 200, 150, 150]
    rh = 79  # deck: 22 px padding x2 + 34 px line + 1 px rule
    x0 = M
    y = content_y(b, 59 + len(b["rows"]) * rh)
    d = ImageDraw.Draw(img, "RGBA")
    a, _ = theme.rise_in(t, 0.5)
    x = x0
    for c, w in zip(cols, widths):
        txt = c.upper()
        tx = x + 18 if c == "Method" else x + w / 2 - theme.text_len(txt, "semibold", 24, 0.05) / 2
        theme.draw_text(img, (tx, y + 14), txt, "semibold", 24, MUTED, tracking=0.05, alpha=a)
        x += w
    d.line([x0, y + 57, x0 + sum(widths), y + 57], fill=theme.rgb(LINE, a), width=2)
    y += 59
    for i, (name, per, agg, sr, tp) in enumerate(b["rows"]):
        a, dy = theme.rise_in(t, 0.8 + 0.18 * i)
        ours = name == "FloMo"
        dim = "no human" in name
        if ours:
            d.rounded_rectangle([x0, y + dy, x0 + sum(widths), y + rh + dy], radius=8, fill=theme.rgb(theme.SOFT_ORANGE, a))
        cells = [name] + per + [agg, str(sr), str(tp)]
        x = x0
        for j, (c, w) in enumerate(zip(cells, widths)):
            wt = "semibold" if (ours or j in (4, 5)) else "medium"
            col = theme.ORANGE_DARK if (ours and j == 0) else (MUTED if dim else INK)
            tx = x + 18 if j == 0 else x + w / 2 - theme.text_len(c, wt, 28) / 2
            theme.draw_text(img, (tx, y + 24 + dy), c, wt, 28, col, alpha=a)
            x += w
        d.line([x0, y + rh - 1, x0 + sum(widths), y + rh - 1], fill=theme.rgb(LINE, a), width=1)
        y += rh
    caption(img, b, t, t0=2.2)


def k_duel(img, b, t):
    headline(img, b, t)
    wordmark(img)
    y = 485  # label; 260 px cards at y+44 sit centred on the video stack (344-974, centre 659) = deck.k_duel
    a, dy = theme.rise_in(t, 0.5)
    theme.draw_text(img, (M, y + dy), b["duel_label"].upper(), "semibold", 22, MUTED, tracking=0.06, alpha=a)
    sw = 560
    d = ImageDraw.Draw(img, "RGBA")
    for i, (v, name) in enumerate(b["duel"]):
        a, dy = theme.rise_in(t, 0.7 + 0.2 * i)
        p = theme.ease_out((t - (0.7 + 0.2 * i)) / 0.8)
        x = M + i * (sw + 120)
        sy = y + 44 + dy
        d.rounded_rectangle([x, sy, x + sw, sy + 260], radius=12, fill=theme.rgb(PANEL, a), outline=theme.rgb(LINE, a))
        col = ORANGE if i == 0 else TEAL_D
        theme.draw_text(img, (x + 34, sy + 28), name, "semibold", 28, INK, alpha=a)
        val = int(v[:-1])
        theme.draw_text(img, (x + 34, sy + 66), f"{round(val * p)}%", "bold", 110, col, tracking=-0.03, alpha=a)
        d.rounded_rectangle([x + 34, sy + 215, x + sw - 34, sy + 233], radius=9, fill=theme.rgb("#E3E7EB", a))
        d.rounded_rectangle([x + 34, sy + 215, x + 34 + max(18, round((sw - 68) * val / 100 * p)), sy + 233], radius=9,
                            fill=theme.rgb(ORANGE if i == 0 else theme.TEAL, a))
    a, _ = theme.rise_in(t, 1.0)
    theme.draw_text(img, (M + sw + 40, sy + 115), "vs", "semibold", 30, MUTED, alpha=a)
    m = b["media"]
    px = M + 1240 + 40
    for i, (k, lab) in enumerate(zip([m["left"], m["right"]], b["labels"])):
        # two small panes stacked on the right (1240 + 40 + 380 = 1660 <= 1728); = deck.k_duel
        py = 344 + i * 345
        vpane(img, [px, py, px + 380, py + 285], k, t, 1.2 + 0.2 * i)
        label(img, px + 190, py + 285 + 14, lab, t, 1.4 + 0.2 * i, size=20)
    caption(img, b, t, t0=1.8, max_w=1240)


def k_insights(img, b, t):
    headline(img, b, t)
    wordmark(img)
    m = b["media"]
    y = content_y(b, 640)
    for i, (k, (big, txt)) in enumerate(zip([m["left"], m["right"]], b["insights"])):
        a, dy = theme.rise_in(t, 0.5 + 0.25 * i)
        x = M + i * (848 + 32)
        d = ImageDraw.Draw(img, "RGBA")
        d.rounded_rectangle([x, y + dy, x + 848, y + 640 + dy], radius=12, fill=theme.rgb(PANEL, a), outline=theme.rgb(LINE, a))
        theme.draw_text(img, (x + 32, y + 18 + dy), big, "bold", 84, ORANGE, tracking=-0.03, alpha=a)
        bw = theme.text_len(big, "bold", 84, -0.03)
        yy = y + 60
        for ln in wrap(txt, "medium", 28, 848 - 64 - bw - 16):
            theme.draw_text(img, (x + 32 + bw + 16, yy + dy), ln, "medium", 28, INK, alpha=a)
            yy += 35
        ipane(img, [x + 32, y + 140, x + 848 - 32, y + 612], k, t, 0.8 + 0.25 * i)  # fills the card (deck .fig flex:1)


KINDS = dict(title=k_title, figure=k_figure, pair=k_pair, triptych=k_triptych, spotlight=k_spotlight,
             pair_cards=k_pair_cards, tasks=k_tasks, chart_fig=k_chart_fig, table=k_table, duel=k_duel,
             insights=k_insights)


# -------------------------------------------------------------- pipeline ---
def compose(task):
    bi, f = task
    b = BEATS[bi]
    img = Image.new("RGB", (W, H), (255, 255, 255))
    t = f / FPS
    KINDS[b["kind"]](img, b, t)
    out_t = b["dur"] - t  # 400 ms white fade-out at the end of every beat (no cuts mid-motion)
    if out_t < 0.4:
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 1 - out_t / 0.4)
    if t < 0.3:
        img = Image.blend(Image.new("RGB", (W, H), (255, 255, 255)), img, theme.ease_out(t / 0.3))
    p = FRAMES / b["id"] / f"{f:05d}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p, compress_level=1)
    return bi


def n_frames(b):
    return round(b["dur"] * FPS)


def render_beat(pool, bi, smoke=0):
    b = BEATS[bi]
    total = n_frames(b)
    frames = list(np.linspace(0, total - 1, smoke).astype(int)) if smoke else list(range(total))
    done = 0
    for _ in pool.imap_unordered(compose, [(bi, int(f)) for f in frames], chunksize=8):
        done += 1
    assert done == len(frames)
    return [int(f) for f in frames]


def encode_beat(bi, frames, tag=""):
    b = BEATS[bi]
    out = BEAT_DIR / f"{b['id']}{tag}.mp4"
    fdir = FRAMES / b["id"]
    if tag:  # smoke: sparse frame numbers -> renumber via a list file
        lst = LOGS / f"{b['id']}_frames.txt"
        lst.write_text("".join(f"file '{fdir / f'{f:05d}.png'}'\nduration {1 / FPS:.6f}\n" for f in frames))
        run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-vsync", "vfr", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", str(out)], LOGS / f"enc_{b['id']}{tag}.log")
        return out
    run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-f", "image2", "-framerate", str(FPS),
         "-i", str(fdir / "%05d.png"), "-frames:v", str(len(frames)), "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], LOGS / f"enc_{b['id']}.log")
    got = frame_count(out)
    assert got == len(frames), f"{out}: {got} frames != {len(frames)}"
    shutil.rmtree(fdir)
    print(f"  encoded {out.name} ({got} frames)", flush=True)
    return out


def concat(beats, name):
    lst = LOGS / f"concat_{name}.txt"
    lst.write_text("".join(f"file '{BEAT_DIR / b['id']}.mp4'\n" for b in beats))
    master = OUT / f"FloMo_v3_{name}.mp4"
    run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", "-movflags", "+faststart", str(master)], LOGS / f"concat_{name}.log")
    expect = sum(n_frames(b) for b in beats)
    got = frame_count(master)
    assert got == expect, f"{master}: {got} frames != {expect}"
    return master


def encode_deliverable(src, dst, crf, scale=None):
    vf = ["-vf", f"scale={scale}:flags=lanczos"] if scale else []
    run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-i", str(src), *vf, "-c:v", "libx264",
         "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(dst)],
        LOGS / f"enc_{dst.stem}.log")
    return dst.stat().st_size


def audit(path, beats, max_mb=None):
    pm = probe(path)
    v = next(s for s in pm["streams"] if s["codec_type"] == "video")
    dur = float(pm["format"]["duration"])
    expect = sum(b["dur"] for b in beats)
    checks = {"duration": abs(dur - expect) < 0.1, "30fps": v["avg_frame_rate"] == "30/1",
              "h264_yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
              "frames": frame_count(path) == sum(n_frames(b) for b in beats)}
    if max_mb:
        checks[f"<= {max_mb} MB"] = path.stat().st_size <= max_mb * 1e6
    r = subprocess.run([FFMPEG, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    checks["decode_clean"] = r.returncode == 0 and r.stderr == ""
    bad = [k for k, ok in checks.items() if not ok]
    assert not bad, f"audit {path.name} failed: {bad}"
    print(f"  audit OK {path.name}: {dur:.2f}s {v['width']}x{v['height']} {path.stat().st_size / 1e6:.1f} MB", flush=True)


def sheet(beats, tag, path):
    cells = []
    for i, b in enumerate(beats):
        mp4 = BEAT_DIR / f"{b['id']}{tag}.mp4"
        n = frame_count(mp4)
        for k, f in enumerate([n // 4, n // 2, 3 * n // 4] if not tag else range(n)):
            tmp = LOGS / "cell.png"
            run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp4), "-vf", f"select=eq(n\\,{f})",
                 "-frames:v", "1", str(tmp)], LOGS / "cell.log")
            cells.append((f"{i:02d} {b['id']} f{f}", Image.open(tmp).convert("RGB").resize((640, 360), Image.LANCZOS)))
    cols, cw, ch, bar = 3, 640, 360, 24
    rows = (len(cells) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw, rows * (ch + bar)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for i, (txt, cell) in enumerate(cells):
        x, y = (i % cols) * cw, (i // cols) * (ch + bar)
        im.paste(cell, (x, y + bar))
        d.text((x + 6, y + 5), txt, fill=theme.rgb(ORANGE)[:3], font=theme.font("semibold", 16))
    im.save(path, quality=86)
    print(f"  sheet {path}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", type=int, default=0, help="N evenly spaced frames per beat -> smoke sheet only")
    ap.add_argument("--beats", help="comma subset of beat ids")
    ap.add_argument("--workers", type=int, default=min(16, os.cpu_count()), help="render pool size (login-node smoke: 4)")
    args = ap.parse_args()
    beats = BEATS if not args.beats else [b for b in BEATS if b["id"] in args.beats.split(",")]
    for p in (FRAMES, BEAT_DIR, LOGS, OUT):
        p.mkdir(parents=True, exist_ok=True)
    pool = Pool(args.workers)
    t0 = time.time()
    idx = [i for i, b in enumerate(BEATS) if b in beats]
    if args.smoke:
        for bi in idx:
            encode_beat(bi, render_beat(pool, bi, smoke=args.smoke), tag="_smoke")
        pool.close()
        pool.join()
        sheet(beats, "_smoke", WORK / "smoke_sheet.jpg")
        print(f"SMOKE OK wall={time.time() - t0:.0f}s")
        return
    for bi in idx:
        print(f"beat {BEATS[bi]['id']} ({n_frames(BEATS[bi])} frames)", flush=True)
        encode_beat(bi, render_beat(pool, bi))
    pool.close()
    pool.join()
    master = concat(beats, "master")
    audit(master, beats)
    x_beats = [b for b in beats if b["id"] not in X_CUT_DROP]
    x_src = concat(x_beats, "xcut") if len(x_beats) != len(beats) else master
    audit(x_src, x_beats)
    print(f"  X {encode_deliverable(x_src, OUT / 'FloMo_v3_x.mp4', 20) / 1e6:.1f} MB", flush=True)
    icra = OUT / "FloMo_v3_icra.mp4"
    encode_deliverable(master, icra, 26)
    if icra.stat().st_size > 20e6:
        encode_deliverable(master, icra, 26, scale="1280:720")
    audit(icra, beats, max_mb=20)
    sheet(beats, "", OUT / "contact_sheet.jpg")
    print(f"DONE master={master} wall={time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
