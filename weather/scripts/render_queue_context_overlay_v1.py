from pathlib import Path
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt

CURVE_PATH = Path(
    "weather/output/operational_curve_v2/"
    "operational_performance_curve_v2.csv"
)

OUTDIR = Path(
    "weather/output/queue_context_overlay_v1"
)

OUTDIR.mkdir(parents=True, exist_ok=True)


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--window-start",
        type=float,
        required=True,
        help="Externally supplied earliest plausible opportunity time in minutes.",
    )

    p.add_argument(
        "--window-end",
        type=float,
        required=True,
        help="Externally supplied latest plausible opportunity time in minutes.",
    )

    p.add_argument(
        "--scenario",
        choices=["cooling", "neutral", "warming"],
        default="neutral",
        help="Physical ambient scenario to display.",
    )

    p.add_argument(
        "--label",
        default="Externally supplied plausible opportunity window",
        help="Label for the queue-context window.",
    )

    return p.parse_args()


def validate_args(args):
    if args.window_start < 0:
        raise ValueError("window-start must be >= 0")

    if args.window_end <= args.window_start:
        raise ValueError("window-end must be greater than window-start")

    if args.window_end > 120:
        raise ValueError(
            "window-end exceeds supported operational horizon of 120 minutes"
        )


def load_curve():
    if not CURVE_PATH.exists():
        raise FileNotFoundError(
            f"Frozen operational curve not found: {CURVE_PATH}"
        )

    df = pd.read_csv(CURVE_PATH)

    required = {
        "scenario",
        "horizon_min",
        "support_status",
        "expected_delta_speed_mph",
        "p_improve",
        "lower_80_mph",
        "upper_80_mph",
        "lower_90_mph",
        "upper_90_mph",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Missing required curve columns: "
            + ", ".join(sorted(missing))
        )

    return df


def add_anchor_points(ax, sub, ycol):
    anchors = sub[
        sub["support_status"] == "CALIBRATED_ANCHOR"
    ]

    ax.scatter(
        anchors["horizon_min"],
        anchors[ycol],
        s=45,
        zorder=5,
        label="Calibrated anchors",
    )


def plot_speed(sub, args):
    fig, ax = plt.subplots(figsize=(10, 6))

    x = sub["horizon_min"]

    ax.fill_between(
        x,
        sub["lower_90_mph"],
        sub["upper_90_mph"],
        alpha=0.12,
        label="90% predictive interval",
    )

    ax.fill_between(
        x,
        sub["lower_80_mph"],
        sub["upper_80_mph"],
        alpha=0.22,
        label="80% predictive interval",
    )

    ax.plot(
        x,
        sub["expected_delta_speed_mph"],
        linewidth=1.8,
        label="Expected speed change",
    )

    add_anchor_points(
        ax,
        sub,
        "expected_delta_speed_mph",
    )

    ax.axvspan(
        args.window_start,
        args.window_end,
        alpha=0.18,
        label=args.label,
    )

    ax.axhline(0, linewidth=1)

    ax.set_xlim(0, 120)

    ax.set_xlabel(
        "Future opportunity horizon h (minutes)"
    )

    ax.set_ylabel(
        "Four-lap speed change (mph)"
    )

    ax.set_title(
        f"Queue Context Overlay — {args.scenario.capitalize()} Scenario"
    )

    ax.legend()

    ax.grid(alpha=0.2)

    fig.tight_layout()

    out = OUTDIR / (
        f"queue_context_speed_{args.scenario}_"
        f"{int(args.window_start)}_"
        f"{int(args.window_end)}min_v1.png"
    )

    fig.savefig(out, dpi=180)
    plt.close(fig)

    return out


def plot_probability(sub, args):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        sub["horizon_min"],
        sub["p_improve"],
        linewidth=1.8,
        label="P(improvement)",
    )

    add_anchor_points(
        ax,
        sub,
        "p_improve",
    )

    ax.axvspan(
        args.window_start,
        args.window_end,
        alpha=0.18,
        label=args.label,
    )

    ax.axhline(
        0.5,
        linewidth=1,
    )

    ax.set_xlim(0, 120)
    ax.set_ylim(0, 1)

    ax.set_xlabel(
        "Future opportunity horizon h (minutes)"
    )

    ax.set_ylabel(
        "P(Δspeed > 0)"
    )

    ax.set_title(
        f"Queue Context Probability Overlay — {args.scenario.capitalize()} Scenario"
    )

    ax.legend()

    ax.grid(alpha=0.2)

    fig.tight_layout()

    out = OUTDIR / (
        f"queue_context_probability_{args.scenario}_"
        f"{int(args.window_start)}_"
        f"{int(args.window_end)}min_v1.png"
    )

    fig.savefig(out, dpi=180)
    plt.close(fig)

    return out


def summarize_window(sub, args):
    window = sub[
        (sub["horizon_min"] >= args.window_start)
        &
        (sub["horizon_min"] <= args.window_end)
    ].copy()

    if window.empty:
        raise RuntimeError(
            "No curve rows fall inside the requested window."
        )

    summary = {
        "scenario": args.scenario,
        "window_start_min": args.window_start,
        "window_end_min": args.window_end,
        "window_source": "external_live_context_or_manual_assumption",
        "queue_wait_model_used": False,
        "queue_wait_prediction": False,
        "best_wait_recommendation": False,
        "strategy_recommendation": False,
        "mean_expected_delta_speed_mph": float(
            window["expected_delta_speed_mph"].mean()
        ),
        "min_expected_delta_speed_mph": float(
            window["expected_delta_speed_mph"].min()
        ),
        "max_expected_delta_speed_mph": float(
            window["expected_delta_speed_mph"].max()
        ),
        "mean_p_improve": float(
            window["p_improve"].mean()
        ),
        "min_p_improve": float(
            window["p_improve"].min()
        ),
        "max_p_improve": float(
            window["p_improve"].max()
        ),
        "interpretation": (
            "These values describe the conditional performance outlook "
            "within an externally supplied opportunity-time window. "
            "The system does not estimate the probability of that window occurring."
        ),
    }

    return summary


def main():
    args = parse_args()
    validate_args(args)

    df = load_curve()

    sub = df[
        (df["scenario"] == args.scenario)
        &
        (df["horizon_min"] >= 15)
    ].copy()

    speed_plot = plot_speed(
        sub,
        args,
    )

    prob_plot = plot_probability(
        sub,
        args,
    )

    summary = summarize_window(
        sub,
        args,
    )

    stem = (
        f"{args.scenario}_"
        f"{int(args.window_start)}_"
        f"{int(args.window_end)}min"
    )

    summary_path = OUTDIR / (
        f"queue_context_summary_{stem}_v1.json"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            indent=2,
        )

    print("=" * 92)
    print("QUEUE CONTEXT OVERLAY V1")
    print("=" * 92)

    print("\nINPUT CONTEXT")
    print(
        f"scenario        : {args.scenario}"
    )
    print(
        f"window          : {args.window_start:.1f}–{args.window_end:.1f} min"
    )
    print(
        "window source   : EXTERNAL / MANUAL"
    )

    print("\nCONDITIONAL OUTLOOK INSIDE WINDOW")
    print(
        "mean expected Δspeed:",
        f"{summary['mean_expected_delta_speed_mph']:+.4f} mph"
    )
    print(
        "range expected Δspeed:",
        f"{summary['min_expected_delta_speed_mph']:+.4f}",
        "to",
        f"{summary['max_expected_delta_speed_mph']:+.4f}",
        "mph"
    )
    print(
        "mean P(improve):",
        f"{summary['mean_p_improve']:.4f}"
    )
    print(
        "range P(improve):",
        f"{summary['min_p_improve']:.4f}",
        "to",
        f"{summary['max_p_improve']:.4f}"
    )

    print("\nBOUNDARY")
    print("queue wait prediction : NO")
    print("best wait             : NO")
    print("strategy recommendation: NO")
    print(
        "meaning               : conditional outlook given externally supplied h-window"
    )

    print("\nOUTPUTS")
    print(speed_plot)
    print(prob_plot)
    print(summary_path)

    print("\nSTATUS: QUEUE_CONTEXT_OVERLAY_V1_CREATED")


if __name__ == "__main__":
    main()
