#!/usr/bin/env python3
"""Cut the archived 61-second overview to 40 seconds with a new architecture scene.

Requires the already-installed Pillow and imageio_ffmpeg packages. Run against
an archive of the original, never against the rendered 40-second release.
"""

import argparse
import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT, FPS = 1920, 1080, 30
ARCHITECTURE_SECONDS = 7
# Output order; None inserts the newly drawn architecture. Never retime footage.
CUTS = ((8, 5), (14, 4), (None, 7), (33, 7), (41.5, 6),
        (49.5, 8), (57.5, 3))
WHITE = '#FFFFFF'
INK = '#21252A'
MUTED = '#626C73'
LINE = '#DCE3E5'
ORANGE = '#F5A014'
TEAL = '#398F91'
PALE_ORANGE = '#FFF6E7'
PALE_TEAL = '#EDF7F6'
FONT_PATH = Path('/System/Library/Fonts/Avenir Next.ttc')
REPO = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def font(size, bold=False):
    # Face indices come from the macOS Avenir Next collection.
    return ImageFont.truetype(str(FONT_PATH), size=size, index=0 if bold else 7)


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def label(draw, xy, text, size=36, color=INK, bold=False, anchor=None):
    draw.text(xy, text, font=font(size, bold), fill=color, anchor=anchor,
              spacing=8)


def card(draw, box, fill=WHITE, border=LINE, width=2, radius=24):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=border,
                           width=width)


def reveal(canvas, progress, painter):
    if progress <= 0:
        return
    if progress >= 1:
        painter(canvas)
        return
    layer = canvas.copy()
    painter(layer)
    canvas.paste(Image.blend(canvas, layer, ease(progress)))


def arrow(draw, points, color=LINE, width=5):
    draw.line(points, fill=color, width=width, joint='curve')
    x, y = points[-1]
    px, py = points[-2]
    angle = math.atan2(y - py, x - px)
    draw.polygon([(x, y),
                  (x - 17 * math.cos(angle - .52), y - 17 * math.sin(angle - .52)),
                  (x - 17 * math.cos(angle + .52), y - 17 * math.sin(angle + .52))],
                 fill=color)


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


def tokens(draw, points, time, color, start=0, period=1.1, count=3):
    if time < start:
        return
    for number in range(count):
        elapsed = time - start - number * .14
        if elapsed < 0:
            continue
        x, y = point_on_path(points, (elapsed % period) / period)
        draw.rounded_rectangle((x - 11, y - 8, x + 11, y + 8), radius=5,
                               fill=color)


def tile_grid(draw, xy, columns, rows, color, pale, time=0, cell=43, gap=12):
    x, y = xy
    for row in range(rows):
        for column in range(columns):
            phase = (column + row * .7) / max(1, columns + rows)
            active = ((time * .65 - phase) % 1) < .35
            card(draw, (x + column * (cell + gap), y + row * (cell + gap),
                        x + column * (cell + gap) + cell,
                        y + row * (cell + gap) + cell),
                 fill=color if active else pale, border=color, radius=8)


def lock(draw, x, y):
    draw.arc((x + 9, y, x + 37, y + 38), 180, 360, fill=TEAL, width=5)
    draw.rounded_rectangle((x, y + 18, x + 46, y + 52), radius=8,
                           fill=PALE_TEAL, outline=TEAL, width=3)
    draw.ellipse((x + 20, y + 30, x + 26, y + 36), fill=TEAL)


class Architecture:
    def __init__(self):
        method = Image.open(REPO / 'static/images/thread_method.png').convert('RGB')
        # These are real illustrations from the paper figure, not predictions.
        self.flow = method.crop((944, 393, 1201, 653))
        self.rgb = method.crop((944, 67, 1202, 329))
        self.logo = Image.open(REPO / 'static/images/flomo_logo.png').convert('RGBA')
        self.logo.thumbnail((180, 85), Image.Resampling.LANCZOS)

    def base(self, heading, second_stage):
        canvas = Image.new('RGB', (WIDTH, HEIGHT), WHITE)
        draw = ImageDraw.Draw(canvas)
        canvas.paste(self.logo, (WIDTH - 96 - self.logo.width, 65), self.logo)
        label(draw, (96, 91), heading, 58, bold=True)
        draw.line((96, 205, 1824, 205), fill=LINE, width=3)
        draw.line((96, 205, 1824 if second_stage else 850, 205), fill=TEAL, width=5)
        return canvas

    def encode_targets(self, time):
        canvas = self.base('Reuse the frozen video VAE', False)
        draw = ImageDraw.Draw(canvas)
        card(draw, (96, 242, 555, 298), PALE_ORANGE, PALE_ORANGE, radius=15)
        label(draw, (116, 249), 'Training-target encoding', 30, color='#9A6100', bold=True)

        card(draw, (96, 330, 540, 780))
        label(draw, (318, 351), 'RGB scene flow', 36, bold=True, anchor='mt')
        crop = ImageOps.fit(self.flow, (310, 310), method=Image.Resampling.LANCZOS)
        canvas.paste(crop, (163, 420))
        draw = ImageDraw.Draw(canvas)

        vae_box = (735, 407, 1185, 707)
        card(draw, vae_box, PALE_TEAL, TEAL, width=3)
        lock(draw, 936, 430)
        label(draw, (960, 503), 'Wan 2.2 VAE', 43, bold=True, anchor='mt')
        label(draw, (960, 566), 'Frozen encoder', 30, anchor='mt')

        card(draw, (1390, 330, 1824, 780))
        label(draw, (1607, 351), 'Video latents', 36, bold=True, anchor='mt')
        if time >= .85:
            tile_grid(draw, (1455, 455), 5, 4, ORANGE, PALE_ORANGE, time, cell=48, gap=14)

        first = [(540, 557), (725, 557)]
        second = [(1185, 557), (1380, 557)]
        arrow(draw, first)
        arrow(draw, second)
        tokens(draw, first, time, ORANGE, start=.12, period=.9)
        tokens(draw, second, time, ORANGE, start=.6, period=.9)
        label(draw, (960, 866), 'No new tokenizer',
              42, color=INK, anchor='mt')
        return canvas

    def predict_jointly(self, time):
        canvas = self.base('Predict motion + actions together', True)
        draw = ImageDraw.Draw(canvas)
        label(draw, (96, 244), 'IMAGE + INSTRUCTION', 29, color=TEAL, bold=True)
        card(draw, (96, 300, 530, 795), PALE_TEAL, TEAL)
        crop = ImageOps.fit(self.rgb, (340, 235), method=Image.Resampling.LANCZOS)
        canvas.paste(crop, (143, 335))
        draw = ImageDraw.Draw(canvas)
        card(draw, (123, 639, 503, 766), WHITE, LINE, radius=16)
        label(draw, (313, 656), '“roll the dough with', 29, anchor='mt')
        label(draw, (313, 701), 'the rolling pin”', 29, anchor='mt')

        pulse = (1 + math.sin(time * 5)) / 2
        inset = int(5 * pulse)
        card(draw, (735 - inset, 381 - inset, 1220 + inset, 727 + inset),
             '#F5F9F8', '#E5F0EE', radius=34)
        card(draw, (750, 396, 1205, 712), WHITE, TEAL, width=3)
        label(draw, (977, 432), 'Wan 2.2', 35, color=MUTED, anchor='mt')
        label(draw, (977, 490), '5B backbone', 49, bold=True, anchor='mt')
        tile_grid(draw, (841, 635), 5, 1, TEAL, PALE_TEAL, time, cell=42, gap=15)

        condition = [(530, 554), (739, 554)]
        flow_path = [(1205, 554), (1305, 554), (1305, 447), (1405, 447)]
        action_path = [(1205, 554), (1305, 554), (1305, 699), (1405, 699)]
        arrow(draw, condition, TEAL)
        arrow(draw, flow_path, ORANGE)
        arrow(draw, action_path, TEAL)
        tokens(draw, condition, time, TEAL, start=.05, period=1.1)
        # Identical time bases make the branches activate and pulse together.
        tokens(draw, flow_path, time, ORANGE, start=1.02, period=1.25)
        tokens(draw, action_path, time, TEAL, start=1.02, period=1.25)

        def outputs(layer):
            d = ImageDraw.Draw(layer)
            card(d, (1415, 330, 1824, 565), PALE_ORANGE, ORANGE, width=3)
            label(d, (1619, 351), 'Scene flow', 40, bold=True, anchor='mt')
            tile_grid(d, (1480, 442), 5, 1, ORANGE, PALE_ORANGE, time, cell=43, gap=12)
            card(d, (1415, 595, 1824, 830), PALE_TEAL, TEAL, width=3)
            label(d, (1619, 616), 'Robot actions', 40, bold=True, anchor='mt')
            tile_grid(d, (1480, 707), 5, 1, TEAL, PALE_TEAL, time, cell=43, gap=12)

        reveal(canvas, (time - 1.02) / .3, outputs)
        return canvas

    def frame(self, number):
        time = number / FPS
        if time < 2.9:
            return self.encode_targets(time)
        prediction = self.predict_jointly(time - 2.9)
        if time < 3.18:
            return Image.blend(self.encode_targets(time), prediction,
                               ease((time - 2.9) / .28))
        return prediction


def encoder_args():
    return ['-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-r', str(FPS), '-video_track_timescale', '15360']


def encode_architecture(ffmpeg, output):
    architecture = Architecture()
    command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
               '-r', str(FPS), '-i', '-', *encoder_args(), str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for number in range(ARCHITECTURE_SECONDS * FPS):
            process.stdin.write(architecture.frame(number).tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError('FFmpeg could not encode the architecture segment')
    except BaseException:
        process.stdin.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
        raise


def render(source, output):
    source = source.resolve(strict=True)
    output = output.resolve()
    if source == output:
        raise ValueError('The output must not overwrite the archived source')
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f'The renderer needs the system font: {FONT_PATH}')
    assert sum(duration for _, duration in CUTS) == 40
    assert next(duration for start, duration in CUTS if start is None) == ARCHITECTURE_SECONDS
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='flomo-overview-') as temporary:
        directory = Path(temporary)
        segments = []
        for index, (start, duration) in enumerate(CUTS):
            segment = directory / f'{index:02d}.mp4'
            if start is None:
                encode_architecture(ffmpeg, segment)
            else:
                subprocess.run(
                    [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                     '-ss', str(start), '-i', str(source),
                     '-vf', f'scale={WIDTH}:{HEIGHT}:flags=lanczos,fps={FPS},setpts=PTS-STARTPTS',
                     '-frames:v', str(round(duration * FPS)),
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
        import shutil
        shutil.copyfile(assembled, output)
    print(f'Rendered 40 seconds / 1200 frames to {output}')


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
