"""v2 render pipeline: per-beat PNG sequences (multiprocessing) -> per-beat mp4
(static imageio ffmpeg) -> concat master + review stills + frame audit.

Motion overlays come from the HD tracks (`--motion trails|dense`, see motion_hd.py).
Renders on cpu-small via release_v2.sbatch; login node only for tiny previews.
"""
import argparse
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path("/storage/project/r-agarg35-0/sgovil9/AMPLIFYv2")
V2 = Path("/storage/project/r-agarg35-0/sgovil9/flomo_release_work/v2")  # scratch1 stat/read is flaky (2026-09-22)
FRAMES = V2 / "frames"
BEAT_DIR = V2 / "beats"
WORK = V2 / "work"
OUT = REPO / "video" / "release" / "v2" / "out"
REVIEW = OUT / "review"
FFMPEG = ("/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/lib/python3.10/"
          "site-packages/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2")  # module ffmpeg 7.1 lacks libx264
FFPROBE = shutil.which("ffprobe") or ("/usr/local/pace-apps/spack/packages/"
                                      "linux-rhel9-x86_64_v3/gcc-12.3.0/ffmpeg-7.1-jm6ru4wgcqsptdq2ihjgsowowk3rq5az/bin/ffprobe")
FPS = 30

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

CTX = None  # per-process compositor context


def run(cmd, log=None):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise ValueError(f"cmd failed ({r.returncode}): {' '.join(map(str, cmd))}\n"
                         f"stderr: {r.stderr[-2000:]}")
    if log:
        Path(log).write_text(r.stderr)
    return r.stderr


class ClipReader:
    """Sequential rawvideo decoder with forward-only reads; reopens on rewind
    (loops). Frame-exact via input seek half a frame before the target. Handles
    portrait (rotation metadata) and HLG sources (auto tone-map per the design
    system's Footage row)."""

    HLG_VF = ("zscale=t=linear:npl=1000,format=gbrpf32le,zscale=p=bt709,"
              "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

    def __init__(self, path):
        self.path = str(path)
        self.proc = None
        self.pos = 0
        self.hlg = probe_color_transfer(self.path) == "arib-std-b67"
        w, h = probe_size(self.path)
        if probe_rotation(self.path) % 360 in (90, 270, -90, -270):
            w, h = h, w  # ffmpeg autorotates before the filter chain
        self.size = (w, h)
        self.raw = w * h * 3

    def _open(self, idx):
        if self.proc:
            self.proc.stdout.close()
            self.proc.terminate()
            self.proc.wait()
        seek = max((idx - 0.5) / FPS, 0.0)
        cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{seek:.4f}",
               "-i", self.path]
        if self.hlg:
            cmd += ["-vf", self.HLG_VF]
        cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.pos = idx

    def frame_at(self, src_t):
        from PIL import Image
        idx = round(src_t * FPS)
        if self.proc is None or idx < self.pos:
            self._open(idx)
        while self.pos < idx:
            if not self.proc.stdout.read(self.raw):
                raise ValueError(f"{self.path}: exhausted seeking {self.pos}->{idx}")
            self.pos += 1
        buf = self.proc.stdout.read(self.raw)
        if len(buf) != self.raw:
            raise ValueError(f"{self.path}: short read at frame {self.pos}")
        self.pos += 1
        return Image.frombuffer("RGB", self.size, buf, "raw", "RGB", 0, 1)


class Ctx:
    """Per-process clip decoders + cached motion/raster streams."""

    def __init__(self):
        self.clips = {}
        self.streams = {}
        self.rasters = {}

    def clip(self, shot):
        import story
        path = story.CLIPS.get(shot)
        assert path and Path(path).exists(), f"clip source missing for {shot!r}: {path}"
        if shot not in self.clips:
            self.clips[shot] = ClipReader(path)
        return self.clips[shot]

    def stream(self, clip_id, t0, t1, arrow_scale=None, key=None, loop=False):
        import motion_hd
        k = (clip_id, round(t0, 3), round(t1, 3), key or "", loop, arrow_scale is not None)
        if k not in self.streams:
            self.streams[k] = motion_hd.MotionStream(clip_id, t0, t1, arrow_scale, loop=loop)
        return self.streams[k]

    def raster(self, clip_id, t0, t1, loop=False):
        import motion_hd
        k = (clip_id, round(t0, 3), round(t1, 3), loop)
        if k not in self.rasters:
            self.rasters[k] = motion_hd.RasterStream(clip_id, t0, t1, loop=loop)
        return self.rasters[k]


def get_ctx():
    global CTX
    if CTX is None:
        CTX = Ctx()
    return CTX


def prepare_media():
    """One-shot decode of each PREP window into a light bt709 intermediate
    (HLG sources get the tone-map chain here, once). Skips existing files."""
    import story
    media = V2 / "media"
    media.mkdir(parents=True, exist_ok=True)
    hlg = ClipReader.HLG_VF
    for key, src, t0, dur in story.PREP:
        out = media / f"{key}.mp4"
        if out.exists() and frame_count(out) >= round(dur * FPS) - 1:
            continue
        cmd = [FFMPEG, "-hide_banner", "-loglevel", "warning", "-y",
               "-ss", f"{t0:.3f}", "-i", src, "-t", f"{dur:.3f}"]
        if probe_color_transfer(src) == "arib-std-b67":
            cmd += ["-vf", hlg]
        cmd += ["-an", "-c:v", "libx264", "-preset", "fast", "-crf", "10",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        run(cmd, WORK / f"prep_{key}.log")
        print(f"  prepared {key} ({dur:.1f}s)", flush=True)


def compose_frame(task):
    """Render one frame to PNG (worker entry)."""
    from PIL import Image
    import theme
    import story
    (bi, f) = task
    bid, start, _, draw = story.BEATS[bi]
    ctx = get_ctx()
    frame = Image.new("RGB", (theme.W, theme.H), (255, 255, 255))
    draw(frame, start + f / FPS, ctx)
    out = FRAMES / bid / f"{f:05d}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out, compress_level=1)
    return bi


def n_frames(beat):
    return round((beat[2] - beat[1]) * FPS)


def render_beat(pool, bi, smoke=0, preview=0.0):
    import story
    bid, start, end, _ = story.BEATS[bi]
    total = n_frames(story.BEATS[bi])
    if preview > 0:  # a mid-beat window, so entrances have settled
        n_prev = min(total, round(preview * FPS))
        f0 = max(0, min(total - n_prev, total // 2 - n_prev // 2))
        frames = list(range(f0, f0 + n_prev))
    else:
        count = min(total, smoke) if smoke else total
        frames = list(range(count))
    done = 0
    for r in pool.imap_unordered(compose_frame, [(bi, f) for f in frames], chunksize=8):
        done += 1
        if done % 120 == 0:
            print(f"  {bid}: {done}/{len(frames)}", flush=True)
    assert done == len(frames)
    return frames


def encode_beat(bi, frames, tag=""):
    import story
    bid = story.BEATS[bi][0]
    out = (BEAT_DIR / f"{bid}{tag}.mp4")
    fdir = FRAMES / bid
    run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y",
         "-f", "image2", "-framerate", str(FPS), "-start_number", str(frames[0]),
         "-i", str(fdir / "%05d.png"), "-frames:v", str(len(frames)),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
        WORK / f"enc_{bid}{tag}.log")
    got = frame_count(out)
    assert got == len(frames), f"{out}: {got} frames != {len(frames)}"
    if not tag:
        shutil.rmtree(fdir)
    print(f"  encoded {out.name} ({len(frames)} frames)", flush=True)
    return out


def frame_count(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets",
                        "-show_entries", "stream=nb_read_packets", "-of",
                        "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def concat_master(beats):
    OUT.mkdir(parents=True, exist_ok=True)
    master = OUT / "FloMo_release_v2_rough.mp4"
    lst = WORK / "concat.txt"
    lst.parent.mkdir(parents=True, exist_ok=True)
    lst.write_text("".join(f"file '{BEAT_DIR / b[0]}.mp4'\n" for b in beats))
    run([FFMPEG, "-hide_banner", "-loglevel", "warning", "-y",
         "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
         "-movflags", "+faststart", str(master)], WORK / "concat.log")
    expect = sum(n_frames(b) for b in beats)
    got = frame_count(master)
    assert got == expect, f"master {got} frames != {expect}"
    return master


def stills(master, beats):
    REVIEW.mkdir(parents=True, exist_ok=True)
    cells = []
    for i, (bid, start, end, _) in enumerate(beats):
        mid = (start + end) / 2
        png = REVIEW / f"{i:02d}_{bid}_t{mid:g}.jpg"
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{mid:.3f}",
             "-i", str(master), "-frames:v", "1", "-q:v", "2", str(png)],
            WORK / "still.log")
        cells.append((png, bid, mid))
        print(f"  still {png.name}", flush=True)
    from PIL import Image, ImageDraw
    cols, cw, ch, bar = 5, 480, 270, 26
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * (ch + bar)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (png, bid, mid) in enumerate(cells):
        x, y = (i % cols) * cw, (i // cols) * (ch + bar)
        sheet.paste(Image.open(png).resize((cw, ch), Image.LANCZOS), (x, y + bar))
        d.text((x + 6, y + 6), f"{i:02d} {bid} t={mid:g}s", fill=theme_rgb_orange())
    sheet.save(OUT / "contact_sheet.jpg", quality=88)
    return cells


def preview_sheet(beats):
    """One still per preview mp4 (midpoint) -> scratch sheet for review."""
    from PIL import Image, ImageDraw
    cells = []
    for bid, start, end, _ in beats:
        mp4 = BEAT_DIR / f"{bid}_prev.mp4"
        tmp = WORK / "prev_cell.jpg"
        mid = frame_count(mp4) / 2 / FPS
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{mid:.3f}",
             "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(tmp)], WORK / "prev.log")
        cells.append((bid, Image.open(tmp).resize((480, 270), Image.LANCZOS)))
    cols, cw, ch, bar = 4, 480, 270, 22
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * (ch + bar)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (bid, im) in enumerate(cells):
        x, y = (i % cols) * cw, (i // cols) * (ch + bar)
        sheet.paste(im, (x, y + bar))
        d.text((x + 6, y + 4), bid, fill=theme_rgb_orange())
    out = V2 / "preview_sheet.jpg"
    sheet.save(out, quality=88)
    print(f"  preview sheet {out}", flush=True)
    return out


def theme_rgb_orange():
    import theme
    return theme.rgb(theme.ORANGE)[:3]


def audit(master, beats):
    """Full-decode + format + black-frame audit of the master."""
    import story
    pm = probe(master)
    dur = float(pm["format"]["duration"])
    v = next(s for s in pm["streams"] if s["codec_type"] == "video")
    checks = {
        f"frames=={sum(n_frames(b) for b in beats)}": frame_count(master) == sum(n_frames(b) for b in beats),
        "duration_120s": abs(dur - 120.0) < 0.1,
        "1080p30": v["width"] == 1920 and v["height"] == 1080 and v["avg_frame_rate"] == "30/1",
        "h264_yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
    }
    r = subprocess.run([FFMPEG, "-v", "error", "-xerror", "-i", str(master), "-f", "null", "-"],
                       capture_output=True, text=True)
    checks["decode_clean"] = r.returncode == 0 and r.stderr == ""
    r = subprocess.run([FFMPEG, "-i", str(master), "-vf", "blackdetect=d=0.1:pix_th=0.10",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    blacks = [ln for ln in r.stderr.splitlines() if "black_start" in ln]
    checks["no_black_frames"] = not blacks
    bad = [k for k, ok in checks.items() if not ok]
    assert not bad, f"audit failed: {bad}\nblack: {blacks}"
    print(f"  audit OK: {dur:.2f}s, {frame_count(master)} frames, no black runs", flush=True)
    return checks


def probe(path):
    import json
    r = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def probe_size(path):
    """(width, height) of the first video stream (ffprobe)."""
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return (int(w), int(h))


def probe_color_transfer(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=color_transfer", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().splitlines()[0].strip(",") if r.stdout.strip() else ""


def probe_rotation(path):
    """Rotation metadata in degrees (0 when absent)."""
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream_side_data=rotation", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    import json
    rot = 0
    for s in json.loads(r.stdout).get("streams", []):
        for sd in s.get("side_data_list", []):
            rot += int(sd.get("rotation", 0))
    return rot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", help="comma subset of beat ids (default all)")
    ap.add_argument("--smoke", type=int, default=0,
                    help="render <=N first frames per beat into scratch (login use only)")
    ap.add_argument("--preview", type=float, default=0.0,
                    help="seconds per beat, mid-beat window, encoded to scratch (bounded)")
    ap.add_argument("--stills-only", action="store_true")
    ap.add_argument("--motion", required=True, choices=("trails", "dense"),
                    help="HD track source for the motion overlays (motion_hd.SRC)")
    args = ap.parse_args()
    import motion_hd
    motion_hd.SRC = args.motion  # set before the Pool forks

    import story
    beats = story.BEATS
    if args.beats:
        want = set(args.beats.split(","))
        beats = [b for b in story.BEATS if b[0] in want]
        assert len(beats) == len(want), f"unknown beat ids: {want - {b[0] for b in beats}}"

    WORK.mkdir(parents=True, exist_ok=True)
    if args.stills_only:
        master = OUT / "FloMo_release_v2_rough.mp4"
        assert master.exists()
        stills(master, beats)
        return
    FRAMES.mkdir(parents=True, exist_ok=True)
    BEAT_DIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    prepare_media()
    pool = Pool(min(16, os.cpu_count()))
    if args.preview:
        for bi in [i for i, b in enumerate(story.BEATS) if b in beats]:
            frames = render_beat(pool, bi, preview=args.preview)
            encode_beat(bi, frames, tag="_prev")
        pool.close()
        pool.join()
        preview_sheet(beats)
        print("PREVIEW OK")
        return
    if args.smoke:
        for bi in [i for i, b in enumerate(story.BEATS) if b in beats]:
            frames = render_beat(pool, bi, smoke=args.smoke)
            encode_beat(bi, frames, tag="_smoke")
        pool.close()
        pool.join()
        print("SMOKE OK")
        return

    BEAT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = __import__("time").time()
    for bi in [i for i, b in enumerate(story.BEATS) if b in beats]:
        print(f"beat {story.BEATS[bi][0]} ({n_frames(story.BEATS[bi])} frames)", flush=True)
        frames = render_beat(pool, bi)
        encode_beat(bi, frames)
    pool.close()
    pool.join()
    master = concat_master(beats)
    audit(master, beats)
    cells = stills(master, beats)
    print(f"DONE master={master} beats={len(beats)} "
          f"wall={__import__('time').time() - t0:.0f}s stills={len(cells)}", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
