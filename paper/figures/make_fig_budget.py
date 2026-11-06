"""Figure: ground-truth nodes found vs. analyst alert budget, per dataset (small multiples).

Inputs (results files): reach_runs/v2dev/{atlas,h501,h051,h201}.json and
reach_runs/velox_lite/{CLEARSCOPE_E3,CADETS_E3,THEIA_E3}/seed0/eval_phase3.json.
Learned detector = Velox-lite in all panels. Interleave on ATLASv2 and OpTC is a development (post-hoc) result.
Usage: python make_fig_budget.py OUT_PDF
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

R = "/home/user/stt-gnn-/dep/data_raw/reach_runs"
BUDGETS = [10, 25, 50, 100, 250, 500]
PANELS = [
    ("ATLASv2 (dev, 10 attacks)", f"{R}/v2dev/atlas.json", {"learned": "velox", "knowledge": "knowledge", "sum": "fused_sum", "interleave": "interleave"}),
    ("OpTC h501 (1 attack)", f"{R}/v2dev/h501.json", {"learned": "velox", "knowledge": "knowledge", "sum": "fused_sum", "interleave": "interleave"}),
    ("OpTC h051 (1 attack)", f"{R}/v2dev/h051.json", {"learned": "velox", "knowledge": "knowledge", "sum": "fused_sum", "interleave": "interleave"}),
    ("OpTC h201 (1 attack)", f"{R}/v2dev/h201.json", {"learned": "velox", "knowledge": "knowledge", "sum": "fused_sum", "interleave": "interleave"}),
    ("E3 CADETS (3 attacks)", f"{R}/velox_lite/CADETS_E3/seed0/eval_phase3.json", {"learned": "velox", "knowledge": "knowledge", "sum": "sum", "interleave": "interleave"}),
    ("E3 THEIA (2 attacks)", f"{R}/velox_lite/THEIA_E3/seed0/eval_phase3.json", {"learned": "velox", "knowledge": "knowledge", "sum": "sum", "interleave": "interleave"}),
    ("E3 CLEARSCOPE (1 attack)", f"{R}/velox_lite/CLEARSCOPE_E3/seed0/eval_phase3.json", {"learned": "velox", "knowledge": "knowledge", "sum": "sum", "interleave": "interleave"}),
]
# validated categorical palette (slots 1-4, fixed order) + secondary encoding by marker and line style
STYLE = {
    "learned": dict(color="#2a78d6", marker="o", ls="-", label="Learned (Velox-lite)"),
    "knowledge": dict(color="#eb6834", marker="s", ls="--", label="Knowledge only"),
    "sum": dict(color="#1baf7a", marker="^", ls="-.", label="Sum fusion"),
    "interleave": dict(color="#eda100", marker="D", ls=":", label="Interleave fusion"),
}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def main(out):
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Liberation Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.titlesize": 8, "axes.titlecolor": INK})
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.8))
    for ax, (title, path, keys) in zip(axes.flat, PANELS):
        r = json.load(open(path))
        for m, k in keys.items():
            y = [r[k][f"gt@{b}"] for b in BUDGETS]
            st = STYLE[m]
            ax.plot(BUDGETS, y, color=st["color"], marker=st["marker"], ls=st["ls"], lw=1.5, ms=4,
                    markeredgecolor="white", markeredgewidth=0.6, label=st["label"])
        ax.set_xscale("log")
        ax.set_xticks(BUDGETS)
        ax.set_xticklabels([str(b) for b in BUDGETS], fontsize=6.5)
        ax.minorticks_off()
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title(title)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    for ax in axes[:, 0]:
        ax.set_ylabel("Ground-truth nodes found")
    for ax in axes[1, :3]:
        ax.set_xlabel("Alert budget (top-k nodes)")
    leg_ax = axes.flat[-1]
    leg_ax.axis("off")
    h, l = axes.flat[0].get_legend_handles_labels()
    leg_ax.legend(h, l, loc="center", frameon=False, fontsize=7.5, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(out)
    fig.savefig(out.replace(".pdf", ".png"), dpi=200)


if __name__ == "__main__":
    main(*sys.argv[1:])
