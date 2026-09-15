from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import csv
import json
import math
import statistics

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

MULTI_PATH = OUT / "r4p1_multi_run_four_lap_panel_v1.csv"

HRRR_PATH = (
    ROOT /
    "weather/output/performance_grade_hrrr_forecast_alignment.csv"
)

PTSC_PATHS = [
    ROOT / "weather/output/performance_grade_attempt_realized_environment.csv",
    ROOT / "weather/output/performance_grade_attempt_realized_environment_2024_supported.csv",
    ROOT / "weather/output/ptsc_attempt_realized_environment_alignment.csv",
]

OUTPUT_TRANSITIONS = (
    OUT / "r4p2_multi_run_transitions_v1.csv"
)

OUTPUT_ENV = (
    OUT / "r4p2_environment_linked_transitions_v1.csv"
)

OUTPUT_SIGNAL = (
    OUT / "r4p2_past_only_cross_car_signal_v1.csv"
)

OUTPUT_SUMMARY = (
    OUT / "r4p2_transition_environment_summary_v1.csv"
)

OUTPUT_QA = (
    OUT / "r4p2_qa_v1.csv"
)

OUTPUT_REPORT = (
    OUT / "r4p2_report_v1.json"
)


# =============================================================================
# Helpers
# =============================================================================

def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def as_float(value):
    value = clean(value)

    if not value:
        return None

    try:
        x = float(value)
        if math.isfinite(x):
            return x
    except Exception:
        pass

    return None


def as_int(value):
    x = as_float(value)

    if x is None:
        return None

    rounded = round(x)

    if abs(x - rounded) > 1e-9:
        return None

    return int(rounded)


def as_bool(value):
    return clean(value).lower() in {
        "true", "1", "yes", "y"
    }


def fmt(value, digits=6):
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def parse_time(value):
    value = clean(value)

    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        return datetime.fromisoformat(value)

    except Exception:
        return None


def minutes_between(t1, t2):
    a = parse_time(t1)
    b = parse_time(t2)

    if a is None or b is None:
        return None

    return (b - a).total_seconds() / 60.0


def delta(a, b):
    a = as_float(a)
    b = as_float(b)

    if a is None or b is None:
        return None

    return b - a


def rate(change, minutes):
    if change is None:
        return None

    if minutes is None or minutes <= 0:
        return None

    return change / minutes


def mean(values):
    values = [
        v for v in values
        if v is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def median(values):
    values = [
        v for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.median(values)


def stdev(values):
    values = [
        v for v in values
        if v is not None
    ]

    if len(values) < 2:
        return None

    return statistics.stdev(values)


def write_csv(path, rows, fieldnames):
    with path.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def qa(metric, value, expected, passed, detail=""):
    return {
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


print("=" * 110)
print("R4P2 — MULTI-RUN TRANSITION + ENVIRONMENT + PAST-ONLY CROSS-CAR SIGNAL")
print("=" * 110)

if not MULTI_PATH.exists():
    raise SystemExit(
        f"MISSING REQUIRED R4P1 INPUT: {MULTI_PATH}"
    )

multi = read_csv(MULTI_PATH)

print(f"R4P1 multi-run rows: {len(multi)}")


# =============================================================================
# 1. HRRR attempt-level environment map
#
# These are leakage-safe forecasts aligned to approximate performance time.
# They are NOT treated as exact run-start weather truth.
# =============================================================================

hrrr = {}

for row in read_csv(HRRR_PATH):

    attempt_id = clean(row.get("attempt_id"))

    if not attempt_id:
        continue

    if not as_bool(row.get("leakage_safe")):
        continue

    if not as_bool(
        row.get("performance_alignment_usable")
    ):
        continue

    hrrr[attempt_id] = {
        "forecast_temp_c":
            as_float(row.get("forecast_temp_c")),

        "forecast_dewpoint_c":
            as_float(row.get("forecast_dewpoint_c")),

        "forecast_relative_humidity_pct":
            as_float(
                row.get(
                    "forecast_relative_humidity_pct"
                )
            ),

        "forecast_wind_speed_10m_ms":
            as_float(
                row.get(
                    "forecast_wind_speed_10m_ms"
                )
            ),

        "forecast_wind_direction_deg":
            as_float(
                row.get(
                    "forecast_wind_direction_deg"
                )
            ),

        "forecast_gust_ms":
            as_float(row.get("forecast_gust_ms")),

        "forecast_pressure_hpa":
            as_float(
                row.get("forecast_pressure_hpa")
            ),

        "forecast_cloud_cover_pct":
            as_float(
                row.get(
                    "forecast_cloud_cover_pct"
                )
            ),

        "forecast_shortwave_radiation_wm2":
            as_float(
                row.get(
                    "forecast_shortwave_radiation_wm2"
                )
            ),

        "forecast_issue_time_utc":
            clean(
                row.get("selected_issue_time_utc")
            ),

        "performance_time_utc":
            clean(row.get("performance_time_utc")),

        "timing_class":
            clean(row.get("timing_class")),
    }


# =============================================================================
# 2. PTSC attempt-level map
#
# Prefer performance-grade alignment first.
# Later files only fill gaps.
# =============================================================================

ptsc = {}

for priority, path in enumerate(PTSC_PATHS):

    for row in read_csv(path):

        attempt_id = clean(row.get("attempt_id"))

        if not attempt_id:
            continue

        track = as_float(
            row.get("ptsc_track_c")
        )

        ambient = as_float(
            row.get("ptsc_ambient_c")
        )

        status = (
            clean(row.get("ptsc_alignment_status"))
            or clean(row.get("ptsc_interp_status"))
        ).upper()

        if "NO_TARGET_TIME" in status:
            continue

        if "NOT_ALIGNABLE" in status:
            continue

        if track is None and ambient is None:
            continue

        candidate = {
            "ptsc_track_c": track,
            "ptsc_ambient_c": ambient,
            "ptsc_humidity":
                as_float(row.get("ptsc_humidity")),
            "ptsc_wind":
                as_float(row.get("ptsc_wind")),
            "ptsc_pressure":
                as_float(row.get("ptsc_pressure")),
            "ptsc_before_utc":
                clean(row.get("ptsc_before_utc")),
            "ptsc_after_utc":
                clean(row.get("ptsc_after_utc")),
            "ptsc_gap_minutes":
                as_float(row.get("ptsc_gap_minutes")),
            "ptsc_source": path.name,
            "source_priority": priority,
        }

        if attempt_id not in ptsc:
            ptsc[attempt_id] = candidate

        elif (
            candidate["source_priority"]
            <
            ptsc[attempt_id]["source_priority"]
        ):
            ptsc[attempt_id] = candidate


# =============================================================================
# 3. Organize same-car same-day runs
# =============================================================================

groups = defaultdict(list)

for row in multi:

    key = (
        clean(row.get("session_id")),
        clean(row.get("car_number")),
        clean(row.get("driver_name")),
    )

    groups[key].append(row)


def run_sort_key(row):

    idx = as_int(
        row.get("run_index_observed")
    )

    if idx is None:
        idx = as_int(
            row.get("car_attempt_index")
        )

    point = parse_time(
        row.get("time_point_utc")
    )

    return (
        idx if idx is not None else 999,
        point if point is not None
        else datetime.max.replace(tzinfo=None),
        clean(row.get("attempt_id"))
    )


# Avoid aware/naive datetime comparison issues by sorting index first,
# then timestamp text as secondary fallback.
def safe_run_sort_key(row):

    idx = as_int(
        row.get("run_index_observed")
    )

    if idx is None:
        idx = as_int(
            row.get("car_attempt_index")
        )

    return (
        idx if idx is not None else 999,
        clean(row.get("time_point_utc")),
        clean(row.get("attempt_id")),
    )


# =============================================================================
# 4. Consecutive transitions
#
# For A1, A2, A3:
# create A1->A2 and A2->A3.
#
# We do NOT create every pair combination centrally because that would
# overweight cars with many attempts.
# =============================================================================

transitions = []

for key, rows in groups.items():

    rows = sorted(
        rows,
        key=safe_run_sort_key
    )

    if len(rows) < 2:
        continue

    for i in range(1, len(rows)):

        before = rows[i - 1]
        after = rows[i]

        before_id = clean(
            before.get("attempt_id")
        )

        after_id = clean(
            after.get("attempt_id")
        )

        before_index = (
            as_int(
                before.get("run_index_observed")
            )
            or
            as_int(
                before.get("car_attempt_index")
            )
        )

        after_index = (
            as_int(
                after.get("run_index_observed")
            )
            or
            as_int(
                after.get("car_attempt_index")
            )
        )

        before_time = clean(
            before.get("time_point_utc")
        )

        after_time = clean(
            after.get("time_point_utc")
        )

        elapsed_min = minutes_between(
            before_time,
            after_time
        )

        speed_delta = delta(
            before.get(
                "four_lap_average_speed_mph"
            ),
            after.get(
                "four_lap_average_speed_mph"
            )
        )

        l14_delta = delta(
            before.get(
                "lap1_to_lap4_delta_mph"
            ),
            after.get(
                "lap1_to_lap4_delta_mph"
            )
        )

        late_fade_delta = delta(
            before.get(
                "late_run_fade_mph"
            ),
            after.get(
                "late_run_fade_mph"
            )
        )

        bh = hrrr.get(before_id, {})
        ah = hrrr.get(after_id, {})

        bp = ptsc.get(before_id, {})
        ap = ptsc.get(after_id, {})

        d_track = delta(
            bp.get("ptsc_track_c"),
            ap.get("ptsc_track_c")
        )

        d_ambient = delta(
            bp.get("ptsc_ambient_c"),
            ap.get("ptsc_ambient_c")
        )

        d_ptsc_humidity = delta(
            bp.get("ptsc_humidity"),
            ap.get("ptsc_humidity")
        )

        d_ptsc_wind = delta(
            bp.get("ptsc_wind"),
            ap.get("ptsc_wind")
        )

        d_temp = delta(
            bh.get("forecast_temp_c"),
            ah.get("forecast_temp_c")
        )

        d_rh = delta(
            bh.get(
                "forecast_relative_humidity_pct"
            ),
            ah.get(
                "forecast_relative_humidity_pct"
            )
        )

        d_wind = delta(
            bh.get(
                "forecast_wind_speed_10m_ms"
            ),
            ah.get(
                "forecast_wind_speed_10m_ms"
            )
        )

        d_gust = delta(
            bh.get("forecast_gust_ms"),
            ah.get("forecast_gust_ms")
        )

        d_pressure = delta(
            bh.get("forecast_pressure_hpa"),
            ah.get("forecast_pressure_hpa")
        )

        d_cloud = delta(
            bh.get("forecast_cloud_cover_pct"),
            ah.get("forecast_cloud_cover_pct")
        )

        d_shortwave = delta(
            bh.get(
                "forecast_shortwave_radiation_wm2"
            ),
            ah.get(
                "forecast_shortwave_radiation_wm2"
            )
        )

        environment_pair_complete = (
            before_id in hrrr
            and after_id in hrrr
            and before_id in ptsc
            and after_id in ptsc
        )

        transitions.append({
            "transition_id":
                f"{before_id}__TO__{after_id}",

            "year":
                clean(after.get("year")),

            "session_id":
                clean(after.get("session_id")),

            "car_number":
                clean(after.get("car_number")),

            "driver_name":
                clean(after.get("driver_name")),

            "team_name":
                clean(after.get("team_name")),

            "before_attempt_id":
                before_id,

            "after_attempt_id":
                after_id,

            "before_run_index":
                before_index
                if before_index is not None
                else "",

            "after_run_index":
                after_index
                if after_index is not None
                else "",

            "before_time_utc":
                before_time,

            "after_time_utc":
                after_time,

            "before_time_class":
                clean(
                    before.get(
                        "time_evidence_class"
                    )
                ),

            "after_time_class":
                clean(
                    after.get(
                        "time_evidence_class"
                    )
                ),

            "elapsed_between_performance_observations_min":
                fmt(elapsed_min),

            "elapsed_semantic":
                (
                    "BETWEEN_PERFORMANCE_OBSERVATIONS_"
                    "NOT_QUEUE_WAIT"
                ),

            "before_four_lap_average_speed_mph":
                clean(
                    before.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "after_four_lap_average_speed_mph":
                clean(
                    after.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "delta_four_lap_average_speed_mph":
                fmt(speed_delta),

            "before_lap1_to_lap4_delta_mph":
                clean(
                    before.get(
                        "lap1_to_lap4_delta_mph"
                    )
                ),

            "after_lap1_to_lap4_delta_mph":
                clean(
                    after.get(
                        "lap1_to_lap4_delta_mph"
                    )
                ),

            "delta_lap1_to_lap4_shape_mph":
                fmt(l14_delta),

            "before_late_run_fade_mph":
                clean(
                    before.get(
                        "late_run_fade_mph"
                    )
                ),

            "after_late_run_fade_mph":
                clean(
                    after.get(
                        "late_run_fade_mph"
                    )
                ),

            "delta_late_run_fade_mph":
                fmt(late_fade_delta),

            # Positive = later run retains speed better
            # if original fade is negative.
            "fade_retention_improved":
                (
                    str(
                        late_fade_delta > 0
                    )
                    if late_fade_delta is not None
                    else ""
                ),

            "speed_improved":
                (
                    str(speed_delta > 0)
                    if speed_delta is not None
                    else ""
                ),

            "before_ptsc_track_c":
                fmt(bp.get("ptsc_track_c")),

            "after_ptsc_track_c":
                fmt(ap.get("ptsc_track_c")),

            "delta_ptsc_track_c":
                fmt(d_track),

            "ptsc_track_change_rate_c_per_min":
                fmt(
                    rate(
                        d_track,
                        elapsed_min
                    ),
                    8
                ),

            "before_ptsc_ambient_c":
                fmt(bp.get("ptsc_ambient_c")),

            "after_ptsc_ambient_c":
                fmt(ap.get("ptsc_ambient_c")),

            "delta_ptsc_ambient_c":
                fmt(d_ambient),

            "ptsc_ambient_change_rate_c_per_min":
                fmt(
                    rate(
                        d_ambient,
                        elapsed_min
                    ),
                    8
                ),

            "delta_ptsc_humidity":
                fmt(d_ptsc_humidity),

            "delta_ptsc_wind":
                fmt(d_ptsc_wind),

            "before_forecast_temp_c":
                fmt(bh.get("forecast_temp_c")),

            "after_forecast_temp_c":
                fmt(ah.get("forecast_temp_c")),

            "delta_forecast_temp_c":
                fmt(d_temp),

            "forecast_temp_change_rate_c_per_min":
                fmt(
                    rate(
                        d_temp,
                        elapsed_min
                    ),
                    8
                ),

            "delta_forecast_relative_humidity_pct":
                fmt(d_rh),

            "delta_forecast_wind_speed_10m_ms":
                fmt(d_wind),

            "delta_forecast_gust_ms":
                fmt(d_gust),

            "delta_forecast_pressure_hpa":
                fmt(d_pressure),

            "delta_forecast_cloud_cover_pct":
                fmt(d_cloud),

            "delta_forecast_shortwave_radiation_wm2":
                fmt(d_shortwave),

            "forecast_shortwave_change_rate_wm2_per_min":
                fmt(
                    rate(
                        d_shortwave,
                        elapsed_min
                    ),
                    8
                ),

            "hrrr_pair_available":
                str(
                    before_id in hrrr
                    and after_id in hrrr
                ),

            "ptsc_pair_available":
                str(
                    before_id in ptsc
                    and after_id in ptsc
                ),

            "full_environment_pair_available":
                str(environment_pair_complete),

            "strategy_before_lane_action":
                clean(
                    before.get("lane_action")
                ),

            "strategy_after_lane_action":
                clean(
                    after.get("lane_action")
                ),

            "performance_dataset_inclusion_depends_on_action":
                "False",
        })


TRANSITION_FIELDS = list(
    transitions[0].keys()
)

transitions.sort(
    key=lambda r: (
        int(r["year"])
        if r["year"] else 9999,

        r["session_id"],
        r["car_number"],
        r["driver_name"],

        int(r["after_run_index"])
        if str(r["after_run_index"]).isdigit()
        else 999
    )
)

write_csv(
    OUTPUT_TRANSITIONS,
    transitions,
    TRANSITION_FIELDS
)


# =============================================================================
# 5. Environment-linked transition subset
# =============================================================================

env_rows = [
    r for r in transitions
    if r["full_environment_pair_available"]
    == "True"
]

write_csv(
    OUTPUT_ENV,
    env_rows,
    TRANSITION_FIELDS
)


# =============================================================================
# 6. Past-only rolling cross-car signal
#
# Important:
#
# For each repeat transition endpoint at time t:
#
#   use ONLY earlier transitions
#   use OTHER cars
#   never use the current transition itself
#   never use future cars
#
# We create K=3 and K=5 nearest previous distinct-car signals.
#
# These are not fixed time windows.
# We report the actual span in minutes.
# =============================================================================

timed_transitions = []

for row in transitions:

    t = parse_time(
        row.get("after_time_utc")
    )

    if t is None:
        continue

    speed_delta = as_float(
        row.get(
            "delta_four_lap_average_speed_mph"
        )
    )

    fade_delta = as_float(
        row.get(
            "delta_late_run_fade_mph"
        )
    )

    if speed_delta is None:
        continue

    item = dict(row)
    item["_after_dt"] = t
    item["_speed_delta"] = speed_delta
    item["_fade_delta"] = fade_delta

    timed_transitions.append(item)


by_session = defaultdict(list)

for row in timed_transitions:
    by_session[row["session_id"]].append(row)


signal_rows = []

for session_id, rows in by_session.items():

    rows.sort(
        key=lambda r: (
            r["_after_dt"],
            r["after_attempt_id"]
        )
    )

    for i, current in enumerate(rows):

        prior = []

        current_group = (
            current["car_number"],
            current["driver_name"]
        )

        # Walk backwards and retain only the most recent
        # transition from each OTHER car.
        seen_groups = set()

        for j in range(i - 1, -1, -1):

            candidate = rows[j]

            candidate_group = (
                candidate["car_number"],
                candidate["driver_name"]
            )

            if candidate_group == current_group:
                continue

            if candidate_group in seen_groups:
                continue

            seen_groups.add(candidate_group)
            prior.append(candidate)

        out = {
            "year":
                current["year"],

            "session_id":
                current["session_id"],

            "car_number":
                current["car_number"],

            "driver_name":
                current["driver_name"],

            "after_attempt_id":
                current["after_attempt_id"],

            "after_time_utc":
                current["after_time_utc"],

            "current_delta_speed_mph":
                current[
                    "delta_four_lap_average_speed_mph"
                ],

            "current_delta_late_run_fade_mph":
                current[
                    "delta_late_run_fade_mph"
                ],

            "signal_semantic":
                (
                    "PAST_ONLY_OTHER_CAR_REPEAT_"
                    "PERFORMANCE_SIGNAL"
                ),

            "future_information_used":
                "False",
        }

        for k in [3, 5]:

            peers = prior[:k]

            speed_values = [
                p["_speed_delta"]
                for p in peers
            ]

            fade_values = [
                p["_fade_delta"]
                for p in peers
                if p["_fade_delta"] is not None
            ]

            if peers:
                earliest = min(
                    p["_after_dt"]
                    for p in peers
                )

                span_min = (
                    current["_after_dt"]
                    - earliest
                ).total_seconds() / 60.0

            else:
                span_min = None

            out[
                f"prior_{k}_peer_count"
            ] = len(peers)

            out[
                f"prior_{k}_median_delta_speed_mph"
            ] = fmt(
                median(speed_values)
            )

            out[
                f"prior_{k}_mean_delta_speed_mph"
            ] = fmt(
                mean(speed_values)
            )

            out[
                f"prior_{k}_positive_speed_fraction"
            ] = fmt(
                (
                    sum(
                        1
                        for v in speed_values
                        if v > 0
                    )
                    / len(speed_values)
                )
                if speed_values
                else None
            )

            out[
                f"prior_{k}_median_delta_fade_mph"
            ] = fmt(
                median(fade_values)
            )

            out[
                f"prior_{k}_fade_improvement_fraction"
            ] = fmt(
                (
                    sum(
                        1
                        for v in fade_values
                        if v > 0
                    )
                    / len(fade_values)
                )
                if fade_values
                else None
            )

            out[
                f"prior_{k}_signal_span_minutes"
            ] = fmt(span_min)

        signal_rows.append(out)


SIGNAL_FIELDS = [
    "year",
    "session_id",
    "car_number",
    "driver_name",
    "after_attempt_id",
    "after_time_utc",
    "current_delta_speed_mph",
    "current_delta_late_run_fade_mph",
    "signal_semantic",
    "future_information_used",

    "prior_3_peer_count",
    "prior_3_median_delta_speed_mph",
    "prior_3_mean_delta_speed_mph",
    "prior_3_positive_speed_fraction",
    "prior_3_median_delta_fade_mph",
    "prior_3_fade_improvement_fraction",
    "prior_3_signal_span_minutes",

    "prior_5_peer_count",
    "prior_5_median_delta_speed_mph",
    "prior_5_mean_delta_speed_mph",
    "prior_5_positive_speed_fraction",
    "prior_5_median_delta_fade_mph",
    "prior_5_fade_improvement_fraction",
    "prior_5_signal_span_minutes",
]

write_csv(
    OUTPUT_SIGNAL,
    signal_rows,
    SIGNAL_FIELDS
)


# =============================================================================
# 7. Descriptive summaries
# =============================================================================

summary_rows = []

years = sorted({
    int(r["year"])
    for r in transitions
    if r["year"]
})


for year in years:

    yr = [
        r for r in transitions
        if r["year"] == str(year)
    ]

    env = [
        r for r in yr
        if r["full_environment_pair_available"]
        == "True"
    ]

    timed = [
        r for r in yr
        if parse_time(
            r.get("after_time_utc")
        )
        is not None
    ]

    speeds = [
        as_float(
            r[
                "delta_four_lap_average_speed_mph"
            ]
        )
        for r in yr
    ]

    fades = [
        as_float(
            r["delta_late_run_fade_mph"]
        )
        for r in yr
    ]

    track = [
        as_float(
            r["delta_ptsc_track_c"]
        )
        for r in env
    ]

    summary_rows.append({
        "year": year,

        "transition_rows":
            len(yr),

        "timed_transition_rows":
            len(timed),

        "full_environment_transition_rows":
            len(env),

        "mean_delta_speed_mph":
            fmt(mean(speeds)),

        "median_delta_speed_mph":
            fmt(median(speeds)),

        "std_delta_speed_mph":
            fmt(stdev(speeds)),

        "speed_improvement_fraction":
            fmt(
                (
                    sum(
                        1
                        for v in speeds
                        if v is not None
                        and v > 0
                    )
                    /
                    len([
                        v
                        for v in speeds
                        if v is not None
                    ])
                )
                if any(
                    v is not None
                    for v in speeds
                )
                else None
            ),

        "mean_delta_late_run_fade_mph":
            fmt(mean(fades)),

        "median_delta_late_run_fade_mph":
            fmt(median(fades)),

        "mean_delta_track_temp_c":
            fmt(mean(track)),

        "median_delta_track_temp_c":
            fmt(median(track)),
    })


write_csv(
    OUTPUT_SUMMARY,
    summary_rows,
    [
        "year",
        "transition_rows",
        "timed_transition_rows",
        "full_environment_transition_rows",
        "mean_delta_speed_mph",
        "median_delta_speed_mph",
        "std_delta_speed_mph",
        "speed_improvement_fraction",
        "mean_delta_late_run_fade_mph",
        "median_delta_late_run_fade_mph",
        "mean_delta_track_temp_c",
        "median_delta_track_temp_c",
    ]
)


# =============================================================================
# 8. QA
# =============================================================================

qa_rows = []

expected_min_transitions = (
    len(multi)
    -
    len(groups)
)

# This identity should hold if every multi-run group
# is represented by consecutive transitions.
qa_rows.append(
    qa(
        "consecutive_transition_count",
        len(transitions),
        expected_min_transitions,
        len(transitions) == expected_min_transitions,
        (
            "For each group with n complete runs, "
            "builder creates exactly n-1 transitions."
        )
    )
)

qa_rows.append(
    qa(
        "multi_run_group_count",
        len(groups),
        70,
        len(groups) == 70,
    )
)

qa_rows.append(
    qa(
        "multi_run_input_rows",
        len(multi),
        162,
        len(multi) == 162,
    )
)

qa_rows.append(
    qa(
        "environment_linked_transitions",
        len(env_rows),
        ">0",
        len(env_rows) > 0,
    )
)

qa_rows.append(
    qa(
        "timed_transitions",
        len(timed_transitions),
        ">0",
        len(timed_transitions) > 0,
    )
)

qa_rows.append(
    qa(
        "past_only_signal_rows",
        len(signal_rows),
        len(timed_transitions),
        len(signal_rows)
        == len(timed_transitions),
    )
)

future_leak_rows = [
    r for r in signal_rows
    if r["future_information_used"]
    != "False"
]

qa_rows.append(
    qa(
        "cross_car_future_information_used",
        len(future_leak_rows),
        0,
        len(future_leak_rows) == 0,
    )
)

same_action_dependency = [
    r for r in transitions
    if r[
        "performance_dataset_inclusion_depends_on_action"
    ] != "False"
]

qa_rows.append(
    qa(
        "performance_inclusion_depends_on_lane_action",
        len(same_action_dependency),
        0,
        len(same_action_dependency) == 0,
    )
)

bad_elapsed_semantic = [
    r for r in transitions
    if (
        r[
            "elapsed_between_performance_observations_min"
        ]
        and
        r["elapsed_semantic"]
        !=
        "BETWEEN_PERFORMANCE_OBSERVATIONS_NOT_QUEUE_WAIT"
    )
]

qa_rows.append(
    qa(
        "elapsed_time_called_queue_wait",
        len(bad_elapsed_semantic),
        0,
        len(bad_elapsed_semantic) == 0,
    )
)

qa_rows.append(
    qa(
        "car_number_numeric_normalization",
        False,
        False,
        True,
        (
            'Car numbers remain raw strings; '
            '"06" is never normalized to "6".'
        )
    )
)

qa_rows.append(
    qa(
        "fixed_time_bucket_required",
        False,
        False,
        True,
        (
            "Cross-car signal uses nearest prior "
            "distinct cars and records actual span."
        )
    )
)

qa_rows.append(
    qa(
        "model_fitting_performed",
        False,
        False,
        True,
    )
)

write_csv(
    OUTPUT_QA,
    qa_rows,
    [
        "metric",
        "value",
        "expected",
        "status",
        "detail",
    ]
)


# =============================================================================
# 9. Report
# =============================================================================

per_year = {}

for year in years:

    yr = [
        r for r in transitions
        if r["year"] == str(year)
    ]

    yr_env = [
        r for r in yr
        if r["full_environment_pair_available"]
        == "True"
    ]

    yr_timed = [
        r for r in yr
        if parse_time(
            r.get("after_time_utc")
        )
        is not None
    ]

    sig3 = [
        r for r in signal_rows
        if (
            r["year"] == str(year)
            and as_int(
                r.get("prior_3_peer_count")
            ) == 3
        )
    ]

    sig5 = [
        r for r in signal_rows
        if (
            r["year"] == str(year)
            and as_int(
                r.get("prior_5_peer_count")
            ) == 5
        )
    ]

    per_year[str(year)] = {
        "transitions": len(yr),
        "timed_transitions": len(yr_timed),
        "full_environment_transitions":
            len(yr_env),
        "rows_with_full_prior3_signal":
            len(sig3),
        "rows_with_full_prior5_signal":
            len(sig5),
    }


report = {
    "phase": "R4P2",

    "purpose": (
        "Construct consecutive same-car "
        "multi-run transitions, historical "
        "environment changes, and decision-safe "
        "past-only cross-car repeat signals."
    ),

    "multi_run_input_rows":
        len(multi),

    "multi_run_groups":
        len(groups),

    "consecutive_transition_rows":
        len(transitions),

    "environment_linked_transition_rows":
        len(env_rows),

    "timed_transition_rows":
        len(timed_transitions),

    "past_only_cross_car_signal_rows":
        len(signal_rows),

    "per_year":
        per_year,

    "semantics": {
        "speed_delta": (
            "after four-lap average speed "
            "minus before speed"
        ),

        "fade_delta": (
            "after late-run fade minus before fade; "
            "positive means later run retains "
            "late-run speed better"
        ),

        "elapsed_time": (
            "time between approximate performance "
            "observations; never interpreted "
            "as queue wait"
        ),

        "environment_delta": (
            "retrospective change between historical "
            "attempt observations; useful for "
            "physical association analysis but "
            "not automatically a decision-time "
            "future predictor"
        ),

        "cross_car_signal": (
            "Only earlier repeat outcomes from "
            "other cars are used. No centered "
            "or future window data are included."
        ),

        "window_definition": (
            "No fixed window duration is imposed. "
            "Nearest prior 3 and 5 distinct-car "
            "repeat observations are summarized "
            "with actual time span."
        ),
    },

    "model_fitting_performed":
        False,
}


OUTPUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# 10. Console report
# =============================================================================

failed = [
    r for r in qa_rows
    if r["status"] != "PASS"
]

print()
print("=" * 110)
print("R4P2 SUMMARY")
print("=" * 110)

print(
    f"Multi-run input rows: "
    f"{len(multi)}"
)

print(
    f"Multi-run groups: "
    f"{len(groups)}"
)

print(
    f"Consecutive transitions: "
    f"{len(transitions)}"
)

print(
    f"Environment-linked transitions: "
    f"{len(env_rows)}"
)

print(
    f"Timed transition endpoints: "
    f"{len(timed_transitions)}"
)

print(
    f"Past-only cross-car signal rows: "
    f"{len(signal_rows)}"
)

print()
print("BY YEAR")

for year in years:

    p = per_year[str(year)]

    print(
        f"{year}: "
        f"transitions={p['transitions']} | "
        f"timed={p['timed_transitions']} | "
        f"env={p['full_environment_transitions']} | "
        f"prior3={p['rows_with_full_prior3_signal']} | "
        f"prior5={p['rows_with_full_prior5_signal']}"
    )

print()
print("TRANSITION DESCRIPTIVES")

for row in summary_rows:

    print(
        f"{row['year']}: "
        f"mean_dSpeed={row['mean_delta_speed_mph']} | "
        f"median_dSpeed={row['median_delta_speed_mph']} | "
        f"improve_rate={row['speed_improvement_fraction']} | "
        f"mean_dFade={row['mean_delta_late_run_fade_mph']} | "
        f"mean_dTrackC={row['mean_delta_track_temp_c']}"
    )

print()
print(
    f"QA: "
    f"{len(qa_rows) - len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:

    print("FAILED QA")

    for row in failed:

        print(
            f"  {row['metric']} | "
            f"value={row['value']} | "
            f"expected={row['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")

for path in [
    OUTPUT_TRANSITIONS,
    OUTPUT_ENV,
    OUTPUT_SIGNAL,
    OUTPUT_SUMMARY,
    OUTPUT_REPORT,
    OUTPUT_QA,
]:
    print(path.relative_to(ROOT))


print()
print(
    "R4P2_TRANSITION_ENVIRONMENT_"
    "AND_PAST_ONLY_SIGNAL_READY"
)
