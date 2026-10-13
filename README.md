# flomo-wam.github.io

The collaborator release draft is at [release-thread.html](https://flomo-wam.github.io/release-thread.html). Its eight posts use results from the September 16, 2026 ICRA 2027 manuscript and link to [this site](https://flomo-wam.github.io/).

The thread includes updated in-distribution and RoboTwin figures and reports the different OOD trial counts for the full-data model (18/30) and no-human-video ablation (1/15).

The thread uses one video in posts 2 and 5; one image in posts 1, 3, 4, 6, and 7; and two images in post 8. Each caption links to the actual attachment. This avoids depending on mixed-media support and fits the [X API attachment rules](https://docs.x.com/x-api/posts/create-post). Copy buttons include only the post text.

The scene-flow attachment is a 1280×720 H.264 export of the existing board-lifting example, padded without cropping. Post 7 uses a per-task bar chart of the Table I ablation, with successes/trials on each bar, in the paper's figure style.

Post 1 leads with the website’s architecture and flow-tokenization figure, not a robot rollout. Post 3 uses a training-data figure built from a human-video frame, its scene flow, and a robot frame, with data hours from Sec. IV-A. No attachment is a website screenshot.

The homepage (`index.html`) presents the ICRA 2027 paper in the original homepage design, with wording and numbers from the [ICRA project page](https://flomo-icra.github.io/). The CoRL 2026 design mockups, the CoRL paper PDF, the internal deck, figure drafts and status page, and assets used only by them were removed. The release video was re-rendered with the ICRA numbers (91% / 51% / 40% in distribution; 60% vs 7% OOD with 18/30 and 1/15 rollouts).
