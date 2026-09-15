from pathlib import Path
import pandas as pd
import numpy as np

from scipy.optimize import lsq_linear

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
SRC = OUT / "r5_2_repeat_analysis_set_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_four_lap_average_speed_mph"
TRACK = "delta_track_temp_c"
AIR = "delta_air_temp_c"
GUST = "delta_gust_ms"

for c in [Y, TRACK, AIR, GUST]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ============================================================
# helpers
# ============================================================

def metrics(y, p):
    e = p - y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }

def constrained_ls(X, y, lower, upper):
    fit = lsq_linear(
        X,
        y,
        bounds=(lower, upper),
        method="trf"
    )
    return fit.x

def constrained_huber(
    X,
    y,
    lower,
    upper,
    delta=1.345,
    max_iter=100
):
    beta = constrained_ls(X, y, lower, upper)

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

        mask = np.abs(u) > delta
        w[mask] = delta / np.abs(u[mask])

        sw = np.sqrt(w)

        Xw = X * sw[:, None]
        yw = y * sw

        new_beta = constrained_ls(
            Xw,
            yw,
            lower,
            upper
        )

        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta


# ============================================================
# model definitions
#
# Track coefficient constrained <= 0
#
# Ambient / gust unconstrained.
# ============================================================

MODELS = {
    "TRACK_CONSTRAINED": {
        "features": [TRACK],
        "lower": [-np.inf],
        "upper": [0.0],
    },

    "TRACK_AIR_CONSTRAINED": {
        "features": [TRACK, AIR],
        "lower": [-np.inf, -np.inf],
        "upper": [0.0, np.inf],
    },

    "TRACK_GUST_CONSTRAINED": {
        "features": [TRACK, GUST],
        "lower": [-np.inf, -np.inf],
        "upper": [0.0, np.inf],
    },

    "TRACK_AIR_GUST_CONSTRAINED": {
        "features": [TRACK, AIR, GUST],
        "lower": [-np.inf, -np.inf, -np.inf],
        "upper": [0.0, np.inf, np.inf],
    },
}


# ============================================================
# PART 1 — LOYO constrained Huber
# ============================================================

print("=" * 150)
print("PART 1 — PHYSICS-CONSTRAINED ROBUST LOYO")
print("=" * 150)

results = []

for model_name, spec in MODELS.items():

    feats = spec["features"]

    z = df[
        ["year", Y] + feats
    ].dropna().copy()

    pred = np.full(len(z), np.nan)

    beta_by_year = []

    for held in sorted(z["year"].unique()):

        train = z["year"] != held
        test = z["year"] == held

        Xtr = z.loc[train, feats].to_numpy(float)
        ytr = z.loc[train, Y].to_numpy(float)

        Xte = z.loc[test, feats].to_numpy(float)

        beta = constrained_huber(
            Xtr,
            ytr,
            np.array(spec["lower"], float),
            np.array(spec["upper"], float),
        )

        pred[test.to_numpy()] = Xte @ beta

        beta_by_year.append(
            (held, beta.copy())
        )

    valid = np.isfinite(pred)

    y = z[Y].to_numpy(float)[valid]
    p = pred[valid]

    m = metrics(y, p)
    base = metrics(y, np.zeros(len(y)))

    # full-data fit
    Xall = z[feats].to_numpy(float)
    yall = z[Y].to_numpy(float)

    beta_all = constrained_huber(
        Xall,
        yall,
        np.array(spec["lower"], float),
        np.array(spec["upper"], float),
    )

    row = {
        "model": model_name,
        "n": len(z),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "baseline_mae": base["mae"],
        "baseline_rmse": base["rmse"],
        "beats_baseline_mae":
            m["mae"] < base["mae"],
        "beats_baseline_rmse":
            m["rmse"] < base["rmse"],
    }

    for f, b in zip(feats, beta_all):
        row["beta_" + f] = b

    results.append(row)

res = pd.DataFrame(results)

print(
    res.sort_values("mae")
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 2 — HELD-OUT YEAR DETAIL
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — HELD-OUT YEAR DETAIL")
print("=" * 150)

for model_name, spec in MODELS.items():

    feats = spec["features"]

    z = df[
        ["year", Y] + feats
    ].dropna().copy()

    print("\nMODEL:", model_name)

    for held in sorted(z["year"].unique()):

        train = z["year"] != held
        test = z["year"] == held

        Xtr = z.loc[train, feats].to_numpy(float)
        ytr = z.loc[train, Y].to_numpy(float)

        Xte = z.loc[test, feats].to_numpy(float)
        yte = z.loc[test, Y].to_numpy(float)

        beta = constrained_huber(
            Xtr,
            ytr,
            np.array(spec["lower"], float),
            np.array(spec["upper"], float),
        )

        p = Xte @ beta

        m = metrics(yte, p)
        base = metrics(
            yte,
            np.zeros(len(yte))
        )

        print(
            "held =", held,
            "n =", len(yte),
            "MAE =", round(m["mae"], 6),
            "base =", round(base["mae"], 6),
            "RMSE =", round(m["rmse"], 6),
            "base_RMSE =", round(base["rmse"], 6),
            "beats_MAE =", m["mae"] < base["mae"],
            "beats_RMSE =", m["rmse"] < base["rmse"],
            "beta =",
            np.round(beta, 6),
        )


# ============================================================
# PART 3 — BOOTSTRAP FULL-DATA COEFFICIENTS
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — BOOTSTRAP COEFFICIENT STABILITY")
print("=" * 150)

rng = np.random.default_rng(500)

for model_name, spec in MODELS.items():

    feats = spec["features"]

    z = df[[Y] + feats].dropna().copy()

    X = z[feats].to_numpy(float)
    y = z[Y].to_numpy(float)

    boot = []

    for _ in range(5000):

        idx = rng.integers(
            0,
            len(z),
            len(z)
        )

        b = constrained_huber(
            X[idx],
            y[idx],
            np.array(spec["lower"], float),
            np.array(spec["upper"], float),
        )

        boot.append(b)

    boot = np.array(boot)

    print("\nMODEL:", model_name)

    for j, f in enumerate(feats):

        lo = np.percentile(
            boot[:, j],
            2.5
        )

        med = np.percentile(
            boot[:, j],
            50
        )

        hi = np.percentile(
            boot[:, j],
            97.5
        )

        print(
            f,
            "median =", round(med, 6),
            "95% =",
            round(lo, 6),
            "to",
            round(hi, 6),
        )


# ============================================================
# PART 4 — RESIDUAL UNCERTAINTY
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — RESIDUAL UNCERTAINTY")
print("=" * 150)

best_name = (
    res.sort_values("mae")
    .iloc[0]["model"]
)

spec = MODELS[best_name]
feats = spec["features"]

z = df[[Y] + feats].dropna().copy()

X = z[feats].to_numpy(float)
y = z[Y].to_numpy(float)

beta = constrained_huber(
    X,
    y,
    np.array(spec["lower"], float),
    np.array(spec["upper"], float),
)

pred = X @ beta
resid = y - pred

print("BEST MODEL =", best_name)
print("N =", len(z))
print("coefficients =", np.round(beta, 6))
print("residual mean =", round(np.mean(resid), 6))
print("residual median =", round(np.median(resid), 6))
print("residual SD =", round(np.std(resid, ddof=1), 6))
print(
    "residual MAD =",
    round(
        np.median(
            np.abs(resid - np.median(resid))
        ),
        6
    )
)

print(
    "empirical residual 5/50/95 percentiles =",
    np.round(
        np.percentile(
            resid,
            [5, 50, 95]
        ),
        6
    )
)


# ============================================================
# save
# ============================================================

OUTFILE = (
    OUT /
    "physics_informed_constrained_core_screen_v1.csv"
)

res.to_csv(
    OUTFILE,
    index=False
)

print("\n" + "=" * 150)
print("OUTPUT")
print("=" * 150)
print(OUTFILE.relative_to(ROOT))

print(
    "\nPHYSICS_INFORMED_CONSTRAINED_CORE_V1_COMPLETE"
)
