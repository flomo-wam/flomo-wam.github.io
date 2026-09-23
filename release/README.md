# FloMo release video + slide deck (v3)

The deck and the video come from the same beat list (`code/story.py`). Edit that list, then rebuild both.

## Contents

| Path | What |
|---|---|
| `deck/index.html` | Slide deck (15 slides, self-contained). Open it in Chrome. Keys: arrow keys = step / slide, `N` = speaker notes, `O` = overview, `#n` in the URL = go to slide n. |
| `videos/FloMo_v3_master.mp4` | Full video, 139 s, 1080p |
| `videos/FloMo_v3_x.mp4` | X/Twitter cut, 122 s (drops RoboTwin + "motion as an action intermediate") |
| `videos/FloMo_v3_icra.mp4` | ICRA accompanying video, 139 s, under 20 MB, anonymous end card |
| `videos/contact_sheet.jpg` | One frame per beat |
| `media/` | Inputs for the deck and the video: `motion/` (head-camera RGB / 3D tracks / arrows / scene-flow-as-RGB clips + `manifest.json`), `footage/` (rollout clips), `figures/` (paper figures + `arch_boxes.json` for the spotlight rings) |
| `fonts/`, `assets/` | Inter fonts, FloMo wordmark |
| `code/` | Builders (below) |

## Code

| File | Role |
|---|---|
| `story.py` | Single source of truth: beat order, headlines, labels, numbers (each cites the paper section), media keys, durations, speaker notes |
| `deck.py` | `story.py` -> `deck/index.html` (copies media into `deck/assets/`) |
| `render.py` | `story.py` -> `videos/*.mp4` (frames in `work/`, audits: duration, size, ICRA <= 20 MB) |
| `theme.py`, `render_v2.py` | Shared design system (colours, fonts, easing) and clip/ffmpeg helpers used by `render.py` |
| `motion_hc.py` | Renders `media/motion/` from SpatialTrackerV2 tracks (training targets, not predictions). Slide 3's scene-flow raster = one-step velocity t -> t+1, re-anchored at each point's current position every frame |
| `footage_figs.py` | Renders `media/footage/` (rollout trims, speed-up with frame blend, colour matching) and `media/figures/` (paper PDFs at 600 dpi) |
| `hlg_capture.js` | Renders the website's HLG clips through Chrome into bt709 (`media/src/`, not included: 2 x ~80 MB). Run from the Bun eval browser: `m = await import(".../hlg_capture.js"); await m.main(browser)` |
| `*.sbatch` | PACE Slurm wrappers (`cpu-small`, `gts-agarg35`, QoS `embers`). Submit from `code/` after `mkdir -p ../work` |

## Rebuild

Python env with numpy, pillow, einops, scipy, h5py, imageio-ffmpeg (PACE: `~sgovil9/.conda/envs/v2r`). ffmpeg path: `FFMPEG` in `render_v2.py`.

```bash
cd release/code
python story.py                          # beat count, total duration, missing-media check
python deck.py --out ../deck             # deck, ~3 s
python render.py --smoke 3 --workers 4   # 3 frames per beat -> ../work/smoke_sheet.jpg, ~70 s
sbatch release_v3.sbatch                 # full render -> ../videos/, ~6 min on cpu-small
```

The deck and the video only need `media/`. To regenerate `media/`, you need data that stays on PACE: robot/human tracks (`motion_hc.DATA`, `STATS`), phone rollouts (`footage_figs.ROLL`), paper figures (`footage_figs.REPO` = AMPLIFYv2 checkout), the HLG captures (`media/src/`, from `hlg_capture.js`). Website clips are read from this repo (`static/videos`).

```bash
python motion_hc.py --out ../media/motion --ffmpeg <ffmpeg> --workers 2 --sets robot_oven   # one set, local, ~1 min
python footage_figs.py --stage figures                                                      # paper figures + arch boxes
python footage_figs.py --stage footage --only string_flomo                                  # one clip
```

## Conventions

- White theme, Inter; orange `#F09018` = FloMo; teal shades `#3D8E92` / `#65B3B7` / `#A8D6D8` = baselines (same as the paper figures).
- Copy uses the paper's wording; every number cites its section in the `notes` field.
- Spotlight slides (4, 5): each step is `(rings, reveal, text)`; box names are in `media/figures/arch_boxes.json` (figure pixels). The pane has a `SPOT_PAD` = 20 px margin so that the rings are never clipped; `spot_geom` must stay the same in `deck.py` and `render.py`.
