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

OUTFILE = (
    OUTDIR /
    "v2b_section_magnitude_control_summary_v1.txt"
)

df = pd.read_csv(METRIC_FILE)

df["abs_delta"] = (
    df["delta_four_lap_average_speed_mph"].abs()
)

df["abs_resid"] = (
    df["abs_residual_loyo_centered"]
)

# ------------------------------------------------------------
# Scale-free section dispersion
# ------------------------------------------------------------

# Mean absolute section change per transition
# reconstructed from long-format section file.
long_file = (
    OUTDIR /
    "v2b_section_changes_long_v1.csv"
)

long = pd.read_csv(long_file)

section_scale = (
    long.groupby("core_row")
    ["delta_section_speed_mph"]
    .apply(lambda x: np.mean(np.abs(x)))
    .rename("mean_abs_section_change")
    .reset_index()
)

df = df.merge(
    section_scale,
    on="core_row",
    how="left"
)

df["relative_section_dispersion"] = (
    df["sd_delta_section_speed_mph"]
    /
    df["mean_abs_section_change"]
    .replace(0, np.nan)
)

# ------------------------------------------------------------
# Basic Spearman relationships
# ------------------------------------------------------------

basic_vars = [
    "abs_delta",
    "direction_coherence",
    "sd_delta_section_speed_mph",
    "relative_section_dispersion",
    "max_abs_section_change_share",
]

basic_rows = []

for var in basic_vars:

    rho = (
        df[
            ["abs_resid", var]
        ]
        .corr(method="spearman")
        .iloc[0, 1]
    )

    basic_rows.append({
        "variable": var,
        "spearman_with_abs_residual": rho
    })

basic = pd.DataFrame(basic_rows)

# ------------------------------------------------------------
# Partial Spearman controlling |delta v|
#
# Partial Spearman:
# rank variables, regress both target and mechanism metric
# on rank(|delta v|), then correlate residuals.
# ------------------------------------------------------------

def partial_spearman(
    data,
    x,
    y,
    control,
):

    sub = data[
        [x, y, control]
    ].dropna().copy()

    if len(sub) < 5:
        return np.nan, len(sub)

    xr = sub[x].rank().to_numpy(float)
    yr = sub[y].rank().to_numpy(float)
    cr = sub[control].rank().to_numpy(float)

    X = np.column_stack([
        np.ones(len(sub)),
        cr,
    ])

    bx = np.linalg.lstsq(
        X,
        xr,
        rcond=None
    )[0]

    by = np.linalg.lstsq(
        X,
        yr,
        rcond=None
    )[0]

    x_resid = xr - X @ bx
    y_resid = yr - X @ by

    rho = np.corrcoef(
        x_resid,
        y_resid
    )[0, 1]

    return float(rho), len(sub)


mechanism_vars = [
    "direction_coherence",
    "sd_delta_section_speed_mph",
    "relative_section_dispersion",
    "max_abs_section_change_share",
]

partial_rows = []

for var in mechanism_vars:

    rho, n = partial_spearman(
        df,
        "abs_resid",
        var,
        "abs_delta",
    )

    partial_rows.append({
        "mechanism_metric": var,
        "n": n,
        "partial_spearman_controlling_abs_delta": rho,
    })

partial = pd.DataFrame(
    partial_rows
)

# ------------------------------------------------------------
# Repeat only for meaningful overall changes
# ------------------------------------------------------------

threshold_rows = []

for threshold in [
    0.10,
    0.20,
    0.50,
]:

    sub = df[
        df["abs_delta"] >= threshold
    ].copy()

    for var in [
        "direction_coherence",
        "relative_section_dispersion",
        "max_abs_section_change_share",
    ]:

        if len(sub) >= 5:

            rho = (
                sub[
                    ["abs_resid", var]
                ]
                .corr(method="spearman")
                .iloc[0, 1]
            )

        else:
            rho = np.nan

        threshold_rows.append({
            "minimum_abs_delta_mph": threshold,
            "n": len(sub),
            "metric": var,
            "spearman_with_abs_residual": rho,
        })

threshold_df = pd.DataFrame(
    threshold_rows
)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B MAGNITUDE-CONTROLLED "
    "SECTION DIAGNOSTIC"
)
add("=" * 100)

add()
add(
    "BASIC SPEARMAN RELATIONSHIPS"
)
add("-" * 100)
add(
    basic.to_string(index=False)
)

add()
add(
    "PARTIAL SPEARMAN CONTROLLING "
    "ABSOLUTE OVERALL SPEED CHANGE"
)
add("-" * 100)
add(
    partial.to_string(index=False)
)

add()
add(
    "SENSITIVITY AMONG NON-TRIVIAL "
    "OVERALL PERFORMANCE CHANGES"
)
add("-" * 100)
add(
    threshold_df.to_string(index=False)
)

add()
add(
    "INTERPRETATION RULE"
)
add("-" * 100)
add(
    "Do not interpret raw section-speed dispersion as a "
    "mechanism effect if its relationship with residual size "
    "disappears after controlling for absolute overall "
    "performance change."
)
add(
    "Direction coherence and max-absolute-section share are "
    "primarily descriptive mechanism evidence, not predictors."
)

summary = "\n".join(lines)

OUTFILE.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 100)
print("OUTPUT")
print("=" * 100)
print(OUTFILE)
print()
print("DONE")
