from pathlib import Path
import csv
import json
import math
from collections import defaultdict

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

FIRST = ROOT / "r5/output/r5_manual_first_run_sequence_physics_v1.csv"

OUT_ROWS = ROOT / "r5/output/r5_manual_first_run_thermal_window_rows_v1.csv"
OUT_MODELS = ROOT / "r5/output/r5_manual_first_run_thermal_window_models_v1.csv"
OUT_REPORT = ROOT / "r5/output/r5_manual_first_run_thermal_window_report_v1.json"


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def corr(rows, xfield, yfield):
    pairs = []

    for r in rows:
        x = num(r.get(xfield))
        y = num(r.get(yfield))

        if x is not None and y is not None:
            pairs.append((x, y))

    if len(pairs) < 3:
        return None, len(pairs)

    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)

    if np.std(x) == 0 or np.std(y) == 0:
        return None, len(pairs)

    return float(np.corrcoef(x, y)[0, 1]), len(pairs)


def loyo(rows, target, features, nonlinear=False, alpha=10.0):
    usable = []

    for r in rows:
        y = num(r.get(target))
        xs = [num(r.get(f)) for f in features]

        if y is None or any(x is None for x in xs):
            continue

        usable.append((r, y, xs))

    X = np.array([u[2] for u in usable], dtype=float)
    y = np.array([u[1] for u in usable], dtype=float)
    groups = np.array([u[0]["year"] for u in usable])

    if nonlinear:
        model = Pipeline([
            ("poly", PolynomialFeatures(
                degree=2,
                include_bias=False
            )),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=alpha))
        ])
    else:
        model = Pipeline([
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=alpha))
        ])

    logo = LeaveOneGroupOut()
    pred = np.full(len(y), np.nan)

    for tr, te in logo.split(X, y, groups):
        model.fit(X[tr], y[tr])
        pred[te] = model.predict(X[te])

    mask = np.isfinite(pred)

    mae = mean_absolute_error(y[mask], pred[mask])
    rmse = np.sqrt(mean_squared_error(y[mask], pred[mask]))
    bias = float(np.mean(y[mask] - pred[mask]))

    return {
        "n": len(y),
        "mae": float(mae),
        "rmse": float(rmse),
        "bias": bias,
    }


_, rows = read_csv(FIRST)

# =====================================================================
# SAME-YEAR NORMALIZATION
# =====================================================================

by_year = defaultdict(list)

for r in rows:
    by_year[r["year"]].append(r)

out_rows = []

for year, yr in sorted(by_year.items()):

    speeds = [
        num(r["four_lap_average_speed_mph"])
        for r in yr
        if num(r["four_lap_average_speed_mph"]) is not None
    ]

    fades = [
        num(r["lap1_to_lap4_delta_mph"])
        for r in yr
        if num(r["lap1_to_lap4_delta_mph"]) is not None
    ]

    speed_med = float(np.median(speeds))
    fade_med = float(np.median(fades))

    for r in yr:
        x = dict(r)

        speed = num(r["four_lap_average_speed_mph"])
        fade = num(r["lap1_to_lap4_delta_mph"])

        x["same_year_first_run_speed_median_mph"] = speed_med
        x["speed_residual_vs_same_year_first_run_median_mph"] = (
            speed - speed_med if speed is not None else ""
        )

        x["same_year_first_run_fade_median_mph"] = fade_med
        x["fade_residual_vs_same_year_first_run_median_mph"] = (
            fade - fade_med if fade is not None else ""
        )

        seq = num(r["first_run_sequence_position"])
        n = num(r["first_run_sequence_n"])

        x["sequence_fraction"] = (
            (seq - 1) / (n - 1)
            if seq is not None and n is not None and n > 1
            else ""
        )

        out_rows.append(x)


write_csv(OUT_ROWS, out_rows)

print("=" * 145)
print("R5 — FIRST-RUN THERMAL WINDOW")
print("=" * 145)

print()
print("A. FIRST-RUN PHYSICAL TREND")
print("-" * 145)

tests = [
    ("first_run_sequence_position", "track_temp_c"),
    ("first_run_sequence_position", "shortwave_radiation_wm2"),
    ("first_run_sequence_position", "air_temp_c"),
    ("first_run_sequence_position", "cloud_cover_pct"),
    ("first_run_sequence_position", "wind_speed_10m_ms"),
]

for x, y in tests:
    r, n = corr(out_rows, x, y)
    txt = f"{r:+.4f}" if r is not None else "NA"
    print(f"{x:32s} -> {y:30s} r={txt} n={n}")


print()
print("B. PHYSICAL STATE VS SAME-YEAR SPEED RESIDUAL")
print("-" * 145)

tests = [
    ("track_temp_c", "speed_residual_vs_same_year_first_run_median_mph"),
    ("shortwave_radiation_wm2", "speed_residual_vs_same_year_first_run_median_mph"),
    ("air_temp_c", "speed_residual_vs_same_year_first_run_median_mph"),
    ("cloud_cover_pct", "speed_residual_vs_same_year_first_run_median_mph"),
    ("wind_speed_10m_ms", "speed_residual_vs_same_year_first_run_median_mph"),
]

for x, y in tests:
    r, n = corr(out_rows, x, y)
    txt = f"{r:+.4f}" if r is not None else "NA"
    print(f"{x:32s} -> speed residual              r={txt} n={n}")


print()
print("C. PHYSICAL STATE VS WITHIN-RUN FADE")
print("-" * 145)

tests = [
    ("track_temp_c", "lap1_to_lap4_delta_mph"),
    ("shortwave_radiation_wm2", "lap1_to_lap4_delta_mph"),
    ("air_temp_c", "lap1_to_lap4_delta_mph"),
    ("cloud_cover_pct", "lap1_to_lap4_delta_mph"),
    ("wind_speed_10m_ms", "lap1_to_lap4_delta_mph"),
]

for x, y in tests:
    r, n = corr(out_rows, x, y)
    txt = f"{r:+.4f}" if r is not None else "NA"
    print(f"{x:32s} -> fade                        r={txt} n={n}")


# =====================================================================
# MODEL COMPARISON
# =====================================================================

specs = {
    "SEQ_ONLY": (
        ["sequence_fraction"],
        False,
    ),

    "TRACK_ONLY": (
        ["track_temp_c"],
        False,
    ),

    "TRACK_NONLINEAR": (
        ["track_temp_c"],
        True,
    ),

    "TRACK_PLUS_SOLAR": (
        [
            "track_temp_c",
            "shortwave_radiation_wm2",
        ],
        False,
    ),

    "TRACK_PLUS_SOLAR_CLOUD": (
        [
            "track_temp_c",
            "shortwave_radiation_wm2",
            "cloud_cover_pct",
        ],
        False,
    ),
}

model_rows = []

print()
print("D. FIRST-RUN SPEED RESIDUAL MODELS")
print("-" * 145)

for name, (features, nonlinear) in specs.items():

    res = loyo(
        out_rows,
        target="speed_residual_vs_same_year_first_run_median_mph",
        features=features,
        nonlinear=nonlinear,
        alpha=10.0,
    )

    model_rows.append({
        "target":
            "speed_residual_vs_same_year_first_run_median_mph",

        "model":
            name,

        "features":
            "|".join(features),

        "nonlinear":
            nonlinear,

        "n":
            res["n"],

        "loyo_mae":
            res["mae"],

        "loyo_rmse":
            res["rmse"],

        "loyo_bias":
            res["bias"],
    })

    print(
        f"{name:28s} | "
        f"n={res['n']:3d} | "
        f"MAE={res['mae']:.4f} | "
        f"RMSE={res['rmse']:.4f} | "
        f"bias={res['bias']:+.4f}"
    )


print()
print("E. FIRST-RUN FADE MODELS")
print("-" * 145)

for name, (features, nonlinear) in specs.items():

    res = loyo(
        out_rows,
        target="lap1_to_lap4_delta_mph",
        features=features,
        nonlinear=nonlinear,
        alpha=10.0,
    )

    model_rows.append({
        "target":
            "lap1_to_lap4_delta_mph",

        "model":
            name,

        "features":
            "|".join(features),

        "nonlinear":
            nonlinear,

        "n":
            res["n"],

        "loyo_mae":
            res["mae"],

        "loyo_rmse":
            res["rmse"],

        "loyo_bias":
            res["bias"],
    })

    print(
        f"{name:28s} | "
        f"n={res['n']:3d} | "
        f"MAE={res['mae']:.4f} | "
        f"RMSE={res['rmse']:.4f} | "
        f"bias={res['bias']:+.4f}"
    )


write_csv(OUT_MODELS, model_rows)

report = {
    "status": "R5_FIRST_RUN_THERMAL_WINDOW_COMPLETE",
    "n": len(out_rows),
    "years": sorted(by_year.keys()),
    "fast_friday_used": False,
    "interpretation": (
        "First-attempt chronology is treated as a natural environmental "
        "time sweep. Same-year median residuals reduce cross-year scale "
        "differences but do not fully control car capability."
    )
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("OUTPUTS")
print("-" * 145)
print(OUT_ROWS.relative_to(ROOT))
print(OUT_MODELS.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("FAST FRIDAY USED: NO")
print("R5_FIRST_RUN_THERMAL_WINDOW_COMPLETE")
