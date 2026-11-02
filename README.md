# flomo-wam.github.io

The seven-post collaborator release draft is at [release-thread.html](https://flomo-wam.github.io/release-thread.html). It links to the [project page](https://flomo-wam.github.io/) and to the named paper with appendix, [static/paper/flomo.pdf](static/paper/flomo.pdf), as do the homepage and release-video page. The narrative-first revision explains the representation and method, then uses two experimental posts to support the story.

## Collaborator review

The draft is not published to X. Post 7 deliberately retains `[collaborator handles]` and `Paper: [arXiv link]`; fill both before posting. Copy buttons copy only the numbered post text. [thread.txt](thread.txt) contains the same `[n/7]` text, with the same separators as the full-thread copy button.

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

Only post 1 uses video; posts 2–6 use static images, and post 7 has no attachment. The thread text is the collaborator's wording, with its two typos fixed and its result placeholders filled from the paper. It follows: video versus motion prediction → scene-flow representation → reuse of video pretraining → comparison evidence → shared human/robot motion → Pull String transfer and the human-video ablation → resources. Post 4 quotes the trained-task averages (91% FloMo, 40% video + actions, 51% video + motion + actions) and the RoboTwin average against the strongest baseline (63.6% vs 44.8% for π0.5). Post 6 quotes Pull String from Table I (7/10, 70%, vs 1/10, 10%, for DreamZero) and the 7% aggregate without human video. Post 4 groups three separate images, titled “In-distribution performance,” “Single-task RoboTwin 2.0 performance,” and “Out-of-distribution performance,” in that order. Post 6's human-video ablation is titled “Human-video transfer performance.” The RoboTwin version is confirmed by manuscript reference [44] (arXiv:2506.18088). The preview stacks the images at readable width. Motion-action legends explicitly identify FloMo. Plots use one title, legends, axes, categories and percentage labels, without subtitles, protocol notes or figure-number footers. Attention analysis remains on the project website.

Post 2's static scene-flow image uses the existing website poster `static/videos/sceneflow/sceneflow_0201.jpg` (Lift board), resized as one intact strip and labeled RGB observation / 2D tracks / RGB scene flow. It is an extracted-data visualization from the website, not a frame taken from the release video or a model prediction.

The paired motion image uses stored window step 11: human `demo_67` frame 66 and robot `demo_36` frame 461. Tracks and flow use the same time within each embodiment. The displayed flow is a four-frame mean-velocity visualization with one shared color scale and deadband, not a model prediction or an exact rendering of the cumulative training target.

Results come from the paper ([static/paper/flomo.pdf](static/paper/flomo.pdf); the ICRA 2027 submission with author names and appendix), which is the reference for all wording on the site. Post 4's real-robot plots compare matched prediction targets: MA (motion + actions, FloMo), VMA (video + motion + actions), and VA (video + actions). ID averages are 91%, 51%, and 40%, respectively, across Oven, Toolbox and Corn, with 15 trials per task and method. OOD percentages on Close Cabinet / Pull String / Highlighter are MA 60 / 70 / 50, VMA 0 / 0 / 20, and VA 0 / 10 / 10; aggregate heights are 18/30 for MA and 2/30 for each video-predicting variant, labeled 60%, 7%, and 7%. The RoboTwin Easy plot compares FloMo, π0.5, FAST-WAM, and BC (the paper's diffusion-policy baseline) across Pick Dual Bottles, Stack Two Bowls, Open Laptop, Hang Mug, and Handover Microphone. Their success percentages are [76, 72, 71, 7, 92], [49, 46, 58, 1, 70], [20, 27, 68, 5, 85], and [25, 0, 66, 0, 5], respectively; the FloMo and π0.5 means are the paper's 63.6% and 44.8%. The simulation evaluation uses 50 demonstrations and 100 episodes per task and method. Per-task numbers and protocols are documented here for review; the thread prose quotes only the averages listed above.

Post 6's human-video ablation uses different trial counts: with human video, 18/30 overall (cabinet 6/10, string 7/10, highlighter 5/10); without human video, 1/15 overall (0/5, 1/5, 0/5). The chart shows rounded percentages only: 60%, 70%, 50% (60% overall) with human video, and 0%, 20%, 0% (7% overall) without it. The overall no-human-video bar uses the unrounded 100/15% value; only the label is rounded.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design; its wording and numbers follow the paper. The current overview is 47.2 seconds (1,416 frames at 30 fps), down from 61 seconds. It opens cold on the website's human and robot scene-flow examples, tiled edge to edge under the FloMo logo; the logo then flies into the corner of the complete RGB-tracks/scene-flow visualization, followed by the “Robot policies should learn from motion.” slide. The architecture section animates the paper diagram itself in four steps, at 1.4x the earlier duration: flow tokenization into RGB, frozen-VAE encoding, instruction and noisy-action conditioning, and joint motion/action prediction by one backbone. The real-robot comparison, matched human/robot motion, and eight-second human-video transfer-results section remain. Following the paper's OOD axes, the yoyo (Pull String) clip is labeled `Unseen task` (the renderer replaces the archived `Unseen motion` text) and the highlighter clip `Unseen object`. Results keep one headline and percentage-only bars, with no secondary subtitle or trial counts. The real-robot comparison identifies `Motion + actions (FloMo)`. [release-video.html](release-video.html) uses the same overview as post 1, with a poster taken from its cold open. Existing rollout excerpts are trimmed, not accelerated.
Task captions appear below the Oven, Toolbox, Pull String (yoyo), and Highlighter rollout clips, outside the video images and above the success bars, and match the homepage rollout captions. Oven (“Open the oven and put the croissant on the plate”), Toolbox (“Open the lid of the toolbox and put the screwdriver inside”), and Corn (“Put the corn in the bowl”) were verified from the UTF-8 `text` dataset in `/storage/project/r-agarg35-0/shared/v2r/real_yam/raw/{croissant_oven/demo_0,screwdriver_toolbox/demo_0,corn_bowl_fixed/demo_1}.hdf5`. The yoyo wording (“Pull the string on the toy in the air”) was verified from `inference_server.task` in `/storage/project/r-agarg35-0/sgovil9/flomo_release_tracks/rollouts/flomo_20260919_203651_1/metadata.json`. Cabinet (“Close the cabinet”) and Highlighter (“Put the highlighter in the bowl”) are concise task descriptions, not recovered verbatim policy prompts. Video line breaks are layout-only. The task-name and unseen-condition labels remain visible.

## Re-rendering the overview

`scripts/render_release_overview.py` uses Pillow, `imageio_ffmpeg`, and the Inter SemiBold font of the original slides (`Inter-SemiBold.ttf` in `scripts/fonts/`, `~/Library/Fonts/`, or `/Library/Fonts/`). Supply the original 61-second overview from commit `d64da858040f665f66732a26c241012a361d431d`, not the current 47.2-second output:

```sh
python3 scripts/render_release_overview.py --source /path/to/original_overview.mp4 --output /path/to/revised_overview.mp4
```

| Output time | Source |
| --- | --- |
| 0–2.9 s | New cold open: original 14.4–17.3 s website scene-flow examples, tiled full-frame; crossfades into the next slide |
| 2.9–7.3 s | Original 8.6–13 s: complete scene-flow visualization |
| 7.3–10 s | Original 3.3–6.0 s: thesis slide, “Robot policies should learn from motion.” |
| 10–23.6 s | New four-step walkthrough of the paper architecture diagram (`static/images/thread_method.png`) |
| 23.6–30.2 s | Original 33.4–40 s: trained-task comparison |
| 30.2–36.2 s | Original 41.5–47.5 s: shared human/robot motion |
| 36.2–44.2 s | Original 49.5–57.5 s: human-video transfer |
| 44.2–47.2 s | Original 57.5–60.5 s: closing |

