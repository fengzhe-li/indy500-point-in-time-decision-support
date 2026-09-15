"""Figure C -- illustrative 2021 car-60 point-in-time shadow case."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path as _Path
OUT_DIR = str(_Path(__file__).resolve().parents[1])

plt.rcParams.update({"font.family": "serif", "font.size": 11})

# authoritative FINAL_V3 values (output/evaluation/phase2_case_table.csv, car 60)
labels = ["Point-in-time\nforecast-conditioned\nE[$\\Delta v$]", "Realised-environment\nE[$\\Delta v$]", "Observed\n$\\Delta v$"]
values = [0.0236, 0.0451, 4.695]
pi80_low, pi80_high = -0.744, 0.798

fig, ax = plt.subplots(figsize=(6.6, 5.0))
colors = ["#5b7fa6", "#7a9e6e", "#333333"]
x = np.arange(3)
bars = ax.bar(x, values, color=colors, width=0.55, zorder=3, edgecolor="black", linewidth=0.8)

# 80% predictive interval on the point-in-time forecast bar only
ax.plot([0, 0], [pi80_low, pi80_high], color="black", linewidth=1.6, zorder=4)
ax.plot([-0.08, 0.08], [pi80_low, pi80_low], color="black", linewidth=1.6, zorder=4)
ax.plot([-0.08, 0.08], [pi80_high, pi80_high], color="black", linewidth=1.6, zorder=4)
ax.text(0.18, pi80_high - 0.05, "80% PI", fontsize=9, va="top")

for xi, v in zip(x, values):
    ax.text(xi, v + 0.13 if v >= 0 else v - 0.28, f"{v:+.3f} mph", ha="center", fontsize=10, fontweight="bold")

ax.axhline(0, color="#888888", linewidth=0.8, zorder=1)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("$\\Delta v$ (mph)")
ax.set_ylim(-1.3, 5.4)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

ax.set_title("ILLUSTRATIVE POINT-IN-TIME SHADOW CASE ONLY\n2021, car 60 -- realised horizon 64.1 min, evaluated at the 60-min calibrated anchor\nEXCLUDED FROM AGGREGATE VALIDATION",
             fontsize=10, fontweight="bold", color="#8a1f1f", linespacing=1.5)

fig.tight_layout()
fig.savefig(f"{OUT_DIR}/figureC_car60_illustrative_case.pdf", bbox_inches="tight")
fig.savefig(f"{OUT_DIR}/figureC_car60_illustrative_case.png", dpi=220, bbox_inches="tight")
print("wrote figure C")
