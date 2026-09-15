from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import csv
import json
import math

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

TRANS_PATH = OUT / "r4p2_multi_run_transitions_v1.csv"
HRRR_PATH = ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"

OUT_SCENARIOS = OUT / "r4p5_decision_safe_forecast_scenarios_v1.csv"
OUT_QA = OUT / "r4p5_decision_safe_forecast_scenarios_qa_v1.csv"
OUT_REPORT = OUT / "r4p5_decision_safe_forecast_scenarios_report_v1.json"

HORIZONS_MIN = [10, 20, 30]

# Conservative availability guard.
# A cycle must be at least 60 minutes old at decision time.
AVAILABILITY_LAG_MIN = 60

FEATURES = [
    "temp_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "wind_speed_10m_ms",
    "wind_direction_deg",
    "pressure_hpa",
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
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def lerp(a, b, w):
    if a is None or b is None:
        return None
    return a + (b - a) * w


def circular_interp_deg(a, b, w):
    if a is None or b is None:
        return None

    ar = math.radians(a)
    br = math.radians(b)

    ax, ay = math.cos(ar), math.sin(ar)
    bx, by = math.cos(br), math.sin(br)

    x = ax + (bx - ax) * w
    y = ay + (by - ay) * w

    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None

    deg = math.degrees(math.atan2(y, x))
    return deg % 360.0


def interpolate_cycle(cycle_rows, target_dt):
    rows = sorted(
        cycle_rows,
        key=lambda r: r["_valid_dt"]
    )

    if not rows:
        return None

    exact = [
        r for r in rows
        if r["_valid_dt"] == target_dt
    ]

    if exact:
        r = exact[0]
        return {
            k: r["_features"][k]
            for k in FEATURES
        }

    before = None
    after = None

    for r in rows:
        if r["_valid_dt"] <= target_dt:
            before = r

        if r["_valid_dt"] >= target_dt:
            after = r
            break

    if before is None or after is None:
        return None

    if before["_valid_dt"] == after["_valid_dt"]:
        return {
            k: before["_features"][k]
            for k in FEATURES
        }

    total = (
        after["_valid_dt"] - before["_valid_dt"]
    ).total_seconds()

    pos = (
        target_dt - before["_valid_dt"]
    ).total_seconds()

    w = pos / total

    out = {}

    for k in FEATURES:
        a = before["_features"][k]
        b = after["_features"][k]

        if k == "wind_direction_deg":
            out[k] = circular_interp_deg(a, b, w)
        else:
            out[k] = lerp(a, b, w)

    return out


print("=" * 110)
print("R4P5 — DECISION-TIME-SAFE FUTURE WEATHER SCENARIOS")
print("=" * 110)

if not TRANS_PATH.exists():
    raise SystemExit(f"MISSING: {TRANS_PATH}")

if not HRRR_PATH.exists():
    raise SystemExit(f"MISSING: {HRRR_PATH}")

transitions = read_csv(TRANS_PATH)
raw_hrrr = read_csv(HRRR_PATH)

print(f"Transitions: {len(transitions)}")
print(f"Raw HRRR rows: {len(raw_hrrr)}")


# ----------------------------------------------------------------------
# 1. Parse HRRR by cycle
# ----------------------------------------------------------------------

cycles = defaultdict(list)

for r in raw_hrrr:
    cycle_dt = parse_dt(r.get("cycle_time_utc"))
    valid_dt = parse_dt(r.get("valid_time_utc"))

    if cycle_dt is None or valid_dt is None:
        continue

    key = cycle_dt

    cycles[key].append({
        "_cycle_dt": cycle_dt,
        "_valid_dt": valid_dt,
        "_forecast_hour": num(r.get("forecast_hour")),
        "_features": {
            k: num(r.get(k))
            for k in FEATURES
        }
    })

cycle_times = sorted(cycles.keys())

print(f"Distinct HRRR cycles: {len(cycle_times)}")


# ----------------------------------------------------------------------
# 2. Build decision-safe scenarios
# ----------------------------------------------------------------------

scenario_rows = []

eligible_transition_count = 0
selected_cycle_count = 0

for t in transitions:

    before_dt = parse_dt(t.get("before_time_utc"))

    if before_dt is None:
        continue

    eligible_transition_count += 1

    latest_allowed_cycle = (
        before_dt - timedelta(
            minutes=AVAILABILITY_LAG_MIN
        )
    )

    available_cycles = [
        c for c in cycle_times
        if c <= latest_allowed_cycle
        and c.date() == before_dt.date()
    ]

    if not available_cycles:
        continue

    selected_cycle = max(available_cycles)

    current_forecast = interpolate_cycle(
        cycles[selected_cycle],
        before_dt
    )

    if current_forecast is None:
        continue

    selected_cycle_count += 1

    base = {
        "year": clean(t.get("year")),
        "session_id": clean(t.get("session_id")),
        "car_number": clean(t.get("car_number")),
        "driver_name": clean(t.get("driver_name")),
        "before_attempt_id": clean(t.get("before_attempt_id")),
        "after_attempt_id": clean(t.get("after_attempt_id")),

        "decision_time_utc": before_dt.isoformat(),
        "selected_hrrr_cycle_utc": selected_cycle.isoformat(),

        "cycle_age_minutes_at_decision": fmt(
            (
                before_dt - selected_cycle
            ).total_seconds() / 60.0
        ),

        "availability_lag_guard_minutes":
            AVAILABILITY_LAG_MIN,

        "actual_next_attempt_time_utc":
            clean(t.get("after_time_utc")),

        "actual_between_attempt_observation_minutes":
            clean(
                t.get(
                    "elapsed_between_performance_observations_min"
                )
            ),

        "actual_next_run_speed_delta_mph":
            clean(
                t.get(
                    "delta_four_lap_average_speed_mph"
                )
            ),

        "actual_next_run_improved":
            clean(t.get("speed_improved")),

        "realized_future_environment_used":
            "False",

        "decision_time_safe":
            "True",
    }

    for k in FEATURES:
        base[f"forecast_now_{k}"] = fmt(
            current_forecast[k]
        )

    for horizon in HORIZONS_MIN:

        target_dt = before_dt + timedelta(
            minutes=horizon
        )

        future = interpolate_cycle(
            cycles[selected_cycle],
            target_dt
        )

        base[
            f"forecast_plus_{horizon}m_available"
        ] = str(future is not None)

        if future is None:
            for k in FEATURES:
                base[
                    f"forecast_plus_{horizon}m_{k}"
                ] = ""

                base[
                    f"forecast_delta_{horizon}m_{k}"
                ] = ""

                base[
                    f"forecast_rate_{horizon}m_{k}_per_min"
                ] = ""

            continue

        for k in FEATURES:

            future_value = future[k]
            current_value = current_forecast[k]

            base[
                f"forecast_plus_{horizon}m_{k}"
            ] = fmt(future_value)

            if (
                future_value is not None
                and current_value is not None
            ):
                d = future_value - current_value

                # Direction is circular; simple numeric delta
                # is not meaningful across 0/360.
                if k == "wind_direction_deg":
                    raw_d = (
                        (future_value - current_value + 180)
                        % 360
                    ) - 180
                    d = raw_d

                base[
                    f"forecast_delta_{horizon}m_{k}"
                ] = fmt(d)

                base[
                    f"forecast_rate_{horizon}m_{k}_per_min"
                ] = fmt(
                    d / horizon,
                    8
                )

            else:
                base[
                    f"forecast_delta_{horizon}m_{k}"
                ] = ""

                base[
                    f"forecast_rate_{horizon}m_{k}_per_min"
                ] = ""

    scenario_rows.append(base)


# ----------------------------------------------------------------------
# 3. Output fields
# ----------------------------------------------------------------------

fields = [
    "year",
    "session_id",
    "car_number",
    "driver_name",
    "before_attempt_id",
    "after_attempt_id",
    "decision_time_utc",
    "selected_hrrr_cycle_utc",
    "cycle_age_minutes_at_decision",
    "availability_lag_guard_minutes",
    "actual_next_attempt_time_utc",
    "actual_between_attempt_observation_minutes",
    "actual_next_run_speed_delta_mph",
    "actual_next_run_improved",
    "realized_future_environment_used",
    "decision_time_safe",
]

for k in FEATURES:
    fields.append(f"forecast_now_{k}")

for horizon in HORIZONS_MIN:
    fields.append(
        f"forecast_plus_{horizon}m_available"
    )

    for k in FEATURES:
        fields.append(
            f"forecast_plus_{horizon}m_{k}"
        )
        fields.append(
            f"forecast_delta_{horizon}m_{k}"
        )
        fields.append(
            f"forecast_rate_{horizon}m_{k}_per_min"
        )

write_csv(
    OUT_SCENARIOS,
    scenario_rows,
    fields
)


# ----------------------------------------------------------------------
# 4. QA
# ----------------------------------------------------------------------

qa_rows = []

bad_leak = [
    r for r in scenario_rows
    if r["realized_future_environment_used"] != "False"
]

bad_cycle = []

for r in scenario_rows:
    d = parse_dt(r["decision_time_utc"])
    c = parse_dt(r["selected_hrrr_cycle_utc"])

    if d is None or c is None:
        bad_cycle.append(r)
        continue

    if c > d - timedelta(
        minutes=AVAILABILITY_LAG_MIN
    ):
        bad_cycle.append(r)

bad_safe = [
    r for r in scenario_rows
    if r["decision_time_safe"] != "True"
]

qa_rows.extend([
    {
        "metric": "transition_rows_with_before_point_time",
        "value": eligible_transition_count,
        "expected": ">0",
        "status": (
            "PASS"
            if eligible_transition_count > 0
            else "FAIL"
        ),
    },
    {
        "metric": "rows_with_selected_safe_cycle",
        "value": len(scenario_rows),
        "expected": ">0",
        "status": (
            "PASS"
            if len(scenario_rows) > 0
            else "FAIL"
        ),
    },
    {
        "metric": "future_realized_environment_used",
        "value": len(bad_leak),
        "expected": 0,
        "status": (
            "PASS"
            if len(bad_leak) == 0
            else "FAIL"
        ),
    },
    {
        "metric": "cycle_availability_guard_violations",
        "value": len(bad_cycle),
        "expected": 0,
        "status": (
            "PASS"
            if len(bad_cycle) == 0
            else "FAIL"
        ),
    },
    {
        "metric": "decision_time_safe_rows",
        "value": len(scenario_rows) - len(bad_safe),
        "expected": len(scenario_rows),
        "status": (
            "PASS"
            if len(bad_safe) == 0
            else "FAIL"
        ),
    },
])

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


# ----------------------------------------------------------------------
# 5. Report
# ----------------------------------------------------------------------

coverage = {}

for year in ["2020", "2021", "2022", "2023", "2024"]:

    yr = [
        r for r in scenario_rows
        if r["year"] == year
    ]

    coverage[year] = {
        "rows": len(yr),

        "plus10_available": sum(
            r["forecast_plus_10m_available"] == "True"
            for r in yr
        ),

        "plus20_available": sum(
            r["forecast_plus_20m_available"] == "True"
            for r in yr
        ),

        "plus30_available": sum(
            r["forecast_plus_30m_available"] == "True"
            for r in yr
        ),
    }


report = {
    "phase": "R4P5",
    "purpose": (
        "Build decision-time-safe HRRR future-weather "
        "scenario features for repeat-run decisions."
    ),
    "availability_guard_minutes":
        AVAILABILITY_LAG_MIN,
    "horizons_minutes":
        HORIZONS_MIN,
    "input_transition_rows":
        len(transitions),
    "point-time_eligible_transitions":
        eligible_transition_count,
    "scenario_rows":
        len(scenario_rows),
    "coverage":
        coverage,
    "realized_future_environment_used":
        False,
    "model_fitting_performed":
        False,
    "important_note": (
        "Future forecast values come from one HRRR cycle "
        "already available before the decision point. "
        "No after-run realized weather is used."
    ),
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# ----------------------------------------------------------------------
# 6. Console
# ----------------------------------------------------------------------

print()
print("=" * 110)
print("R4P5 SUMMARY")
print("=" * 110)

print(
    f"Transitions with decision point time: "
    f"{eligible_transition_count}"
)

print(
    f"Decision-safe scenario rows: "
    f"{len(scenario_rows)}"
)

print()
print("BY YEAR")

for year in ["2020", "2021", "2022", "2023", "2024"]:
    c = coverage[year]

    print(
        f"{year}: "
        f"rows={c['rows']} | "
        f"+10m={c['plus10_available']} | "
        f"+20m={c['plus20_available']} | "
        f"+30m={c['plus30_available']}"
    )

print()
print("QA")

failed = []

for r in qa_rows:
    print(
        f"{r['metric']}: "
        f"{r['value']} | "
        f"{r['status']}"
    )

    if r["status"] != "PASS":
        failed.append(r)

if failed:
    raise SystemExit(1)

print()
print("OUTPUTS")
print(OUT_SCENARIOS.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("R4P5_DECISION_SAFE_FORECAST_SCENARIOS_READY")
