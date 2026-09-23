#!/usr/bin/env python
"""FloMo release v3: footage trims + figure renders.

Stages:
  footage  -- scrub strips, clip trims, sheet, manifest (run under Slurm)
  figures  -- PDF/PNG renders, wordmark, arch box annotations (login node, light)

Outputs land in MEDIA (/storage/project/.../flomo_release_work/v3/media).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = HERE + '/media'
FOOT = MEDIA + '/footage'
FIGS = MEDIA + '/figures'
SITE = os.path.dirname(HERE) + '/static/videos'  # this website repo
ROLL = '/storage/project/r-agarg35-0/sgovil9/flomo_release_tracks/rollouts'
REPO = '/storage/project/r-agarg35-0/sgovil9/AMPLIFYv2'
FFMPEG = ('/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/lib/python3.10/'
          'site-packages/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2')
FFPROBE = ('/usr/local/pace-apps/spack/packages/linux-rhel9-x86_64_v3/gcc-12.3.0/'
           'ffmpeg-7.1-jm6ru4wgcqsptdq2ihjgsowowk3rq5az/bin/ffprobe')
FONTS = HERE + '/fonts'

ENC = ['-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
       '-movflags', '+faststart', '-an', '-colorspace', 'bt709',
       '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', '30']

SOURCES = {
    'oven': SITE + '/ma10h_oven_success.mp4',
    'toolbox': SITE + '/ma10h_toolbox_success.mp4',
    'corn': SITE + '/ma10h_corn_success.mp4',
    'cabinet': SITE + '/option-compare/door_landscape.mp4',
    # HLG website clips: the SDR intermediates are Chrome's own rendering of the site
    # mp4 (hlg_capture.py), so the release matches the website look frame for frame.
    'yoyo': MEDIA + '/src/yoyo_sdr.mp4',
    'highlighter': MEDIA + '/src/highlighter_sdr.mp4',
    'dreamzero': SITE + '/dreamzero_yoyo_failure.mp4',
    'oven_hc': ROLL + '/flomo_20260919_201408_1/front_img_1.mp4',
    'toolbox_hc': ROLL + '/flomo_20260919_202449_1/front_img_1.mp4',
}
SCRUB_N = 12
# The site's own FloMo string clip (string.mp4, 3x, burned-in label) is the look the
# HLG captures must match: per-channel levels fitted on static regions of it vs the
# capture (site_levels).  Regions are [x0, y0, x1, y1] at 1920x1080.
SITE_LOOK = {'yoyo', 'highlighter'}
LOOK_REF = dict(site=(SITE + '/string.mp4', 2.0), cap=(SOURCES['yoyo'], 0.5))
LOOK_REGIONS = dict(
    site=dict(table=[(100, 560, 900, 680), (1200, 560, 1900, 680)], black=[(400, 435, 680, 475)],
              pole=[(978, 120, 994, 440)], toy=[(1480, 700, 1550, 745)]),
    cap=dict(table=[(100, 660, 900, 780), (1200, 640, 1900, 760)], black=[(440, 550, 720, 590)],
             pole=[(998, 120, 1014, 520)], toy=[(1525, 790, 1595, 835)]))

# Segments picked by scrubbing (in_s/out_s = source seconds; speed = playback rate).
# crop = (x, y, w, h) in source pixels.
# Speed-ups stay <= 2.5x and blend round(speed) source frames per output frame
# (tmix): plain decimation of a 30 fps source reads as choppy.  720p is plenty
# for the 560 px panes and keeps three simultaneous deck videos light.
CLIPS = [
    dict(name='id_oven', src='oven', in_s=7.0, out_s=36.6, speed=2.5,
         size=(1280, 720)),
    dict(name='id_toolbox', src='toolbox', in_s=39.0, out_s=69.0, speed=2.5,
         size=(1280, 720)),
    dict(name='id_corn', src='corn', in_s=5.0, out_s=11.4, speed=1.0,
         size=(1280, 720)),
    dict(name='id_oven_headcam', src='oven_hc', in_s=43.0, out_s=60.0, speed=2.0,
         size=(960, 720)),
    dict(name='id_toolbox_headcam', src='toolbox_hc', in_s=36.5, out_s=54.0,
         speed=2.0, size=(960, 720)),
    dict(name='ood_cabinet', src='cabinet', in_s=1.4, out_s=11.4, speed=1.0,
         size=(1280, 720)),
    dict(name='ood_string', src='yoyo', in_s=5.8, out_s=14.9, speed=1.0,
         size=(1280, 720)),
    dict(name='ood_highlighter', src='highlighter', in_s=2.0, out_s=8.5,
         speed=1.0, size=(1280, 720)),
    # string pair: cameras differ by ~1.39x zoom and a small offset, so crops
    # differ in size to match apparent scale; ball lands at output (1027, 500)
    # in both.  FloMo (string_src_tail.jpg): gripper reaches the toy 6.8 s, works
    # the string until 11.3 s, pulls it up 11.6-13.4 s (highest 12.5-13.0 s),
    # backs off 13.9 s; source ends 14.97 s.  DreamZero source is 7.87 s long.
    dict(name='string_flomo', src='yoyo', in_s=5.8, out_s=14.9, speed=1.0,
         size=(1280, 720), crop=(142, 80, 1778, 1000)),
    dict(name='string_dreamzero', src='dreamzero', in_s=0.0, out_s=7.8,
         speed=1.0, size=(1280, 720), crop=(372, 219, 1280, 720)),
]


def run(cmd):
    p = subprocess.run(cmd)
    if p.returncode:
        sys.exit('FAILED: ' + ' '.join(cmd))


def out_of(text):
    p = subprocess.run(text, capture_output=True, text=True)
    if p.returncode:
        sys.exit('FAILED: ' + ' '.join(text) + '\n' + p.stderr)
    return p.stdout


def probe(path):
    j = json.loads(out_of([FFPROBE, '-v', 'error', '-select_streams', 'v:0',
                           '-show_entries',
                           'stream=width,height,r_frame_rate,nb_frames',
                           '-of', 'json', path]))
    s = j['streams'][0]
    num, den = s['r_frame_rate'].split('/')
    return dict(width=s['width'], height=s['height'],
                fps=round(int(num) / int(den), 5), frames=int(s['nb_frames']))


def dec_frames(src):
    # frames that actually decode (container nb_frames can be stale)
    p = subprocess.run(
        [FFMPEG, '-v', 'info', '-i', src, '-map', '0:v', '-f', 'null', '-'],
        capture_output=True, text=True)
    if p.returncode:
        sys.exit('decode count failed: ' + src)
    hits = [ln for ln in p.stderr.replace('\r', '\n').splitlines()
            if ln.startswith('frame=')]
    if not hits:
        sys.exit('no progress lines for ' + src)
    m = re.search(r'frame=\s*(\d+)', hits[-1])
    if not m:
        sys.exit('cannot parse progress for ' + src)
    return int(m.group(1))


def grab(src, t):
    png = f'/tmp/look_{os.path.basename(src)}_{t}.png'
    run([FFMPEG, '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', png])
    return np.asarray(Image.open(png).convert('RGB')).astype(np.float64)


def site_levels():
    """Per-channel affine (colorlevels) taking the Chrome capture to the site look:
    least squares on the region means of LOOK_REGIONS; residual must stay < 4/255."""
    means = {}
    for k, (src, t) in LOOK_REF.items():
        img = grab(src, t)
        means[k] = np.stack([np.concatenate([img[y0:y1, x0:x1].reshape(-1, 3)
                                             for x0, y0, x1, y1 in rects]).mean(0)
                             for rects in LOOK_REGIONS[k].values()])
    parts, fit = [], {}
    for ch, name in enumerate('rgb'):
        A = np.stack([means['cap'][:, ch], np.ones(len(means['cap']))], 1)
        a, b = np.linalg.lstsq(A, means['site'][:, ch], rcond=None)[0]
        res = np.abs(A @ (a, b) - means['site'][:, ch]).max()
        if res > 4:
            sys.exit(f'site look fit: channel {name} residual {res:.1f}/255 > 4')
        parts.append(f'{name}imin={-b / a / 255:.4f}:{name}imax={(255 - b) / a / 255:.4f}')
        fit[name] = dict(gain=round(float(a), 4), offset=round(float(b), 2), max_residual=round(float(res), 2))
    print('[look] colorlevels ' + ':'.join(parts) + ' ' + json.dumps(fit))
    return 'colorlevels=' + ':'.join(parts), fit


def clip_vf(c, levels):
    src = SOURCES[c['src']]
    info = probe(src)
    f = [levels] if c['src'] in SITE_LOOK else []
    if 'crop' in c:
        x, y, w, h = c['crop']
        if x + w > info['width'] or y + h > info['height']:
            sys.exit(f"crop {c['crop']} exceeds source {info['width']}x{info['height']}")
        f.append(f'crop={w}:{h}:{x}:{y}')
    w, h = c['size']
    f.append(f'scale={w}:{h}:flags=lanczos')
    if c['speed'] != 1.0:
        f.append(f"tmix=frames={round(c['speed'])}")
        f.append(f"setpts=PTS/{c['speed']}")
    f += ['fps=30', 'format=yuv420p']
    return ','.join(f), info


def encode(c, levels):
    n = round((c['out_s'] - c['in_s']) * 30 / c['speed'])
    vf, _ = clip_vf(c, levels)
    dst = f'{FOOT}/{c["name"]}.mp4'
    run([FFMPEG, '-v', 'error', '-y', '-ss', f'{c["in_s"]:.3f}', '-i',
         SOURCES[c['src']], '-vf', vf, '-frames:v', str(n)] + ENC + [dst])
    print(f"[clip] {c['name']}: {c['in_s']}-{c['out_s']}s x{c['speed']} -> {n} frames")
    return dst


def scrub_strips():
    os.makedirs(FOOT, exist_ok=True)
    for name, src in SOURCES.items():
        info = probe(src)
        n_dec = dec_frames(src)
        dur = n_dec / info['fps']
        thumbs = []
        for k in range(SCRUB_N):
            t = (k + 0.5) / SCRUB_N * dur
            png = f'/tmp/scrub_{name}_{k:02d}.png'
            run([FFMPEG, '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src,
                 '-frames:v', '1', png])
            thumbs.append((t, png))
        tw = 470
        th0 = Image.open(thumbs[0][1])
        th = round(tw * th0.height / th0.width)
        pad, lab = 4, 30
        cols, rows = 4, 3
        sheet = Image.new('RGB', (cols * (tw + 2 * pad), rows * (th + lab + 2 * pad)),
                          (24, 26, 31))
        d = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(FONTS + '/Inter-Medium.ttf', 22)
        for k, (t, png) in enumerate(thumbs):
            cx, cy = k % cols, k // cols
            x = cx * (tw + 2 * pad) + pad
            y = cy * (th + lab + 2 * pad) + pad
            sheet.paste(Image.open(png).resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x + 4, y + th + 4), f't={t:6.2f}s', fill=(240, 240, 240),
                   font=font)
        sheet.save(f'{FOOT}/scrub_{name}.jpg', quality=88)
        print(f'[scrub] {name}: {n_dec} dec frames, {dur:.2f}s -> '
              f'scrub_{name}.jpg')


def sheet_and_manifest(clips_meta):
    font = ImageFont.truetype(FONTS + '/Inter-SemiBold.ttf', 22)
    tw, lab, pad = 512, 30, 4
    rows = []
    for c in clips_meta:
        w, h = c['width'], c['height']
        th = round(tw * h / w)
        dur = (c['out_s'] - c['in_s']) / c['speed']
        imgs = []
        for frac in (0.0, 0.5, 0.999):
            t = min(dur - 0.05, dur * frac)  # last frame pts = dur - 1/30
            png = f'/tmp/sheet_{c["name"]}_{frac}.png'
            run([FFMPEG, '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i',
                 f'{FOOT}/{c["name"]}.mp4', '-frames:v', '1', png])
            imgs.append((t, png, th))
        rows.append((c, imgs, th))
    H = sum(max(im[2] for im in r[1]) + lab + 2 * pad for r in rows) + pad
    sheet = Image.new('RGB', (3 * (tw + 2 * pad) + pad, H), (24, 26, 31))
    d = ImageDraw.Draw(sheet)
    y = pad
    for c, imgs, th in rows:
        for k, (t, png, _) in enumerate(imgs):
            x = k * (tw + 2 * pad) + pad
            sheet.paste(Image.open(png).resize((tw, th), Image.LANCZOS), (x, y))
        tag = ('first / mid / last  |  '
               f"{c['in_s']}-{c['out_s']}s x{c['speed']}")
        d.text((pad + 4, y + th + 4), f"{c['name']}   {tag}",
               fill=(245, 245, 245), font=font)
        y += th + lab + 2 * pad
    sheet.save(f'{FOOT}/sheet.jpg', quality=90)
    print('[sheet] ' + f'{FOOT}/sheet.jpg')
    json.dump(dict(
        sources={k: dict(path=v, **probe(v), scrub=f'{FOOT}/scrub_{k}.jpg',
                         decodable_frames=dec_frames(v))
                 for k, v in SOURCES.items()},
        clips=clips_meta), open(f'{FOOT}/manifest.json', 'w'), indent=2)
    print('[manifest] ' + f'{FOOT}/manifest.json')


def stage_footage(scrub_only, only):
    if not only:
        scrub_strips()
    if scrub_only:
        print('[scrub-only] stopping before encodes')
        return
    levels, fit = site_levels()
    metas = []
    for c in CLIPS:
        dst = encode(c, levels) if not only or c['name'] in only else f'{FOOT}/{c["name"]}.mp4'
        info = probe(dst)
        metas.append(dict(
            name=c['name'], source=SOURCES[c['src']],
            in_s=c['in_s'], out_s=c['out_s'], speed=c['speed'],
            crop=c['crop'] if 'crop' in c else None,
            site_look=fit if c['src'] in SITE_LOOK else None, output=dst, **info))
    sheet_and_manifest(metas)


# ---------------- figures ----------------

FIG_PDFS = [
    ('fig_id.png', REPO + '/paper/figures/figure_policy_indist.pdf'),
    ('fig_scaling.png', REPO + '/paper/figures/figure_id_scaling.pdf'),
    ('fig_robotwin_scaling.png', REPO + '/figures/paper_figures/robotwin_id_combined.pdf'),
]
FIG_COPIES = [
    ('fig_attention.png', REPO + '/paper/figures/figure_attention_share.png'),
    ('fig_arch.png', REPO + '/paper/figures/figure_arch.png'),
]

# the deck's spotlight headline replaces the figure's own "Flow Tokenization" label
ARCH_LABEL = (944, 10, 1140, 46)
# pixel boxes [x0,y0,x1,y1] in fig_arch.png (1603x720); verified via
# arch_boxes_check.png.  band_*/tok_q* are the spotlight reveal regions: they tile
# each half so every connector and token row appears with its step (deck.py checks).
ARCH_BOXES = {
    # the four inputs include their column headers (Text / Action / Image / 3D Scene Flow)
    'text_input': [12, 12, 252, 133],
    'text_encoder': [15, 149, 250, 234],
    'action_input': [306, 12, 510, 101],
    'action_encoder': [327, 148, 489, 237],
    'image_input': [553, 12, 648, 143],
    'flow_input': [690, 12, 870, 143],
    'video_encoder': [531, 148, 853, 241],
    'backbone': [249, 268, 855, 446],  # DiT block plus its input and output token rows
    'action_decoder': [327, 456, 489, 543],
    'video_decoder': [523, 452, 851, 543],
    'action_out': [306, 587, 510, 634],
    'motion_out': [603, 573, 776, 665],
    'label_action_out': [322, 674, 500, 706],
    'label_motion_out': [594, 674, 778, 706],
    'cross_attn': [80, 306, 244, 402],
    'tok_frames': [938, 34, 1228, 366],
    'tok_flow3d': [1289, 38, 1583, 366],
    'tok_cube': [1300, 430, 1575, 706],
    'tok_flowrgb': [938, 373, 1228, 705],
    'left_half': [0, 0, 941, 720],
    'right_half': [943, 0, 1603, 720],
    'band_inputs': [0, 0, 941, 146],
    'band_encoders': [0, 146, 941, 262],
    'band_backbone': [0, 262, 941, 452],
    'band_outputs': [0, 452, 941, 720],
    'tok_q1': [943, 0, 1230, 370],
    'tok_q2': [1230, 0, 1603, 370],
    'tok_q3': [1300, 366, 1603, 720],
    'tok_q4': [943, 370, 1300, 720],
}


def trim(img, margin, alpha=False):
    a = np.asarray(img)
    if alpha:
        mask = a[..., 3] > 0
    else:
        mask = (a[..., :3] < 250).any(axis=2)
    ys, xs = np.where(mask)
    if not len(xs):
        sys.exit('trim: empty content')
    x0 = max(0, int(xs.min()) - margin)
    y0 = max(0, int(ys.min()) - margin)
    x1 = min(a.shape[1], int(xs.max()) + 1 + margin)
    y1 = min(a.shape[0], int(ys.max()) + 1 + margin)
    return img.crop((x0, y0, x1, y1))


def stage_figures():
    os.makedirs(FIGS, exist_ok=True)
    man = []
    for name, src in FIG_PDFS:
        run(['pdftoppm', '-png', '-r', '600', '-singlefile', src, '/tmp/figrender'])
        img = trim(Image.open('/tmp/figrender.png'), 24)
        img.save(f'{FIGS}/{name}')
        man.append(dict(name=name, source=src, dpi=600,
                        size=list(img.size)))
        print(f'[fig] {name}: {img.size}')
    for name, src in FIG_COPIES:
        shutil.copyfile(src, f'{FIGS}/{name}')
        man.append(dict(name=name, source=src, dpi='native',
                        size=list(Image.open(src).size)))
        print(f'[fig] {name}: copy')
    arch = Image.open(f'{FIGS}/fig_arch.png').convert('RGB')
    ImageDraw.Draw(arch).rectangle(ARCH_LABEL, fill=(255, 255, 255))
    arch.save(f'{FIGS}/fig_arch.png')
    # RoboTwin panel (a) of the paper's Fig. 3 (tasks on x, success rate on y); the
    # divider is the darkest near-full-height column in the middle third
    both = Image.open(f'{FIGS}/fig_robotwin_scaling.png').convert('RGB')
    col = (np.asarray(both).astype(int) < 128).all(axis=2).sum(axis=0)
    lo, hi = both.width // 3, 2 * both.width // 3
    div = lo + int(np.argmax(col[lo:hi]))
    if col[div] < 0.8 * both.height:
        sys.exit(f'robotwin divider not found (best column {div} covers {col[div]}/{both.height} rows)')
    panel_a = trim(both.crop((0, 0, div - 8, both.height)), 24)
    panel_a.save(f'{FIGS}/fig_robotwin.png')
    man.append(dict(name='fig_robotwin.png', source=dict(FIG_PDFS)['fig_robotwin_scaling.png'],
                    note=f'panel (a) of fig_robotwin_scaling.png, left of the divider at x={div}',
                    size=list(panel_a.size)))
    print(f'[fig] fig_robotwin.png: {panel_a.size} (divider {div})')
    # wordmark ~1600 px wide, transparent
    logo = REPO + '/paper/logo/flomo_logo.pdf'
    run(['pdftocairo', '-png', '-transp', '-r', '300', '-singlefile', logo,
         '/tmp/wm0'])
    w0 = Image.open('/tmp/wm0.png').width
    dpi = round(300 * 1600 / w0)
    run(['pdftocairo', '-png', '-transp', '-r', str(dpi), '-singlefile', logo,
         '/tmp/wm1'])
    wm = trim(Image.open('/tmp/wm1.png'), 0, alpha=True)
    wm.save(f'{FIGS}/wordmark.png')
    man.append(dict(name='wordmark.png', source=logo, dpi=dpi,
                    size=list(wm.size)))
    print(f'[fig] wordmark.png: {wm.size} (dpi {dpi})')
    # arch boxes + check overlay
    arch = Image.open(f'{FIGS}/fig_arch.png').convert('RGB')
    ov = Image.new('RGBA', arch.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    font = ImageFont.truetype(FONTS + '/Inter-SemiBold.ttf', 20)
    # halves first (their full-frame fills replace overlay px), then components
    names = [n for n in ARCH_BOXES if n in ('left_half', 'right_half')] + \
            [n for n in ARCH_BOXES if n not in ('left_half', 'right_half')]
    for i, name in enumerate(names):
        col = [(228, 60, 40), (30, 120, 190), (40, 150, 60), (200, 120, 20),
               (150, 60, 180)][i % 5]
        soft = (255, 255, 255, 60) if name in ('left_half', 'right_half') \
            else col + (36,)
        box = ARCH_BOXES[name]
        d.rectangle(box, outline=col + (255,), width=3, fill=soft)
        d.text((box[0] + 6, box[1] + 4), name, fill=col + (255,), font=font)
    Image.alpha_composite(arch.convert('RGBA'), ov).convert('RGB').save(
        f'{FIGS}/arch_boxes_check.png')
    json.dump(ARCH_BOXES, open(f'{FIGS}/arch_boxes.json', 'w'), indent=2)
    man.append(dict(name='arch_boxes.json', source=FIG_COPIES[1][1],
                    note='pixel boxes [x0,y0,x1,y1] in fig_arch.png; '
                         'verified in arch_boxes_check.png',
                    check=f'{FIGS}/arch_boxes_check.png',
                    n_boxes=len(ARCH_BOXES)))
    json.dump(man, open(f'{FIGS}/manifest.json', 'w'), indent=2)
    print('[manifest] ' + f'{FIGS}/manifest.json')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', choices=['footage', 'figures'], required=True)
    ap.add_argument('--scrub-only', action='store_true',
                    help='footage stage: write scrub strips, skip encodes')
    ap.add_argument('--only', nargs='+', help='footage stage: re-encode these clips only (no scrubs); sheet + manifest cover all')
    a = ap.parse_args()
    if a.stage == 'footage':
        stage_footage(a.scrub_only, a.only)
    else:
        stage_figures()


if __name__ == '__main__':
    main()
