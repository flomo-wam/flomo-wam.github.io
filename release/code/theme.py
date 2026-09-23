"""v2 design system as code: paper theme (white, Inter, orange/teal).

Every plate and overlay in the v2 compositor draws through this module.
Canvas 1920x1080@30; hex values from tasks/release-video.md "v2 design system".
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
MARGIN = 96
SS = 2  # supersample factor for arrows / hairlines

# palette
CANVAS = "#FFFFFF"
PANEL = "#F6F8FA"
LINE = "#DFE4E9"
INK = "#1F2733"
MUTED = "#5B6675"
ORANGE = "#F09018"
ORANGE_DARK = "#B86600"
TEAL = "#307890"
TEAL_DARK = "#245D70"
SOFT_TEAL = "#EAF3F5"
SOFT_ORANGE = "#FCF1E3"
IMAGE_C = "#2E5C8A"   # modality: image
TEXT_C = "#2A8A4F"    # modality: text
MOTION_C = "#6B4C8C"  # modality: motion
ACTION_C = "#B23A48"  # modality: action
BASE_T1 = "#A8D6D8"   # baseline bars, light -> dark teal
BASE_T2 = "#65B3B7"
BASE_T3 = "#3D8E92"

FONT_DIR = str(Path(__file__).resolve().parents[1] / "fonts")  # scratch1 copy unreadable since 2026-09-22
_WEIGHTS = {"regular": "Inter-Regular", "medium": "Inter-Medium",
            "semibold": "Inter-SemiBold", "bold": "Inter-Bold"}
WORDMARK = str(Path(__file__).resolve().parents[1] / "assets" / "f_wordmark.png")

# type scale (px)
HEADLINE, SUB, CAPTION, CHIP, SMALL, VALUE = 72, 40, 28, 24, 22, 32


def rgb(hexstr, a=255):
    h = hexstr.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(a * 255) if a <= 1 else int(a))


@lru_cache(maxsize=64)
def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}/{_WEIGHTS[weight]}.ttf", size)


def ease_out(p):
    """Cubic ease-out, clamped: the only easing in the design system."""
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def rise_in(t, t0, dur=0.3, rise=8):
    """Design-system text entrance: 300 ms fade + 8 px rise. Returns (alpha, dy)."""
    p = ease_out((t - t0) / dur)
    return p, round((1 - p) * rise)


def fade_out(t, t_end, dur=0.2):
    return 1.0 - ease_out((t - (t_end - dur)) / dur) if t > t_end - dur else 1.0


@lru_cache(maxsize=8)
def wordmark(width=180):
    im = Image.open(WORDMARK).convert("RGBA")
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def text_len(text, weight, size, tracking=0.0):
    """Advanced width incl. tracking (em units)."""
    f = font(weight, size)
    dummy = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    base = sum(dummy.textlength(ch, font=f) for ch in text)
    return base + tracking * size * max(len(text) - 1, 0)


def draw_text(img, xy, text, weight, size, fill, tracking=0.0, alpha=1.0):
    """Tracked text drawn char by char (PIL has no letter-spacing)."""
    if alpha <= 0:
        return
    f = font(weight, size)
    d = ImageDraw.Draw(img)
    col = rgb(fill) if isinstance(fill, str) else fill
    if alpha < 0.999:
        col = col[:3] + (int(col[3] * alpha) if len(col) == 4 else int(255 * alpha),)
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=col)
        x += d.textlength(ch, font=f) + tracking * size
    return x


def card(img, box, radius=12, alpha=0.92):
    """White rounded card at `alpha` (caption cards, chips)."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle(box, radius=radius, fill=(255, 255, 255, int(255 * alpha)))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"), (0, 0))
    d2 = ImageDraw.Draw(img)
    d2.rounded_rectangle(box, radius=radius, outline=rgb(LINE), width=1)


def caption_card(img, lines, t, t_in, t_out=None, x=MARGIN, y=None, pad=24):
    """Bottom-left white card inside the margin; lines = [(text, weight, size, color)].
    Never bare text on footage. 300 ms fade + 8 px rise, 200 ms fade out."""
    a_in, dy = rise_in(t, t_in)
    a = a_in * (fade_out(t, t_out) if t_out else 1.0)
    if a <= 0:
        return
    lh = [round(size * 1.24) for _, _, size, _ in lines]
    w = max(text_len(s, wt, sz, -0.02 if sz == HEADLINE else 0.0) for s, wt, sz, _ in lines) + 2 * pad
    h = sum(lh) + 2 * pad - (lh[-1] - round(lines[-1][2] * 0.86))
    if y is None:
        y = H - MARGIN - h
    box = [x, y + dy, x + round(w), y + dy + h]
    card(img, box)
    ty = y + dy + pad - round(lines[0][2] * 0.18)
    for (s, wt, sz, colr), step in zip(lines, lh):
        draw_text(img, (x + pad, ty), s, wt, sz, colr, tracking=-0.02 if sz == HEADLINE else 0.0, alpha=a)
        ty += step


def chip(img, xy, text, t_in=0.0, t=0.0, fill=INK):
    """24 px SemiBold uppercase chip +0.06 em on a small white card."""
    text = text.upper()
    pad_x, pad_y = 12, 7
    w = text_len(text, "semibold", CHIP, 0.06) + 2 * pad_x
    h = round(CHIP * 1.3) + 2 * pad_y
    x, y = xy
    a, _ = rise_in(t, t_in) if t_in else (1.0, 0)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=(255, 255, 255, int(255 * 0.92 * a)))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"), (0, 0))
    draw_text(img, (x + pad_x, y + pad_y - 2), text, "semibold", CHIP, fill, tracking=0.06, alpha=a)
    return w, h


def cover(media, box):
    """Center-crop media to fill box (cover)."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    m = Image.fromarray(media) if isinstance(media, np.ndarray) else media
    s = max(bw / m.width, bh / m.height)
    m = m.resize((round(m.width * s), round(m.height * s)), Image.LANCZOS)
    x0 = (m.width - bw) // 2
    y0 = (m.height - bh) // 2
    return m.crop((x0, y0, x0 + bw, y0 + bh))


def pane(img, box, media=None, border=True, fill=True):
    """12 px radius pane, 1 px LINE border, no shadows; PANEL fill when requested."""
    d = ImageDraw.Draw(img)
    if fill:
        d.rounded_rectangle(box, radius=12, fill=rgb(PANEL))
    if media is not None:
        mask = Image.new("L", (box[2] - box[0], box[3] - box[1]), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, box[2] - box[0] - 1, box[3] - box[1] - 1], radius=12, fill=255)
        img.paste(cover(media, box), (box[0], box[1]), mask)
    if border:
        d.rounded_rectangle(box, radius=12, outline=rgb(LINE), width=1)


def paste_faded(img, rgba, xy, alpha):
    if alpha >= 0.999:
        img.paste(rgba, xy, rgba)
    elif alpha > 0:
        img.paste(rgba, xy, rgba.getchannel("A").point(lambda v: int(v * alpha)))


def overlay_canvas(alpha_scale=1.0):
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def disp_to_rgb(d, scale):
    """(dX,dY,dZ) -> RGB cube; 128 gray = still. d: (... ,3) array, scale in same units."""
    c = 128 + 127 * np.clip(d / max(scale, 1e-6), -1, 1)
    return np.rint(c).astype(np.uint8)


def arrow(d, p0, p1, color, shaft=2, head=6, alpha=255):
    """Supersampled arrow: shaft line + triangular head, drawn at SS x by the caller.
    Reused pattern from video/release/motion.py:draw_arrow (min-length guarded)."""
    p0 = np.asarray(p0, float) * SS
    p1 = np.asarray(p1, float) * SS
    v = p1 - p0
    n = float(np.hypot(*v))
    if n < head * SS * 1.2:  # too short for a head: draw a dot instead
        r = max(1.5 * SS, 0.0)
        d.ellipse([p0[0] - r, p0[1] - r, p0[0] + r, p0[1] + r], fill=color + (alpha,))
        return
    col = color + (alpha,)
    d.line([tuple(p0), tuple(p1 - v / n * (head * SS * 0.6))], fill=col, width=max(shaft * SS, 1), joint="curve")
    r = shaft * SS / 2
    d.ellipse([p0[0] - r, p0[1] - r, p0[0] + r, p0[1] + r], fill=col)
    perp = np.array([-v[1], v[0]]) / n
    base = p1 - v / n * head * SS
    d.polygon([tuple(p1), tuple(base + perp * head * SS * 0.6), tuple(base - perp * head * SS * 0.6)], fill=col)


def dot(d, p, color, r=1.5, alpha=255):
    q = np.asarray(p, float) * SS
    d.ellipse([q[0] - r * SS, q[1] - r * SS, q[0] + r * SS, q[1] + r * SS], fill=color + (alpha,))


def bar_chart(img, x, y, w, rows, t, t0, source=None, maxv=100.0, bar_h=40, gap=30):
    """Horizontal rounded bars: label left 28 ink, value right 32 bold tabular,
    bar 40 px / 8 px radius, grow 600 ms stagger 80 ms, cubic ease-out.
    rows: (label, value, color) or (label, value, color, value_str, sub_label);
    orange = FloMo, teal shades = baselines."""
    label_w = 400
    val_w = 150
    for i, row in enumerate(rows):
        label, value, colorr = row[0], row[1], row[2]
        value_str = row[3] if len(row) > 3 else f"{value:g}%"
        sub = row[4] if len(row) > 4 else None
        g = ease_out((t - (t0 + 0.08 * i)) / 0.6)
        a = ease_out((t - (t0 + 0.08 * i)) / 0.3)
        if a <= 0:
            continue
        ry = y + i * (bar_h + gap + (26 if sub else 0))
        d = ImageDraw.Draw(img, "RGBA")
        track_x0, track_x1 = x + label_w, x + w - val_w
        d.rounded_rectangle([track_x0, ry, track_x1, ry + bar_h], radius=8, fill=rgb(PANEL, a))
        d.rounded_rectangle([track_x0, ry, track_x0 + max(round((track_x1 - track_x0) * value / maxv * g), 2),
                             ry + bar_h], radius=8, fill=rgb(colorr, a))
        draw_text(img, (x, ry + 4), label, "medium", CAPTION, INK, alpha=a)
        if sub:
            draw_text(img, (x, ry + bar_h + 8), sub, "regular", 22, MUTED, alpha=a)
        vw = text_len(value_str, "bold", VALUE)
        draw_text(img, (x + w - vw, ry + 1), value_str, "bold", VALUE, INK, alpha=a)
    if source:
        sy = y + sum((bar_h + gap + (26 if len(r) > 4 else 0)) for r in rows) - gap + 6
        a = ease_out((t - t0 - 0.08 * len(rows)) / 0.3)
        draw_text(img, (x, sy), source, "medium", SMALL, MUTED, alpha=a)


def headline_block(img, lines, t, t_in, t_out=None, x=MARGIN, y=None, align="left"):
    """Headline/sub block on white beats (not on footage): 300 ms fade + 8 px rise."""
    a, dy = rise_in(t, t_in)
    a *= fade_out(t, t_out) if t_out else 1.0
    if a <= 0:
        return
    ty = (H // 2 - 80 if y is None else y) + dy
    for s, wt, sz, colr in lines:
        if align == "center":
            xx = x - text_len(s, wt, sz, -0.02 if sz == HEADLINE else 0.0) / 2
        else:
            xx = x
        draw_text(img, (xx, ty), s, wt, sz, colr, tracking=-0.02 if sz == HEADLINE else 0.0, alpha=a)
        ty += round(sz * 1.3)
