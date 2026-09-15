from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

SRC = OUT / "track_temperature_future_transition_panel_v1.csv"

df = pd.read_csv(SRC)

Y = "delta_track_temp_c"

for c in [
    Y,
    "requested_horizon_min",
    "current_track_temp_c",
    "delta_ambient_temp_c",
    "delta_shortwave_wm2",
]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Fixed physical reference, not estimated from test years
TRACK_REFERENCE_C = 40.0

df["horizon_hours"] = (
    df["requested_horizon_min"] / 60.0
)

df["horizon_x_track_state"] = (
    df["horizon_hours"]
    *
    (df["current_track_temp_c"] - TRACK_REFERENCE_C)
)

# Scale solar change only for numerical conditioning.
df["delta_shortwave_100"] = (
    df["delta_shortwave_wm2"] / 100.0
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

        large = np.abs(u) > delta
        w[large] = delta / np.abs(u[large])

        sw = np.sqrt(w)

        new_beta = np.linalg.lstsq(
            X * sw[:, None],
            y * sw,
            rcond=None
        )[0]

        if np.max(np.abs(new_beta-beta)) < 1e-10:
            beta = new_beta
            break

        beta = new_beta

    return beta


def metrics(y, p):
    e = p-y
    return {
        "mae": np.mean(np.abs(e)),
        "rmse": np.sqrt(np.mean(e**2)),
        "bias": np.mean(e),
    }


MODELS = {
    "HORIZON_ONLY_INVARIANT": [
        "horizon_hours",
    ],

    "HORIZON_STATE_INVARIANT": [
        "horizon_hours",
        "horizon_x_track_state",
    ],

    "THERMAL_CORE_INVARIANT": [
        "horizon_hours",
        "horizon_x_track_state",
        "delta_ambient_temp_c",
    ],

    "THERMAL_SOLAR_INVARIANT": [
        "horizon_hours",
        "horizon_x_track_state",
        "delta_ambient_temp_c",
        "delta_shortwave_100",
    ],
}


# ============================================================
# PART 1 — LOYO SCREEN
# ============================================================

print("="*150)
print("PART 1 — INVARIANT FUTURE TRACK MODEL LOYO SCREEN")
print("="*150)

results=[]

for name, feats in MODELS.items():

    z=df[["year",Y]+feats].dropna().copy()

    for robust in [False, True]:

        pred=np.full(len(z),np.nan)

        for held in sorted(z["year"].unique()):

            train=z["year"]!=held
            test=z["year"]==held

            Xtr=z.loc[train,feats].to_numpy(float)
            ytr=z.loc[train,Y].to_numpy(float)
            Xte=z.loc[test,feats].to_numpy(float)

            beta=(
                fit_huber_zero(Xtr,ytr)
                if robust
                else fit_ols_zero(Xtr,ytr)
            )

            pred[test.to_numpy()]=Xte@beta

        valid=np.isfinite(pred)

        y=z[Y].to_numpy(float)[valid]
        p=pred[valid]

        m=metrics(y,p)
        base=metrics(y,np.zeros(len(y)))

        results.append({
            "model":name,
            "fit":"HUBER" if robust else "OLS",
            "n":len(y),
            "mae":m["mae"],
            "rmse":m["rmse"],
            "bias":m["bias"],
            "zero_change_baseline_mae":base["mae"],
            "zero_change_baseline_rmse":base["rmse"],
            "beats_zero_baseline_mae":
                m["mae"] < base["mae"],
            "beats_zero_baseline_rmse":
                m["rmse"] < base["rmse"],
        })

res=pd.DataFrame(results)

print(
    res.sort_values(["mae","rmse"])
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 2 — HELD-OUT YEAR DETAIL FOR BEST HUBER
# ============================================================

print("\n"+"="*150)
print("PART 2 — BEST INVARIANT MODEL HELD-OUT YEAR")
print("="*150)

best_name=(
    res[res["fit"]=="HUBER"]
    .sort_values("mae")
    .iloc[0]["model"]
)

feats=MODELS[best_name]

z=df[["year",Y]+feats].dropna().copy()

print("BEST =",best_name)

for held in sorted(z["year"].unique()):

    train=z["year"]!=held
    test=z["year"]==held

    Xtr=z.loc[train,feats].to_numpy(float)
    ytr=z.loc[train,Y].to_numpy(float)

    Xte=z.loc[test,feats].to_numpy(float)
    yte=z.loc[test,Y].to_numpy(float)

    beta=fit_huber_zero(Xtr,ytr)
    p=Xte@beta

    m=metrics(yte,p)
    base=metrics(yte,np.zeros(len(yte)))

    print(
        "held =",held,
        "n =",len(yte),
        "MAE =",round(m["mae"],6),
        "base =",round(base["mae"],6),
        "RMSE =",round(m["rmse"],6),
        "base_RMSE =",round(base["rmse"],6),
        "beats_MAE =",m["mae"]<base["mae"],
        "beats_RMSE =",m["rmse"]<base["rmse"],
        "beta =",np.round(beta,6),
    )


# ============================================================
# PART 3 — FULL FIT
# ============================================================

print("\n"+"="*150)
print("PART 3 — BEST INVARIANT MODEL FULL FIT")
print("="*150)

X=z[feats].to_numpy(float)
y=z[Y].to_numpy(float)

beta=fit_huber_zero(X,y)

print("MODEL =",best_name)
print("TRACK_REFERENCE_C =",TRACK_REFERENCE_C)

for f,b in zip(feats,beta):
    print(f,"=",round(b,6))


# ============================================================
# PART 4 — ZERO-HORIZON INVARIANCE
# ============================================================

print("\n"+"="*150)
print("PART 4 — ZERO-HORIZON PHYSICS SANITY")
print("="*150)

test_tracks=[25,35,40,45,55]

for t in test_tracks:

    values={
        "horizon_hours":0.0,
        "horizon_x_track_state":
            0.0*(t-TRACK_REFERENCE_C),
        "delta_ambient_temp_c":0.0,
        "delta_shortwave_100":0.0,
    }

    x=np.array(
        [values[f] for f in feats],
        float
    )

    pred=x@beta

    print(
        "current_track =",t,
        "wait = 0",
        "predicted Δtrack =",
        round(float(pred),12)
    )

    assert abs(pred)<1e-12

print("PASS: wait=0 => predicted Δtrack=0")


# ============================================================
# PART 5 — LOYO RESIDUAL UNCERTAINTY
# ============================================================

print("\n"+"="*150)
print("PART 5 — INVARIANT TRACK MODEL RESIDUALS")
print("="*150)

pred=np.full(len(z),np.nan)

for held in sorted(z["year"].unique()):

    train=z["year"]!=held
    test=z["year"]==held

    b=fit_huber_zero(
        z.loc[train,feats].to_numpy(float),
        z.loc[train,Y].to_numpy(float)
    )

    pred[test.to_numpy()] = (
        z.loc[test,feats].to_numpy(float) @ b
    )

z["pred_loyo_invariant"]=pred
z["residual_loyo_invariant"]=(
    z[Y]-z["pred_loyo_invariant"]
)

r=z["residual_loyo_invariant"].dropna().to_numpy(float)

print("N =",len(r))
print("mean =",round(np.mean(r),6))
print("median =",round(np.median(r),6))
print("SD =",round(np.std(r,ddof=1),6))
print(
    "5/25/50/75/95 =",
    np.round(
        np.percentile(r,[5,25,50,75,95]),
        6
    )
)


# ============================================================
# PART 6 — ERROR BY HORIZON
# ============================================================

print("\n"+"="*150)
print("PART 6 — ERROR BY HORIZON")
print("="*150)

# recover horizon from original indices
zh=df.loc[z.index].copy()
zh["pred_loyo"]=pred
zh["abs_error"]=(
    zh[Y]-zh["pred_loyo"]
).abs()

for h,g in zh.groupby("requested_horizon_min"):

    print(
        "horizon =",h,
        "n =",len(g),
        "MAE =",round(g["abs_error"].mean(),6),
        "bias =",round(
            (g["pred_loyo"]-g[Y]).mean(),
            6
        )
    )


# ============================================================
# PART 7 — SAVE
# ============================================================

MODEL={
    "version":
        "R5.2_FUTURE_TRACK_TEMP_INVARIANT_V2",

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

    "coefficients":{
        f:float(b)
        for f,b in zip(feats,beta)
    },

    "physical_invariance":{
        "wait_zero_implies_delta_track_zero":
            True
    },

    "residual":{
        "source":
            "leave-one-year-out",

        "mean":
            float(np.mean(r)),

        "median":
            float(np.median(r)),

        "sd":
            float(np.std(r,ddof=1)),

        "p05":
            float(np.percentile(r,5)),

        "p95":
            float(np.percentile(r,95)),
    }
}

MODEL_FILE=(
    OUT /
    "future_track_temperature_invariant_model_v2.json"
)

with open(MODEL_FILE,"w",encoding="utf-8") as f:
    json.dump(MODEL,f,indent=2)

SCREEN_FILE=(
    OUT /
    "future_track_temperature_invariant_screen_v2.csv"
)

res.to_csv(SCREEN_FILE,index=False)

RESID_FILE=(
    OUT /
    "future_track_temperature_invariant_loyo_residuals_v2.csv"
)

z.to_csv(RESID_FILE,index=False)

print("\n"+"="*150)
print("OUTPUTS")
print("="*150)

print(MODEL_FILE.relative_to(ROOT))
print(SCREEN_FILE.relative_to(ROOT))
print(RESID_FILE.relative_to(ROOT))

print("\nINVARIANT_FUTURE_TRACK_MODEL_V2_COMPLETE")
