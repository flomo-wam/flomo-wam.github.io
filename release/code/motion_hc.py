"""FloMo v3 release: head-camera motion sets from SpatialTrackerV2 tracks.

White-theme 960x720 panes for the release deck: rgb, 2D trails, cumulative
displacement arrows and the training-target raster (scene flow as RGB) for six
robot/human head-cam sets, plus a per-set labelled contact sheet. Loaders and
geometry are reused from video/release/motion.py (v1).
Provenance: extracted training target from SpatialTrackerV2 tracks, not a model prediction.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault('HDF5_USE_FILE_LOCKING', 'FALSE')  # project storage hangs otherwise

import h5py
import numpy as np
from einops import rearrange
from PIL import Image, ImageDraw, ImageFont

DATA = Path('/storage/project/r-agarg35-0/shared/v2r/real_yam')
TRACKS = DATA / 'uniform_4096_reinit_16'
STATS = Path('/storage/home/hcoda1/0/sgovil9/.cache/flomo/track_stats/flow_pct_realyam_034702fde15dc60d.json')
VIEW = 'front_img_1'
WIN = 16
HOLD = 4           # output frames per window frame (single-window sets)
HOLD_SEQ = 2       # output frames per window frame when a set plays consecutive windows
LAST_HOLD = 30     # extra output frames holding the last window frame
FPS = 30
PANE = (960, 720)
TRACK_SPACE = 256
SS = 2             # supersampled drawing, LANCZOS down
STEP = 4
MIN_VIS = 100
WHITE = (255, 255, 255)
INK = (0x1F, 0x27, 0x33)
MUTED = '#5B6675'
LINE = '#DFE4E9'
FONTS = Path(__file__).resolve().parents[1] / 'fonts'
INTER = {w: str(FONTS / f'Inter-{w}.ttf') for w in ('Regular', 'Medium', 'SemiBold', 'Bold')}
# start=None: highest-displacement window (candidates sheet written); start=int: fixed by visual
# phase match so the human/robot pair shows the same segment of the task.
# windows: consecutive training windows played back to back (start fixed), so the
# RGB pane moves through the task while every window stays an honest target.
SETS = [
    {'name': 'robot_oven', 'task': 'croissant_oven', 'demo': 'demo_0', 'start': 540, 'windows': 1,
     'note': 'carry the croissant from the oven tray to the plate (matches human_oven 44)'},
    {'name': 'human_oven', 'task': 'croissant_out_oven_human_aligned', 'demo': 'demo_0', 'start': 44, 'windows': 1,
     'note': 'carry the croissant from the oven tray to the plate (matches robot_oven 540)'},
    {'name': 'robot_oven_seq', 'task': 'croissant_oven', 'demo': 'demo_0', 'start': 496, 'windows': 6,
     'note': 'grasp, lift, carry, place, release (oven_windows.jpg) for the scene-flow triptych'},
    {'name': 'robot_toolbox', 'task': 'screwdriver_toolbox', 'demo': 'demo_0', 'start': None, 'windows': 1, 'note': None},
    {'name': 'human_toolbox', 'task': 'screwdriver_toolbox_human_aligned', 'demo': 'demo_0', 'start': None, 'windows': 1, 'note': None},
    {'name': 'robot_corn', 'task': 'corn_bowl_fixed', 'demo': 'demo_1', 'start': None, 'windows': 1, 'note': None},
    {'name': 'human_corn', 'task': 'corn_bowl_human', 'demo': 'demo_0', 'start': None, 'windows': 1, 'note': None},
]
KINDS = ['rgb', 'tracks', 'arrows', 'flow']
COLOUR_NOTE = ('colour = clip((d-low)/(high-low),0,1)*255 per channel; zero displacement is (128,110,136) by design. '
               'd = cumulative displacement from frame 0 for every kind; flow raster = the model input '
               '(modalities._traj_to_flow_grid, cumulative_disp): 64x64 query grid "(w h) -> h w", bilinear up')
PROVENANCE = 'extracted training target from SpatialTrackerV2 tracks, not a model prediction'


def paths(task, demo):
    return {
        'raw': DATA / 'raw' / task / f'{demo}.hdf5',
        '3d': TRACKS / 'spatialtracker_3d' / task / f'{demo}.hdf5',
        '2d': TRACKS / 'spatialtracker_2d' / task / f'{demo}.hdf5',
        'pose': TRACKS / 'spatialtracker_pose' / task / f'{demo}.hdf5',
    }


def load_stats():
    s = json.loads(STATS.read_text())
    low = np.asarray(s['cum_disp_pct_low'], dtype=np.float32)
    high = np.asarray(s['cum_disp_pct_high'], dtype=np.float32)
    return low, high


def load_raw(pp, start):
    with h5py.File(pp['raw'], 'r') as f:
        raw = np.asarray(f[f'observations/images/{VIEW}'][start:start + WIN])
    assert raw.shape[0] == WIN and raw.ndim == 4 and raw.dtype == np.uint8, raw.shape  # corn_bowl_fixed is 480x640, the rest 240x320
    return raw


def load_tracks(pp, start):
    with h5py.File(pp['3d'], 'r') as f:
        xyz = np.asarray(f[f'root/{VIEW}/3d_tracks'][start], dtype=np.float32)
        vis = np.asarray(f[f'root/{VIEW}/vis'][start], dtype=np.float32)
    with h5py.File(pp['2d'], 'r') as f:
        xy = np.asarray(f[f'root/{VIEW}/tracks'][start], dtype=np.float32)
    assert xyz.shape == (WIN, 4096, 3) and xy.shape == (WIN, 4096, 2) and vis.shape == (WIN, 4096)
    assert np.isfinite(xyz).all() and np.isfinite(xy).all()
    return xyz, xy, vis


def n_windows(pp):
    with h5py.File(pp['3d'], 'r') as f:
        t = f[f'root/{VIEW}/3d_tracks'].shape[0]
    with h5py.File(pp['raw'], 'r') as f:
        assert f[f'observations/images/{VIEW}'].shape[0] == t, 'raw/track length mismatch'
    return t


def scan_window(pp, start):
    xyz, _, vis = load_tracks(pp, start)
    ok = (vis > 0.5).all(axis=0)
    n = int(ok.sum())
    if n < MIN_VIS:
        return {'start': int(start), 'score': None, 'n_vis': n}
    d = np.linalg.norm(xyz[WIN - 1][ok] - xyz[0][ok], axis=1)
    return {'start': int(start), 'score': float(d.mean()), 'n_vis': n}


def scan_demo(task, demo):
    pp = paths(task, demo)
    rows = [scan_window(pp, s) for s in range(0, n_windows(pp) - WIN + 1, STEP)]
    rows = [r for r in rows if r['score'] is not None]
    rows.sort(key=lambda r: -r['score'])
    return rows


def subsample_ids(step):
    grid = rearrange(np.arange(4096), '(w h) -> w h', w=64, h=64)  # queries are a 64x64 grid in (w h) order
    return rearrange(grid[::step, ::step], 'a b -> (a b)')  # step=4: 16x16=256; step=3: 22x22=484


def disp_colors(disp, low, high):
    c = np.clip((disp - low) / (high - low), 0, 1)
    return np.rint(c * 255).astype(np.uint8)  # (...,3); zero disp lands on (128,110,136) by design


def pattern(spec):
    """Output frames as (window, t): 16*4 + 30 = 94 for one window, 16*2 per window + 30 for a sequence."""
    nw = spec['windows']
    hold = HOLD if nw == 1 else HOLD_SEQ
    return [(w, t) for w in range(nw) for t in range(WIN) for _ in range(hold)] + [(nw - 1, WIN - 1)] * LAST_HOLD


def pane(frame):
    return Image.fromarray(frame).resize(PANE, Image.Resampling.LANCZOS)


def draw_arrow(d, a, b, color, shaft, head, halfw, min_len):
    v = b - a
    ln = float(np.hypot(v[0], v[1]))
    if ln < min_len:
        return
    u = v / ln
    perp = np.array([-u[1], u[0]])
    head_len = min(head, 0.45 * ln)  # head never dominates; short arrows stay shaft-first
    if ln - head_len < 6.0:  # a shaft shorter than its stroke reads as a lone arrowhead: draw nothing
        return
    base = b - u * head_len
    col = tuple(int(c) for c in color) + (255,)
    d.line([tuple(a), tuple(base)], fill=col, width=shaft)
    d.polygon([tuple(b), tuple(base + perp * 0.5 * head_len), tuple(base - perp * 0.5 * head_len)], fill=col)


def build_frames(raw, xy, vis, cols, ts):
    """Frame arrays for the window indices ts, per kind."""
    pts4 = subsample_ids(4)  # tracks: every 4th query (16x16)
    pts3 = subsample_ids(3)  # arrows: every 3rd query (22x22)
    scale = np.asarray([PANE[0] * SS / TRACK_SPACE, PANE[1] * SS / TRACK_SPACE], dtype=np.float64)
    vis_and = np.logical_and.accumulate(vis > 0.5, axis=0)  # visible in all frames up to t
    vis_pt = vis > 0.5
    rgb, tracks, arrows, flow = {}, {}, {}, {}

    for t in ts:
        rgb[t] = np.asarray(pane(raw[t]))

    for t in ts:
        img = Image.fromarray(raw[t]).resize((PANE[0] * SS, PANE[1] * SS), Image.Resampling.LANCZOS).convert('RGBA')
        d = ImageDraw.Draw(img)
        for n in pts4:
            if not vis_and[t, n]:
                continue
            traj = xy[:t + 1, n] * scale  # (t+1,2) at 2x
            c = tuple(int(v) for v in cols[t, n]) + (255,)
            d.line([tuple(p) for p in traj], fill=c, width=3 * SS, joint='curve')  # 3 px at 960
            x, y = traj[-1]
            r = 4.0 * SS  # 4 px dot at 960 with a 1 px white outline
            d.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=WHITE + (255,), width=SS)
        tracks[t] = np.asarray(img.convert('RGB').resize(PANE, Image.Resampling.LANCZOS))

    for t in ts:
        ov = Image.new('RGBA', (PANE[0] * SS, PANE[1] * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for n in pts3:
            if not (vis_pt[0, n] and vis_pt[t, n]):
                continue
            draw_arrow(d, xy[0, n] * scale, xy[t, n] * scale, cols[t, n],
                       shaft=3 * SS, head=10 * SS, halfw=5 * SS, min_len=8 * SS)  # 3/10/8 px at 960
        base = Image.fromarray(rgb[t]).convert('RGBA')
        base.alpha_composite(ov.resize(PANE, Image.Resampling.LANCZOS))
        arrows[t] = np.asarray(base.convert('RGB'))

    for t in ts:  # training target: query grid (w h) -> image (h w), not re-anchored
        grid = rearrange(cols[t], '(w h) d -> h w d', w=64, h=64)
        flow[t] = np.asarray(Image.fromarray(grid).resize(PANE, Image.Resampling.BILINEAR))

    return {'rgb': rgb, 'tracks': tracks, 'arrows': arrows, 'flow': flow}


def encode(frames, path, ffmpeg):
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
           '-video_size', f'{PANE[0]}x{PANE[1]}', '-framerate', str(FPS), '-i', 'pipe:0', '-an',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-threads', '2', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = 0
    for fr in frames:
        assert fr.shape == (PANE[1], PANE[0], 3) and fr.dtype == np.uint8, (path, fr.shape)
        proc.stdin.write(fr.tobytes())
        n += 1
    proc.stdin.close()
    code = proc.wait()
    assert code == 0 and path.exists() and path.stat().st_size > 0, f'ffmpeg failed: {path}'
    print(f'wrote {path} ({n} frames)', flush=True)
    return n


def write_candidates(rows, out_path, spec, pp):
    cell_w, cell_h, bar = 384, 288, 30
    im = Image.new('RGB', (6 * cell_w, 2 * (cell_h + bar)), '#FFFFFF')
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(INTER['Medium'], 17)
    cache = {}

    def frame(idx):
        if idx not in cache:
            with h5py.File(pp['raw'], 'r') as f:
                cache[idx] = np.asarray(f[f'observations/images/{VIEW}'][idx])
        return cache[idx]

    for i, r in enumerate(rows[:12]):
        x, y = (i % 6) * cell_w, (i // 6) * (cell_h + bar)
        im.paste(Image.fromarray(frame(r['start'] + WIN - 1)).resize((cell_w, cell_h), Image.Resampling.LANCZOS), (x, y + bar))
        d.text((x + 6, y + 6), f"{spec['task']}/{spec['demo']} start={r['start']} score={r['score']:.4f} vis={r['n_vis']}", font=font, fill='#1F2733')
        d.rectangle((x, y, x + cell_w - 1, y + bar - 1), outline=LINE)
    im.save(out_path, quality=92)
    print(f'wrote {out_path}', flush=True)


def render_set(job):
    """One set: scan (unless start fixed), render 4 clips + stills, return a manifest fragment + sheet cells."""
    spec, seq = job['spec'], job['seq']
    out = Path(job['out'])
    pp = paths(spec['task'], spec['demo'])
    if job['start'] is None:
        rows = scan_demo(spec['task'], spec['demo'])
        assert rows, f'no valid windows (MIN_VIS={MIN_VIS}) in {spec["task"]}/{spec["demo"]}'
        chosen = rows[0]  # scan_demo already bounds start so start+WIN-1 stays inside the demo
        start, score, n_vis = chosen['start'], chosen['score'], chosen['n_vis']
        write_candidates(rows, out / f"candidates_{spec['name']}.jpg", spec, pp)
    else:
        start = job['start']
        rs = [scan_window(pp, start + w * WIN) for w in range(spec['windows'])]
        assert all(r['score'] is not None for r in rs), \
            f'{spec["name"]}: a window from {start} of {spec["task"]}/{spec["demo"]} has < {MIN_VIS} persistent tracks'
        score, n_vis, rows = rs[0]['score'], rs[0]['n_vis'], None
    frames = {k: {} for k in KINDS}
    for w in range(spec['windows']):
        s0 = start + w * WIN
        raw = load_raw(pp, s0)
        xyz, xy, vis = load_tracks(pp, s0)
        disp = xyz - xyz[:1]  # (16,4096,3), displacement in the window's first camera frame
        cols = disp_colors(disp, job['low'], job['high'])
        ts = sorted({t for ww, t in seq if ww == w})
        fw = build_frames(raw, xy, vis, cols, ts)
        for k in KINDS:
            frames[k].update({(w, t): fw[k][t] for t in ts})
    counts = {}
    for kind in KINDS:
        counts[kind] = encode((frames[kind][wt] for wt in seq), out / f"{spec['name']}_{kind}.mp4", job['ffmpeg'])
    last = seq[-1]
    Image.fromarray(frames['rgb'][seq[0]]).save(out / f"{spec['name']}_still.png")
    Image.fromarray(frames['flow'][last]).save(out / f"{spec['name']}_flow_last.png")
    Image.fromarray(frames['tracks'][last]).save(out / f"{spec['name']}_tracks_last.png")
    print(f"set {spec['name']} start={start} score={score:.4f} vis={n_vis} done", flush=True)
    cells = {k: np.asarray(Image.fromarray(frames[k][last]).resize((480, 360), Image.Resampling.LANCZOS)) for k in KINDS}
    return {'name': spec['name'], 'task': spec['task'], 'demo': spec['demo'],
            'hdf5': {'raw': str(pp['raw']), '3d': str(pp['3d']), '2d': str(pp['2d'])},
            'raw_shape': [int(x) for x in load_raw_shape(pp)],
            'start': int(start), 'windows': spec['windows'], 'score': float(score), 'n_vis': int(n_vis),
            'scores': rows, 'counts': counts, 'cells': cells, 'note': spec['note']}


def load_raw_shape(pp):
    with h5py.File(pp['raw'], 'r') as f:
        return f[f'observations/images/{VIEW}'].shape


def sheet_grid(frags, path):
    """One row per set, columns rgb/tracks/arrows/flow at the window's last frame."""
    gutter, header, cw, ch = 270, 44, 480, 360
    im = Image.new('RGB', (gutter + len(KINDS) * cw, header + len(frags) * ch), '#FFFFFF')
    d = ImageDraw.Draw(im)
    f_head = ImageFont.truetype(INTER['SemiBold'], 24)
    f_name = ImageFont.truetype(INTER['SemiBold'], 22)
    f_sub = ImageFont.truetype(INTER['Medium'], 15)
    for c, kind in enumerate(KINDS):
        w = d.textlength(kind, font=f_head)
        d.text((gutter + c * cw + (cw - w) / 2, 10), kind, font=f_head, fill='#1F2733')
    for r, fr in enumerate(frags):
        y = header + r * ch
        d.text((16, y + 44), fr['name'], font=f_name, fill='#1F2733')
        d.text((16, y + 80), f"{fr['task']}/{fr['demo']}", font=f_sub, fill=MUTED)
        d.text((16, y + 102), f"start={fr['start']}  score={fr['score']:.4f}", font=f_sub, fill=MUTED)
        d.text((16, y + 124), f"vis={fr['n_vis']}", font=f_sub, fill=MUTED)
        for c, kind in enumerate(KINDS):
            x = gutter + c * cw
            im.paste(Image.fromarray(fr['cells'][kind]), (x, y))
            d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=LINE)
    im.save(path, quality=92)
    print(f'wrote {path}', flush=True)


def hold_dict():
    return {'window_frames': WIN, 'hold_per_frame': HOLD, 'hold_per_frame_seq': HOLD_SEQ, 'last_frame_hold': LAST_HOLD}


def entry_of(fr, out):
    entry = {
        'task': fr['task'], 'demo': fr['demo'], 'hdf5': fr['hdf5'],
        'raw_shape': fr['raw_shape'], 'chosen_start': fr['start'], 'windows': fr['windows'],
        'score': fr['score'], 'n_vis': fr['n_vis'],
        'hold_pattern': hold_dict(), 'clip_frames': fr['counts'],
        'clips': {k: str(out / f"{fr['name']}_{k}.mp4") for k in KINDS},
        'still': str(out / f"{fr['name']}_still.png"),
        'flow_last': str(out / f"{fr['name']}_flow_last.png"),
        'tracks_last': str(out / f"{fr['name']}_tracks_last.png"),
        'window_scores': fr['scores'],
    }
    if fr['scores'] is not None:
        entry['candidates_sheet'] = str(out / f"candidates_{fr['name']}.jpg")
    if fr['note']:
        entry['note'] = fr['note']
    return entry


def full(args):
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    low, high = load_stats()
    jobs, skipped = [], []
    for spec in [s for s in SETS if s['name'] in args.sets] if args.sets else SETS:
        pp = paths(spec['task'], spec['demo'])
        missing = [k for k in ('raw', '3d', '2d') if not Path(pp[k]).exists()]
        if missing:
            skipped.append({'name': spec['name'], 'task': spec['task'], 'demo': spec['demo'],
                            'skipped': f'missing hdf5: {missing}', 'hdf5': {k: str(pp[k]) for k in ('raw', '3d', '2d')}})
            print(f"SKIP {spec['name']}: missing {missing}", flush=True)
            continue
        jobs.append({'spec': spec, 'start': spec['start'], 'seq': pattern(spec), 'out': str(out),
                     'ffmpeg': args.ffmpeg, 'low': low, 'high': high})
    with Pool(min(args.workers, len(jobs))) as pool:
        frags = pool.map(render_set, jobs)
    if args.sets:  # targeted re-render: replace those entries in the existing manifest, keep the sheet
        manifest = json.loads((out / 'manifest.json').read_text())
        for fr in frags:
            manifest['sets'][fr['name']] = entry_of(fr, out)
        cm = manifest['colour_map']
        cm.pop('vel_smooth')
        cm['note'] = COLOUR_NOTE
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        print(f'updated {out / "manifest.json"} for {args.sets} ({time.time() - t0:.0f} s)', flush=True)
        return
    sheet_grid(frags, out / 'sheet.jpg')
    sets = {fr['name']: entry_of(fr, out) for fr in frags}
    for s in skipped:
        sets[s['name']] = s
    manifest = {
        'provenance': PROVENANCE,
        'fps': FPS,
        'canvas': list(PANE),
        'encode': 'H.264 libx264 CRF 16 yuv420p +faststart, 30 fps',
        'scan': {'step': STEP, 'min_vis': MIN_VIS, 'rule': 'highest-score window whose last frame stays inside the demo'},
        'hold_pattern': hold_dict(),
        'colour_map': {'stats_path': str(STATS), 'cum_disp_pct_low': [float(x) for x in low],
                       'cum_disp_pct_high': [float(x) for x in high],
                       'note': COLOUR_NOTE},
        'sheet_jpg': str(out / 'sheet.jpg'),
        'sets': sets,
        'slurm_job_id': os.environ.get('SLURM_JOB_ID', ''),
        'elapsed_s': round(time.time() - t0, 1),
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'wrote {out / "manifest.json"} ({time.time() - t0:.0f} s total)', flush=True)
    print(json.dumps({n: e.get('clips') for n, e in sets.items()}), flush=True)


def smoke(args):
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    low, high = load_stats()
    spec = SETS[0]  # robot_oven, fixed start
    job = {'spec': spec, 'start': spec['start'], 'seq': [(0, 0), (0, WIN - 1)], 'out': str(out),
           'ffmpeg': args.ffmpeg, 'low': low, 'high': high}
    frag = render_set(job)
    dt = time.time() - t0
    print(f'smoke ok in {dt:.1f} s (limit 30 s): {json.dumps(frag["counts"])}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ffmpeg', required=True)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--smoke', action='store_true', help='render robot_oven (SETS[0]) at its fixed start, 2 frames per clip only')
    ap.add_argument('--sets', nargs='+', help='re-render only these sets and patch their manifest entries')
    args = ap.parse_args()
    smoke(args) if args.smoke else full(args)


if __name__ == '__main__':
    main()
