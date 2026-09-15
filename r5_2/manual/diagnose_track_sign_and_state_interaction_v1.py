from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

SRC = OUT / "r5_2_repeat_analysis_set_v1.csv"

df = pd.read_csv(SRC)

TARGET = "delta_four_lap_average_speed_mph"
DT = "delta_track_temp_c"
T0 = "previous_track_temp_c"

for c in [TARGET, DT, T0]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

d = df[
    [
        "year",
        "car_number",
        "driver_name",
        "analysis_source",
        TARGET,
        DT,
        T0,
        "before_four_lap_average_speed_mph",
        "after_four_lap_average_speed_mph",
    ]
].dropna(subset=[TARGET, DT]).copy()

# ============================================================
# PART 1 — WHO DRIVES THE ZERO-INTERCEPT SIGN?
# beta = sum(x*y) / sum(x^2)
# ============================================================

print("=" * 150)
print("PART 1 — ZERO-INTERCEPT SIGN CONTRIBUTION")
print("=" * 150)

d["xy_contribution"] = d[DT] * d[TARGET]
d["x2_contribution"] = d[DT] ** 2

beta = d["xy_contribution"].sum() / d["x2_contribution"].sum()

print("N =", len(d))
print("ZERO-INTERCEPT BETA =", round(beta, 6))
print("SUM x*y =", round(d["xy_contribution"].sum(), 6))
print("SUM x^2 =", round(d["x2_contribution"].sum(), 6))

show = [
    "year",
    "car_number",
    "driver_name",
    "analysis_source",
    "before_four_lap_average_speed_mph",
    "after_four_lap_average_speed_mph",
    TARGET,
    DT,
    "xy_contribution",
]

print("\nTOP POSITIVE x*y CONTRIBUTIONS:")
print(
    d.sort_values("xy_contribution", ascending=False)
    [show]
    .head(12)
    .round(6)
    .to_string(index=False)
)

print("\nTOP NEGATIVE x*y CONTRIBUTIONS:")
print(
    d.sort_values("xy_contribution", ascending=True)
    [show]
    .head(12)
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 2 — SENSITIVITY TO EXTREME PERFORMANCE DELTAS
# Diagnostic only; NOT automatically excluding anything.
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — EXTREME-DELTA SENSITIVITY")
print("=" * 150)

rows = []

for threshold in [None, 4.0, 3.0, 2.0, 1.5, 1.0]:

    if threshold is None:
        z = d.copy()
        label = "ALL"
    else:
        z = d[d[TARGET].abs() <= threshold].copy()
        label = f"ABS_DSPEED_LE_{threshold}"

    if len(z) < 5:
        continue

    x = z[DT].to_numpy(float)
    y = z[TARGET].to_numpy(float)

    beta0 = np.sum(x * y) / np.sum(x * x)

    pear = pd.Series(x).corr(pd.Series(y), method="pearson")
    spear = pd.Series(x).corr(pd.Series(y), method="spearman")

    rows.append({
        "subset": label,
        "n": len(z),
        "zero_intercept_beta": beta0,
        "pearson": pear,
        "spearman": spear,
        "median_abs_dspeed": np.median(np.abs(y)),
        "max_abs_dspeed": np.max(np.abs(y)),
    })

sens = pd.DataFrame(rows)

print(
    sens.round(6).to_string(index=False)
)

sens.to_csv(
    OUT / "track_sign_extreme_delta_sensitivity_v1.csv",
    index=False
)


# ============================================================
# PART 3 — CURRENT-STATE INTERACTION
#
# Δspeed =
# β1 * Δtrack
# + β2 * Δtrack * (T_before - center)
#
# Still guarantees:
# Δtrack = 0 -> predicted thermal Δspeed = 0
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — CURRENT-TRACK-STATE INTERACTION")
print("=" * 150)

z = df[
    [
        "year",
        TARGET,
        DT,
        T0,
    ]
].dropna().copy()

def fit_zero(X, y, ridge=0.0):
    p = X.shape[1]
    return np.linalg.solve(
        X.T @ X + ridge * np.eye(p),
        X.T @ y
    )

def metrics(y, pred):
    e = pred - y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }

model_rows = []

for model_name in [
    "TRACK_ONLY",
    "TRACK_STATE_INTERACTION",
]:

    preds = np.full(len(z), np.nan)

    for yr in sorted(z["year"].unique()):

        train = z["year"] != yr
        test = z["year"] == yr

        train_df = z.loc[train].copy()
        test_df = z.loc[test].copy()

        center = train_df[T0].mean()

        if model_name == "TRACK_ONLY":

            Xtr = train_df[[DT]].to_numpy(float)
            Xte = test_df[[DT]].to_numpy(float)

        else:

            train_df["_interaction"] = (
                train_df[DT] *
                (train_df[T0] - center)
            )

            test_df["_interaction"] = (
                test_df[DT] *
                (test_df[T0] - center)
            )

            Xtr = train_df[
                [DT, "_interaction"]
            ].to_numpy(float)

            Xte = test_df[
                [DT, "_interaction"]
            ].to_numpy(float)

        ytr = train_df[TARGET].to_numpy(float)

        beta = fit_zero(Xtr, ytr)

        preds[test.to_numpy()] = Xte @ beta

    valid = ~np.isnan(preds)

    y = z[TARGET].to_numpy(float)

    m = metrics(
        y[valid],
        preds[valid]
    )

    base = metrics(
        y[valid],
        np.zeros(valid.sum())
    )

    model_rows.append({
        "model": model_name,
        "n": int(valid.sum()),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "no_change_mae": base["mae"],
        "no_change_rmse": base["rmse"],
        "beats_no_change_mae":
            m["mae"] < base["mae"],
        "beats_no_change_rmse":
            m["rmse"] < base["rmse"],
    })

model_res = pd.DataFrame(model_rows)

print("\nLOYO PERFORMANCE:")
print(
    model_res.round(6).to_string(index=False)
)

# Full-data coefficients for interpretation only
center = z[T0].mean()

z["_interaction"] = (
    z[DT] * (z[T0] - center)
)

X = z[
    [DT, "_interaction"]
].to_numpy(float)

y = z[TARGET].to_numpy(float)

beta = fit_zero(X, y)

print("\nFULL-DATA STATE-INTERACTION FIT:")
print("REFERENCE TRACK TEMP =", round(center, 4))
print("beta_delta_track =", round(beta[0], 6))
print("beta_delta_track_x_current_state =", round(beta[1], 6))

# implied local thermal slope at several current track temperatures
for temp in [30, 35, 40, 45, 50, 55]:
    local_slope = beta[0] + beta[1] * (temp - center)
    print(
        f"implied slope at current track {temp}C =",
        round(local_slope, 6),
        "mph per C"
    )

model_res.to_csv(
    OUT / "track_state_interaction_loyo_v1.csv",
    index=False
)

print("\n" + "=" * 150)
print("TRACK_SIGN_AND_STATE_INTERACTION_DIAGNOSTIC_COMPLETE")
print("=" * 150)
