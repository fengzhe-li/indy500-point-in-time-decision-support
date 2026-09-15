from pathlib import Path
import csv
import json
import math
import numpy as np

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

WITHIN = ROOT / "r5/output/r5_manual_within_run_fade_physics_v1.csv"
REPEAT = ROOT / "r5/output/r5_manual_same_car_repeat_physics_v1.csv"

OUT_MODELS = ROOT / "r5/output/r5_manual_physics_model_comparison_v1.csv"
OUT_REPEAT_PRED = ROOT / "r5/output/r5_manual_same_car_physics_predictions_v1.csv"
OUT_FADE_PRED = ROOT / "r5/output/r5_manual_fade_physics_predictions_v1.csv"
OUT_REPORT = ROOT / "r5/output/r5_manual_physics_model_report_v1.json"


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


def lo_year_cv(rows, target, features, nonlinear=False, alpha=10.0):
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
                include_bias=False,
                interaction_only=False
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

    preds = np.full(len(y), np.nan)

    for train, test in logo.split(X, y, groups):
        model.fit(X[train], y[train])
        preds[test] = model.predict(X[test])

    mask = np.isfinite(preds)

    mae = mean_absolute_error(y[mask], preds[mask])
    rmse = np.sqrt(mean_squared_error(y[mask], preds[mask]))
    bias = float(np.mean(y[mask] - preds[mask]))

    # final fit only for coefficient inspection
    model.fit(X, y)

    out_rows = []

    for i, (r, actual, _) in enumerate(usable):
        out_rows.append({
            "year": r["year"],
            "driver_name": r.get("driver_name", ""),
            "car_number": r.get("car_number", ""),
            "actual": actual,
            "predicted_loyo": preds[i],
            "error_actual_minus_predicted": (
                actual - preds[i]
                if np.isfinite(preds[i])
                else ""
            )
        })

    return {
        "n": len(usable),
        "mae": float(mae),
        "rmse": float(rmse),
        "bias": bias,
        "pred_rows": out_rows,
        "model": model,
        "X": X,
        "y": y,
        "groups": groups,
    }


_, within = read_csv(WITHIN)
_, repeat = read_csv(REPEAT)

print("=" * 145)
print("R5 — PHYSICS MODEL DIAGNOSTICS")
print("=" * 145)


# =============================================================================
# A. WITHIN-RUN FADE
# =============================================================================

fade_specs = {
    "FADE_TRACK_ONLY": [
        "track_temp_c",
    ],

    "FADE_TRACK_NONLINEAR": [
        "track_temp_c",
    ],

    "FADE_THERMAL_CORE": [
        "track_temp_c",
        "air_temp_c",
        "shortwave_radiation_wm2",
    ],

    "FADE_FULL_PHYSICS": [
        "track_temp_c",
        "air_temp_c",
        "shortwave_radiation_wm2",
        "cloud_cover_pct",
        "wind_speed_10m_ms",
        "relative_humidity_pct",
    ],
}

comparison = []
fade_results = {}

print()
print("A. WITHIN-RUN LAP FADE")
print("-" * 145)

for name, features in fade_specs.items():

    nonlinear = name == "FADE_TRACK_NONLINEAR"

    result = lo_year_cv(
        within,
        target="lap1_to_lap4_delta_mph",
        features=features,
        nonlinear=nonlinear,
        alpha=10.0,
    )

    fade_results[name] = result

    comparison.append({
        "evidence_layer": "WITHIN_RUN_FADE",
        "model": name,
        "target": "lap1_to_lap4_delta_mph",
        "features": "|".join(features),
        "nonlinear": nonlinear,
        "n": result["n"],
        "loyo_mae": result["mae"],
        "loyo_rmse": result["rmse"],
        "loyo_bias": result["bias"],
    })

    print(
        f"{name:26s} | "
        f"n={result['n']:3d} | "
        f"MAE={result['mae']:.4f} | "
        f"RMSE={result['rmse']:.4f} | "
        f"bias={result['bias']:+.4f}"
    )


# =============================================================================
# B. SAME-CAR REPEAT ΔSPEED
# =============================================================================

repeat_specs = {
    "REPEAT_TIME_ONLY": [
        "elapsed_minutes",
    ],

    "REPEAT_TRACK_CHANGE": [
        "delta_track_temp_c",
    ],

    "REPEAT_TRACK_STATE_AND_CHANGE": [
        "before_track_temp_c",
        "delta_track_temp_c",
    ],

    "REPEAT_THERMAL_CORE": [
        "before_track_temp_c",
        "delta_track_temp_c",
        "delta_air_temp_c",
        "delta_shortwave_radiation_wm2",
    ],

    "REPEAT_FULL_PHYSICS": [
        "before_track_temp_c",
        "delta_track_temp_c",
        "delta_air_temp_c",
        "delta_shortwave_radiation_wm2",
        "delta_cloud_cover_pct",
        "delta_wind_speed_10m_ms",
        "delta_relative_humidity_pct",
        "elapsed_minutes",
    ],
}

repeat_results = {}

print()
print("B. SAME-CAR REPEAT PERFORMANCE CHANGE")
print("-" * 145)

for name, features in repeat_specs.items():

    result = lo_year_cv(
        repeat,
        target="delta_four_lap_average_speed_mph",
        features=features,
        nonlinear=False,
        alpha=10.0,
    )

    repeat_results[name] = result

    comparison.append({
        "evidence_layer": "SAME_CAR_REPEAT",
        "model": name,
        "target": "delta_four_lap_average_speed_mph",
        "features": "|".join(features),
        "nonlinear": False,
        "n": result["n"],
        "loyo_mae": result["mae"],
        "loyo_rmse": result["rmse"],
        "loyo_bias": result["bias"],
    })

    print(
        f"{name:30s} | "
        f"n={result['n']:3d} | "
        f"MAE={result['mae']:.4f} | "
        f"RMSE={result['rmse']:.4f} | "
        f"bias={result['bias']:+.4f}"
    )


# =============================================================================
# SIMPLE CORRELATIONS — physical interpretation diagnostics
# =============================================================================

print()
print("C. PHYSICAL CORRELATIONS")
print("-" * 145)

fade_pairs = [
    ("track_temp_c", "lap1_to_lap4_delta_mph"),
    ("air_temp_c", "lap1_to_lap4_delta_mph"),
    ("shortwave_radiation_wm2", "lap1_to_lap4_delta_mph"),
    ("cloud_cover_pct", "lap1_to_lap4_delta_mph"),
    ("wind_speed_10m_ms", "lap1_to_lap4_delta_mph"),
]

for xfield, yfield in fade_pairs:
    pairs = [
        (num(r.get(xfield)), num(r.get(yfield)))
        for r in within
    ]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]

    x = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])

    corr = np.corrcoef(x, y)[0, 1]

    print(
        f"fade: {xfield:32s} "
        f"r={corr:+.4f}  n={len(pairs)}"
    )

print()

repeat_pairs = [
    ("delta_track_temp_c", "delta_four_lap_average_speed_mph"),
    ("delta_air_temp_c", "delta_four_lap_average_speed_mph"),
    ("delta_shortwave_radiation_wm2", "delta_four_lap_average_speed_mph"),
    ("delta_cloud_cover_pct", "delta_four_lap_average_speed_mph"),
    ("delta_wind_speed_10m_ms", "delta_four_lap_average_speed_mph"),
]

for xfield, yfield in repeat_pairs:
    pairs = [
        (num(r.get(xfield)), num(r.get(yfield)))
        for r in repeat
    ]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]

    x = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])

    corr = np.corrcoef(x, y)[0, 1]

    print(
        f"repeat: {xfield:30s} "
        f"r={corr:+.4f}  n={len(pairs)}"
    )


# =============================================================================
# SAVE
# =============================================================================

write_csv(OUT_MODELS, comparison)

best_fade = min(
    fade_results,
    key=lambda k: fade_results[k]["mae"]
)

best_repeat = min(
    repeat_results,
    key=lambda k: repeat_results[k]["mae"]
)

fade_pred = fade_results[best_fade]["pred_rows"]
repeat_pred = repeat_results[best_repeat]["pred_rows"]

for r in fade_pred:
    r["selected_model"] = best_fade

for r in repeat_pred:
    r["selected_model"] = best_repeat

write_csv(OUT_FADE_PRED, fade_pred)
write_csv(OUT_REPEAT_PRED, repeat_pred)

report = {
    "status": "R5_MANUAL_PHYSICS_DIAGNOSTIC_COMPLETE",

    "important": (
        "Fast Friday was not used in any model in this diagnostic."
    ),

    "within_run": {
        "n": len(within),
        "selected_by_mae_for_diagnostic_only": best_fade,
        "mae": fade_results[best_fade]["mae"],
        "rmse": fade_results[best_fade]["rmse"],
    },

    "same_car_repeat": {
        "n": len(repeat),
        "selected_by_mae_for_diagnostic_only": best_repeat,
        "mae": repeat_results[best_repeat]["mae"],
        "rmse": repeat_results[best_repeat]["rmse"],
    },

    "scientific_boundary": (
        "Lowest MAE here is diagnostic only. Final model selection must "
        "retain the mandatory physical mechanism and use all three evidence "
        "layers, including first-run chronology."
    )
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("=" * 145)
print("DIAGNOSTIC SUMMARY")
print("=" * 145)
print(f"Best fade diagnostic:       {best_fade}")
print(f"Best same-car diagnostic:   {best_repeat}")
print()
print("FAST FRIDAY USED: NO")
print()
print("OUTPUTS:")
print(OUT_MODELS.relative_to(ROOT))
print(OUT_FADE_PRED.relative_to(ROOT))
print(OUT_REPEAT_PRED.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))
print()
print("R5_MANUAL_PHYSICS_DIAGNOSTIC_COMPLETE")
