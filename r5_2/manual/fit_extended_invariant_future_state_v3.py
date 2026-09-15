from pathlib import Path
import pandas as pd
import numpy as np
import json

from scipy.optimize import nnls

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

SRC = OUT / "track_temperature_extended_horizon_panel_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_track_temp_c"

for c in [
    Y,
    "actual_horizon_min",
    "requested_horizon_min",
    "current_track_temp_c",
    "delta_ambient_temp_c",
]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

TRACK_REFERENCE_C = 40.0

# Actual elapsed time is the correct physical horizon.
df["h"] = df["actual_horizon_min"] / 60.0
df["h2"] = df["h"] ** 2

df["h_x_track_state"] = (
    df["h"]
    *
    (df["current_track_temp_c"] - TRACK_REFERENCE_C)
)

# ============================================================
# helpers
# ============================================================

def fit_ols_zero(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def fit_huber_zero(X, y, delta=1.345, max_iter=100):

    beta = fit_ols_zero(X, y)

    for _ in range(max_iter):

        r = y - X @ beta

        med = np.median(r)
        mad = np.median(np.abs(r - med))

        scale = (
            mad / 0.6745
            if mad > 0
            else np.std(r)
        )

        if not np.isfinite(scale) or scale < 1e-10:
            break

        u = r / scale

        w = np.ones(len(r))

        mask = np.abs(u) > delta
        w[mask] = delta / np.abs(u[mask])

        sw = np.sqrt(w)

        new_beta = np.linalg.lstsq(
            X * sw[:, None],
            y * sw,
            rcond=None
        )[0]

        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta


def metrics(y, pred):

    e = pred - y

    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }


MODELS = {

    "EXTENDED_THERMAL_LINEAR": [
        "h",
        "h_x_track_state",
        "delta_ambient_temp_c",
    ],

    "EXTENDED_THERMAL_QUADRATIC": [
        "h",
        "h2",
        "h_x_track_state",
        "delta_ambient_temp_c",
    ],
}


# ============================================================
# PART 1 — LOYO MODEL SCREEN
# ============================================================

print("=" * 150)
print("PART 1 — EXTENDED INVARIANT FUTURE-STATE LOYO")
print("=" * 150)

results = []

stored_loyo = {}

for name, feats in MODELS.items():

    z = df[
        [
            "year",
            "requested_horizon_min",
            Y,
        ] + feats
    ].dropna().copy()

    pred = np.full(len(z), np.nan)

    for held in sorted(z["year"].unique()):

        train = z["year"] != held
        test = z["year"] == held

        Xtr = z.loc[train, feats].to_numpy(float)
        ytr = z.loc[train, Y].to_numpy(float)

        Xte = z.loc[test, feats].to_numpy(float)

        beta = fit_huber_zero(Xtr, ytr)

        pred[test.to_numpy()] = Xte @ beta

    valid = np.isfinite(pred)

    y = z[Y].to_numpy(float)[valid]
    p = pred[valid]

    m = metrics(y, p)
    base = metrics(y, np.zeros(len(y)))

    results.append({
        "model": name,
        "n": len(y),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "baseline_mae": base["mae"],
        "baseline_rmse": base["rmse"],
        "beats_baseline_mae":
            m["mae"] < base["mae"],
        "beats_baseline_rmse":
            m["rmse"] < base["rmse"],
    })

    z["pred_loyo"] = pred
    z["residual_loyo"] = z[Y] - pred

    stored_loyo[name] = z


res = pd.DataFrame(results)

print(
    res.sort_values(["mae", "rmse"])
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 2 — SELECT BEST MODEL + YEAR CHECK
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — BEST MODEL HELD-OUT YEAR")
print("=" * 150)

best_name = (
    res.sort_values(["mae", "rmse"])
    .iloc[0]["model"]
)

feats = MODELS[best_name]

print("BEST MODEL =", best_name)

z = stored_loyo[best_name].copy()

for yr, g in z.groupby("year"):

    y = g[Y].to_numpy(float)
    p = g["pred_loyo"].to_numpy(float)

    m = metrics(y, p)
    base = metrics(y, np.zeros(len(y)))

    print(
        "year =", int(yr),
        "n =", len(g),
        "MAE =", round(m["mae"], 6),
        "base =", round(base["mae"], 6),
        "RMSE =", round(m["rmse"], 6),
        "base_RMSE =", round(base["rmse"], 6),
        "beats_MAE =", m["mae"] < base["mae"],
        "beats_RMSE =", m["rmse"] < base["rmse"],
    )


# ============================================================
# PART 3 — FULL FIT COEFFICIENTS
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — FINAL EXTENDED FUTURE-STATE COEFFICIENTS")
print("=" * 150)

fit_df = df[[Y] + feats].dropna().copy()

X = fit_df[feats].to_numpy(float)
y = fit_df[Y].to_numpy(float)

beta = fit_huber_zero(X, y)

print("MODEL =", best_name)
print("TRACK_REFERENCE_C =", TRACK_REFERENCE_C)

for f, b in zip(feats, beta):
    print(
        f,
        "=",
        round(float(b), 8)
    )


# ============================================================
# PART 4 — ZERO WAIT SANITY
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — ZERO-WAIT FUTURE-STATE SANITY")
print("=" * 150)

for track in [25, 35, 40, 45, 55]:

    values = {
        "h": 0.0,
        "h2": 0.0,
        "h_x_track_state":
            0.0 * (track - TRACK_REFERENCE_C),
        "delta_ambient_temp_c": 0.0,
    }

    x = np.array(
        [values[f] for f in feats],
        float
    )

    pred = x @ beta

    print(
        "current_track =", track,
        "wait = 0",
        "predicted_delta_track =",
        round(float(pred), 12)
    )

    assert abs(pred) < 1e-12

print(
    "PASS: wait=0 => future track change=0"
)


# ============================================================
# PART 5 — ERROR BY HORIZON
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — LOYO ERROR BY HORIZON")
print("=" * 150)

horizon_stats = []

for h, g in z.groupby(
    "requested_horizon_min"
):

    r = g["residual_loyo"].to_numpy(float)

    row = {
        "horizon_min": float(h),
        "n": len(r),
        "mae": np.mean(np.abs(r)),
        "rmse": np.sqrt(np.mean(r**2)),
        "bias": np.mean(
            g["pred_loyo"].to_numpy(float)
            -
            g[Y].to_numpy(float)
        ),
        "residual_sd":
            np.std(r, ddof=1),
        "residual_mad":
            np.median(
                np.abs(
                    r - np.median(r)
                )
            ),
    }

    horizon_stats.append(row)

hs = pd.DataFrame(horizon_stats)

print(
    hs.round(6)
    .to_string(index=False)
)


# ============================================================
# PART 6 — HORIZON-DEPENDENT UNCERTAINTY SCALE
#
# Fit:
#
# sigma(h) =
# a * sqrt(h_hours)
# + b * h_hours
#
# with a,b >= 0.
#
# Therefore sigma(0)=0 automatically.
# ============================================================

print("\n" + "=" * 150)
print("PART 6 — FUTURE-TRACK UNCERTAINTY SCALE")
print("=" * 150)

hh = hs["horizon_min"].to_numpy(float) / 60.0

A = np.column_stack([
    np.sqrt(hh),
    hh,
])

target_sigma = hs[
    "residual_sd"
].to_numpy(float)

scale_beta, _ = nnls(
    A,
    target_sigma
)

a = scale_beta[0]
b = scale_beta[1]

hs["fitted_sigma"] = (
    a * np.sqrt(hh)
    +
    b * hh
)

print(
    "sigma(h_hours) =",
    round(a, 6),
    "* sqrt(h) +",
    round(b, 6),
    "* h"
)

print("\nObserved vs fitted:")
print(
    hs[
        [
            "horizon_min",
            "n",
            "residual_sd",
            "fitted_sigma",
        ]
    ]
    .round(6)
    .to_string(index=False)
)

print(
    "\nsigma(0 min) =",
    0.0
)

for minutes in [
    15, 30, 45, 60,
    90, 120, 150, 180
]:

    h = minutes / 60.0

    sigma = (
        a * np.sqrt(h)
        +
        b * h
    )

    print(
        f"sigma({minutes} min) =",
        round(float(sigma), 6)
    )


# ============================================================
# PART 7 — STANDARDIZED EMPIRICAL RESIDUAL POOL
#
# residual / sigma(h)
#
# This keeps the empirical heavy-tail shape while allowing
# uncertainty magnitude to expand with wait time.
# ============================================================

print("\n" + "=" * 150)
print("PART 7 — STANDARDIZED RESIDUAL POOL")
print("=" * 150)

z["horizon_hours"] = (
    z["requested_horizon_min"] / 60.0
)

z["sigma_h"] = (
    a * np.sqrt(
        z["horizon_hours"]
    )
    +
    b * z["horizon_hours"]
)

z["standardized_residual"] = (
    z["residual_loyo"]
    /
    z["sigma_h"]
)

sr = z[
    "standardized_residual"
].replace(
    [np.inf, -np.inf],
    np.nan
).dropna().to_numpy(float)

# Remove location shift;
# track-state uncertainty should not create systematic drift.
sr = sr - np.median(sr)

print("N =", len(sr))
print("mean =", round(np.mean(sr), 6))
print("median =", round(np.median(sr), 6))
print("SD =", round(np.std(sr, ddof=1), 6))

print(
    "5/25/50/75/95 =",
    np.round(
        np.percentile(
            sr,
            [5, 25, 50, 75, 95]
        ),
        6
    )
)


# ============================================================
# PART 8 — SAVE FINAL FUTURE STATE BUNDLE
# ============================================================

MODEL = {
    "version":
        "R5.2_EXTENDED_INVARIANT_FUTURE_STATE_V3",

    "validated_horizon_minutes": {
        "minimum": 0,
        "maximum": 180,
    },

    "target":
        "delta_track_temp_c",

    "model":
        best_name,

    "features":
        feats,

    "track_reference_c":
        TRACK_REFERENCE_C,

    "fit":
        "zero-intercept Huber",

    "coefficients": {
        f: float(v)
        for f, v in zip(
            feats,
            beta
        )
    },

    "zero_wait_invariance":
        True,

    "uncertainty_scale": {
        "formula":
            "sigma(h)=a*sqrt(h_hours)+b*h_hours",

        "a":
            float(a),

        "b":
            float(b),

        "sigma_at_zero":
            0.0,
    },

    "residual_shape":
        "median-centered standardized empirical LOYO residuals",
}

MODEL_FILE = (
    OUT /
    "extended_invariant_future_state_model_v3.json"
)

with open(
    MODEL_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        MODEL,
        f,
        indent=2
    )


SCREEN_FILE = (
    OUT /
    "extended_invariant_future_state_screen_v3.csv"
)

res.to_csv(
    SCREEN_FILE,
    index=False
)


HORIZON_FILE = (
    OUT /
    "extended_future_state_horizon_uncertainty_v3.csv"
)

hs.to_csv(
    HORIZON_FILE,
    index=False
)


RESID_FILE = (
    OUT /
    "extended_future_state_standardized_residuals_v3.csv"
)

pd.DataFrame({
    "standardized_residual":
        sr
}).to_csv(
    RESID_FILE,
    index=False
)


print("\n" + "=" * 150)
print("OUTPUTS")
print("=" * 150)

print(MODEL_FILE.relative_to(ROOT))
print(SCREEN_FILE.relative_to(ROOT))
print(HORIZON_FILE.relative_to(ROOT))
print(RESID_FILE.relative_to(ROOT))

print(
    "\nEXTENDED_INVARIANT_FUTURE_STATE_V3_COMPLETE"
)
