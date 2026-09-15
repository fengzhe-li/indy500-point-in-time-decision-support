"""Phase 2 Step 14 — figures.

Only ONE figure is generated. With a genuinely defensible scientific
sample size of N=1 (see phase2_minimum_data_plan.md), Figures A
(error-distribution comparison), C (multi-case error-decomposition
scatter), and D (P(improve) calibration) would require aggregating
across many cases and are not defensible here -- generating them would
imply a sample size that does not exist. Producing them anyway to hit a
figure-count target is exactly the "decorative figure" the specification
prohibits.

The one figure produced (Figure B, singular-case version) plots the
single real case's observed outcome against both comparison inferences
with their predictive intervals. Its own title says N=1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

EVAL_DIR = Path(__file__).resolve().parents[1] / "output" / "evaluation"
CASE_TABLE = EVAL_DIR / "phase2_case_table.csv"
FIGURE_DATA = EVAL_DIR / "figure_b_single_case_plotting_data.csv"
FIGURE_PNG = EVAL_DIR / "figure_b_single_case_observed_vs_predicted.png"


def main() -> int:
    df = pd.read_csv(CASE_TABLE)
    supported = df[df["applicability_status"] == "SUPPORTED"]
    if supported.empty:
        print("No SUPPORTED cases available; no figure generated.")
        return 0

    row = supported.iloc[0]
    plot_rows = [
        dict(series="Observed (realised)", value=row["observed_delta_v"], pi80_low=None, pi80_high=None),
        dict(series="Point-in-time forecast", value=row["expected_delta_v"],
             pi80_low=row["pi80_low"], pi80_high=row["pi80_high"]),
        dict(series="Realised-environment", value=row["realised_env_expected_delta_v"],
             pi80_low=None, pi80_high=None),
    ]
    plot_df = pd.DataFrame(plot_rows)
    plot_df.to_csv(FIGURE_DATA, index=False)

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(plot_df))
    ax.bar(x, plot_df["value"], color=["#444444", "#2c6b4a", "#2c3e6b"])
    for i, r in plot_df.iterrows():
        if pd.notna(r["pi80_low"]):
            ax.plot([i, i], [r["pi80_low"], r["pi80_high"]], color="black", linewidth=1.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(plot_df["series"], rotation=15, ha="right")
    ax.set_ylabel("Δv (mph)")
    ax.set_title(
        f"Case {row['case_id']}, h={row['target_horizon_minutes']} min -- N=1, ILLUSTRATIVE ONLY\n"
        "(not a general performance claim; see phase2_qa_report.md)"
    )
    ax.axhline(0, color="grey", linewidth=0.5)
    fig.tight_layout()
    fig.savefig(FIGURE_PNG, dpi=150)
    print(f"Wrote {FIGURE_PNG}")
    print(f"Wrote {FIGURE_DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
