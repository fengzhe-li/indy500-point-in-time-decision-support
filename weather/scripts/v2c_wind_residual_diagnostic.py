from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MAP = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_transition_map_v1.csv"
)

WIND = Path(
    "r5_2/manual/r5_2_repeat_analysis_set_v1.csv"
)

CORE = Path(
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
)

OUTDIR = Path(
    "weather/output/v2c_wind_diagnostic"
)
OUTDIR.mkdir(parents=True, exist_ok=True)

OUT_DATA = OUTDIR / "v2c_wind_residual_diagnostic_v1.csv"
OUT_SUMMARY = OUTDIR / "v2c_wind_residual_diagnostic_summary_v1.txt"


def norm_id(x):
    if pd.isna(x):
        return None
    return str(x).strip()


def rank_partial_spearman(x, y, control):
    """
    Partial Spearman:
    rank-transform x, y, control;
    residualize ranked x and y against ranked control;
    correlate residuals.
    """
    d = pd.DataFrame({
        "x": x,
        "y": y,
        "c": control,
    }).dropna()

    if len(d) < 5:
        return np.nan, len(d)

    rx = d["x"].rank(method="average").to_numpy(float)
    ry = d["y"].rank(method="average").to_numpy(float)
    rc = d["c"].rank(method="average").to_numpy(float)

    X = np.column_stack([
        np.ones(len(rc)),
        rc
    ])

    bx = np.linalg.lstsq(X, rx, rcond=None)[0]
    by = np.linalg.lstsq(X, ry, rcond=None)[0]

    ex = rx - X @ bx
    ey = ry - X @ by

    if np.std(ex) == 0 or np.std(ey) == 0:
        return np.nan, len(d)

    rho = np.corrcoef(ex, ey)[0, 1]
    return float(rho), len(d)


tm = pd.read_csv(MAP)
wind = pd.read_csv(WIND)
core = pd.read_csv(CORE)

for df in [tm, wind]:
    for c in ["before_attempt_id", "after_attempt_id"]:
        if c in df.columns:
            df[c] = df[c].map(norm_id)

# ------------------------------------------------------------------
# Merge exact attempt-pair wind evidence onto the 39 linked transitions
# ------------------------------------------------------------------

wind_cols = [
    "before_attempt_id",
    "after_attempt_id",
    "previous_wind_speed_ms",
    "next_wind_speed_ms",
    "delta_wind_speed_ms",
    "previous_gust_ms",
    "next_gust_ms",
    "delta_gust_ms",
    "previous_wind_direction_deg",
    "next_wind_direction_deg",
    "delta_wind_direction_deg",
    "previous_wind_u_ms",
    "previous_wind_v_ms",
    "next_wind_u_ms",
    "next_wind_v_ms",
    "delta_wind_u_ms",
    "delta_wind_v_ms",
    "delta_ptsc_wind",
    "delta_forecast_wind_speed_10m_ms",
    "delta_forecast_gust_ms",
    "analysis_source",
]

wind_cols = [
    c for c in wind_cols
    if c in wind.columns
]

w = wind[wind_cols].copy()

if w.duplicated(
    ["before_attempt_id", "after_attempt_id"]
).any():
    raise RuntimeError(
        "Duplicate attempt pairs exist in wind evidence."
    )

d = tm.merge(
    w,
    on=["before_attempt_id", "after_attempt_id"],
    how="left",
    validate="one_to_one",
)

# ------------------------------------------------------------------
# Attach final-core residual by core_row if available.
# Otherwise use year/car/driver/delta matching.
# ------------------------------------------------------------------

if (
    "core_row" in d.columns
    and d["core_row"].notna().all()
):

    core2 = core.reset_index().rename(
        columns={"index": "core_row"}
    )

    residual_cols = [
        "core_row",
        "delta_four_lap_average_speed_mph",
        "predicted_physical_delta_mph_loyo",
        "residual_loyo_raw",
        "residual_loyo_centered",
    ]

    residual_cols = [
        c for c in residual_cols
        if c in core2.columns
    ]

    d = d.merge(
        core2[residual_cols],
        on="core_row",
        how="left",
        validate="many_to_one",
        suffixes=("", "_core"),
    )

else:
    raise RuntimeError(
        "core_row is required for defensible residual linkage."
    )

# ------------------------------------------------------------------
# Derived diagnostics
# ------------------------------------------------------------------

if "delta_four_lap_average_speed_mph" in d.columns:
    d["abs_delta_speed_mph"] = (
        pd.to_numeric(
            d["delta_four_lap_average_speed_mph"],
            errors="coerce"
        ).abs()
    )
elif "delta_speed_mph" in d.columns:
    d["abs_delta_speed_mph"] = (
        pd.to_numeric(
            d["delta_speed_mph"],
            errors="coerce"
        ).abs()
    )

# IMPORTANT:
# Use raw LOYO residual as model error diagnostic.
# centered residual was created for uncertainty symmetrization.
d["abs_physics_residual_mph"] = (
    pd.to_numeric(
        d["residual_loyo_raw"],
        errors="coerce"
    ).abs()
)

for c in [
    "delta_wind_speed_ms",
    "delta_gust_ms",
    "delta_ptsc_wind",
    "delta_forecast_wind_speed_10m_ms",
    "delta_forecast_gust_ms",
]:
    if c in d.columns:
        d[f"abs_{c}"] = (
            pd.to_numeric(
                d[c],
                errors="coerce"
            ).abs()
        )

# Vector-state change magnitude.
if {
    "delta_wind_u_ms",
    "delta_wind_v_ms"
}.issubset(d.columns):

    du = pd.to_numeric(
        d["delta_wind_u_ms"],
        errors="coerce"
    )

    dv = pd.to_numeric(
        d["delta_wind_v_ms"],
        errors="coerce"
    )

    d["wind_vector_change_ms"] = np.sqrt(
        du ** 2 + dv ** 2
    )

# Current/overall wind severity descriptors.
if {
    "previous_wind_speed_ms",
    "next_wind_speed_ms"
}.issubset(d.columns):

    d["mean_wind_speed_ms"] = (
        pd.to_numeric(
            d["previous_wind_speed_ms"],
            errors="coerce"
        )
        +
        pd.to_numeric(
            d["next_wind_speed_ms"],
            errors="coerce"
        )
    ) / 2

if {
    "previous_gust_ms",
    "next_gust_ms"
}.issubset(d.columns):

    d["mean_gust_ms"] = (
        pd.to_numeric(
            d["previous_gust_ms"],
            errors="coerce"
        )
        +
        pd.to_numeric(
            d["next_gust_ms"],
            errors="coerce"
        )
    ) / 2

d.to_csv(OUT_DATA, index=False)

# ------------------------------------------------------------------
# Coverage
# ------------------------------------------------------------------

candidate_metrics = [
    "abs_delta_wind_speed_ms",
    "abs_delta_gust_ms",
    "wind_vector_change_ms",
    "mean_wind_speed_ms",
    "mean_gust_ms",
    "abs_delta_ptsc_wind",
    "abs_delta_forecast_wind_speed_10m_ms",
    "abs_delta_forecast_gust_ms",
]

candidate_metrics = [
    c for c in candidate_metrics
    if c in d.columns
]

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add("INDY 500 V2-C WIND / PHYSICS-RESIDUAL DIAGNOSTIC")
add("=" * 100)

add()
add("LINKAGE / COVERAGE")
add("-" * 100)
add(f"V2-B linked transitions: {len(d)}")
add(
    "rows with raw LOYO residual: "
    f"{d['residual_loyo_raw'].notna().sum()}/{len(d)}"
)

for metric in candidate_metrics:
    add(
        f"{metric}: "
        f"{d[metric].notna().sum()}/{len(d)}"
    )

# ------------------------------------------------------------------
# Raw Spearman
# ------------------------------------------------------------------

add()
add("RAW SPEARMAN WITH ABSOLUTE PHYSICS RESIDUAL")
add("-" * 100)

raw_results = []

for metric in candidate_metrics:

    q = d[
        [
            metric,
            "abs_physics_residual_mph"
        ]
    ].dropna()

    if len(q) < 5:
        continue

    rho, p = spearmanr(
        q[metric],
        q["abs_physics_residual_mph"]
    )

    raw_results.append(
        (
            metric,
            len(q),
            float(rho),
            float(p),
        )
    )

raw_df = pd.DataFrame(
    raw_results,
    columns=[
        "wind_metric",
        "n",
        "spearman_rho",
        "p_value_descriptive_only",
    ]
)

add(
    raw_df.to_string(
        index=False
    )
)

# ------------------------------------------------------------------
# Partial Spearman controlling |overall delta speed|
# ------------------------------------------------------------------

add()
add(
    "PARTIAL SPEARMAN CONTROLLING ABSOLUTE OVERALL PERFORMANCE CHANGE"
)
add("-" * 100)

partial_results = []

for metric in candidate_metrics:

    rho, n = rank_partial_spearman(
        d[metric],
        d["abs_physics_residual_mph"],
        d["abs_delta_speed_mph"],
    )

    partial_results.append(
        (
            metric,
            n,
            rho,
        )
    )

partial_df = pd.DataFrame(
    partial_results,
    columns=[
        "wind_metric",
        "n",
        "partial_spearman_controlling_abs_delta",
    ]
)

add(
    partial_df.to_string(
        index=False
    )
)

# ------------------------------------------------------------------
# Year stability
# ------------------------------------------------------------------

add()
add("BY-YEAR DESCRIPTIVE SPEARMAN")
add("-" * 100)

year_results = []

for year, g in d.groupby("year"):

    for metric in candidate_metrics:

        q = g[
            [
                metric,
                "abs_physics_residual_mph"
            ]
        ].dropna()

        if len(q) < 4:
            continue

        rho, _ = spearmanr(
            q[metric],
            q["abs_physics_residual_mph"]
        )

        year_results.append(
            (
                year,
                metric,
                len(q),
                float(rho),
            )
        )

year_df = pd.DataFrame(
    year_results,
    columns=[
        "year",
        "wind_metric",
        "n",
        "spearman_rho",
    ]
)

if len(year_df):
    add(
        year_df.to_string(
            index=False
        )
    )
else:
    add("insufficient within-year sample sizes")

# ------------------------------------------------------------------
# Largest residual cases
# ------------------------------------------------------------------

add()
add("LARGEST ABSOLUTE PHYSICS RESIDUAL CASES")
add("-" * 100)

display_cols = [
    "year",
    "car_number",
    "driver_name",
    "delta_speed_mph",
    "abs_physics_residual_mph",
    "delta_wind_speed_ms",
    "delta_gust_ms",
    "wind_vector_change_ms",
    "mean_wind_speed_ms",
    "mean_gust_ms",
]

display_cols = [
    c for c in display_cols
    if c in d.columns
]

add(
    d.sort_values(
        "abs_physics_residual_mph",
        ascending=False
    )[
        display_cols
    ].head(10).to_string(
        index=False
    )
)

add()
add("INTERPRETATION BOUNDARY")
add("-" * 100)
add(
    "This is a residual diagnostic, not a new predictive wind model."
)
add(
    "PTSC and HRRR-derived wind evidence are not merged into a single physical variable."
)
add(
    "Raw wind associations must not be interpreted without the magnitude-controlled result."
)
add(
    "Wind direction is treated through vector-state change where possible rather than raw angular difference."
)
add(
    "No deterministic wind coefficient is justified solely by this diagnostic."
)

summary = "\n".join(lines)

OUT_SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)
print(OUT_DATA)
print(OUT_SUMMARY)
print()
print("DONE")
