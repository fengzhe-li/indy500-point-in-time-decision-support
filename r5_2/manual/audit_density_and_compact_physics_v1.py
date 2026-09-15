from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
SRC = OUT / "r5_2_repeat_analysis_set_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_four_lap_average_speed_mph"
DENS = "delta_air_density_kg_m3"
TRACK = "delta_track_temp_c"
GUST = "delta_gust_ms"

for c in [Y, DENS, TRACK, GUST]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ============================================================
# helpers
# ============================================================

def beta_zero(x, y):
    den = np.sum(x*x)
    return np.sum(x*y)/den if den > 0 else np.nan

def metrics(y, p):
    e = p-y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }

def huber_zero(X, y, delta=1.345, iters=100):
    beta = np.linalg.lstsq(X, y, rcond=None)[0]

    for _ in range(iters):
        r = y - X @ beta
        scale = np.median(np.abs(r - np.median(r))) / 0.6745

        if not np.isfinite(scale) or scale < 1e-9:
            break

        u = r / scale
        w = np.ones(len(r))
        big = np.abs(u) > delta
        w[big] = delta / np.abs(u[big])

        W = np.sqrt(w)[:, None]
        new_beta = np.linalg.lstsq(X*W, y*np.sqrt(w), rcond=None)[0]

        if np.max(np.abs(new_beta-beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta

# ============================================================
# PART 1 — raw density relationship
# ============================================================

print("="*150)
print("PART 1 — DENSITY RAW RELATIONSHIP")
print("="*150)

d = df[[Y, DENS, "year", "driver_name", "car_number"]].dropna().copy()

x = d[DENS].to_numpy(float)
y = d[Y].to_numpy(float)

print("N =", len(d))
print("Pearson =", round(pd.Series(x).corr(pd.Series(y)), 6))
print("Spearman =", round(pd.Series(x).corr(pd.Series(y), method="spearman"), 6))
print("Zero-intercept beta =", round(beta_zero(x, y), 6))

# bootstrap
rng = np.random.default_rng(500)
boots = []

for _ in range(10000):
    idx = rng.integers(0, len(d), len(d))
    boots.append(beta_zero(x[idx], y[idx]))

boots = np.array(boots)

print(
    "Bootstrap 95% =",
    round(np.percentile(boots,2.5),6),
    "to",
    round(np.percentile(boots,97.5),6)
)
print("P(beta < 0) =", round(np.mean(boots < 0),6))

# ============================================================
# PART 2 — density coefficient by year
# ============================================================

print("\n"+"="*150)
print("PART 2 — DENSITY SIGN BY YEAR")
print("="*150)

rows = []

for yr, g in d.groupby("year"):
    if len(g) < 4:
        continue

    xx = g[DENS].to_numpy(float)
    yy = g[Y].to_numpy(float)

    rows.append({
        "year": yr,
        "n": len(g),
        "beta_zero": beta_zero(xx,yy),
        "pearson": pd.Series(xx).corr(pd.Series(yy)),
        "spearman": pd.Series(xx).corr(pd.Series(yy), method="spearman"),
        "mean_delta_density": np.mean(xx),
        "mean_delta_speed": np.mean(yy),
    })

yrres = pd.DataFrame(rows)
print(yrres.round(6).to_string(index=False))

# ============================================================
# PART 3 — leave-one-year-out fitted coefficients
# ============================================================

print("\n"+"="*150)
print("PART 3 — LOYO TRAINING COEFFICIENT STABILITY")
print("="*150)

rows = []

for held in sorted(d["year"].unique()):
    tr = d[d["year"] != held]
    te = d[d["year"] == held]

    if len(te) == 0:
        continue

    xx = tr[DENS].to_numpy(float)
    yy = tr[Y].to_numpy(float)

    b = beta_zero(xx, yy)

    pred = te[DENS].to_numpy(float) * b
    m = metrics(te[Y].to_numpy(float), pred)
    base = metrics(te[Y].to_numpy(float), np.zeros(len(te)))

    rows.append({
        "held_out_year": held,
        "train_n": len(tr),
        "test_n": len(te),
        "train_beta_density": b,
        "test_mae": m["mae"],
        "test_rmse": m["rmse"],
        "baseline_mae": base["mae"],
        "baseline_rmse": base["rmse"],
        "beats_baseline_mae": m["mae"] < base["mae"],
        "beats_baseline_rmse": m["rmse"] < base["rmse"],
    })

loyo = pd.DataFrame(rows)
print(loyo.round(6).to_string(index=False))

# ============================================================
# PART 4 — robust density fit
# ============================================================

print("\n"+"="*150)
print("PART 4 — ROBUST ZERO-INTERCEPT DENSITY")
print("="*150)

X = d[[DENS]].to_numpy(float)

ols_beta = np.linalg.lstsq(X,y,rcond=None)[0][0]
huber_beta = huber_zero(X,y)[0]

print("OLS beta =", round(ols_beta,6))
print("Huber beta =", round(huber_beta,6))

print("\nLargest |Δspeed| rows:")
print(
    d.assign(abs_dspeed=d[Y].abs())
    .sort_values("abs_dspeed", ascending=False)
    [["year","car_number","driver_name",Y,DENS]]
    .head(12)
    .round(6)
    .to_string(index=False)
)

# ============================================================
# PART 5 — predictor dependence
# ============================================================

print("\n"+"="*150)
print("PART 5 — PHYSICAL PREDICTOR DEPENDENCE")
print("="*150)

p = df[[DENS,TRACK,GUST]].dropna()

print("N complete =",len(p))
print("\nPearson:")
print(p.corr(method="pearson").round(4).to_string())

print("\nSpearman:")
print(p.corr(method="spearman").round(4).to_string())

# ============================================================
# PART 6 — residualized track effect after density
# ============================================================

print("\n"+"="*150)
print("PART 6 — TRACK EFFECT CONDITIONAL ON DENSITY")
print("="*150)

z = df[[Y,DENS,TRACK,"year"]].dropna().copy()

# Through-origin density prediction
bd = beta_zero(
    z[DENS].to_numpy(float),
    z[Y].to_numpy(float)
)

z["density_pred"] = bd*z[DENS]
z["speed_residual_after_density"] = z[Y] - z["density_pred"]

print("density beta =", round(bd,6))
print(
    "Residual vs Δtrack Pearson =",
    round(
        z["speed_residual_after_density"].corr(z[TRACK]),
        6
    )
)
print(
    "Residual vs Δtrack Spearman =",
    round(
        z["speed_residual_after_density"].corr(
            z[TRACK],
            method="spearman"
        ),
        6
    )
)

# ============================================================
# PART 7 — compact candidates, robust vs OLS
# ============================================================

print("\n"+"="*150)
print("PART 7 — COMPACT MODEL ROBUSTNESS")
print("="*150)

models = {
    "DENSITY_ONLY":[DENS],
    "TRACK_DENSITY":[TRACK,DENS],
    "TRACK_GUST":[TRACK,GUST],
}

rows=[]

for name, feats in models.items():

    z = df[["year",Y]+feats].dropna().copy()

    X = z[feats].to_numpy(float)
    y = z[Y].to_numpy(float)

    ols = np.linalg.lstsq(X,y,rcond=None)[0]
    hub = huber_zero(X,y)

    row = {
        "model":name,
        "n":len(z)
    }

    for f,b in zip(feats,ols):
        row["ols_"+f]=b

    for f,b in zip(feats,hub):
        row["huber_"+f]=b

    rows.append(row)

rob = pd.DataFrame(rows)
print(rob.round(6).to_string(index=False))

# ============================================================
# save
# ============================================================

yrres.to_csv(OUT/"density_year_stability_v1.csv",index=False)
loyo.to_csv(OUT/"density_loyo_coefficient_stability_v1.csv",index=False)
rob.to_csv(OUT/"compact_model_robust_coefficients_v1.csv",index=False)

print("\n"+"="*150)
print("DENSITY_AND_COMPACT_PHYSICS_AUDIT_V1_COMPLETE")
print("="*150)
