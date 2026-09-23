"""FloMo release v3: one beat list shared by the HTML deck (deck.py) and the
video renderer (render.py). Order and copy follow the paper of record
(ICRA27_7042_MS.pdf); every number cites its section. Media keys are paths
under MEDIA (see tasks/release-video.md "v3 story").
"""
from pathlib import Path

MEDIA = Path(__file__).resolve().parents[1] / "media"
TITLE = "3D Scene Flow as a World Action Model Intermediate for Learning from Human Video"
X_CUT_DROP = ("robotwin", "why")  # X (<= 140 s) drops the sim + analysis beats; ICRA keeps all
# stat colours = the paper figures' legends (figures/paper_figures/style.py): ours
# orange; VMA / pi0.5 BASELINE_SHADES[3]; FAST-WAM [2]; VA / BC BASELINE_SHADES[1]
ORANGE, TEAL, TEAL_MID, TEAL_LIGHT = "#F09018", "#3D8E92", "#65B3B7", "#A8D6D8"

# Table I (ICRA27_7042_MS.pdf p.5): SR = successes / rollouts, 10 per condition;
# no-human-video ablation 5 per condition. Columns: Close Cabinet, Pull String, Highlighter.
OOD_ROWS = [
    ("VMA", ["0/10", "0/10", "2/10"], "2/30", 7, 15),
    ("VA", ["0/10", "1/10", "1/10"], "2/30", 7, 15),
    ("DreamZero", ["5/10", "1/10", "0/10"], "6/30", 20, 30),
    ("AMPLIFY", ["6/10", "0/10", "0/10"], "6/30", 20, 23),
    ("FloMo, no human video", ["0/5", "1/5", "0/5"], "1/15", 7, 30),
    ("FloMo", ["6/10", "7/10", "5/10"], "18/30", 60, 68),
]

BEATS = [
    dict(
        id="title", kind="title", dur=6.0,
        headline=TITLE,
        media={},
        credits="",  # X cut only: authors / lab / link. Empty = anonymous (ICRA).
        notes="Title card only: the method visuals need context, so they start on the next slide.",
    ),
    dict(
        id="entropy", kind="pair", dur=8.0,
        headline="Video contains unnecessary information",
        media=dict(left="motion/robot_oven_rgb.mp4", right="motion/robot_oven_arrows.mp4"),
        labels=["What WAMs predict", "Motion necessary for control"],
        notes="Intro, p.1: videos that differ in texture, lighting, material and background depict the "
              "same motion and imply the same action. Head camera of the robot during the oven task; "
              "arrows are the tracked 3D displacement of scene points over the window. Extracted "
              "target, not a prediction.",
    ),
    dict(
        id="sceneflow", kind="triptych", dur=10.0,
        headline="3D scene flow as the prediction target",
        media=dict(panes=["motion/robot_oven_rgb.mp4", "motion/robot_oven_tracks.mp4",
                          "motion/robot_oven_flow.mp4"]),
        labels=["RGB", "3D point tracks", "Scene flow as RGB"],
        notes="Sec. III-B: 64x64 query grid, T = 16 frames, first-frame camera frame (invariant to "
              "ego-motion). One training window (motion_hc robot_oven: carry to the plate). The raster "
              "is the training target itself: cumulative displacement from frame 0 on the 64x64 query "
              "grid, colour-mapped with the dataset's percentile bounds. Mauve gray is zero displacement.",
    ),
    dict(
        id="tokenize", kind="spotlight", dur=10.0,
        headline="Rendering 3D scene flow as RGB",
        media=dict(figure="figures/fig_arch.png", boxes="figures/arch_boxes.json"), crop="right_half",
        steps=[  # (rings, reveal, text): rings outline the components, reveal un-dims the region
            (["tok_frames"], ["tok_q1"], "A 16-frame clip"),
            (["tok_flow3d"], ["tok_q2"], "Tracked 64 x 64 grid of points"),
            (["tok_cube"], ["tok_q3"], "(dX, dY, dZ) becomes (R, G, B)"),
            (["tok_flowrgb"], ["tok_q4"], "Scene flow as RGB"),
        ],
        notes="Sec. III-C: clip each displacement channel to its per-dataset 1st/99th percentile, "
              "rescale to [0, 1], treat it exactly like an RGB video. The frozen Wan 2.2 VAE encodes "
              "it on the next slide; no new tokenizer.",
    ),
    dict(
        id="arch", kind="spotlight", dur=12.0,
        headline="Architecture",
        media=dict(figure="figures/fig_arch.png", boxes="figures/arch_boxes.json"), crop="left_half",
        steps=[
            (["text_input", "image_input", "flow_input", "action_input"], ["band_inputs"],
             "Inputs: instruction, image, noisy scene flow, noisy actions"),
            (["text_encoder", "video_encoder"], ["band_encoders"],
             "Frozen umT5-XXL and Wan 2.2 VAE encoders"),
            (["backbone", "cross_attn"], ["band_backbone"],
             "Wan 2.2 5B DiT, LoRA r = 64"),
            (["video_decoder", "motion_out", "label_motion_out", "action_decoder", "action_out",
              "label_action_out"], ["band_outputs"],
             "Denoised scene flow and actions"),
        ],
        notes="Sec. III-D/E: LoRA r = 64, alpha = 128 on attention and FFN of all 30 blocks (161M "
              "trainable); bidirectional attention; flow matching on scene-flow latents and action "
              "tokens jointly, loss weights flow 1, action 0.1 (1 in fine-tuning); 10 UniPC steps, "
              "0.7 s per 16-action chunk on one H100.",
    ),
    dict(
        id="data", kind="pair_cards", dur=9.0,
        headline="Co-training on human video and robot teleoperation",
        media=dict(left="motion/human_oven_tracks.mp4", right="motion/robot_oven_tracks.mp4"),
        labels=["Human video: scene flow", "Robot teleoperation: scene flow + actions"],
        cards=[("81 h", "egocentric human video (EgoVerse)"),
               ("14 h", "bimanual YAM teleoperation")],
        notes="Sec. III-F, IV-A: 81 h EgoVerse (filtered from 1,362 h) + 0.7 h internal human demos; "
              "robot: 10 h MolmoAct2-BimanualYAM + 3.7 h task demos + 0.4 h play. "
              "Mid-training 14k steps at batch 512; fine-tuning 1.5k steps at batch 256.",
    ),
    dict(
        id="tasks", kind="tasks", dur=12.0,
        headline="In-distribution real-robot tasks",
        chip="FloMo rollouts",
        media=dict(clips=["footage/id_oven.mp4", "footage/id_toolbox.mp4", "footage/id_corn.mp4"]),
        tasks=[("Oven", "Open the oven and put the croissant in the plate"),
               ("Toolbox", "Open the toolbox and put the screwdriver inside"),
               ("Corn", "Put the corn in the bowl")],
        notes="Sec. IV-B.1 setup; the descriptions are the language instructions given to the policy. "
              "Bimanual YAM platform as in MolmoAct2. 15 rollouts per task. Clips at 2.5x (oven, "
              "toolbox) and 1x (corn).",
    ),
    dict(
        id="id_results", kind="chart_fig", dur=9.0,
        headline="In-distribution success rates",
        media=dict(figure="figures/fig_id.png"),
        stats=[("91", "FloMo: motion + action", ORANGE), ("51", "VMA: video + motion + action", TEAL),
               ("40", "VA: video + action", TEAL_LIGHT)],
        stat_label="Average success rate, 15 rollouts per task",
        notes="Fig. 2: Oven 93/60/33, Toolbox 87/13/13, Corn 93/80/73. Same backbone and data; "
              "adding a video target costs 40 points, replacing motion with video costs 51.",
    ),
    dict(
        id="ood_tasks", kind="tasks", dur=9.0,
        headline="Out-of-distribution real-robot tasks",
        chip="FloMo rollouts",
        media=dict(clips=["footage/ood_cabinet.mp4", "footage/ood_string.mp4",
                          "footage/ood_highlighter.mp4"]),
        tasks=[("Close Cabinet", "Unseen motion primitive"),
               ("Pull String", "Unseen task"),
               ("Highlighter", "Unseen object")],
        notes="Sec. IV-B.2: 10 rollouts per condition; task progress counts the intermediate stage "
              "(contact the door, grasp the string, pick the highlighter). Only the human video "
              "contains these motions (text search of the training instructions).",
    ),
    dict(
        id="ood_results", kind="table", dur=11.0,
        headline="Out-of-distribution success rates",
        columns=["Close Cabinet", "Pull String", "Highlighter", "Aggregate", "SR %", "TP %"],
        rows=OOD_ROWS,
        media={},
        notes="Table I. SR = successful rollouts / total; TP = average fraction of the two stages "
              "completed. Full-data methods: 10 rollouts per condition; the ablation row: 5. All "
              "methods that predict pixels (VMA, VA, DreamZero) or 2D tracks (AMPLIFY) degrade.",
    ),
    dict(
        id="ablation", kind="duel", dur=9.0,
        headline="Transfer from human video",
        duel=[("60%", "FloMo"), ("7%", "FloMo (no human video)")],
        duel_label="Out-of-distribution success rate",
        media=dict(left="motion/human_oven_tracks.mp4", right="motion/robot_oven_tracks.mp4"),
        labels=["Human video", "Robot teleoperation"],
        notes="Sec. IV-C: the ablation removes the 81 h EgoVerse subset and the 0.7 h internal human "
              "demos: 0/5, 1/5 and 0/5. It begins each task but rarely completes the novel motion.",
    ),
    dict(
        id="robotwin", kind="chart_fig", dur=7.0,
        headline="RoboTwin sim results",
        media=dict(figure="figures/fig_robotwin.png"),
        stats=[("63.6", "FloMo", ORANGE), ("44.8", "\u03c0 0.5", TEAL), ("41.0", "FAST-WAM", TEAL_MID),
               ("19.2", "BC", TEAL_LIGHT)],
        stat_label="Average success rate, RoboTwin Easy, 5 tasks",
        notes="Sec. IV-B.3, Fig. 3a: 50 demos per task, 100 episodes per task and method. Baselines: "
              "pi0.5 VLA, FAST-WAM video-based WAM, diffusion-policy BC without video pretraining.",
    ),
    dict(
        id="why", kind="insights", dur=10.0,
        headline="Motion as an action intermediate",
        media=dict(left="figures/fig_scaling.png", right="figures/fig_attention.png"),
        insights=[("22%", "lower action error than video at 1% of the action data"),
                  ("3x", "more action-query attention to motion than to video")],
        notes="Sec. IV-D: inverse-dynamics probe from ground-truth motion vs. ground-truth video, "
              "0.058 vs 0.074 at 1% data, gap closes above 10%; action-query attention in the joint "
              "video + motion + action model reaches about 55% at the late-middle layers, video "
              "declines to about 10%.",
    ),
    dict(
        id="close", kind="title", dur=8.0,
        headline=TITLE,
        media={},
        credits="flomo-icra.github.io",  # the paper's (anonymous) site, so it stays in the ICRA cut
        notes="Bookend: wordmark + title + site. Sec. V: the priors of video pretraining are carried "
              "by the weights, not by the prediction target.",
    ),
]


def media_keys():
    keys = set()
    for b in BEATS:
        for v in b["media"].values():
            keys.update(v if isinstance(v, list) else [v])
    return sorted(keys)


if __name__ == "__main__":
    total = sum(b["dur"] for b in BEATS)
    print(f"{len(BEATS)} beats, {total:.0f} s")
    for k in media_keys():
        print(("ok " if (MEDIA / k).exists() else "-- ") + k)
