# flomo-wam.github.io

The seven-post collaborator release draft is at [release-thread.html](https://flomo-wam.github.io/release-thread.html). It links to the [project page](https://flomo-wam.github.io/) and preserves the existing paper link. The narrative-first revision explains the representation and method, then uses two experimental posts to support the story.

## Collaborator review

The draft is not published to X. Post 7 deliberately retains `[collaborator handles]` and `arXiv: [link]`; fill both before posting. Copy buttons copy only the numbered post text. [thread.txt](thread.txt) contains the same `[n/7]` text, with the same separators as the full-thread copy button.

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

Only post 1 uses video; posts 2–6 use static images, and post 7 has no attachment. The story is: motivating question → scene-flow representation → reuse of video pretraining → comparison evidence → shared human/robot representation → human-video transfer evidence → resources. Posts 4–7 state the main conclusions without numeric scores, trial counts, or evaluation-protocol details. Post 4 groups three separate images, titled “In-distribution performance,” “Single-task RoboTwin 2.0 performance,” and “Out-of-distribution performance,” in that order. Post 6's human-video ablation is titled “Human-video transfer performance.” The RoboTwin version is confirmed by manuscript reference [44] (arXiv:2506.18088). The preview stacks the images at readable width. Motion-action legends explicitly identify FloMo. Plots use one title, legends, axes, categories and percentage labels, without subtitles, protocol notes or figure-number footers. Attention analysis remains on the project website.

Post 2's static scene-flow image uses the existing website poster `static/videos/sceneflow/sceneflow_0201.jpg` (Lift board), resized as one intact strip and labeled RGB observation / 2D tracks / RGB scene flow. It is an extracted-data visualization from the website, not a frame taken from the release video or a model prediction.

The paired motion image uses stored window step 11: human `demo_67` frame 66 and robot `demo_36` frame 461. Tracks and flow use the same time within each embodiment. The displayed flow is a four-frame mean-velocity visualization with one shared color scale and deadband, not a model prediction or an exact rendering of the cumulative training target.

Results come from the September 16, 2026 ICRA 2027 manuscript and the [project page](https://flomo-wam.github.io/). Post 4's real-robot plots compare matched prediction targets: MA (motion + actions, FloMo), VMA (video + motion + actions), and VA (video + actions). ID averages are 91%, 51%, and 40%, respectively, across Oven, Toolbox and Corn, with 15 trials per task and method. OOD percentages on Close Cabinet / Pull String / Highlighter are MA 60 / 70 / 50, VMA 0 / 0 / 20, and VA 0 / 10 / 10; aggregate heights are 18/30 for MA and 2/30 for each video-predicting variant, labeled 60%, 7%, and 7%. The RoboTwin Easy plot compares FloMo, π0.5, FAST-WAM, and Diffusion Policy across Pick Dual Bottles, Stack Two Bowls, Open Laptop, Hang Mug, and Handover Microphone. Their success percentages are [76, 72, 71, 7, 92], [49, 46, 58, 1, 70], [20, 27, 68, 5, 85], and [25, 0, 66, 0, 5], respectively. The simulation evaluation uses 50 demonstrations and 100 episodes per task and method. These numbers and protocols are documented here for review; they do not appear in the thread prose.

Post 6's human-video ablation uses different trial counts: with human video, 18/30 overall (cabinet 6/10, string 7/10, highlighter 5/10); without human video, 1/15 overall (0/5, 1/5, 0/5). The chart shows rounded percentages only: 60%, 70%, 50% (60% overall) with human video, and 0%, 20%, 0% (7% overall) without it. The overall no-human-video bar uses the unrounded 100/15% value; only the label is rounded. The post text states the conclusion without quoting these scores.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design, with wording and numbers from the [ICRA project page](https://flomo-icra.github.io/). The CoRL 2026 design mockups, the CoRL paper PDF, the internal deck, figure drafts and status page, and assets used only by them were removed. The current overview is 61 seconds (1,830 frames at 30 fps). It retains the representation, method, real-robot comparison, and matched human/robot motion scenes, followed by the 8-second human-video transfer-results section (49.5–57.5 seconds). The yoyo clip is labeled `Unseen motion`; the highlighter clip is labeled `Unseen object`. This section keeps one headline and percentage-only human-video ablation bars, with no secondary subtitle or trial counts. The earlier real-robot comparison still identifies `Motion + actions (FloMo)`. [release-video.html](release-video.html) uses the same overview and poster as post 1, rather than the older separate cut.
Task-demo captions appear below the Oven, Toolbox, Pull String (yoyo), and Highlighter rollout clips, outside the video images and above the success bars. They use the published task instructions in the project page's Real-robot rollouts section (`index.html`, lines 420, 426, 444, and 450), rather than newly recovered policy-prompt logs. The task-name and unseen-condition labels remain visible, and the overview remains 61 seconds.

