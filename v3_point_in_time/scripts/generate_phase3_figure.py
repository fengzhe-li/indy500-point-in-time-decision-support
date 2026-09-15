"""Phase 3 Step 14 — one figure: Historical Replay Evidence Outcomes.

A simple bar count is genuinely clearer here than any richer chart
would be (41 transitions falling into three coarse buckets); no
decorative alternative is produced.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPLAY_DIR = Path(__file__).resolve().parents[1] / "output" / "replay"
SUMMARY_CSV = REPLAY_DIR / "replay_abstention_summary.csv"
FIGURE_PNG = REPLAY_DIR / "figure_historical_replay_evidence_outcomes.png"


def main() -> int:
    df = pd.read_csv(SUMMARY_CSV).set_index("category")["count"]

    supported = int(df.get("FULL_SHADOW_INFERENCE_SUPPORTED", 0)) + int(
        df.get("CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED", 0)
    )
    illustrative = int(df.get("ILLUSTRATIVE_ONLY", 0))
    abstained = (
        int(df.get("ABSTAINED_INSUFFICIENT_TIMESTAMP", 0))
        + int(df.get("ABSTAINED_OUT_OF_SUPPORT", 0))
        + int(df.get("ABSTAINED_FORECAST_UNAVAILABLE", 0))
    )

    labels = [
        "SUPPORTED\n(conditional outlook issued;\nhistorical scoring not claimed)",
        "ILLUSTRATIVE\n(diagnostic only,\nnot aggregate validation)",
        "ABSTAINED\n(insufficient timestamp /\nout of support / no forecast)",
    ]
    counts = [supported, illustrative, abstained]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, counts, color=["#2c6b4a", "#c98a2c", "#888888"])
    for i, v in enumerate(counts):
        ax.text(i, v + 0.5, str(v), ha="center")
    ax.set_ylabel("Number of transitions (of 41 total)")
    ax.set_title(
        "Historical Replay Evidence Outcomes\n"
        "(41 real same-car transitions; SUPPORTED means inference was issued, "
        "not that historical validation occurred)"
    )
    fig.tight_layout()
    fig.savefig(FIGURE_PNG, dpi=150)
    print(f"Wrote {FIGURE_PNG}")
    print(f"supported={supported} illustrative={illustrative} abstained={abstained}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
