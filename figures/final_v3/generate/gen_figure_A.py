"""Figure A -- FINAL_V3 system architecture (publication style)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

from pathlib import Path as _Path
OUT_DIR = str(_Path(__file__).resolve().parents[1])

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9.5,
    "axes.edgecolor": "black",
})

fig, ax = plt.subplots(figsize=(7.2, 8.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 15.2)
ax.axis("off")

BOX_H = "#dbe4ee"
BOX_S = "#f1e6cf"
BOX_CORE = "#e3e3e3"
EDGE = "#333333"


def box(x, y, w, h, text, fc, fontsize=9, style="round,pad=0.10,rounding_size=0.08"):
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.1,
                        edgecolor=EDGE, facecolor=fc, zorder=2)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, zorder=3, linespacing=1.35)
    return (x + w / 2, y, x + w / 2, y + h)


def arrow(x0, y0, x1, y1, color=EDGE, style="-|>", lw=1.2):
    a = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=12,
                         linewidth=lw, color=color, zorder=1)
    ax.add_patch(a)


# ---- Title labels for the two columns ----
ax.text(2.3, 14.7, "HISTORICAL PATH", ha="center", fontsize=11, fontweight="bold")
ax.text(7.7, 14.7, "HYPOTHETICAL PATH", ha="center", fontsize=11, fontweight="bold")

col_l, col_r = 0.6, 5.6
w = 3.4
h = 0.95
gap = 0.42

labels_left = [
    "Historical evidence\n(real qualifying results,\nHRRR forecast vintages,\ntrack/ambient observations)",
    "Point-in-time information guard\n(forecast.issue_time ≤ decision_time)",
    "Forecast vintage selection",
    "Frozen FINAL_V2 scientific core\n(unmodified adapter)",
    "Historical Shadow Replay\n(time-ordered replay events)",
    "Evidence-Aware Abstention\n(machine-readable reason codes)",
    "Read-only historical API",
    "Pit-Wall application\n(Outlook / Replay / Evidence /\nValidation pages)",
]

labels_right = [
    "User-supplied\nhypothetical physical state",
    "Scenario input validation\n(fail-closed on missing input)",
    "",
    "Frozen FINAL_V2 scientific core\n(same adapter, unmodified)",
    "",
    "",
    "",
    "Ephemeral hypothetical outlook\n(HYPOTHETICAL_SCENARIO /\nNOT_HISTORICAL_EVIDENCE)",
]

y = 13.5
centers_l = []
for i, lab in enumerate(labels_left):
    if lab:
        cx, cy0, _, cy1 = box(col_l, y, w, h, lab, BOX_CORE if "FINAL_V2" in lab or "FINAL_V2" in lab else BOX_H)
        centers_l.append((cx, cy0, cy1))
    else:
        centers_l.append(None)
    y -= (h + gap)

y = 13.5
centers_r = []
for i, lab in enumerate(labels_right):
    if lab:
        cx, cy0, cy1 = None, None, None
        cx, cy0, _, cy1 = box(col_r, y, w, h, lab, BOX_CORE if "FINAL_V2" in lab else BOX_S)
        centers_r.append((cx, cy0, cy1))
    else:
        centers_r.append(None)
    y -= (h + gap)

# arrows down the left column
for i in range(len(centers_l) - 1):
    if centers_l[i] and centers_l[i + 1]:
        cx, cy0, cy1 = centers_l[i]
        cx2, cy02, cy12 = centers_l[i + 1]
        arrow(cx, cy0, cx2, cy12)

# right column: box0 -> box1 -> box3 (skip blanks) -> box7
seq_r = [i for i, c in enumerate(centers_r) if c is not None]
for a_i, b_i in zip(seq_r[:-1], seq_r[1:]):
    cx, cy0, cy1 = centers_r[a_i]
    cx2, cy02, cy12 = centers_r[b_i]
    arrow(cx, cy0, cx2, cy12)

# isolation gap marker between columns
ax.plot([col_l + w + 0.55, col_l + w + 0.55], [0.3, 14.3], linestyle=(0, (5, 4)),
        color="#888888", linewidth=1.3, zorder=1)
ax.text(col_l + w + 0.55, 14.5, "isolated -- no shared\nstate or storage", ha="center",
        fontsize=8, color="#555555", style="italic")

# forbidden-outputs box at the bottom
fb_y = 0.15
fb = FancyBboxPatch((col_l, fb_y), col_r + w - col_l, 1.15, boxstyle="round,pad=0.08",
                     linewidth=1.3, edgecolor="#8a1f1f", facecolor="#fbeaea", zorder=2)
ax.add_patch(fb)
ax.text(col_l + (col_r + w - col_l) / 2, fb_y + 0.575,
        "NOT MODELLED, ANYWHERE IN EITHER PATH:\n"
        r"no queue model $\cdot$ no $P(H \mid Q)$ $\cdot$ no strategy / retain / withdraw recommendation",
        ha="center", va="center", fontsize=9, color="#5a1414", fontweight="bold", linespacing=1.5)

fig.tight_layout()
fig.savefig(f"{OUT_DIR}/figureA_final_v3_architecture.pdf", bbox_inches="tight")
fig.savefig(f"{OUT_DIR}/figureA_final_v3_architecture.png", dpi=220, bbox_inches="tight")
print("wrote figure A")
