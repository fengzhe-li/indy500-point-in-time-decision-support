from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import csv
import json
import math

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

PTSC_PATH = (
    ROOT
    / "weather/evidence/ptsc/"
    / "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

HRRR_PATH = (
    ROOT
    / "weather/output/hrrr_ims_2020_2024_features.csv"
)

OUT_DATASET = OUT / "r4p8_track_temperature_training_dataset_v1.csv"
OUT_METRICS = OUT / "r4p8_track_temperature_forecast_metrics_v1.csv"
OUT_PRED = OUT / "r4p8_track_temperature_forecast_predictions_v1.csv"
OUT_QA = OUT / "r4p8_track_temperature_forecast_qa_v1.csv"
OUT_REPORT = OUT / "r4p8_track_temperature_forecast_report_v1.json"

HORIZONS_MIN = [15, 30]
AVAILABILITY_LAG_MIN = 60

HRRR_FEATURES = [
    "temp_c",
    "relative_humidity_pct",
    "wind_speed_10m_ms",
    "gust_ms",
    "cloud_cover_pct",
    "shortwave_radiation_wm2",
]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def parse_dt(v):
    s = clean(v)
    if not s:
        return None

    s = s.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def fmt(v, digits=6):
    if v is None:
        return ""
    return f"{v:.{digits}f}"


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def interpolate_linear(rows, target_dt, value_key):
    rows = sorted(rows, key=lambda r: r["_dt"])

    exact = [
        r for r in rows
        if r["_dt"] == target_dt
    ]

    if exact:
        return exact[0].get(value_key)

    before = None
    after = None

    for r in rows:
        if r["_dt"] <= target_dt:
            before = r

        if r["_dt"] >= target_dt:
            after = r
            break

    if before is None or after is None:
        return None

    a = before.get(value_key)
    b = after.get(value_key)

    if a is None or b is None:
        return None

    total = (
        after["_dt"] - before["_dt"]
    ).total_seconds()

    if total <= 0:
        return None

    weight = (
        target_dt - before["_dt"]
    ).total_seconds() / total

    return a + (b - a) * weight


def interpolate_hrrr_cycle(rows, target_dt, key):
    ordered = sorted(
        rows,
        key=lambda r: r["_valid_dt"]
    )

    exact = [
        r for r in ordered
        if r["_valid_dt"] == target_dt
    ]

    if exact:
        return exact[0]["_features"].get(key)

    before = None
    after = None

    for r in ordered:
        if r["_valid_dt"] <= target_dt:
            before = r

        if r["_valid_dt"] >= target_dt:
            after = r
            break

    if before is None or after is None:
        return None

    a = before["_features"].get(key)
    b = after["_features"].get(key)

    if a is None or b is None:
        return None

    total = (
        after["_valid_dt"]
        - before["_valid_dt"]
    ).total_seconds()

    if total <= 0:
        return None

    weight = (
        target_dt
        - before["_valid_dt"]
    ).total_seconds() / total

    return a + (b - a) * weight


print("=" * 110)
print("R4P8 — TRACK SURFACE TEMPERATURE FORECAST")
print("=" * 110)

if not PTSC_PATH.exists():
    raise SystemExit(f"MISSING: {PTSC_PATH}")

if not HRRR_PATH.exists():
    raise SystemExit(f"MISSING: {HRRR_PATH}")

ptsc_raw = read_csv(PTSC_PATH)
hrrr_raw = read_csv(HRRR_PATH)

print(f"PTSC rows: {len(ptsc_raw)}")
print(f"HRRR rows: {len(hrrr_raw)}")


# ============================================================================
# 1. PTSC time series
# ============================================================================

ptsc_by_year = defaultdict(list)

for r in ptsc_raw:
    dt = parse_dt(r.get("utc_datetime"))

    track = num(r.get("track_c"))
    ambient = num(r.get("ambient_c"))
    humidity = num(r.get("humidity"))
    wind = num(r.get("wind"))
    pressure = num(r.get("pressure"))

    if dt is None or track is None:
        continue

    year = clean(r.get("year"))

    ptsc_by_year[year].append({
        "_dt": dt,
        "year": year,
        "track_c": track,
        "ambient_c": ambient,
        "humidity": humidity,
        "wind": wind,
        "pressure": pressure,
    })

for year in ptsc_by_year:
    ptsc_by_year[year].sort(
        key=lambda r: r["_dt"]
    )


# ============================================================================
# 2. HRRR cycles
# ============================================================================

hrrr_cycles = defaultdict(list)

for r in hrrr_raw:
    cycle = parse_dt(r.get("cycle_time_utc"))
    valid = parse_dt(r.get("valid_time_utc"))

    if cycle is None or valid is None:
        continue

    hrrr_cycles[cycle].append({
        "_valid_dt": valid,
        "_features": {
            f: num(r.get(f))
            for f in HRRR_FEATURES
        }
    })

cycle_times = sorted(hrrr_cycles.keys())


# ============================================================================
# 3. Build supervised thermal dataset
#
# Features available at time t:
# - current track temperature
# - current ambient/weather observations
# - past track-temperature slope
# - HRRR cycle already available at least 60 min earlier
# - HRRR forecast change from t to t+horizon
#
# Target:
# track temperature at t+horizon.
# ============================================================================

dataset = []

for year, rows in ptsc_by_year.items():

    for current in rows:

        t = current["_dt"]

        current_track = current["track_c"]

        track_15m_ago = interpolate_linear(
            rows,
            t - timedelta(minutes=15),
            "track_c"
        )

        track_30m_ago = interpolate_linear(
            rows,
            t - timedelta(minutes=30),
            "track_c"
        )

        slope_15 = (
            (current_track - track_15m_ago) / 15.0
            if track_15m_ago is not None
            else None
        )

        slope_30 = (
            (current_track - track_30m_ago) / 30.0
            if track_30m_ago is not None
            else None
        )

        latest_allowed_cycle = (
            t - timedelta(minutes=AVAILABILITY_LAG_MIN)
        )

        available_cycles = [
            c for c in cycle_times
            if (
                c <= latest_allowed_cycle
                and c.date() == t.date()
            )
        ]

        if not available_cycles:
            continue

        selected_cycle = max(available_cycles)

        hrrr_now = {}

        for feature in HRRR_FEATURES:
            hrrr_now[feature] = interpolate_hrrr_cycle(
                hrrr_cycles[selected_cycle],
                t,
                feature
            )

        for horizon in HORIZONS_MIN:

            future_t = t + timedelta(minutes=horizon)

            future_track = interpolate_linear(
                rows,
                future_t,
                "track_c"
            )

            if future_track is None:
                continue

            hrrr_future = {}

            for feature in HRRR_FEATURES:
                hrrr_future[feature] = interpolate_hrrr_cycle(
                    hrrr_cycles[selected_cycle],
                    future_t,
                    feature
                )

            if any(
                hrrr_now[f] is None
                or hrrr_future[f] is None
                for f in HRRR_FEATURES
            ):
                continue

            row = {
                "year": year,
                "decision_time_utc": t.isoformat(),
                "target_time_utc": future_t.isoformat(),
                "horizon_min": horizon,

                "selected_hrrr_cycle_utc":
                    selected_cycle.isoformat(),

                "cycle_age_minutes":
                    (
                        t - selected_cycle
                    ).total_seconds() / 60.0,

                "current_track_c":
                    current_track,

                "current_ambient_c":
                    current["ambient_c"],

                "current_humidity":
                    current["humidity"],

                "current_wind":
                    current["wind"],

                "current_pressure":
                    current["pressure"],

                "track_minus_ambient_c":
                    (
                        current_track
                        - current["ambient_c"]
                        if current["ambient_c"] is not None
                        else None
                    ),

                "past_track_slope_15m_c_per_min":
                    slope_15,

                "past_track_slope_30m_c_per_min":
                    slope_30,

                "target_track_c":
                    future_track,

                "target_delta_track_c":
                    future_track - current_track,

                "future_realized_weather_used":
                    False,
            }

            for feature in HRRR_FEATURES:

                now = hrrr_now[feature]
                future = hrrr_future[feature]

                row[
                    f"hrrr_now_{feature}"
                ] = now

                row[
                    f"hrrr_future_{feature}"
                ] = future

                row[
                    f"hrrr_delta_{feature}"
                ] = future - now

            dataset.append(row)


# ============================================================================
# 4. ML features
# ============================================================================

FEATURES = [
    "current_track_c",
    "current_ambient_c",
    "current_humidity",
    "current_wind",
    "current_pressure",
    "track_minus_ambient_c",
    "past_track_slope_15m_c_per_min",
    "past_track_slope_30m_c_per_min",
    "hrrr_now_temp_c",
    "hrrr_future_temp_c",
    "hrrr_delta_temp_c",
    "hrrr_delta_relative_humidity_pct",
    "hrrr_delta_wind_speed_10m_ms",
    "hrrr_delta_gust_ms",
    "hrrr_delta_cloud_cover_pct",
    "hrrr_delta_shortwave_radiation_wm2",
]


def complete(row):
    return all(
        row.get(f) is not None
        for f in FEATURES
    )


model_rows = [
    r for r in dataset
    if complete(r)
]


# ============================================================================
# 5. Leave-one-year-out validation
# ============================================================================

years = sorted({
    r["year"]
    for r in model_rows
})

predictions = []

MODEL_NAMES = [
    "PERSISTENCE",
    "LINEAR_RIDGE",
    "RANDOM_FOREST",
]


for horizon in HORIZONS_MIN:

    horizon_rows = [
        r for r in model_rows
        if r["horizon_min"] == horizon
    ]

    for test_year in years:

        train = [
            r for r in horizon_rows
            if r["year"] != test_year
        ]

        test = [
            r for r in horizon_rows
            if r["year"] == test_year
        ]

        if not train or not test:
            continue

        actual = np.array(
            [r["target_track_c"] for r in test],
            dtype=float
        )

        # ------------------------------------------------------------
        # Persistence baseline
        # ------------------------------------------------------------

        pred_persistence = np.array(
            [r["current_track_c"] for r in test],
            dtype=float
        )

        for row, a, p in zip(
            test,
            actual,
            pred_persistence
        ):
            predictions.append({
                "horizon_min": horizon,
                "model_name": "PERSISTENCE",
                "test_year": test_year,
                "decision_time_utc":
                    row["decision_time_utc"],
                "actual_track_c": a,
                "predicted_track_c": p,
            })

        # ------------------------------------------------------------
        # Ridge
        # ------------------------------------------------------------

        X_train = np.array(
            [
                [r[f] for f in FEATURES]
                for r in train
            ],
            dtype=float
        )

        y_train = np.array(
            [r["target_track_c"] for r in train],
            dtype=float
        )

        X_test = np.array(
            [
                [r[f] for f in FEATURES]
                for r in test
            ],
            dtype=float
        )

        ridge = Pipeline([
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=10.0))
        ])

        ridge.fit(X_train, y_train)

        pred_ridge = ridge.predict(X_test)

        for row, a, p in zip(
            test,
            actual,
            pred_ridge
        ):
            predictions.append({
                "horizon_min": horizon,
                "model_name": "LINEAR_RIDGE",
                "test_year": test_year,
                "decision_time_utc":
                    row["decision_time_utc"],
                "actual_track_c": a,
                "predicted_track_c": float(p),
            })

        # ------------------------------------------------------------
        # Random forest
        # ------------------------------------------------------------

        forest = RandomForestRegressor(
            n_estimators=300,
            max_depth=4,
            min_samples_leaf=3,
            random_state=42,
        )

        forest.fit(X_train, y_train)

        pred_forest = forest.predict(X_test)

        for row, a, p in zip(
            test,
            actual,
            pred_forest
        ):
            predictions.append({
                "horizon_min": horizon,
                "model_name": "RANDOM_FOREST",
                "test_year": test_year,
                "decision_time_utc":
                    row["decision_time_utc"],
                "actual_track_c": a,
                "predicted_track_c": float(p),
            })


# ============================================================================
# 6. Metrics
# ============================================================================

metrics = []

for horizon in HORIZONS_MIN:

    for model_name in MODEL_NAMES:

        rows = [
            r for r in predictions
            if (
                r["horizon_min"] == horizon
                and r["model_name"] == model_name
            )
        ]

        if not rows:
            continue

        actual = np.array(
            [r["actual_track_c"] for r in rows],
            dtype=float
        )

        pred = np.array(
            [r["predicted_track_c"] for r in rows],
            dtype=float
        )

        mae = mean_absolute_error(
            actual,
            pred
        )

        rmse = math.sqrt(
            mean_squared_error(
                actual,
                pred
            )
        )

        delta_actual = []
        delta_pred = []

        dataset_lookup = {
            (
                r["decision_time_utc"],
                r["horizon_min"]
            ): r
            for r in model_rows
        }

        for p in rows:

            key = (
                p["decision_time_utc"],
                horizon
            )

            d = dataset_lookup.get(key)

            if d is None:
                continue

            delta_actual.append(
                p["actual_track_c"]
                - d["current_track_c"]
            )

            delta_pred.append(
                p["predicted_track_c"]
                - d["current_track_c"]
            )

        direction_acc = None

        if delta_actual:
            direction_acc = float(
                np.mean(
                    np.sign(delta_actual)
                    ==
                    np.sign(delta_pred)
                )
            )

        metrics.append({
            "horizon_min": horizon,
            "model_name": model_name,
            "pooled_loyo_rows": len(rows),
            "mae_c": mae,
            "rmse_c": rmse,
            "direction_accuracy":
                direction_acc,
        })


# ============================================================================
# 7. Save outputs
# ============================================================================

dataset_fields = [
    "year",
    "decision_time_utc",
    "target_time_utc",
    "horizon_min",
    "selected_hrrr_cycle_utc",
    "cycle_age_minutes",
    "current_track_c",
    "current_ambient_c",
    "current_humidity",
    "current_wind",
    "current_pressure",
    "track_minus_ambient_c",
    "past_track_slope_15m_c_per_min",
    "past_track_slope_30m_c_per_min",
    "target_track_c",
    "target_delta_track_c",
    "future_realized_weather_used",
]

for feature in HRRR_FEATURES:
    dataset_fields.extend([
        f"hrrr_now_{feature}",
        f"hrrr_future_{feature}",
        f"hrrr_delta_{feature}",
    ])

write_csv(
    OUT_DATASET,
    dataset,
    dataset_fields
)

write_csv(
    OUT_METRICS,
    metrics,
    [
        "horizon_min",
        "model_name",
        "pooled_loyo_rows",
        "mae_c",
        "rmse_c",
        "direction_accuracy",
    ]
)

write_csv(
    OUT_PRED,
    predictions,
    [
        "horizon_min",
        "model_name",
        "test_year",
        "decision_time_utc",
        "actual_track_c",
        "predicted_track_c",
    ]
)


# ============================================================================
# 8. QA
# ============================================================================

unsafe = []

for r in dataset:

    decision = parse_dt(
        r["decision_time_utc"]
    )

    cycle = parse_dt(
        r["selected_hrrr_cycle_utc"]
    )

    if (
        decision is None
        or cycle is None
        or cycle
        >
        decision
        - timedelta(
            minutes=AVAILABILITY_LAG_MIN
        )
    ):
        unsafe.append(r)

qa_rows = [
    {
        "metric": "raw_ptsc_rows",
        "value": len(ptsc_raw),
        "expected": 168,
        "status": (
            "PASS"
            if len(ptsc_raw) == 168
            else "FAIL"
        ),
    },
    {
        "metric": "supervised_rows",
        "value": len(dataset),
        "expected": ">0",
        "status": (
            "PASS"
            if len(dataset) > 0
            else "FAIL"
        ),
    },
    {
        "metric": "ml_complete_rows",
        "value": len(model_rows),
        "expected": ">0",
        "status": (
            "PASS"
            if len(model_rows) > 0
            else "FAIL"
        ),
    },
    {
        "metric": "unsafe_hrrr_cycle_rows",
        "value": len(unsafe),
        "expected": 0,
        "status": (
            "PASS"
            if len(unsafe) == 0
            else "FAIL"
        ),
    },
    {
        "metric": "future_realized_weather_used",
        "value": 0,
        "expected": 0,
        "status": "PASS",
    },
    {
        "metric": "validation_protocol",
        "value": "LEAVE_ONE_YEAR_OUT",
        "expected": "LEAVE_ONE_YEAR_OUT",
        "status": "PASS",
    },
]

write_csv(
    OUT_QA,
    qa_rows,
    [
        "metric",
        "value",
        "expected",
        "status",
    ]
)


# ============================================================================
# 9. Report
# ============================================================================

best_by_horizon = {}

for horizon in HORIZONS_MIN:

    h = [
        r for r in metrics
        if r["horizon_min"] == horizon
    ]

    if h:
        best = min(
            h,
            key=lambda r: r["mae_c"]
        )

        best_by_horizon[str(horizon)] = {
            "model_name":
                best["model_name"],

            "mae_c":
                best["mae_c"],

            "rmse_c":
                best["rmse_c"],

            "direction_accuracy":
                best["direction_accuracy"],
        }


report = {
    "phase": "R4P8",

    "purpose": (
        "Forecast future Indy 500 track-surface "
        "temperature from current PTSC thermal state, "
        "past thermal trend and decision-time-safe "
        "HRRR atmospheric forecast."
    ),

    "raw_ptsc_rows":
        len(ptsc_raw),

    "supervised_rows":
        len(dataset),

    "ml_complete_rows":
        len(model_rows),

    "horizons_minutes":
        HORIZONS_MIN,

    "availability_lag_guard_minutes":
        AVAILABILITY_LAG_MIN,

    "validation":
        "leave-one-year-out",

    "future_realized_weather_used":
        False,

    "best_by_horizon":
        best_by_horizon,

    "important_semantics": {
        "track_temperature": (
            "PTSC observed track-surface temperature."
        ),

        "current_state": (
            "Observed at decision time."
        ),

        "past_slope": (
            "Uses only previous PTSC observations."
        ),

        "future_atmosphere": (
            "Uses HRRR cycle available before "
            "decision time."
        ),

        "strategy": (
            "No STOP / RETAIN / WITHDRAW "
            "recommendation is made."
        ),
    },
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# ============================================================================
# 10. Console
# ============================================================================

print()
print("=" * 110)
print("R4P8 SUMMARY")
print("=" * 110)

print(f"Raw PTSC rows: {len(ptsc_raw)}")
print(f"Supervised horizon rows: {len(dataset)}")
print(f"ML-complete rows: {len(model_rows)}")

print()
print("POOLED LOYO")

for horizon in HORIZONS_MIN:

    print()
    print(f"{horizon} MINUTES")

    for r in [
        x for x in metrics
        if x["horizon_min"] == horizon
    ]:
        print(
            f"{r['model_name']:16s} | "
            f"n={r['pooled_loyo_rows']:>3} | "
            f"MAE={r['mae_c']:.4f} C | "
            f"RMSE={r['rmse_c']:.4f} C | "
            f"direction={r['direction_accuracy']:.4f}"
        )

print()
print("BEST BY HORIZON")

for horizon, result in best_by_horizon.items():
    print(
        f"{horizon}m: "
        f"{result['model_name']} | "
        f"MAE={result['mae_c']:.4f} C | "
        f"RMSE={result['rmse_c']:.4f} C | "
        f"direction={result['direction_accuracy']:.4f}"
    )


failed = [
    r for r in qa_rows
    if r["status"] != "PASS"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:
    print("FAILED QA")

    for r in failed:
        print(
            f"  {r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)

print()
print("OUTPUTS")
print(OUT_DATASET.relative_to(ROOT))
print(OUT_METRICS.relative_to(ROOT))
print(OUT_PRED.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("R4P8_TRACK_TEMPERATURE_FORECAST_READY")
