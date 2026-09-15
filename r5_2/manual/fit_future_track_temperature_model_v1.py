from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

SRC = OUT / "track_temperature_future_transition_panel_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_track_temp_c"

FEATURES_ALL = [
    "requested_horizon_min",
    "current_track_temp_c",
    "current_ambient_temp_c",
    "delta_ambient_temp_c",
    "current_shortwave_wm2",
    "delta_shortwave_wm2",
    "current_wind_ms",
    "delta_wind_ms",
    "current_cloud_pct",
]

for c in [Y] + FEATURES_ALL:
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


def fit_ols(X, y):
    X1 = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(X1, y, rcond=None)[0]


def predict(beta, X):
    X1 = np.column_stack([np.ones(len(X)), X])
    return X1 @ beta


def fit_huber(X, y, delta=1.345, max_iter=100):
    X1 = np.column_stack([np.ones(len(X)), X])
    beta = np.linalg.lstsq(X1, y, rcond=None)[0]

    for _ in range(max_iter):
        resid = y - X1 @ beta
        med = np.median(resid)
        mad = np.median(np.abs(resid - med))
        scale = mad / 0.6745 if mad > 0 else np.std(resid)

        if not np.isfinite(scale) or scale < 1e-10:
            break

        u = resid / scale
        w = np.ones(len(resid))
        big = np.abs(u) > delta
        w[big] = delta / np.abs(u[big])

        sw = np.sqrt(w)
        Xw = X1 * sw[:, None]
        yw = y * sw

        new_beta = np.linalg.lstsq(Xw, yw, rcond=None)[0]

        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta


# ============================================================
# candidate models
# ============================================================

MODELS = {
    "HORIZON_ONLY": [
        "requested_horizon_min",
    ],

    "THERMAL_CORE": [
        "requested_horizon_min",
        "current_track_temp_c",
        "delta_ambient_temp_c",
    ],

    "THERMAL_SOLAR": [
        "requested_horizon_min",
        "current_track_temp_c",
        "delta_ambient_temp_c",
        "delta_shortwave_wm2",
    ],

    "THERMAL_SOLAR_WIND": [
        "requested_horizon_min",
        "current_track_temp_c",
        "delta_ambient_temp_c",
        "delta_shortwave_wm2",
        "current_wind_ms",
    ],

    "FULL_COMPACT": [
        "requested_horizon_min",
        "current_track_temp_c",
        "current_ambient_temp_c",
        "delta_ambient_temp_c",
        "delta_shortwave_wm2",
        "current_wind_ms",
        "delta_wind_ms",
        "current_cloud_pct",
    ],
}


# ============================================================
# PART 1 — LOYO model screen
# ============================================================

print("=" * 150)
print("PART 1 — FUTURE TRACK TEMP LOYO MODEL SCREEN")
print("=" * 150)

rows = []

for model_name, feats in MODELS.items():

    z = df[["year", Y] + feats].dropna().copy()

    for robust in [False, True]:

        preds = np.full(len(z), np.nan)

        for held in sorted(z["year"].unique()):

            train = z["year"] != held
            test = z["year"] == held

            Xtr = z.loc[train, feats].to_numpy(float)
            ytr = z.loc[train, Y].to_numpy(float)
            Xte = z.loc[test, feats].to_numpy(float)

            beta = (
                fit_huber(Xtr, ytr)
                if robust
                else fit_ols(Xtr, ytr)
            )

            preds[test.to_numpy()] = predict(beta, Xte)

        valid = np.isfinite(preds)

        y = z[Y].to_numpy(float)[valid]
        p = preds[valid]

        m = metrics(y, p)

        base = metrics(
            y,
            np.full(len(y), np.mean(y))
        )

        rows.append({
            "model": model_name,
            "fit": "HUBER" if robust else "OLS",
            "n": len(y),
            "mae": m["mae"],
            "rmse": m["rmse"],
            "bias": m["bias"],
            "baseline_mae": base["mae"],
            "baseline_rmse": base["rmse"],
            "beats_baseline_mae": m["mae"] < base["mae"],
            "beats_baseline_rmse": m["rmse"] < base["rmse"],
        })

res = pd.DataFrame(rows)

print(
    res.sort_values(["mae", "rmse"])
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 2 — HELD-OUT YEAR PERFORMANCE
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — HELD-OUT YEAR PERFORMANCE")
print("=" * 150)

best_name = (
    res[
        res["fit"] == "HUBER"
    ]
    .sort_values("mae")
    .iloc[0]["model"]
)

best_feats = MODELS[best_name]

z = df[["year", Y] + best_feats].dropna().copy()

print("BEST HUBER MODEL =", best_name)

for held in sorted(z["year"].unique()):

    train = z["year"] != held
    test = z["year"] == held

    Xtr = z.loc[train, best_feats].to_numpy(float)
    ytr = z.loc[train, Y].to_numpy(float)
    Xte = z.loc[test, best_feats].to_numpy(float)
    yte = z.loc[test, Y].to_numpy(float)

    beta = fit_huber(Xtr, ytr)
    pred = predict(beta, Xte)

    m = metrics(yte, pred)

    base_pred = np.full(
        len(yte),
        np.mean(ytr)
    )

    base = metrics(yte, base_pred)

    print(
        "held =", held,
        "n =", len(yte),
        "MAE =", round(m["mae"], 5),
        "base =", round(base["mae"], 5),
        "RMSE =", round(m["rmse"], 5),
        "base_RMSE =", round(base["rmse"], 5),
        "beats_MAE =", m["mae"] < base["mae"],
        "beats_RMSE =", m["rmse"] < base["rmse"],
    )


# ============================================================
# PART 3 — FULL FIT COEFFICIENTS
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — BEST MODEL FULL FIT")
print("=" * 150)

X = z[best_feats].to_numpy(float)
y = z[Y].to_numpy(float)

beta = fit_huber(X, y)

print("MODEL =", best_name)
print("INTERCEPT =", round(beta[0], 6))

for f, b in zip(best_feats, beta[1:]):
    print(f, "=", round(b, 6))


# ============================================================
# PART 4 — LOYO RESIDUAL UNCERTAINTY
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — FUTURE TRACK TEMP RESIDUAL UNCERTAINTY")
print("=" * 150)

preds = np.full(len(z), np.nan)

for held in sorted(z["year"].unique()):

    train = z["year"] != held
    test = z["year"] == held

    Xtr = z.loc[train, best_feats].to_numpy(float)
    ytr = z.loc[train, Y].to_numpy(float)
    Xte = z.loc[test, best_feats].to_numpy(float)

    b = fit_huber(Xtr, ytr)

    preds[test.to_numpy()] = predict(b, Xte)

z["pred_loyo"] = preds
z["residual_loyo"] = z[Y] - z["pred_loyo"]

r = z["residual_loyo"].dropna().to_numpy(float)

print("N residuals =", len(r))
print("mean =", round(np.mean(r), 6))
print("median =", round(np.median(r), 6))
print("SD =", round(np.std(r, ddof=1), 6))
print(
    "5/25/50/75/95 =",
    np.round(
        np.percentile(r, [5, 25, 50, 75, 95]),
        6
    )
)


# ============================================================
# PART 5 — ERROR BY HORIZON
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — ERROR BY HORIZON")
print("=" * 150)

z2 = z.copy()
z2["abs_error"] = (
    z2[Y] - z2["pred_loyo"]
).abs()

for h, g in z2.groupby("requested_horizon_min"):

    print(
        "horizon =", h,
        "n =", len(g),
        "MAE =", round(g["abs_error"].mean(), 6),
        "bias =", round(
            (g["pred_loyo"] - g[Y]).mean(),
            6
        )
    )


# ============================================================
# save model bundle
# ============================================================

MODEL = {
    "version": "R5.2_FUTURE_TRACK_TEMP_MODEL_V1",
    "target": "delta_track_temp_c",
    "best_model": best_name,
    "features": best_feats,
    "fit": "Huber regression",
    "coefficients": {
        "intercept": float(beta[0]),
        **{
            f: float(b)
            for f, b in zip(best_feats, beta[1:])
        }
    },
    "residual": {
        "source": "leave-one-year-out residuals",
        "mean": float(np.mean(r)),
        "median": float(np.median(r)),
        "sd": float(np.std(r, ddof=1)),
        "p05": float(np.percentile(r, 5)),
        "p50": float(np.percentile(r, 50)),
        "p95": float(np.percentile(r, 95)),
    }
}

MODEL_FILE = OUT / "future_track_temperature_model_v1.json"

with open(MODEL_FILE, "w", encoding="utf-8") as f:
    json.dump(MODEL, f, indent=2)

RESID_FILE = OUT / "future_track_temperature_loyo_residuals_v1.csv"
z.to_csv(RESID_FILE, index=False)

SCREEN_FILE = OUT / "future_track_temperature_model_screen_v1.csv"
res.to_csv(SCREEN_FILE, index=False)

print("\n" + "=" * 150)
print("OUTPUTS")
print("=" * 150)

print(MODEL_FILE.relative_to(ROOT))
print(RESID_FILE.relative_to(ROOT))
print(SCREEN_FILE.relative_to(ROOT))

print("\nFUTURE_TRACK_TEMPERATURE_MODEL_V1_COMPLETE")
