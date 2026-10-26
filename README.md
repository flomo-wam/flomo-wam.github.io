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
| 3 | Shared human/robot motion target | `static/images/thread_shared_motion.jpg` | — |
| 4 | Matched prediction-target results | `static/images/thread_policy_results.png` | — |
| 5 | Human-video transfer | `static/images/thread_transfer.jpg` | — |
| 6 | Action-token attention | `static/images/figure_attention_share.png` | — |
| 7 | Collaborators and links | None | — |

Only post 1 uses video; posts 2–6 use static images, and post 7 has no attachment. Method and shared-motion explanations precede the results in posts 4–5. The architecture image retains the corrected Wan 2.2 5B DiT and scene-flow labels. Example motion fields are extracted **RGB scene flow**, not model predictions. The shared-motion image pairs human and robot oven demonstrations with their extracted RGB scene flow. The transfer image shows string-pulling and highlighter successes.

Results come from the September 16, 2026 ICRA 2027 manuscript. Post 4 compares the same architecture and training protocol: motion + actions 91%, video + motion + actions 51%, and video + actions 40%, averaged across Oven, Toolbox, and Corn. Each task and method uses 15 trials (45 per method).

Post 5 reports the different transfer trial counts: with human video, 18/30 overall (cabinet 6/10, string 7/10, highlighter 5/10); without human video, 1/15 overall (0/5, 1/5, 0/5). Rounded success is 60% versus 7%. Post 6 uses the existing attention-share figure for the video–motion–action variant on held-out robot data: action tokens allocate about three times as much attention to motion as video, averaged across layers.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design, with wording and numbers from the [ICRA project page](https://flomo-icra.github.io/). The CoRL 2026 design mockups, the CoRL paper PDF, the internal deck, figure drafts and status page, and assets used only by them were removed. The release video was re-rendered with the ICRA numbers (91% / 51% / 40% in distribution; 60% vs 7% OOD with 18/30 and 1/15 rollouts).
