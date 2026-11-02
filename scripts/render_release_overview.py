#!/usr/bin/env python3
"""Cut the archived 61-second overview to 44.6 seconds with a diagram-based architecture scene.

Requires the already-installed Pillow and imageio_ffmpeg packages and the Inter
SemiBold font used by the original slides. Run against an archive of the
original, never against the rendered 44.6-second release.
"""

import argparse
import math
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

WIDTH, HEIGHT, FPS = 1920, 1080, 30
FOOTAGE_FILTER = f'scale={WIDTH}:{HEIGHT}:flags=lanczos,fps={FPS},setpts=PTS-STARTPTS'
TOTAL_FRAMES = 1338
ARCHITECTURE_FRAMES = 291
# Output order as (source start, seconds); None inserts the animated paper
# diagram. Footage is only trimmed, never retimed.
# Starts at 14.4 and 33.4 skip the original's crossfades from the prior slide.
CUTS = ((8, 5), (3.3, 2.7), (14.4, 3.6), (None, 9.7), (33.4, 6.6), (41.5, 6),
        (49.5, 8), (57.5, 3))
WHITE = (255, 255, 255)
INK = (32, 38, 48)
ORANGE = (240, 143, 23)
TEAL = (57, 143, 145)
GRAY = (120, 124, 130)
REPO = Path(__file__).resolve().parents[1]
# The original slides use Inter SemiBold; it is not bundled with macOS.
FONT_CANDIDATES = (
    REPO / 'scripts/fonts/Inter-SemiBold.ttf',
    Path.home() / 'Library/Fonts/Inter-SemiBold.ttf',
    Path('/Library/Fonts/Inter-SemiBold.ttf'),
    Path.home() / 'Downloads/deck/assets/fonts/Inter-SemiBold.ttf',
)

# The paper diagram sits exactly where the original architecture slides put it.
DIAGRAM_X, DIAGRAM_Y, DIAGRAM_WIDTH = 96, 220, 1728
SCALE = DIAGRAM_WIDTH / 1603
DIM = .65  # Blend toward white for out-of-focus parts, as in the original.
TITLE_XY = (96, 112)
LOGO_BOX = (1650, 76, 1834, 132)  # FLOMO logo in the original slide frame.
LOGO_TIME = 23

# Source-pixel boxes in static/images/thread_method.png (1603x720). Each
# region's edges sit in whitespace so focus changes never cut a drawn element.
REGIONS = {
    'divider': (905, 0, 926, 720),
    'panel_title': (926, 0, 1250, 42),
    'frames': (928, 42, 1228, 362),
    'arrow_right': (1228, 185, 1292, 218),
    'scene_flow': (1292, 42, 1595, 362),
    'arrow_down': (1420, 362, 1452, 420),
    'cube': (1300, 420, 1595, 712),
    'arrow_left': (1228, 511, 1292, 544),
    'flow_rgb': (928, 366, 1228, 712),
    'text': (5, 0, 247, 412),
    'action': (295, 0, 516, 268),
    'teal_in': (295, 268, 516, 309),
    'encoder': (516, 0, 905, 268),
    'orange_in': (516, 268, 905, 309),
    'backbone': (247, 309, 905, 412),
    'tokens_out': (247, 412, 905, 447),
    'action_decoder': (247, 447, 516, 572),
    'video_decoder': (516, 447, 905, 572),
    'action_out': (247, 572, 516, 720),
    'motion_out': (516, 572, 905, 720),
}
WIPES = {'arrow_right': 'right', 'arrow_down': 'down', 'arrow_left': 'left'}
# Tight content boxes (image plus caption) that briefly scale up as they land.
POPS = {'frames': ((944, 50, 1228, 360), .25), 'scene_flow': ((1296, 44, 1580, 361), .9),
        'cube': ((1318, 428, 1572, 700), 1.5), 'flow_rgb': ((945, 382, 1228, 698), 2.1),
        'action_out': ((310, 592, 502, 700), 7.85), 'motion_out': ((600, 575, 770, 700), 7.85)}
TEAL_IN = [(317, 280, 356, 302), (366, 280, 404, 302),
           (414, 280, 453, 302), (465, 280, 504, 302)]
ORANGE_IN = [(595, 280, 635, 303), (645, 280, 684, 303),
             (694, 280, 734, 303), (743, 280, 783, 303)]
TEAL_OUT = [(x0, 414, x1, 436) for x0, _, x1, _ in TEAL_IN]
ORANGE_OUT = [(x0, 414, x1, 437) for x0, _, x1, _ in ORANGE_IN]
SIDE_TOKENS = [(213, 317, 237, 356), (213, 366, 237, 405)]
# Glow outlines traced on drawn shapes: (kind, source points, colour).
SHAPES = {
    'flow_rgb': ('rect', (945, 382, 1228, 662), ORANGE),
    'slot': ('rect', (702, 42, 824, 132), ORANGE),
    'text_encoder': ('rect', (16, 153, 248, 233), GRAY),
    'action_encoder': ('rect', (332, 153, 487, 233), TEAL),
    'video_encoder': ('poly', [(529, 152), (847, 152), (793, 232), (583, 232)], ORANGE),
    'backbone': ('rect', (249, 311, 851, 407), GRAY),
    'action_decoder': ('rect', (330, 461, 485, 539), TEAL),
    'video_decoder': ('poly', [(585, 461), (789, 461), (847, 539), (530, 539)], ORANGE),
}
FLOW_RGB_FRONT = (947, 397, 1212, 661)
SCENE_FLOW_SLOT = (704, 52, 781, 130)
# Focus outlines; the first three match the original slides' orange boxes.
FOCUS = [(0, (929, 3, 1594, 712)), (2.6, (518, 3, 872, 264)),
         (4.8, (5, 3, 517, 412)), (6.4, (241, 264, 872, 716))]
TITLES = [(0, '1', 'Turn 3D motion into RGB video'),
          (2.6, '2', 'Encode it with the frozen video VAE'),
          (4.8, '3', 'Add the instruction and noisy actions'),
          (6.4, '4', 'One backbone predicts motion + actions')]
FINALE = 8.4
# The paper calls Pull String an unseen task; the archived slide says "Unseen motion".
BADGE_SECONDS = (49.5, 57.8)  # transfer slide, including its fade in and crossfade out
BADGE_PILL = (113, 258, 291, 293)  # opaque pill at the top left of the yoyo clip
BADGE_TEXT = (8, 5, 170, 28)  # old text area, relative to BADGE_PILL
BADGE_FILL = (18, 23, 27)


@lru_cache(maxsize=None)
def font(size):
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError('The renderer needs Inter-SemiBold.ttf in one of: '
                            + ', '.join(map(str, FONT_CANDIDATES)))


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def rise(time, start, duration=.4):
    return ease((time - start) / duration)


def window(time, start, end=None, duration=.4):
    level = rise(time, start, duration)
    if end is not None:
        level *= 1 - rise(time, end, duration)
    return max(level, rise(time, FINALE, .5))


def bump(time, start, duration):
    """0 -> 1 -> 0 over the interval."""
    progress = (time - start) / duration
    return math.sin(math.pi * progress) if 0 < progress < 1 else 0.0


def scaled(box):
    return tuple(round(value * SCALE) for value in box)


def to_frame(x, y):
    return DIAGRAM_X + x * SCALE, DIAGRAM_Y + y * SCALE


def frame_box(box):
    x0, y0 = to_frame(*box[:2])
    x1, y1 = to_frame(*box[2:])
    return x0, y0, x1, y1


def point_on_path(points, fraction):
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(points, points[1:])]
    distance = fraction * sum(lengths)
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if distance <= length:
            ratio = distance / length if length else 0
            return a[0] + ratio * (b[0] - a[0]), a[1] + ratio * (b[1] - a[1])
        distance -= length
    return points[-1]


def with_alpha(sprite, level):
    if level >= 1:
        return sprite
    sprite = sprite.copy()
    sprite.putalpha(sprite.getchannel('A').point(lambda value: round(value * level)))
    return sprite


def overlay(canvas, sprite, xy, level):
    level = max(0.0, min(1.0, level))
    if level > .01:
        canvas.alpha_composite(with_alpha(sprite, level), (round(xy[0]), round(xy[1])))


def lerp_box(a, b, progress):
    return tuple(p + (q - p) * progress for p, q in zip(a, b))


def frame_from_video(ffmpeg, source, seconds):
    raw = subprocess.run(
        [ffmpeg, '-hide_banner', '-loglevel', 'error', '-ss', str(seconds),
         '-i', str(source), '-frames:v', '1', '-vf', f'scale={WIDTH}:{HEIGHT}',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], check=True,
        capture_output=True).stdout
    return Image.frombytes('RGB', (WIDTH, HEIGHT), raw)


class Architecture:
    """Steps through the real paper diagram; only highlights are drawn on top."""

    def __init__(self, ffmpeg, source):
        method = Image.open(REPO / 'static/images/thread_method.png').convert('RGB')
        height = round(method.height * SCALE)
        self.full = method.resize((DIAGRAM_WIDTH, height), Image.Resampling.LANCZOS)
        self.dim = Image.blend(self.full, Image.new('RGB', self.full.size, WHITE), DIM)
        self.lit = ImageEnhance.Brightness(
            ImageEnhance.Color(self.full).enhance(1.6)).enhance(1.04)
        self.logo = frame_from_video(ffmpeg, source, LOGO_TIME).crop(LOGO_BOX)
        self.titles = [self.title(number, text) for _, number, text in TITLES]
        self.dot = {color: self.make_dot(color) for color in (ORANGE, TEAL, GRAY)}
        self.glows = {name: self.make_glow(*shape) for name, shape in SHAPES.items()}
        self.tokens = {}
        for boxes, color in ((TEAL_IN, TEAL), (ORANGE_IN, ORANGE), (TEAL_OUT, TEAL),
                             (ORANGE_OUT, ORANGE), (SIDE_TOKENS, GRAY)):
            for box in boxes:
                self.tokens[box] = self.make_token(box, color)
        x0, y0, x1, y1 = scaled(FLOW_RGB_FRONT)
        self.flying = self.full.crop((x0, y0, x1, y1))

    @staticmethod
    def title(number, text):
        layer = Image.new('RGBA', (1500, 130), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        heading = font(58)
        top, bottom = heading.getbbox('H')[1::2]
        centre = (top + bottom) / 2
        draw.ellipse((0, centre - 28, 56, centre + 28), fill=ORANGE)
        draw.text((28, centre), number, font=font(36), fill=WHITE, anchor='mm')
        draw.text((78, 0), text, font=heading, fill=INK)
        return layer

    @staticmethod
    def make_dot(color):
        size = 72
        sprite = Image.new('RGBA', (size, size), (*color, 0))
        halo = Image.new('L', (size, size), 0)
        ImageDraw.Draw(halo).ellipse((20, 20, 52, 52), fill=170)
        sprite.putalpha(halo.filter(ImageFilter.GaussianBlur(8)))
        draw = ImageDraw.Draw(sprite)
        draw.ellipse((27, 27, 45, 45), fill=(*color, 255))
        draw.ellipse((32, 32, 40, 40), fill=(255, 255, 255, 230))
        return sprite

    @staticmethod
    def make_glow(kind, points, color, pad=36):
        if kind == 'rect':
            x0, y0, x1, y1 = frame_box(points)
            outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        else:
            outline = [to_frame(*point) for point in points]
        left = min(x for x, _ in outline) - pad
        top = min(y for _, y in outline) - pad
        outline = [(x - left, y - top) for x, y in outline]
        size = (round(max(x for x, _ in outline) + pad),
                round(max(y for _, y in outline) + pad))
        halo = Image.new('L', size, 0)
        ImageDraw.Draw(halo).polygon(outline, outline=200, width=12)
        sprite = Image.new('RGBA', size, (*color, 0))
        sprite.putalpha(halo.filter(ImageFilter.GaussianBlur(10)))
        ImageDraw.Draw(sprite).polygon(outline, outline=(*color, 255), width=4)
        return (left, top), sprite

    def make_token(self, box, color, pad=18):
        x0, y0, x1, y1 = scaled(box)
        crop = self.lit.crop((x0, y0, x1, y1)).convert('RGBA')
        halo = Image.new('L', (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), 0)
        ImageDraw.Draw(halo).rounded_rectangle(
            (pad - 3, pad - 3, pad + x1 - x0 + 2, pad + y1 - y0 + 2), radius=8, fill=150)
        glow = Image.new('RGBA', halo.size, (*color, 0))
        glow.putalpha(halo.filter(ImageFilter.GaussianBlur(7)))
        return crop, glow, pad

    def regions(self, time):
        flow_steps = [('panel_title', .05), ('frames', .25), ('arrow_right', .6),
                      ('scene_flow', .9), ('arrow_down', 1.25), ('cube', 1.5),
                      ('arrow_left', 1.85), ('flow_rgb', 2.1)]
        levels = {'divider': 1.0}
        for name, start in flow_steps:
            duration = .3 if name in WIPES else .35
            end = 2.95 if name == 'flow_rgb' else 2.6
            levels[name] = window(time, start, end, duration)
        levels['encoder'] = window(time, 2.6, 6.4)
        levels['orange_in'] = window(time, 4.1, duration=.3)
        levels['text'] = window(time, 4.8, 6.4, .35)
        levels['action'] = window(time, 4.8, 6.4, .35)
        levels['teal_in'] = window(time, 5.55, duration=.3)
        levels['backbone'] = window(time, 6.4)
        levels['tokens_out'] = window(time, 6.4)
        levels['action_decoder'] = window(time, 6.45)
        levels['video_decoder'] = window(time, 6.45)
        levels['action_out'] = window(time, 7.85, duration=.3)
        levels['motion_out'] = window(time, 7.85, duration=.3)
        return levels

    def diagram(self, time):
        mask = Image.new('L', self.full.size, 0)
        for name, level in self.regions(time).items():
            if level <= 0:
                continue
            x0, y0, x1, y1 = scaled(REGIONS[name])
            direction = WIPES.get(name)
            if direction and level < 1:
                # Arrows draw on along their direction instead of fading.
                if direction == 'right':
                    x1 = round(x0 + (x1 - x0) * level)
                elif direction == 'left':
                    x0 = round(x1 - (x1 - x0) * level)
                else:
                    y1 = round(y0 + (y1 - y0) * level)
                level = 1
            mask.paste(round(255 * level), (x0, y0, x1, y1))
        diagram = Image.composite(self.full, self.dim, mask)
        for box, start in POPS.values():
            amount = bump(time, start, .45)
            if amount:
                x0, y0, x1, y1 = scaled(box)
                part = diagram.crop((x0, y0, x1, y1))
                factor = 1 + .045 * amount
                size = (round(part.width * factor), round(part.height * factor))
                diagram.paste(part.resize(size, Image.Resampling.LANCZOS),
                              (x0 - (size[0] - part.width) // 2,
                               y0 - (size[1] - part.height) // 2))
        return diagram

    def glow(self, canvas, name, level):
        (left, top), sprite = self.glows[name]
        overlay(canvas, sprite, (left, top), level)

    def light(self, canvas, box, start, end=None):
        time = self.time
        level = rise(time, start, .2) * (1 - rise(time, FINALE, .5))
        if end is not None:
            level *= 1 - rise(time, end, .4)
        if level <= .01:
            return
        crop, glow, pad = self.tokens[box]
        x0, y0, x1, y1 = frame_box(box)
        overlay(canvas, glow, (x0 - pad, y0 - pad), level)
        factor = 1 + .16 * bump(time, start, .35)
        width, height = round(crop.width * factor), round(crop.height * factor)
        token = crop.resize((width, height), Image.Resampling.LANCZOS)
        overlay(canvas, token, ((x0 + x1 - width) / 2, (y0 + y1 - height) / 2), level)

    def pulse(self, canvas, points, color, start, duration):
        progress = (self.time - start) / duration
        if not 0 <= progress <= 1:
            return
        x, y = to_frame(*point_on_path(points, ease(progress)))
        level = min(1.0, progress * 6, (1 - progress) * 6)
        sprite = self.dot[color]
        overlay(canvas, sprite, (x - sprite.width / 2, y - sprite.height / 2), level)

    def fly(self, canvas, start=2.8, duration=.7, linger=.3):
        progress = (self.time - start) / duration
        if progress < 0 or progress > 1 + linger / duration:
            return
        box = lerp_box(frame_box(FLOW_RGB_FRONT), frame_box(SCENE_FLOW_SLOT),
                       ease(min(progress, 1)))
        level = 1 - rise(self.time, start + duration, linger)
        lift = bump(self.time, start, duration)
        x0, y0, x1, y1 = box
        size = (round(x1 - x0), round(y1 - y0))
        image = self.flying.resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        shadow = Image.new('RGBA', (size[0] + 40, size[1] + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle((20, 20, 20 + size[0], 20 + size[1]),
                                         fill=(0, 0, 0, 90))
        shadow = shadow.filter(ImageFilter.GaussianBlur(9))
        overlay(canvas, shadow, (x0 - 20 + 6 * lift, y0 - 20 + 10 * lift), level * lift)
        overlay(canvas, image, (x0, y0), level)

    def outline(self, canvas):
        box = FOCUS[0][1]
        for start, target in FOCUS[1:]:
            box = lerp_box(box, target, rise(self.time, start, .45))
        level = rise(self.time, 0, .3) * (1 - rise(self.time, FINALE, .45))
        if level <= .01:
            return
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle(
            [round(value) for value in frame_box(box)], radius=6,
            outline=(*ORANGE, 255), width=4)
        canvas.alpha_composite(with_alpha(layer, level))

    def heading(self, canvas):
        for index, (start, _, _) in enumerate(TITLES):
            nxt = TITLES[index + 1][0] if index + 1 < len(TITLES) else None
            fade_in = 1.0 if start == 0 else rise(self.time, start + .12, .28)
            fade_out = 0.0 if nxt is None else rise(self.time, nxt, .18)
            level = fade_in * (1 - fade_out)
            offset = 10 * (1 - fade_in)
            overlay(canvas, self.titles[index],
                    (TITLE_XY[0], TITLE_XY[1] + offset), level)

    def frame(self, number):
        time = self.time = number / FPS
        canvas = Image.new('RGBA', (WIDTH, HEIGHT), (*WHITE, 255))
        canvas.paste(self.diagram(time), (DIAGRAM_X, DIAGRAM_Y))

        # 1. Flow tokenization: (4) lands, then a copy flies into the input slot.
        self.glow(canvas, 'flow_rgb', bump(time, 2.35, .6))
        self.fly(canvas)
        # 2. Frozen VAE encodes the RGB scene flow into orange tokens.
        self.glow(canvas, 'slot', bump(time, 3.4, .5))
        self.pulse(canvas, [(797, 127), (797, 139), (688, 139), (688, 152)],
                   ORANGE, 3.5, .3)
        self.glow(canvas, 'video_encoder', bump(time, 3.65, .55))
        self.pulse(canvas, [(687, 233), (687, 279)], ORANGE, 3.95, .25)
        for index, box in enumerate(ORANGE_IN):
            self.light(canvas, box, 4.15 + .1 * index)
        # 3. Instruction via cross-attention, noisy actions into teal tokens.
        self.pulse(canvas, [(130, 121), (130, 152)], GRAY, 5.0, .2)
        self.glow(canvas, 'text_encoder', bump(time, 5.12, .45))
        self.pulse(canvas, [(130, 234), (130, 362), (204, 362)], GRAY, 5.4, .5)
        for box in SIDE_TOKENS:
            self.light(canvas, box, 5.85, end=6.4)
        self.pulse(canvas, [(410, 99), (410, 152)], TEAL, 5.0, .2)
        self.glow(canvas, 'action_encoder', bump(time, 5.12, .45))
        self.pulse(canvas, [(410, 234), (410, 279)], TEAL, 5.4, .2)
        for index, box in enumerate(TEAL_IN):
            self.light(canvas, box, 5.6 + .1 * index)
        # 4. The backbone denoises both streams; both decoders run together.
        self.glow(canvas, 'backbone', bump(time, 6.6, .6))
        for index, (teal, orange) in enumerate(zip(TEAL_OUT, ORANGE_OUT)):
            self.light(canvas, teal, 7.0 + .08 * index)
            self.light(canvas, orange, 7.0 + .08 * index)
        self.pulse(canvas, [(410, 438), (410, 460)], TEAL, 7.38, .14)
        self.pulse(canvas, [(684, 438), (684, 460)], ORANGE, 7.38, .14)
        self.glow(canvas, 'action_decoder', bump(time, 7.45, .45))
        self.glow(canvas, 'video_decoder', bump(time, 7.45, .45))
        self.pulse(canvas, [(410, 541), (410, 568)], TEAL, 7.72, .15)
        self.pulse(canvas, [(684, 541), (684, 568)], ORANGE, 7.72, .15)

        self.outline(canvas)
        self.heading(canvas)
        canvas = canvas.convert('RGB')
        canvas.paste(self.logo, LOGO_BOX[:2])
        return canvas


class Badge:
    """Swaps the badge text as a difference image, so fades stay intact."""

    def __init__(self, ffmpeg, source):
        steady = [frame_from_video(ffmpeg, source, 50 + index / 2).crop(BADGE_PILL)
                  for index in range(15)]
        old = steady[0]
        for count, image in enumerate(steady[1:], 2):
            old = Image.blend(old, image, 1 / count)
        new = old.copy()
        draw = ImageDraw.Draw(new)
        draw.rectangle(BADGE_TEXT, fill=BADGE_FILL)
        left, _, right, _ = draw.textbbox((0, 0), 'Unseen task', font=font(22))
        draw.text(((new.width - left - right) / 2, 3), 'Unseen task', font=font(22), fill=WHITE)
        self.add = ImageChops.subtract(new, old)
        self.remove = ImageChops.subtract(old, new)
        gray = old.convert('L')
        self.text = gray.point(lambda value: 255 if value > 200 else 0)
        self.body = gray.point(lambda value: 255 if value < 40 else 0)
        self.full = self.contrast(old)

    def contrast(self, image):
        gray = image.convert('L')
        return ImageStat.Stat(gray, self.text).mean[0] - ImageStat.Stat(gray, self.body).mean[0]

    def __call__(self, frame, seconds):
        if not BADGE_SECONDS[0] <= seconds < BADGE_SECONDS[1]:
            return frame
        crop = frame.crop(BADGE_PILL)
        # The old text's contrast over the pill measures how visible the slide is.
        level = max(0.0, min(1.0, self.contrast(crop) / self.full))
        if level > .01:
            crop = ImageChops.add(crop, self.add.point(lambda value: round(value * level)))
            crop = ImageChops.subtract(crop, self.remove.point(lambda value: round(value * level)))
            frame.paste(crop, BADGE_PILL[:2])
        return frame


def encoder_args():
    return ['-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-r', str(FPS), '-video_track_timescale', '15360']


def encode_frames(ffmpeg, images, output):
    command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
               '-r', str(FPS), '-i', '-', *encoder_args(), str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for image in images:
            process.stdin.write(image.tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError(f'FFmpeg could not encode {output.name}')
    except BaseException:
        process.stdin.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
        raise


def encode_architecture(ffmpeg, source, output):
    architecture = Architecture(ffmpeg, source)
    encode_frames(ffmpeg, (architecture.frame(number) for number in range(ARCHITECTURE_FRAMES)),
                  output)


def footage(ffmpeg, source, start, count, badge):
    command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-ss', str(start), '-i', str(source),
               '-vf', FOOTAGE_FILTER,
               '-frames:v', str(count), '-r', str(FPS), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        for number in range(count):
            raw = process.stdout.read(WIDTH * HEIGHT * 3)
            if len(raw) < WIDTH * HEIGHT * 3:
                raise RuntimeError(f'Source ended {number} frames into the cut at {start}s')
            yield badge(Image.frombytes('RGB', (WIDTH, HEIGHT), raw), start + number / FPS)


def frames(duration):
    count = round(duration * FPS)
    assert abs(duration * FPS - count) < 1e-6, f'{duration}s is not a whole frame count'
    return count


def render(source, output):
    source = source.resolve(strict=True)
    output = output.resolve()
    if source == output:
        raise ValueError('The output must not overwrite the archived source')
    font(58)  # Fail before encoding anything if the slide font is missing.
    assert sum(frames(duration) for _, duration in CUTS) == TOTAL_FRAMES
    assert next(frames(duration) for start, duration in CUTS
                if start is None) == ARCHITECTURE_FRAMES
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    badge = Badge(ffmpeg, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='flomo-overview-') as temporary:
        directory = Path(temporary)
        segments = []
        for index, (start, duration) in enumerate(CUTS):
            segment = directory / f'{index:02d}.mp4'
            if start is None:
                encode_architecture(ffmpeg, source, segment)
            elif start < BADGE_SECONDS[1] and start + duration > BADGE_SECONDS[0]:
                encode_frames(ffmpeg, footage(ffmpeg, source, start, frames(duration), badge),
                              segment)
            else:
                subprocess.run(
                    [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                     '-ss', str(start), '-i', str(source),
                     '-vf', FOOTAGE_FILTER,
                     '-frames:v', str(frames(duration)),
                     *encoder_args(), str(segment)], check=True)
            segments.append(segment)
        manifest = directory / 'segments.txt'
        manifest.write_text(''.join(f"file '{segment.name}'\n" for segment in segments))
        # All segments use the same codec, dimensions, frame rate and time base.
        assembled = directory / 'overview.mp4'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                        '-f', 'concat', '-safe', '0', '-i', str(manifest),
                        '-map', '0:v:0', '-an', '-c:v', 'copy',
                        '-movflags', '+faststart', str(assembled)], check=True)
        # Leave an existing destination untouched if any encoding step fails.
        shutil.copyfile(assembled, output)
    print(f'Rendered {TOTAL_FRAMES / FPS:g} seconds / {TOTAL_FRAMES} frames to {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='Preserved original 61-second thread_overview.mp4')
    parser.add_argument('--output', type=Path, required=True,
                        help='Destination MP4; must differ from the source')
    args = parser.parse_args()
    render(args.source, args.output)


if __name__ == '__main__':
    main()
