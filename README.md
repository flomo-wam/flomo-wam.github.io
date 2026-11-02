# flomo-wam.github.io

The seven-post collaborator release draft is at [release-thread.html](https://flomo-wam.github.io/release-thread.html). It links to the [project page](https://flomo-wam.github.io/) and preserves the existing paper link. The narrative-first revision explains the representation and method, then uses two experimental posts to support the story.

## Collaborator review

The draft is not published to X. Post 7 deliberately retains `[collaborator handles]` and `Paper: [link]`; fill both before posting. Copy buttons copy only the numbered post text. [thread.txt](thread.txt) contains the same `[n/7]` text, with the same separators as the full-thread copy button.

The header also links to [FloMo-release-thread.zip](FloMo-release-thread.zip), the downloadable collaborator bundle. Package the thread page, standalone video page, `thread.txt`, their local CSS/JS, and all referenced media, posters, logo, and favicons with their relative paths intact. The archive opens at `release-thread.html`. This repository serves static files directly; no build step is required. `.gitignore` excludes `*.zip`, so publishing the bundle requires an explicit forced add.

## Approved post order and attachments

| Post | Topic | Attachment | Poster |
| --- | --- | --- | --- |
| 1 | Motion versus video prediction | `static/videos/thread_overview.mp4` | `static/images/posters/thread_overview.jpg` |
| 2 | What 3D motion means: RGB observation, tracks, RGB scene flow | `static/images/thread_scene_flow.png` | — |
| 3 | Frozen video VAE reuse and joint motion/action prediction | `static/images/thread_method.png` | — |
| 4 | Real-robot ID, RoboTwin simulation, and real-robot OOD comparisons | `static/images/thread_policy_results.png` + `static/images/thread_robotwin_results.png` + `static/images/thread_ood_results.png` (three attachments) | — |
| 5 | Shared human/robot motion representation | `static/images/thread_shared_motion.png` | — |
| 6 | Human-video ablation on OOD tasks | `static/images/thread_transfer_results.png` | — |
| 7 | Collaborators and links | None | — |

Only post 1 uses video; posts 2–6 use static images, and post 7 has no attachment. The collaborator revision follows: video versus motion prediction → scene-flow representation → reuse of video pretraining → comparison evidence → shared human/robot motion → yoyo and highlighter transfer → resources. Posts 4–7 state the main conclusions without numeric scores, trial counts, or evaluation-protocol details. Post 4 groups three separate images, titled “In-distribution performance,” “Single-task RoboTwin 2.0 performance,” and “Out-of-distribution performance,” in that order. Post 6's human-video ablation is titled “Human-video transfer performance.” The RoboTwin version is confirmed by manuscript reference [44] (arXiv:2506.18088). The preview stacks the images at readable width. Motion-action legends explicitly identify FloMo. Plots use one title, legends, axes, categories and percentage labels, without subtitles, protocol notes or figure-number footers. Attention analysis remains on the project website.

Post 2's static scene-flow image uses the existing website poster `static/videos/sceneflow/sceneflow_0201.jpg` (Lift board), resized as one intact strip and labeled RGB observation / 2D tracks / RGB scene flow. It is an extracted-data visualization from the website, not a frame taken from the release video or a model prediction.

The paired motion image uses stored window step 11: human `demo_67` frame 66 and robot `demo_36` frame 461. Tracks and flow use the same time within each embodiment. The displayed flow is a four-frame mean-velocity visualization with one shared color scale and deadband, not a model prediction or an exact rendering of the cumulative training target.

Results come from the September 16, 2026 ICRA 2027 manuscript and the [project page](https://flomo-wam.github.io/). Post 4's real-robot plots compare matched prediction targets: MA (motion + actions, FloMo), VMA (video + motion + actions), and VA (video + actions). ID averages are 91%, 51%, and 40%, respectively, across Oven, Toolbox and Corn, with 15 trials per task and method. OOD percentages on Close Cabinet / Pull String / Highlighter are MA 60 / 70 / 50, VMA 0 / 0 / 20, and VA 0 / 10 / 10; aggregate heights are 18/30 for MA and 2/30 for each video-predicting variant, labeled 60%, 7%, and 7%. The RoboTwin Easy plot compares FloMo, π0.5, FAST-WAM, and Diffusion Policy across Pick Dual Bottles, Stack Two Bowls, Open Laptop, Hang Mug, and Handover Microphone. Their success percentages are [76, 72, 71, 7, 92], [49, 46, 58, 1, 70], [20, 27, 68, 5, 85], and [25, 0, 66, 0, 5], respectively. The simulation evaluation uses 50 demonstrations and 100 episodes per task and method. These numbers and protocols are documented here for review; they do not appear in the thread prose.

Post 6's human-video ablation uses different trial counts: with human video, 18/30 overall (cabinet 6/10, string 7/10, highlighter 5/10); without human video, 1/15 overall (0/5, 1/5, 0/5). The chart shows rounded percentages only: 60%, 70%, 50% (60% overall) with human video, and 0%, 20%, 0% (7% overall) without it. The overall no-human-video bar uses the unrounded 100/15% value; only the label is rounded. The post text states the conclusion without quoting these scores.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design, with wording and numbers from the [ICRA project page](https://flomo-icra.github.io/). The current overview is 40 seconds (1,200 frames at 30 fps), down from 61 seconds. It opens directly on the complete RGB-tracks/scene-flow visualization, skipping the old title sequence and progressive reveal. A new seven-second architecture animation separates training-target encoding through the frozen VAE from image/instruction-conditioned joint prediction. Moving tokens and simultaneous output branches replace static architecture highlights. The representation, real-robot comparison, matched human/robot motion, and eight-second human-video transfer-results section remain. The yoyo clip is labeled `Unseen motion`; the highlighter clip is labeled `Unseen object`. Results keep one headline and percentage-only bars, with no secondary subtitle or trial counts. The real-robot comparison identifies `Motion + actions (FloMo)`. [release-video.html](release-video.html) uses the same overview and opening-frame poster as post 1. Existing rollout excerpts are trimmed, not accelerated.
Task captions appear below the Oven, Toolbox, Pull String (yoyo), and Highlighter rollout clips, outside the video images and above the success bars, and match the homepage rollout captions. Oven (“Open the oven and put the croissant on the plate”), Toolbox (“Open the lid of the toolbox and put the screwdriver inside”), and Corn (“Put the corn in the bowl”) were verified from the UTF-8 `text` dataset in `/storage/project/r-agarg35-0/shared/v2r/real_yam/raw/{croissant_oven/demo_0,screwdriver_toolbox/demo_0,corn_bowl_fixed/demo_1}.hdf5`. The yoyo wording (“Pull the string on the toy in the air”) was verified from `inference_server.task` in `/storage/project/r-agarg35-0/sgovil9/flomo_release_tracks/rollouts/flomo_20260919_203651_1/metadata.json`. Cabinet (“Close the cabinet”) and Highlighter (“Put the highlighter in the bowl”) are concise task descriptions, not recovered verbatim policy prompts. Video line breaks are layout-only. The task-name and unseen-condition labels remain visible.

## Re-rendering the overview

`scripts/render_release_overview.py` uses Pillow, `imageio_ffmpeg`, and the macOS Avenir Next system font. Supply the original 61-second overview from commit `d64da858040f665f66732a26c241012a361d431d`, not the current 40-second output:

```sh
python3 scripts/render_release_overview.py --source /path/to/original_overview.mp4 --output /path/to/revised_overview.mp4
```

| Output time | Source |
| --- | --- |
| 0–5 s | Original 8–13 s: complete scene-flow visualization |
| 5–9 s | Original 14–18 s: website scene-flow examples |
| 9–16 s | New frozen-VAE and joint-prediction animation |
| 16–23 s | Original 33–40 s: trained-task comparison |
| 23–29 s | Original 41.5–47.5 s: shared human/robot motion |
| 29–37 s | Original 49.5–57.5 s: human-video transfer |
| 37–40 s | Original 57.5–60.5 s: closing |

