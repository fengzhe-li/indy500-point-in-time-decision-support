from pathlib import Path
import pandas as pd
import numpy as np

METRIC_FILE = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_transition_section_mechanism_metrics_v1.csv"
)

OUTDIR = Path(
    "weather/output/v2b_section_mechanism"
)

OUT_DETAIL = (
    OUTDIR /
    "v2b_section_residual_diagnostics_v1.csv"
)

OUT_SUMMARY = (
    OUTDIR /
    "v2b_section_residual_diagnostics_summary_v1.txt"
)

df = pd.read_csv(METRIC_FILE)

df["abs_delta_speed_mph"] = (
    df[
        "delta_four_lap_average_speed_mph"
    ].abs()
)

# =============================================================================
# SPEARMAN RANK CORRELATION
# =============================================================================

variables = [
    "direction_coherence",
    "sd_delta_section_speed_mph",
    "max_abs_section_change_share",
]

corr_rows = []

for threshold in [
    0.0,
    0.05,
    0.10,
    0.20,
    0.50,
]:

    sub = df[
        df["abs_delta_speed_mph"]
        >= threshold
    ].copy()

    for var in variables:

        if len(sub) >= 3:

            rho = (
                sub[
                    [
                        "abs_residual_loyo_centered",
                        var,
                    ]
                ]
                .corr(
                    method="spearman"
                )
                .iloc[0, 1]
            )

        else:
            rho = np.nan

        corr_rows.append({
            "minimum_abs_delta_speed_mph":
                threshold,
            "n":
                len(sub),
            "mechanism_metric":
                var,
            "spearman_rho_with_abs_residual":
                rho,
        })

corr = pd.DataFrame(
    corr_rows
)

# =============================================================================
# COHERENCE DISTRIBUTION UNDER ABS-DELTA SENSITIVITY FILTERS
# =============================================================================

sensitivity_rows = []

for threshold in [
    0.0,
    0.05,
    0.10,
    0.20,
    0.50,
]:

    sub = df[
        df["abs_delta_speed_mph"]
        >= threshold
    ].copy()

    if len(sub) == 0:
        continue

    sensitivity_rows.append({
        "minimum_abs_delta_speed_mph":
            threshold,
        "n":
            len(sub),
        "mean_direction_coherence":
            sub[
                "direction_coherence"
            ].mean(),
        "median_direction_coherence":
            sub[
                "direction_coherence"
            ].median(),
        "fraction_at_least_6_of_9":
            (
                sub[
                    "direction_coherence"
                ]
                >= 6 / 9
            ).mean(),
        "fraction_at_least_7_of_9":
            (
                sub[
                    "direction_coherence"
                ]
                >= 7 / 9
            ).mean(),
        "fraction_at_least_8_of_9":
            (
                sub[
                    "direction_coherence"
                ]
                >= 8 / 9
            ).mean(),
        "fraction_9_of_9":
            (
                sub[
                    "direction_coherence"
                ]
                == 1.0
            ).mean(),
    })

sensitivity = pd.DataFrame(
    sensitivity_rows
)

# =============================================================================
# RESIDUAL SIZE BY COHERENCE LEVEL
#
# Do not call these mechanism "classes" yet.
# These are descriptive bins only.
# =============================================================================

def coherence_bin(x):

    if pd.isna(x):
        return "unknown"

    if x <= 4 / 9:
        return "<=4/9"

    if x <= 6 / 9:
        return "5-6/9"

    if x <= 8 / 9:
        return "7-8/9"

    return "9/9"


df["coherence_bin"] = (
    df[
        "direction_coherence"
    ]
    .map(
        coherence_bin
    )
)

bin_order = [
    "<=4/9",
    "5-6/9",
    "7-8/9",
    "9/9",
]

group_rows = []

for b in bin_order:

    g = df[
        df["coherence_bin"] == b
    ]

    if len(g) == 0:
        continue

    group_rows.append({
        "coherence_bin":
            b,
        "n":
            len(g),
        "median_abs_delta_speed_mph":
            g[
                "abs_delta_speed_mph"
            ].median(),
        "mean_abs_residual_mph":
            g[
                "abs_residual_loyo_centered"
            ].mean(),
        "median_abs_residual_mph":
            g[
                "abs_residual_loyo_centered"
            ].median(),
        "mean_section_dispersion_mph":
            g[
                "sd_delta_section_speed_mph"
            ].mean(),
        "mean_max_abs_change_share":
            g[
                "max_abs_section_change_share"
            ].mean(),
    })

groups = pd.DataFrame(
    group_rows
)

# =============================================================================
# IDENTIFY INTERESTING CONTRAST CASES
# =============================================================================

high_resid_cut = (
    df[
        "abs_residual_loyo_centered"
    ]
    .quantile(0.75)
)

high_residual = df[
    df[
        "abs_residual_loyo_centered"
    ] >= high_resid_cut
].copy()

high_residual = high_residual.sort_values(
    "abs_residual_loyo_centered",
    ascending=False
)

# High residual + high coherence:
global_unexplained = high_residual[
    high_residual[
        "direction_coherence"
    ] >= 7 / 9
].copy()

# High residual + low/mixed coherence:
mixed_unexplained = high_residual[
    high_residual[
        "direction_coherence"
    ] <= 5 / 9
].copy()

# =============================================================================
# SAVE DETAIL
# =============================================================================

df.to_csv(
    OUT_DETAIL,
    index=False
)

# =============================================================================
# SUMMARY
# =============================================================================

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B SECTION / RESIDUAL DIAGNOSTIC SUMMARY"
)
add("=" * 100)

add()
add("ABS-DELTA SENSITIVITY OF DIRECTION COHERENCE")
add("-" * 100)
add(
    sensitivity.to_string(
        index=False
    )
)

add()
add("SPEARMAN ASSOCIATION WITH ABSOLUTE PHYSICS RESIDUAL")
add("-" * 100)
add(
    corr.to_string(
        index=False
    )
)

add()
add("DESCRIPTIVE COHERENCE BINS")
add("-" * 100)
add(
    groups.to_string(
        index=False
    )
)

add()
add(
    f"HIGH-RESIDUAL THRESHOLD (75th percentile): "
    f"{high_resid_cut:.6f} mph"
)

add()
add(
    "HIGH RESIDUAL + HIGH COHERENCE (>=7/9)"
)
add("-" * 100)

show_cols = [
    "year",
    "car_number",
    "driver_name",
    "delta_four_lap_average_speed_mph",
    "abs_residual_loyo_centered",
    "direction_coherence",
    "sd_delta_section_speed_mph",
    "max_abs_section_change_share",
]

if len(global_unexplained):

    add(
        global_unexplained[
            show_cols
        ]
        .to_string(
            index=False
        )
    )

else:
    add("none")

add()
add(
    "HIGH RESIDUAL + LOW/MIXED COHERENCE (<=5/9)"
)
add("-" * 100)

if len(mixed_unexplained):

    add(
        mixed_unexplained[
            show_cols
        ]
        .to_string(
            index=False
        )
    )

else:
    add("none")

summary = "\n".join(
    lines
)

OUT_SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)
print(OUT_DETAIL)
print(OUT_SUMMARY)

print()
print("DONE")
