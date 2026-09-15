"""Figure B -- point-in-time evidence / abstention flow (publication style)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from pathlib import Path as _Path
OUT_DIR = str(_Path(__file__).resolve().parents[1])

plt.rcParams.update({"font.family": "serif", "font.size": 10})

fig, ax = plt.subplots(figsize=(11.5, 7.2))
XMAX = 15.3
ax.set_xlim(0, XMAX)
ax.set_ylim(0, 8.4)
ax.axis("off")

EDGE = "#333333"


def box(cx, cy, w, h, text, fc, fontsize=10, fontweight="normal", edge=EDGE, lw=1.2):
    p = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.10,rounding_size=0.08",
                        linewidth=lw, edgecolor=edge, facecolor=fc, zorder=2)
    ax.add_patch(p)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, fontweight=fontweight,
            zorder=3, linespacing=1.3)
    return cx - w / 2, cx + w / 2


def arrow(x0, y0, x1, y1, color=EDGE, lw=1.3):
    a = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=13,
                         linewidth=lw, color=color, zorder=1)
    ax.add_patch(a)


cx_top = XMAX / 2  # 7.25

# Row 1
box(cx_top, 7.8, 5.2, 0.75, "41 same-car transitions\n(frozen 2020-2024 reference core)", "#e3e3e3", fontweight="bold")

# Row 2
cx_excl, cx_cand = 3.0, 10.6
box(cx_excl, 6.35, 4.6, 0.9, "31 excluded / abstained pre-candidates\n(ambiguous attempt pairing or\nno usable decision timestamp)", "#f3d9d9")
box(cx_cand, 6.35, 4.2, 0.75, "10 genuine point-in-time\ncandidate cases", "#dbe4ee", fontweight="bold")
arrow(cx_top - 0.3, 7.42, cx_excl + 0.4, 6.83)
arrow(cx_top + 0.3, 7.42, cx_cand - 0.4, 6.75)

box(cx_excl, 5.0, 4.6, 0.6, "reason: INSUFFICIENT_ATTEMPT_TIMESTAMP\n(retained in audit output, not discarded)", "#fbeaea", fontsize=8.8)
arrow(cx_excl, 5.88, cx_excl, 5.32)

# Row 3
cx_9, cx_1 = 9.0, 12.9
box(cx_9, 4.85, 4.0, 0.9, "9 cases: full 5-horizon\nconditional physical outlook\n(inference support)", "#dbe4ee", fontweight="bold")
box(cx_1, 4.85, 2.9, 0.9, "1 illustrative-only\ncase\n(2021, car 60)", "#f1e6cf", fontweight="bold", fontsize=9.5)
arrow(cx_cand - 0.5, 5.96, cx_9 + 0.2, 5.32)
arrow(cx_cand + 0.5, 5.96, cx_1 - 0.3, 5.32)

# Row 4
box(cx_9, 3.35, 4.6, 0.95, "historical scoring ABSTAINED\n(realised recurrence horizon > 120 min;\nHORIZON_OUT_OF_SUPPORT)", "#f3d9d9", fontsize=9.0)
box(cx_1, 3.35, 3.4, 0.95, "historical scoring:\nILLUSTRATIVE ONLY\n(NON_ANCHOR_EVALUATION_\nNOT_APPROVED)", "#f1e6cf", fontsize=8.4)
arrow(cx_9, 4.39, cx_9, 3.83)
arrow(cx_1, 4.39, cx_1, 3.83)

# Final result
box(cx_top, 1.4, 9.6, 0.95,
    "Cases contributing to formal aggregate exact-anchor\nhistorical-scoring validation: 0",
    "#ffffff", fontweight="bold", edge="#8a1f1f", lw=1.8, fontsize=12)
arrow(cx_9 - 0.5, 2.87, cx_top, 1.88)
arrow(cx_1 - 0.6, 2.87, cx_top + 0.6, 1.88)

ax.text(0.1, 0.15, "Note: inference support (row 3, left) is not historical scoring support (row 4).",
        fontsize=8.6, style="italic", color="#444444")

fig.tight_layout()
fig.savefig(f"{OUT_DIR}/figureB_pit_evidence_abstention_flow.pdf", bbox_inches="tight")
fig.savefig(f"{OUT_DIR}/figureB_pit_evidence_abstention_flow.png", dpi=220, bbox_inches="tight")
print("wrote figure B")
