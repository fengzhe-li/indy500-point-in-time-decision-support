from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
SRC = OUT / "r5_2_repeat_analysis_set_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_four_lap_average_speed_mph"
TRACK = "delta_track_temp_c"
AIR = "delta_air_temp_c"
GUST = "delta_gust_ms"
WIND = "delta_wind_speed_ms"
SW = "delta_shortwave_radiation_wm2"

for c in [Y, TRACK, AIR, GUST, WIND, SW]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# ============================================================
# helpers
# ============================================================

def metrics(y, pred):
    e = pred - y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }

def fit_ols_zero(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]

def fit_huber_zero(X, y, delta=1.345, iters=100):
    beta = fit_ols_zero(X, y)

    for _ in range(iters):
        r = y - X @ beta

        med = np.median(r)
        mad = np.median(np.abs(r - med))
        scale = mad / 0.6745 if mad > 0 else np.std(r)

        if not np.isfinite(scale) or scale < 1e-9:
            break

        u = r / scale
        w = np.ones(len(r))

        mask = np.abs(u) > delta
        w[mask] = delta / np.abs(u[mask])

        sw = np.sqrt(w)
        Xw = X * sw[:, None]
        yw = y * sw

        new_beta = np.linalg.lstsq(Xw, yw, rcond=None)[0]

        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta

def loyo_eval(data, features, robust=False):
    z = data[["year", Y] + features].dropna().copy()

    if len(z) < 10:
        return None

    pred = np.full(len(z), np.nan)

    for yr in sorted(z["year"].unique()):
        train = z["year"] != yr
        test = z["year"] == yr

        Xtr = z.loc[train, features].to_numpy(float)
        ytr = z.loc[train, Y].to_numpy(float)
        Xte = z.loc[test, features].to_numpy(float)

        if len(ytr) <= len(features):
            continue

        beta = (
            fit_huber_zero(Xtr, ytr)
            if robust
            else fit_ols_zero(Xtr, ytr)
        )

        pred[test.to_numpy()] = Xte @ beta

    valid = np.isfinite(pred)

    y = z[Y].to_numpy(float)[valid]
    p = pred[valid]

    m = metrics(y, p)
    base = metrics(y, np.zeros(len(y)))

    Xall = z[features].to_numpy(float)
    yall = z[Y].to_numpy(float)

    beta_all = (
        fit_huber_zero(Xall, yall)
        if robust
        else fit_ols_zero(Xall, yall)
    )

    result = {
        "n": len(z),
        "loyo_n": int(valid.sum()),
        "mae": m["mae"],
        "rmse": m["rmse"],
        "bias": m["bias"],
        "no_change_mae": base["mae"],
        "no_change_rmse": base["rmse"],
        "beats_no_change_mae": m["mae"] < base["mae"],
        "beats_no_change_rmse": m["rmse"] < base["rmse"],
    }

    for f, b in zip(features, beta_all):
        result["beta_" + f] = b

    return result

# ============================================================
# PART 1 — RAW DIRECTIONAL EVIDENCE
# ============================================================

print("=" * 150)
print("PART 1 — RAW DIRECTIONAL EVIDENCE")
print("=" * 150)

for feature in [TRACK, AIR, GUST, WIND, SW]:
    if feature not in df.columns:
        continue

    z = df[[Y, feature]].dropna()

    if len(z) < 5:
        continue

    pear = z[feature].corr(z[Y], method="pearson")
    spear = z[feature].corr(z[Y], method="spearman")

    print(
        f"{feature:35s}",
        "N =", len(z),
        "Pearson =", round(pear, 6),
        "Spearman =", round(spear, 6)
    )

# ============================================================
# PART 2 — OFFICIAL-PHYSICS CANDIDATE SCREEN
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — OFFICIAL-PHYSICS COMPACT MODEL SCREEN")
print("=" * 150)

models = {
    "TRACK_ONLY": [TRACK],
    "AIR_ONLY": [AIR],
    "TRACK_AIR": [TRACK, AIR],
    "TRACK_GUST": [TRACK, GUST],
    "TRACK_WIND": [TRACK, WIND],
    "TRACK_AIR_GUST": [TRACK, AIR, GUST],
    "TRACK_AIR_WIND": [TRACK, AIR, WIND],
    "TRACK_AIR_SHORTWAVE": [TRACK, AIR, SW],
}

rows = []

for name, feats in models.items():
    feats = [f for f in feats if f in df.columns]

    for robust in [False, True]:
        r = loyo_eval(df, feats, robust=robust)

        if r is None:
            continue

        r["model"] = name
        r["fit"] = "HUBER" if robust else "OLS"
        rows.append(r)

res = pd.DataFrame(rows)

show = [
    "model",
    "fit",
    "n",
    "mae",
    "rmse",
    "bias",
    "no_change_mae",
    "no_change_rmse",
    "beats_no_change_mae",
    "beats_no_change_rmse",
]

print(
    res[show]
    .sort_values(["mae", "rmse"])
    .round(6)
    .to_string(index=False)
)

# ============================================================
# PART 3 — COEFFICIENTS FOR TOP ROBUST MODELS
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — ROBUST COEFFICIENTS")
print("=" * 150)

rob = res[res["fit"] == "HUBER"].copy()

beta_cols = [c for c in rob.columns if c.startswith("beta_")]

cols = ["model", "n", "mae", "rmse"] + beta_cols

print(
    rob[cols]
    .sort_values("mae")
    .round(6)
    .to_string(index=False)
)

# ============================================================
# PART 4 — YEAR-BLOCK ROBUSTNESS FOR MAIN CANDIDATES
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — HELD-OUT YEAR PERFORMANCE")
print("=" * 150)

main_models = {
    "TRACK_AIR": [TRACK, AIR],
    "TRACK_GUST": [TRACK, GUST],
    "TRACK_AIR_GUST": [TRACK, AIR, GUST],
}

for name, feats in main_models.items():

    z = df[["year", Y] + feats].dropna().copy()

    print("\nMODEL:", name)

    for yr in sorted(z["year"].unique()):

        train = z["year"] != yr
        test = z["year"] == yr

        Xtr = z.loc[train, feats].to_numpy(float)
        ytr = z.loc[train, Y].to_numpy(float)
        Xte = z.loc[test, feats].to_numpy(float)
        yte = z.loc[test, Y].to_numpy(float)

        if len(ytr) <= len(feats):
            continue

        beta = fit_huber_zero(Xtr, ytr)
        pred = Xte @ beta

        m = metrics(yte, pred)
        base = metrics(yte, np.zeros(len(yte)))

        print(
            "held_out_year =", yr,
            "test_n =", len(yte),
            "MAE =", round(m["mae"], 6),
            "baseline_MAE =", round(base["mae"], 6),
            "RMSE =", round(m["rmse"], 6),
            "baseline_RMSE =", round(base["rmse"], 6),
            "beats_MAE =", m["mae"] < base["mae"],
            "beats_RMSE =", m["rmse"] < base["rmse"],
        )

# ============================================================
# PART 5 — THERMAL DIRECTION CONSISTENCY
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — THERMAL DIRECTION CONSISTENCY")
print("=" * 150)

for feature in [TRACK, AIR]:

    z = df[["year", Y, feature]].dropna()

    print("\nFEATURE:", feature)

    for yr, g in z.groupby("year"):

        if len(g) < 3:
            continue

        print(
            "year =", yr,
            "n =", len(g),
            "Pearson =", round(g[feature].corr(g[Y]), 6),
            "Spearman =", round(g[feature].corr(g[Y], method="spearman"), 6),
            "mean_delta =", round(g[feature].mean(), 6),
            "mean_dspeed =", round(g[Y].mean(), 6),
        )

# ============================================================
# save
# ============================================================

OUTFILE = OUT / "official_physics_core_screen_v1.csv"
res.to_csv(OUTFILE, index=False)

print("\n" + "=" * 150)
print("OUTPUT")
print("=" * 150)
print(OUTFILE.relative_to(ROOT))

print("\nOFFICIAL_PHYSICS_CORE_SCREEN_V1_COMPLETE")
