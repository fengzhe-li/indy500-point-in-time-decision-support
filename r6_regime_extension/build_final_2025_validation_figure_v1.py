from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

INPUT = (
    ROOT /
    "r6_regime_extension/output/"
    "external_regime_inference_backtest_2025_v2/"
    "external_regime_inference_backtest_2025_rows_v2.csv"
)

OUTDIR = (
    ROOT /
    "r6_regime_extension/output/"
    "final_williams_figures_v1"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

PNG_OUT = (
    OUTDIR /
    "figure_2_2025_external_regime_validation_v1.png"
)

PDF_OUT = (
    OUTDIR /
    "figure_2_2025_external_regime_validation_v1.pdf"
)


# ============================================================
# Load
# ============================================================

df = pd.read_csv(
    INPUT,
    low_memory=False
)

required = [
    "driver_name",
    "actual_wait_min",
    "actual_delta_speed_mph",
    "model_expected_delta_speed_mph",
    "lower_80_mph",
    "upper_80_mph",
    "lower_90_mph",
    "upper_90_mph",
    "validation_band",
]

missing = [
    c
    for c in required
    if c not in df.columns
]

if missing:
    raise RuntimeError(
        "Missing required columns:\n"
        +
        "\n".join(
            missing
        )
    )


# ============================================================
# Sort by actual historical interval
# ============================================================

df = (
    df
    .sort_values(
        "actual_wait_min"
    )
    .reset_index(
        drop=True
    )
)

x = np.arange(
    len(df)
)


# ============================================================
# Values
# ============================================================

pred = df[
    "model_expected_delta_speed_mph"
].to_numpy(
    dtype=float
)

actual = df[
    "actual_delta_speed_mph"
].to_numpy(
    dtype=float
)

lower80 = df[
    "lower_80_mph"
].to_numpy(
    dtype=float
)

upper80 = df[
    "upper_80_mph"
].to_numpy(
    dtype=float
)

lower90 = df[
    "lower_90_mph"
].to_numpy(
    dtype=float
)

upper90 = df[
    "upper_90_mph"
].to_numpy(
    dtype=float
)


err80 = np.vstack([
    pred - lower80,
    upper80 - pred,
])

err90 = np.vstack([
    pred - lower90,
    upper90 - pred,
])


# ============================================================
# Labels
# ============================================================

def display_driver(name):

    s = str(
        name
    )

    if "," in s:

        surname, first = [
            p.strip()
            for p in s.split(
                ",",
                1
            )
        ]

        return f"{first[0]}. {surname}"

    return s


labels = [
    (
        f"{display_driver(r['driver_name'])}\n"
        f"{r['actual_wait_min']:.0f} min"
    )
    for _, r in df.iterrows()
]


# ============================================================
# Find production / extended boundary
# ============================================================

product_mask = (
    df[
        "actual_wait_min"
    ]
    <=
    120.0
)

product_n = int(
    product_mask.sum()
)


# ============================================================
# Plot
# ============================================================

fig, ax = plt.subplots(
    figsize=(
        15,
        7.8
    )
)


# 90% interval
ax.errorbar(
    x,
    pred,
    yerr=err90,
    fmt="none",
    capsize=4,
    linewidth=1.0,
    alpha=0.45,
    label="90% predictive interval",
)


# 80% interval
ax.errorbar(
    x,
    pred,
    yerr=err80,
    fmt="none",
    capsize=5,
    linewidth=2.2,
    alpha=0.85,
    label="80% predictive interval",
)


# Expected physical contribution
ax.scatter(
    x,
    pred,
    s=65,
    zorder=4,
    label="Expected physical Δspeed",
)


# Actual observed result
ax.scatter(
    x,
    actual,
    marker="x",
    s=85,
    linewidths=2.0,
    zorder=5,
    label="Observed Δspeed",
)


# Zero line
ax.axhline(
    0.0,
    linestyle="--",
    linewidth=1.0,
    alpha=0.7,
)


# Product / extended separator
if (
    product_n > 0
    and
    product_n < len(
        df
    )
):

    separator_x = (
        product_n
        -
        0.5
    )

    ax.axvline(
        separator_x,
        linestyle=":",
        linewidth=1.2,
        alpha=0.8,
    )

    y_top = ax.get_ylim()[
        1
    ]

    ax.text(
        (
            product_n
            -
            1
        )
        /
        2,
        y_top,
        "Production horizon ≤120 min",
        ha="center",
        va="bottom",
        fontsize=10,
    )

    ax.text(
        (
            product_n
            +
            len(df)
            -
            1
        )
        /
        2,
        y_top,
        "Extended validation 120–180 min",
        ha="center",
        va="bottom",
        fontsize=10,
    )


# ============================================================
# Axes / title
# ============================================================

ax.set_xticks(
    x
)

ax.set_xticklabels(
    labels,
    rotation=55,
    ha="right",
)

ax.set_ylabel(
    "Change in four-lap average qualifying speed (mph)"
)

ax.set_xlabel(
    "2025 historical repeat-attempt case"
)

ax.set_title(
    "2025 Hybrid-Era External Validation of the Frozen 2020–2024 Physics Inference Core"
)

ax.grid(
    axis="y",
    alpha=0.20
)

ax.legend(
    loc="upper left",
    ncol=2,
)


# ============================================================
# Footer annotation
# ============================================================

footer = (
    "n=15 external-regime cases ≤180 min | "
    "MAE=0.492 mph | "
    "80% interval coverage=80% | "
    "90% interval coverage=100% | "
    "Point-direction accuracy=46.7%\n"
    "Intervals represent physics-conditioned performance uncertainty; "
    "the model is not a standalone requalification outcome predictor."
)

fig.text(
    0.5,
    0.015,
    footer,
    ha="center",
    va="bottom",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.07,
        1,
        1
    ]
)


fig.savefig(
    PNG_OUT,
    dpi=220,
    bbox_inches="tight"
)

fig.savefig(
    PDF_OUT,
    bbox_inches="tight"
)

plt.close(
    fig
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 120
)

print(
    "FINAL 2025 VALIDATION FIGURE"
)

print(
    "=" * 120
)

print(
    "cases:",
    len(
        df
    )
)

print(
    "product horizon cases <=120:",
    product_n
)

print(
    "extended validation cases 120-180:",
    len(
        df
    )
    -
    product_n
)

print(
    "\nOUTPUTS"
)

print(
    PNG_OUT.relative_to(
        ROOT
    )
)

print(
    PDF_OUT.relative_to(
        ROOT
    )
)

print(
    "\nFINAL_2025_VALIDATION_FIGURE_V1_COMPLETE"
)
