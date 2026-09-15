from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

REPEAT = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"
FADE = ROOT / "r5_1/output/day1_within_run_fade_physics_v1.csv"

repeat = pd.read_csv(REPEAT)
fade = pd.read_csv(FADE)


# ============================================================
# BASIC HELPERS
# ============================================================

def num(df, c):
    return pd.to_numeric(df[c], errors="coerce")

def metrics(y, pred):
    e = pred - y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e ** 2)),
        "bias": np.mean(e),
    }

def fit_zero_intercept(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta

def fit_with_intercept(X, y):
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return beta

def pred_with_intercept(X, beta):
    X1 = np.column_stack([np.ones(len(X)), X])
    return X1 @ beta


# ============================================================
# PART 1
# SAME-CAR REPEAT
#
# PRIMARY PHYSICAL MODEL MUST PASS THROUGH ORIGIN:
# delta physical = 0 -> delta physical performance = 0
# ============================================================

print("\n" + "=" * 150)
print("PART 1 — SAME-CAR REPEAT ZERO-INTERCEPT MODEL SCREEN")
print("=" * 150)

repeat_models = {
    "R0_TRACK_ONLY": [
        "delta_track_temp_c",
    ],
    "R1_TRACK_GUST": [
        "delta_track_temp_c",
        "delta_gust_ms",
    ],
    "R2_TRACK_CLOUD": [
        "delta_track_temp_c",
        "delta_cloud_cover_pct",
    ],
    "R3_TRACK_GUST_CLOUD": [
        "delta_track_temp_c",
        "delta_gust_ms",
        "delta_cloud_cover_pct",
    ],
    "R4_TRACK_WIND_VECTOR": [
        "delta_track_temp_c",
        "delta_wind_u_ms",
        "delta_wind_v_ms",
    ],
    "R5_TRACK_ATMOSPHERE": [
        "delta_track_temp_c",
        "delta_air_density_kg_m3",
    ],
}

target = "delta_four_lap_average_speed_mph"

repeat_results = []
repeat_coeffs = []

for model_name, feats in repeat_models.items():

    cols = [target, "year"] + feats
    d = repeat[cols].copy()

    for c in [target] + feats:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna()

    if len(d) < 10:
        continue

    y = d[target].to_numpy(float)
    X = d[feats].to_numpy(float)

    # full-data coefficients
    beta = fit_zero_intercept(X, y)

    for f, b in zip(feats, beta):
        repeat_coeffs.append({
            "model": model_name,
            "feature": f,
            "coefficient": b,
            "n": len(d),
        })

    # LOYO
    preds = np.full(len(d), np.nan)

    years = sorted(d["year"].unique())

    for yr in years:
        train = d["year"] != yr
        test = d["year"] == yr

        if train.sum() < len(feats) + 2:
            continue

        b = fit_zero_intercept(
            d.loc[train, feats].to_numpy(float),
            d.loc[train, target].to_numpy(float),
        )

        preds[test] = (
            d.loc[test, feats].to_numpy(float) @ b
        )

    valid = ~np.isnan(preds)

    if valid.sum() == 0:
        continue

    m = metrics(y[valid], preds[valid])

    # no-change benchmark
    baseline = metrics(
        y[valid],
        np.zeros(valid.sum())
    )

    repeat_results.append({
        "model": model_name,
        "n": len(d),
        "loyo_n": int(valid.sum()),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "no_change_mae": baseline["mae"],
        "no_change_rmse": baseline["rmse"],
        "beats_no_change_mae": m["mae"] < baseline["mae"],
        "beats_no_change_rmse": m["rmse"] < baseline["rmse"],
    })


repeat_res = pd.DataFrame(repeat_results)
repeat_coef = pd.DataFrame(repeat_coeffs)

print("\nMODEL PERFORMANCE:")
print(
    repeat_res.sort_values("mae")
    .round(5)
    .to_string(index=False)
)

print("\nCOEFFICIENTS:")
print(
    repeat_coef.round(6)
    .to_string(index=False)
)

repeat_res.to_csv(
    OUT / "repeat_zero_intercept_model_screen_v1.csv",
    index=False
)

repeat_coef.to_csv(
    OUT / "repeat_zero_intercept_coefficients_v1.csv",
    index=False
)


# ============================================================
# PART 2
# BOOTSTRAP TRACK TEMP COEFFICIENT
#
# zero-intercept:
# delta speed = beta_track * delta track temp
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — TRACK TEMP ZERO-INTERCEPT BOOTSTRAP")
print("=" * 150)

d = repeat[
    ["delta_four_lap_average_speed_mph", "delta_track_temp_c"]
].copy()

d.iloc[:, 0] = pd.to_numeric(d.iloc[:, 0], errors="coerce")
d.iloc[:, 1] = pd.to_numeric(d.iloc[:, 1], errors="coerce")
d = d.dropna()

y = d["delta_four_lap_average_speed_mph"].to_numpy(float)
x = d["delta_track_temp_c"].to_numpy(float)

beta_track = np.sum(x * y) / np.sum(x * x)

rng = np.random.default_rng(500)

boots = []

for _ in range(10000):
    idx = rng.integers(0, len(d), len(d))

    xb = x[idx]
    yb = y[idx]

    denom = np.sum(xb * xb)

    if denom > 0:
        boots.append(
            np.sum(xb * yb) / denom
        )

boots = np.array(boots)

print("N =", len(d))
print("beta_track =", round(beta_track, 6))
print(
    "bootstrap 95% =",
    round(np.percentile(boots, 2.5), 6),
    "to",
    round(np.percentile(boots, 97.5), 6)
)
print(
    "P(beta_track < 0) =",
    round(np.mean(boots < 0), 5)
)


# ============================================================
# PART 3
# WITHIN-CAR-YEAR FADE RESPONSE
#
# Remove each car-year's natural degradation baseline.
#
# Target:
# fade residual relative to same car-year mean.
#
# This avoids comparing naturally high-fade and low-fade cars directly.
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — WITHIN-CAR-YEAR FADE PHYSICAL RESPONSE")
print("=" * 150)

fade_cols = [
    "year",
    "car_number",
    "lap4_minus_lap1",
    "track_temperature_c_assembled",
    "forecast_shortwave_radiation_wm2",
    "wind_u_ms",
    "wind_v_ms",
    "forecast_gust_ms",
]

for c in fade_cols:
    if c not in fade.columns:
        fade[c] = np.nan

fd = fade[fade_cols].copy()

for c in fade_cols[2:]:
    fd[c] = pd.to_numeric(fd[c], errors="coerce")

# only car-years with >=2 usable complete runs
counts = (
    fd.groupby(["year", "car_number"])
    ["lap4_minus_lap1"]
    .count()
)

valid_groups = counts[counts >= 2].index

fd = fd.set_index(["year", "car_number"])
fd = fd.loc[
    fd.index.isin(valid_groups)
].reset_index()

features = {
    "F0_TRACK_ONLY": [
        "track_temperature_c_assembled",
    ],
    "F1_SHORTWAVE_ONLY": [
        "forecast_shortwave_radiation_wm2",
    ],
    "F2_TRACK_SHORTWAVE": [
        "track_temperature_c_assembled",
        "forecast_shortwave_radiation_wm2",
    ],
    "F3_TRACK_SHORTWAVE_WINDV": [
        "track_temperature_c_assembled",
        "forecast_shortwave_radiation_wm2",
        "wind_v_ms",
    ],
    "F4_TRACK_SHORTWAVE_GUST": [
        "track_temperature_c_assembled",
        "forecast_shortwave_radiation_wm2",
        "forecast_gust_ms",
    ],
}

fade_results = []

for model_name, feats in features.items():

    cols = [
        "year",
        "car_number",
        "lap4_minus_lap1",
    ] + feats

    d = fd[cols].dropna().copy()

    if len(d) < 15:
        continue

    # within-car-year centering
    group = d.groupby(["year", "car_number"])

    d["_y"] = (
        d["lap4_minus_lap1"]
        - group["lap4_minus_lap1"].transform("mean")
    )

    centered_feats = []

    for f in feats:
        cf = "_c_" + f
        d[cf] = d[f] - group[f].transform("mean")
        centered_feats.append(cf)

    # rows with effectively no physical within-group variation can remain;
    # zero-intercept structure handles them naturally.

    preds = np.full(len(d), np.nan)

    for yr in sorted(d["year"].unique()):
        train = d["year"] != yr
        test = d["year"] == yr

        if train.sum() < len(feats) + 2:
            continue

        Xtr = d.loc[train, centered_feats].to_numpy(float)
        ytr = d.loc[train, "_y"].to_numpy(float)

        beta = fit_zero_intercept(Xtr, ytr)

        preds[test] = (
            d.loc[test, centered_feats].to_numpy(float)
            @ beta
        )

    valid = ~np.isnan(preds)

    if valid.sum() == 0:
        continue

    y = d["_y"].to_numpy(float)

    m = metrics(
        y[valid],
        preds[valid]
    )

    baseline = metrics(
        y[valid],
        np.zeros(valid.sum())
    )

    # full coefficients
    Xall = d[centered_feats].to_numpy(float)
    yall = d["_y"].to_numpy(float)

    beta_all = fit_zero_intercept(Xall, yall)

    row = {
        "model": model_name,
        "n": len(d),
        "car_year_groups": d.groupby(
            ["year", "car_number"]
        ).ngroups,
        "loyo_n": int(valid.sum()),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "no_change_mae": baseline["mae"],
        "no_change_rmse": baseline["rmse"],
        "beats_no_change_mae": (
            m["mae"] < baseline["mae"]
        ),
    }

    for f, b in zip(feats, beta_all):
        row["beta_" + f] = b

    fade_results.append(row)


fade_res = pd.DataFrame(fade_results)

print(
    fade_res.sort_values("mae")
    .round(6)
    .to_string(index=False)
)

fade_res.to_csv(
    OUT / "within_car_year_fade_model_screen_v1.csv",
    index=False
)


# ============================================================
# PART 4
# DIRECTIONAL CONSISTENCY CHECK
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — THERMAL DIRECTION CONSISTENCY")
print("=" * 150)

# raw fade relation
fade_pair = fade[
    ["lap4_minus_lap1", "track_temperature_c_assembled"]
].copy()

fade_pair.iloc[:, 0] = pd.to_numeric(
    fade_pair.iloc[:, 0], errors="coerce"
)
fade_pair.iloc[:, 1] = pd.to_numeric(
    fade_pair.iloc[:, 1], errors="coerce"
)

fade_pair = fade_pair.dropna()

fade_spear = fade_pair[
    "lap4_minus_lap1"
].corr(
    fade_pair["track_temperature_c_assembled"],
    method="spearman"
)

repeat_pair = repeat[
    [
        "delta_four_lap_average_speed_mph",
        "delta_track_temp_c",
    ]
].copy()

repeat_pair.iloc[:, 0] = pd.to_numeric(
    repeat_pair.iloc[:, 0], errors="coerce"
)
repeat_pair.iloc[:, 1] = pd.to_numeric(
    repeat_pair.iloc[:, 1], errors="coerce"
)

repeat_pair = repeat_pair.dropna()

repeat_spear = repeat_pair[
    "delta_four_lap_average_speed_mph"
].corr(
    repeat_pair["delta_track_temp_c"],
    method="spearman"
)

print("RAW FADE track-temp Spearman:", round(fade_spear, 5))
print("REPEAT delta track-temp Spearman:", round(repeat_spear, 5))

print("\nExpected thermal consistency:")
print(
    "track temp higher -> Lap4-Lap1 more negative -> fade worse"
)
print(
    "track temp decreases -> delta speed more positive -> repeat improves"
)

if fade_spear < 0 and repeat_spear < 0:
    print("\nTHERMAL_DIRECTION_CONSISTENT = TRUE")
else:
    print("\nTHERMAL_DIRECTION_CONSISTENT = FALSE")


print("\n" + "=" * 150)
print("COMPACT_PHYSICS_MODEL_SCREEN_V1_COMPLETE")
print("=" * 150)
