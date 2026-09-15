from pathlib import Path
import pandas as pd
import numpy as np
import json

from scipy.optimize import lsq_linear

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
SRC = OUT / "r5_2_repeat_analysis_set_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_four_lap_average_speed_mph"
TRACK = "delta_track_temp_c"
AIR = "delta_air_temp_c"

for c in [Y, TRACK, AIR]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

d = df[
    [
        "year",
        "car_number",
        "driver_name",
        Y,
        TRACK,
        AIR,
    ]
].dropna().copy()

FEATURES = [TRACK, AIR]

LOWER = np.array([-np.inf, -np.inf], float)
UPPER = np.array([0.0, np.inf], float)


# ============================================================
# helpers
# ============================================================

def constrained_ls(X, y):
    return lsq_linear(
        X,
        y,
        bounds=(LOWER, UPPER),
        method="trf"
    ).x


def constrained_huber(X, y, delta=1.345, max_iter=100):

    beta = constrained_ls(X, y)

    for _ in range(max_iter):

        resid = y - X @ beta

        med = np.median(resid)
        mad = np.median(np.abs(resid - med))

        scale = (
            mad / 0.6745
            if mad > 0
            else np.std(resid)
        )

        if not np.isfinite(scale) or scale < 1e-10:
            break

        u = resid / scale
        w = np.ones(len(resid))

        large = np.abs(u) > delta
        w[large] = delta / np.abs(u[large])

        sw = np.sqrt(w)

        new_beta = lsq_linear(
            X * sw[:, None],
            y * sw,
            bounds=(LOWER, UPPER),
            method="trf"
        ).x

        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta


def metrics(y, pred):
    e = pred - y
    return {
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e**2))),
        "bias": float(np.mean(e)),
    }


# ============================================================
# PART 1 — FINAL ROBUST MEAN CORE
# ============================================================

print("=" * 150)
print("PART 1 — FINAL ROBUST PHYSICS MEAN CORE")
print("=" * 150)

X = d[FEATURES].to_numpy(float)
y = d[Y].to_numpy(float)

beta = constrained_huber(X, y)

print("N =", len(d))
print("beta_track =", round(beta[0], 8))
print("beta_ambient =", round(beta[1], 8))

pred_full = X @ beta
resid_raw = y - pred_full

print("\nFull-data diagnostic:")
print("MAE =", round(np.mean(np.abs(resid_raw)), 6))
print("RMSE =", round(np.sqrt(np.mean(resid_raw**2)), 6))
print("Residual mean =", round(np.mean(resid_raw), 6))
print("Residual median =", round(np.median(resid_raw), 6))


# ============================================================
# PART 2 — LOYO OUT-OF-YEAR RESIDUALS
#
# These are preferred for uncertainty calibration.
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — LOYO OUT-OF-YEAR RESIDUAL CALIBRATION")
print("=" * 150)

pred_loyo = np.full(len(d), np.nan)

held_rows = []

for held in sorted(d["year"].unique()):

    train = d["year"] != held
    test = d["year"] == held

    Xtr = d.loc[train, FEATURES].to_numpy(float)
    ytr = d.loc[train, Y].to_numpy(float)
    Xte = d.loc[test, FEATURES].to_numpy(float)
    yte = d.loc[test, Y].to_numpy(float)

    b = constrained_huber(Xtr, ytr)
    p = Xte @ b

    pred_loyo[test.to_numpy()] = p

    m = metrics(yte, p)
    base = metrics(yte, np.zeros(len(yte)))

    held_rows.append({
        "held_out_year": int(held),
        "n": int(len(yte)),
        "beta_track": float(b[0]),
        "beta_ambient": float(b[1]),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "baseline_mae": base["mae"],
        "baseline_rmse": base["rmse"],
    })

held_df = pd.DataFrame(held_rows)

print(held_df.round(6).to_string(index=False))

d["predicted_physical_delta_mph_loyo"] = pred_loyo
d["residual_loyo_raw"] = (
    d[Y] - d["predicted_physical_delta_mph_loyo"]
)

# CRITICAL:
# Do not retain average later-attempt improvement as an intercept.
# Median-center unexplained residual component.
resid_center = float(np.median(d["residual_loyo_raw"]))

d["residual_loyo_centered"] = (
    d["residual_loyo_raw"] - resid_center
)

r = d["residual_loyo_centered"].to_numpy(float)

print("\nLOYO residual center removed =", round(resid_center, 6))
print("Centered residual median =", round(np.median(r), 6))
print("Centered residual mean =", round(np.mean(r), 6))
print("Centered residual SD =", round(np.std(r, ddof=1), 6))
print(
    "Centered residual percentiles 2.5/5/25/50/75/95/97.5 =",
    np.round(
        np.percentile(
            r,
            [2.5, 5, 25, 50, 75, 95, 97.5]
        ),
        6
    )
)


# ============================================================
# PART 3 — COEFFICIENT BOOTSTRAP
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — COEFFICIENT BOOTSTRAP")
print("=" * 150)

rng = np.random.default_rng(500)

NBOOT = 5000

boots = np.empty((NBOOT, 2))

for i in range(NBOOT):

    idx = rng.integers(
        0,
        len(d),
        len(d)
    )

    boots[i] = constrained_huber(
        X[idx],
        y[idx]
    )

for j, feature in enumerate(FEATURES):

    q = np.percentile(
        boots[:, j],
        [2.5, 25, 50, 75, 97.5]
    )

    print(
        feature,
        "2.5/25/50/75/97.5 =",
        np.round(q, 6)
    )


# ============================================================
# PART 4 — HISTORICAL PROBABILISTIC BACKTEST
#
# Draw:
# beta uncertainty
# +
# median-centered LOYO empirical residual uncertainty
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — HISTORICAL PROBABILISTIC BACKTEST")
print("=" * 150)

NSIM = 20000

backtest = []

for i, row in d.iterrows():

    x = np.array([
        row[TRACK],
        row[AIR]
    ], float)

    bidx = rng.integers(
        0,
        len(boots),
        NSIM
    )

    ridx = rng.integers(
        0,
        len(r),
        NSIM
    )

    sim = (
        boots[bidx] @ x
        +
        r[ridx]
    )

    actual = row[Y]

    lo80, hi80 = np.percentile(
        sim,
        [10, 90]
    )

    lo90, hi90 = np.percentile(
        sim,
        [5, 95]
    )

    p_improve = float(
        np.mean(sim > 0)
    )

    backtest.append({
        "year": row["year"],
        "car_number": row["car_number"],
        "driver_name": row["driver_name"],

        "actual_delta_speed_mph": actual,

        "predicted_median_mph":
            float(np.median(sim)),

        "predicted_mean_mph":
            float(np.mean(sim)),

        "p_improve":
            p_improve,

        "lower_80":
            float(lo80),

        "upper_80":
            float(hi80),

        "lower_90":
            float(lo90),

        "upper_90":
            float(hi90),

        "inside_80":
            bool(lo80 <= actual <= hi80),

        "inside_90":
            bool(lo90 <= actual <= hi90),
    })

bt = pd.DataFrame(backtest)

print(
    "80% empirical interval coverage =",
    round(bt["inside_80"].mean(), 4)
)

print(
    "90% empirical interval coverage =",
    round(bt["inside_90"].mean(), 4)
)

print(
    "median absolute probabilistic-point error =",
    round(
        np.median(
            np.abs(
                bt["predicted_median_mph"]
                -
                bt["actual_delta_speed_mph"]
            )
        ),
        6
    )
)

print("\nP(improve) diagnostic:")
print(
    bt[
        [
            "actual_delta_speed_mph",
            "predicted_median_mph",
            "p_improve",
            "inside_80",
            "inside_90",
        ]
    ]
    .sort_values("p_improve")
    .round(4)
    .to_string(index=False)
)


# ============================================================
# PART 5 — ZERO-STATE SANITY TEST
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — ZERO-PHYSICAL-CHANGE SANITY TEST")
print("=" * 150)

zero_x = np.array([0.0, 0.0])

physical_draws = boots @ zero_x

print(
    "physical mean correction at zero state change =",
    float(np.mean(physical_draws))
)

print(
    "physical median correction at zero state change =",
    float(np.median(physical_draws))
)

assert np.allclose(
    physical_draws,
    0.0,
    atol=1e-12
)

print("PASS: Δphysical = 0 => physical correction = 0")


# ============================================================
# PART 6 — SAVE FROZEN PROBABILISTIC CORE BUNDLE
# ============================================================

print("\n" + "=" * 150)
print("PART 6 — SAVE MODEL BUNDLE")
print("=" * 150)

MODEL = {
    "version":
        "R5.2_PROBABILISTIC_PHYSICS_CORE_V1",

    "target":
        "delta_four_lap_average_speed_mph",

    "performance_unit":
        "mph",

    "observation_unit":
        "one complete four-lap qualifying attempt",

    "mean_core": {
        "features": [
            TRACK,
            AIR,
        ],

        "coefficient_constraints": {
            TRACK: "<=0",
            AIR: "unconstrained",
        },

        "full_data_huber_coefficients": {
            TRACK: float(beta[0]),
            AIR: float(beta[1]),
        },

        "generic_reattempt_intercept":
            0.0,
    },

    "uncertainty": {
        "coefficient_bootstrap_draws":
            NBOOT,

        "residual_source":
            "leave-one-year-out residuals",

        "residual_centering":
            "median centered",

        "removed_residual_median_mph":
            resid_center,

        "residual_sd_mph":
            float(np.std(r, ddof=1)),

        "residual_percentiles_mph": {
            "p05":
                float(np.percentile(r, 5)),
            "p50":
                float(np.percentile(r, 50)),
            "p95":
                float(np.percentile(r, 95)),
        },
    },

    "secondary_variables": {
        "gust_wind":
            "sensitivity / uncertainty; not frozen as mean causal coefficient",

        "shortwave_cloud":
            "thermal forcing / track-state mechanism",

        "air_density":
            "diagnostic only",
    },

    "physical_zero_invariance":
        True,
}

MODEL_FILE = (
    OUT /
    "probabilistic_physics_core_v1.json"
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

BOOT_FILE = (
    OUT /
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

pd.DataFrame(
    boots,
    columns=[
        "beta_track_temp",
        "beta_ambient_temp",
    ]
).to_csv(
    BOOT_FILE,
    index=False
)

RESID_FILE = (
    OUT /
    "probabilistic_physics_loyo_residuals_v1.csv"
)

d.to_csv(
    RESID_FILE,
    index=False
)

BT_FILE = (
    OUT /
    "probabilistic_physics_historical_backtest_v1.csv"
)

bt.to_csv(
    BT_FILE,
    index=False
)

print("MODEL:", MODEL_FILE.relative_to(ROOT))
print("BOOTSTRAP:", BOOT_FILE.relative_to(ROOT))
print("RESIDUALS:", RESID_FILE.relative_to(ROOT))
print("BACKTEST:", BT_FILE.relative_to(ROOT))

print(
    "\nPROBABILISTIC_PHYSICS_CORE_V1_COMPLETE"
)
