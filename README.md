# flomo-wam.github.io

The seven-post collaborator release draft is at [release-thread.html](https://flomo-wam.github.io/release-thread.html). It links to the [project page](https://flomo-wam.github.io/) and preserves the existing paper link. The approved copy replaces the earlier eight-post draft.

## Collaborator review

The draft is not published to X. Post 7 deliberately retains `[collaborator handles]` and `arXiv: [link]`; fill both before posting. Copy buttons copy only the numbered post text. [thread.txt](thread.txt) contains the same `[n/7]` text, with the same separators as the full-thread copy button.

The header also links to [FloMo-release-thread.zip](FloMo-release-thread.zip), the downloadable collaborator bundle. Package the thread page, `thread.txt`, its local CSS/JS, and all referenced media, posters, logo, and favicons with their relative paths intact. The archive opens at `release-thread.html`. This repository serves static files directly; no build step is required. `.gitignore` excludes `*.zip`, so publishing the bundle requires an explicit forced add.

## Approved post order and attachments

| Post | Topic | Attachment | Poster |
| --- | --- | --- | --- |
| 1 | Motion versus video prediction | `static/videos/thread_overview.mp4` | `static/images/posters/thread_overview.jpg` |
| 2 | RGB scene flow, frozen video VAE, joint prediction | `static/images/thread_method.png` | — |
| 3 | Shared human/robot motion target | `static/images/thread_shared_motion.png` | — |
| 4 | MA / VMA / VA on ID and OOD tasks | `static/images/thread_policy_results.png` + `static/images/thread_ood_results.png` (two attachments) | — |
| 5 | Task-level RoboTwin Easy results | `static/images/thread_robotwin_results.png` | — |
| 6 | Human-video ablation on OOD tasks | `static/images/thread_transfer_results.png` | — |
| 7 | Collaborators and links | None | — |

Only post 1 uses video; posts 2–6 use static images, and post 7 has no attachment. The opening introduces motion as the link between video pretraining and robot control; it makes no broader empirical claim. Method and shared-motion explanations precede the three experiment posts: prediction-target comparison, RoboTwin simulation, then human-data ablation. Post 4 attaches two plots: ID first, OOD second. X permits up to four photos per post/reply ([official guidance](https://help.x.com/en/using-x/posting-gifs-and-pictures)). The preview shows these side by side on desktop and stacked on mobile. Plots keep only legends, axes, categories and percentage labels, without subtitles, protocol notes or figure-number footers. Attention analysis is no longer part of the thread; the homepage figure is unchanged.

The paired motion image uses stored window step 11: human `demo_67` frame 66 and robot `demo_36` frame 461. Tracks and flow use the same time within each embodiment. The displayed flow is a four-frame mean-velocity visualization with one shared color scale and deadband, not a model prediction or an exact rendering of the cumulative training target.

Results come from the September 16, 2026 ICRA 2027 manuscript and the [project page](https://flomo-wam.github.io/). Post 4 compares matched prediction targets: MA (motion + actions), VMA (video + motion + actions), and VA (video + actions). ID averages are 91%, 51%, and 40%, respectively, across Oven, Toolbox and Corn, with 15 trials per task and method. OOD percentages on Close Cabinet / Pull String / Highlighter are MA 60 / 70 / 50, VMA 0 / 0 / 20, and VA 0 / 10 / 10. OOD aggregates are 18/30 for MA and 2/30 for each video-predicting variant, displayed as 60%, 7%, and 7%; bars use unrounded aggregate values.

Post 5 shows all five RoboTwin Easy tasks, in order: Pick Dual Bottles, Stack Two Bowls, Open Laptop, Hang Mug, Handover Microphone. Success percentages are FloMo [76, 72, 71, 7, 92], π0.5 [49, 46, 58, 1, 70], FAST-WAM [20, 27, 68, 5, 85], and Diffusion Policy [25, 0, 66, 0, 5]. Averages are 63.6%, 44.8%, 41.0%, and 19.2%. Each method uses 50 demonstrations and 100 evaluation episodes per task.

Post 6's human-video ablation uses different trial counts: with human video, 18/30 overall (cabinet 6/10, string 7/10, highlighter 5/10); without human video, 1/15 overall (0/5, 1/5, 0/5). The post and chart show rounded percentages only: 60%, 70%, 50% (60% overall) with human video, and 0%, 20%, 0% (7% overall) without it. The overall no-human-video bar uses the unrounded 100/15% value; only the label is rounded.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design, with wording and numbers from the [ICRA project page](https://flomo-icra.github.io/). The CoRL 2026 design mockups, the CoRL paper PDF, the internal deck, figure drafts and status page, and assets used only by them were removed. The release video was re-rendered with the ICRA numbers (91% / 51% / 40% in distribution; 60% vs 7% OOD with 18/30 and 1/15 rollouts).
