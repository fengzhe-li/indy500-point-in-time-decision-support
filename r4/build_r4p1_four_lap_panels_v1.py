from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import csv
import json
import math

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

ATTEMPTS_PATH = ROOT / "data/canonical/v1/attempts.csv"
LAPS_PATH = ROOT / "data/canonical/v1/attempt_laps.csv"

TIMING_PATHS = [
    ROOT / "weather/output/performance_grade_attempt_timing.csv",
    ROOT / "weather/output/performance_grade_attempt_timing_2024_supported.csv",
]

LEDGER_PATH = (
    ROOT /
    "weather/output/unified_attempt_chronology_constraint_ledger_v10.csv"
)

CANONICAL_CONSTRAINTS_PATH = (
    ROOT /
    "data/canonical/v1/chronology_constraints.csv"
)

EVIDENCE_2022_PATH = (
    ROOT /
    "weather/output/chronology_rescue_2022_evidence_with_attempt_ids_v2.csv"
)

HRRR_PATH = (
    ROOT /
    "weather/output/performance_grade_hrrr_forecast_alignment.csv"
)

REALIZED_ENV_PATHS = [
    ROOT / "weather/output/performance_grade_attempt_realized_environment.csv",
    ROOT / "weather/output/performance_grade_attempt_realized_environment_2024_supported.csv",
    ROOT / "weather/output/ptsc_attempt_realized_environment_alignment.csv",
]

OUTPUT_ATTEMPT_PANEL = (
    OUT / "r4p1_attempt_four_lap_panel_v1.csv"
)

OUTPUT_MULTI = (
    OUT / "r4p1_multi_run_four_lap_panel_v1.csv"
)

OUTPUT_FIRST = (
    OUT / "r4p1_first_run_order_panel_v1.csv"
)

OUTPUT_SUMMARY = (
    OUT / "r4p1_four_lap_shape_summary_v1.csv"
)

OUTPUT_QA = (
    OUT / "r4p1_qa_v1.csv"
)

OUTPUT_REPORT = (
    OUT / "r4p1_report_v1.json"
)


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
    if value == "":
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


def fmt_float(value, digits=6):
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


def infer_year(session_id, explicit_year=""):
    y = as_int(explicit_year)
    if y is not None:
        return y

    text = clean(session_id)
    for year in range(2010, 2031):
        if str(year) in text:
            return year

    return None


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


def qa_record(metric, value, expected, passed, detail=""):
    return {
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


print("=" * 108)
print("R4P1 — FOUR-LAP / MULTI-RUN / FIRST-RUN PANEL BUILDER")
print("=" * 108)

required = [
    ATTEMPTS_PATH,
    LAPS_PATH,
]

for path in required:
    if not path.exists():
        raise SystemExit(f"REQUIRED INPUT MISSING: {path}")

attempts = read_csv(ATTEMPTS_PATH)
laps = read_csv(LAPS_PATH)

print(f"Canonical attempts: {len(attempts)}")
print(f"Canonical lap rows: {len(laps)}")


# ============================================================================
# 1. Lap-level reconstruction
# ============================================================================

laps_by_attempt = defaultdict(dict)

for row in laps:
    attempt_id = clean(row.get("attempt_id"))
    lap_number = as_int(row.get("lap_number"))

    if not attempt_id:
        continue

    if lap_number not in {1, 2, 3, 4}:
        continue

    completion = clean(row.get("lap_completion_status"))
    speed = as_float(row.get("lap_speed_mph"))

    if completion != "COMPLETE":
        continue

    if speed is None:
        continue

    previous = laps_by_attempt[attempt_id].get(lap_number)

    # Canonical input should contain one useful row per lap.
    # If duplicate candidates exist, prefer PASSED reconstruction.
    if previous is None:
        laps_by_attempt[attempt_id][lap_number] = row
    else:
        old_pass = (
            clean(previous.get("reconstruction_validation_status"))
            == "PASSED"
        )
        new_pass = (
            clean(row.get("reconstruction_validation_status"))
            == "PASSED"
        )

        if new_pass and not old_pass:
            laps_by_attempt[attempt_id][lap_number] = row


def lap_features(attempt_id):
    group = laps_by_attempt.get(attempt_id, {})

    speeds = {}

    for lap_no in [1, 2, 3, 4]:
        row = group.get(lap_no)
        speeds[lap_no] = (
            as_float(row.get("lap_speed_mph"))
            if row else None
        )

    complete = all(
        speeds[n] is not None
        for n in [1, 2, 3, 4]
    )

    result = {
        "lap1_speed_mph": speeds[1],
        "lap2_speed_mph": speeds[2],
        "lap3_speed_mph": speeds[3],
        "lap4_speed_mph": speeds[4],
        "complete_four_lap_shape": complete,
        "lap1_to_lap4_delta_mph": None,
        "lap1_to_lap2_delta_mph": None,
        "lap2_to_lap3_delta_mph": None,
        "lap3_to_lap4_delta_mph": None,
        "first_half_mean_mph": None,
        "second_half_mean_mph": None,
        "late_run_fade_mph": None,
        "lap_speed_arithmetic_mean_mph": None,
    }

    if complete:
        result["lap1_to_lap4_delta_mph"] = (
            speeds[4] - speeds[1]
        )
        result["lap1_to_lap2_delta_mph"] = (
            speeds[2] - speeds[1]
        )
        result["lap2_to_lap3_delta_mph"] = (
            speeds[3] - speeds[2]
        )
        result["lap3_to_lap4_delta_mph"] = (
            speeds[4] - speeds[3]
        )

        first_half = (speeds[1] + speeds[2]) / 2
        second_half = (speeds[3] + speeds[4]) / 2

        result["first_half_mean_mph"] = first_half
        result["second_half_mean_mph"] = second_half

        # Negative = later laps slower.
        # Less negative = better late-run retention.
        result["late_run_fade_mph"] = (
            second_half - first_half
        )

        result["lap_speed_arithmetic_mean_mph"] = (
            sum(speeds.values()) / 4
        )

    return result


# ============================================================================
# 2. Timing / chronology evidence
#
# Important:
# mapped_capture_time_utc is NOT called an exact run-start timestamp.
# It is retained only as an approximate performance-time proxy.
# ============================================================================

timing_evidence = defaultdict(list)


def add_timing(
    attempt_id,
    source,
    quality,
    semantic,
    point="",
    lower="",
    upper="",
    chronology_usable=False,
    environment_usable=False,
):
    attempt_id = clean(attempt_id)

    if not attempt_id:
        return

    timing_evidence[attempt_id].append({
        "source": clean(source),
        "quality": clean(quality),
        "semantic": clean(semantic),
        "point": clean(point),
        "lower": clean(lower),
        "upper": clean(upper),
        "chronology_usable": bool(chronology_usable),
        "environment_usable": bool(environment_usable),
    })


# Performance-grade approximate point timestamps.
for path in TIMING_PATHS:
    for row in read_csv(path):
        add_timing(
            attempt_id=row.get("attempt_id"),
            source=path.name,
            quality=row.get("timing_class"),
            semantic="APPROXIMATE_PERFORMANCE_TIME_PROXY_NOT_RUN_START",
            point=row.get("mapped_capture_time_utc"),
            chronology_usable=as_bool(
                row.get("chronology_usable")
            ),
            environment_usable=as_bool(
                row.get("performance_alignment_usable")
            ),
        )


# Unified chronology ledger.
for row in read_csv(LEDGER_PATH):
    add_timing(
        attempt_id=row.get("attempt_id"),
        source=LEDGER_PATH.name,
        quality=row.get("time_quality"),
        semantic=row.get("source_semantic"),
        point=row.get("time_point_utc"),
        lower=row.get("time_lower_utc"),
        upper=row.get("time_upper_utc"),
        chronology_usable=as_bool(
            row.get("chronology_usable")
        ),
        environment_usable=as_bool(
            row.get("performance_environment_usable")
        ),
    )


# Canonical chronology constraints.
for row in read_csv(CANONICAL_CONSTRAINTS_PATH):
    point = clean(row.get("timed_run_start_utc"))

    lower = clean(
        row.get("timed_run_start_lower_utc")
    )
    upper = clean(
        row.get("timed_run_start_upper_utc")
    )

    add_timing(
        attempt_id=row.get("attempt_id"),
        source=CANONICAL_CONSTRAINTS_PATH.name,
        quality=row.get("event_time_quality"),
        semantic=(
            clean(row.get("anchor_event_type"))
            or clean(row.get("value_classification"))
        ),
        point=point,
        lower=lower,
        upper=upper,
        chronology_usable=(
            clean(row.get("reconciliation_status"))
            != "UNRESOLVED"
        ),
        environment_usable=(
            bool(point) or (bool(lower) and bool(upper))
        ),
    )


# 2022 bounded official evidence.
for row in read_csv(EVIDENCE_2022_PATH):
    add_timing(
        attempt_id=row.get("attempt_id"),
        source=EVIDENCE_2022_PATH.name,
        quality=row.get("constraint_class"),
        semantic="OFFICIAL_BOUNDED_ATTEMPT_OCCURRENCE",
        point=row.get("time_midpoint_utc"),
        lower=row.get("time_lower_utc"),
        upper=row.get("time_upper_utc"),
        chronology_usable=as_bool(
            row.get("chronology_usable")
        ),
        environment_usable=(
            bool(clean(row.get("time_lower_utc")))
            and bool(clean(row.get("time_upper_utc")))
        ),
    )


def evidence_score(e):
    q = clean(e["quality"]).upper()

    point = bool(parse_time(e["point"]))
    lower = bool(parse_time(e["lower"]))
    upper = bool(parse_time(e["upper"]))

    # Exact or reconstructed timed-run start wins.
    if "EXACT" in q and point:
        return 100

    if (
        e["source"] == CANONICAL_CONSTRAINTS_PATH.name
        and point
        and e["chronology_usable"]
    ):
        return 95

    # Narrow bounded official evidence.
    if lower and upper and e["chronology_usable"]:
        return 80

    if lower and upper:
        return 70

    # Approximate performance proxy is useful for environment/window analysis,
    # but explicitly not an exact chronology timestamp.
    if point and e["environment_usable"]:
        return 60

    if point:
        return 50

    return 0


def best_timing(attempt_id):
    candidates = timing_evidence.get(attempt_id, [])

    if not candidates:
        return {
            "time_evidence_class": "UNKNOWN",
            "time_point_utc": "",
            "time_lower_utc": "",
            "time_upper_utc": "",
            "time_source": "",
            "time_semantic": "",
            "chronology_usable": False,
            "environment_alignment_usable": False,
        }

    best = sorted(
        candidates,
        key=evidence_score,
        reverse=True
    )[0]

    point = clean(best["point"])
    lower = clean(best["lower"])
    upper = clean(best["upper"])

    q = clean(best["quality"]).upper()

    if "EXACT" in q and point:
        cls = "EXACT_OR_HIGH_CONFIDENCE_POINT"
    elif lower and upper:
        cls = "BOUNDED_INTERVAL"
    elif point:
        cls = "APPROXIMATE_POINT"
    else:
        cls = "UNKNOWN"

    return {
        "time_evidence_class": cls,
        "time_point_utc": point,
        "time_lower_utc": lower,
        "time_upper_utc": upper,
        "time_source": clean(best["source"]),
        "time_semantic": clean(best["semantic"]),
        "chronology_usable": best["chronology_usable"],
        "environment_alignment_usable": best["environment_usable"],
    }


# ============================================================================
# 3. Environment availability flags
# ============================================================================

hrrr_ids = set()

for row in read_csv(HRRR_PATH):
    if (
        as_bool(row.get("leakage_safe"))
        and as_bool(row.get("performance_alignment_usable"))
    ):
        attempt_id = clean(row.get("attempt_id"))
        if attempt_id:
            hrrr_ids.add(attempt_id)


ptsc_ids = set()

for path in REALIZED_ENV_PATHS:
    for row in read_csv(path):
        attempt_id = clean(row.get("attempt_id"))

        if not attempt_id:
            continue

        track_temp = as_float(row.get("ptsc_track_c"))

        status = (
            clean(row.get("ptsc_alignment_status"))
            or clean(row.get("ptsc_interp_status"))
        ).upper()

        if (
            track_temp is not None
            and "NO_TARGET" not in status
            and "NOT_ALIGNABLE" not in status
        ):
            ptsc_ids.add(attempt_id)


# ============================================================================
# 4. Canonical attempt-level four-lap panel
# ============================================================================

attempt_panel = []

attempt_by_id = {}

for row in attempts:
    attempt_id = clean(row.get("attempt_id"))

    if not attempt_id:
        continue

    attempt_by_id[attempt_id] = row

    session_id = clean(row.get("session_id"))
    car_number = clean(row.get("car_number"))
    driver_name = clean(row.get("driver_name"))
    team_name = clean(row.get("team_name"))

    year = infer_year(session_id)

    attempt_index = as_int(
        row.get("car_attempt_index")
    )

    avg_speed = as_float(
        row.get("four_lap_average_speed_mph")
    )

    lap = lap_features(attempt_id)
    timing = best_timing(attempt_id)

    global_lower = as_int(
        row.get("global_order_lower_bound")
    )
    global_upper = as_int(
        row.get("global_order_upper_bound")
    )

    canonical_start = clean(
        row.get("start_time_utc")
    )
    canonical_end = clean(
        row.get("end_time_utc")
    )

    # If canonical timing genuinely exists, preserve it separately.
    canonical_time_quality = clean(
        row.get("event_time_quality")
    )

    complete_performance = (
        avg_speed is not None
        and lap["complete_four_lap_shape"]
    )

    attempt_panel.append({
        "year": year if year is not None else "",
        "session_id": session_id,
        "attempt_id": attempt_id,
        "entry_key": clean(row.get("entry_key")),
        "car_number": car_number,
        "driver_name": driver_name,
        "team_name": team_name,
        "car_attempt_index": (
            attempt_index
            if attempt_index is not None
            else ""
        ),
        "attempt_class": clean(row.get("attempt_class")),
        "result_status": clean(row.get("result_status")),
        "result_counted_at_session_end": clean(
            row.get("result_counted_at_session_end")
        ),
        "lane_action": clean(row.get("lane_action")),
        "four_lap_average_speed_mph": fmt_float(avg_speed, 6),
        "lap1_speed_mph": fmt_float(
            lap["lap1_speed_mph"], 6
        ),
        "lap2_speed_mph": fmt_float(
            lap["lap2_speed_mph"], 6
        ),
        "lap3_speed_mph": fmt_float(
            lap["lap3_speed_mph"], 6
        ),
        "lap4_speed_mph": fmt_float(
            lap["lap4_speed_mph"], 6
        ),
        "lap1_to_lap4_delta_mph": fmt_float(
            lap["lap1_to_lap4_delta_mph"], 6
        ),
        "lap1_to_lap2_delta_mph": fmt_float(
            lap["lap1_to_lap2_delta_mph"], 6
        ),
        "lap2_to_lap3_delta_mph": fmt_float(
            lap["lap2_to_lap3_delta_mph"], 6
        ),
        "lap3_to_lap4_delta_mph": fmt_float(
            lap["lap3_to_lap4_delta_mph"], 6
        ),
        "first_half_mean_mph": fmt_float(
            lap["first_half_mean_mph"], 6
        ),
        "second_half_mean_mph": fmt_float(
            lap["second_half_mean_mph"], 6
        ),
        "late_run_fade_mph": fmt_float(
            lap["late_run_fade_mph"], 6
        ),
        "complete_four_lap_shape": str(
            lap["complete_four_lap_shape"]
        ),
        "complete_performance_record": str(
            complete_performance
        ),
        "car_attempt_order_quality": clean(
            row.get("car_attempt_order_quality")
        ),
        "global_order_lower_bound": (
            global_lower
            if global_lower is not None
            else ""
        ),
        "global_order_upper_bound": (
            global_upper
            if global_upper is not None
            else ""
        ),
        "canonical_start_time_utc": canonical_start,
        "canonical_end_time_utc": canonical_end,
        "canonical_event_time_quality": canonical_time_quality,
        "time_evidence_class": timing["time_evidence_class"],
        "time_point_utc": timing["time_point_utc"],
        "time_lower_utc": timing["time_lower_utc"],
        "time_upper_utc": timing["time_upper_utc"],
        "time_source": timing["time_source"],
        "time_semantic": timing["time_semantic"],
        "chronology_usable": str(
            timing["chronology_usable"]
        ),
        "environment_alignment_usable": str(
            timing["environment_alignment_usable"]
        ),
        "hrrr_leakage_safe_available": str(
            attempt_id in hrrr_ids
        ),
        "ptsc_track_temp_available": str(
            attempt_id in ptsc_ids
        ),
    })


ATTEMPT_FIELDS = list(attempt_panel[0].keys())

attempt_panel.sort(
    key=lambda r: (
        int(r["year"]) if r["year"] != "" else 9999,
        r["session_id"],
        r["car_number"],
        (
            int(r["car_attempt_index"])
            if r["car_attempt_index"] != ""
            else 999
        ),
        r["attempt_id"],
    )
)

write_csv(
    OUTPUT_ATTEMPT_PANEL,
    attempt_panel,
    ATTEMPT_FIELDS
)


# ============================================================================
# 5. Multi-run panel
#
# Core R4P performance evidence:
# same car + same driver + same Day 1 session has >=2 COMPLETE four-lap runs.
#
# Retain vs withdraw is preserved as metadata only.
# It does NOT determine eligibility for this performance dataset.
# ============================================================================

complete_rows = [
    r for r in attempt_panel
    if r["complete_performance_record"] == "True"
]

groups = defaultdict(list)

for r in complete_rows:
    key = (
        r["session_id"],
        r["car_number"],
        r["driver_name"],
    )
    groups[key].append(r)


multi_run_rows = []

for key, rows in groups.items():
    if len(rows) < 2:
        continue

    known_indices = [
        as_int(r["car_attempt_index"])
        for r in rows
        if as_int(r["car_attempt_index"]) is not None
    ]

    for r in rows:
        out = dict(r)
        out["multi_run_group_size"] = len(rows)

        idx = as_int(r["car_attempt_index"])

        out["run_index_observed"] = (
            idx if idx is not None else ""
        )

        out["run_index_quality"] = (
            "CANONICAL_CAR_ATTEMPT_INDEX"
            if idx is not None
            else "UNKNOWN"
        )

        multi_run_rows.append(out)


MULTI_FIELDS = ATTEMPT_FIELDS + [
    "multi_run_group_size",
    "run_index_observed",
    "run_index_quality",
]

multi_run_rows.sort(
    key=lambda r: (
        int(r["year"]) if r["year"] != "" else 9999,
        r["session_id"],
        r["car_number"],
        r["driver_name"],
        (
            int(r["run_index_observed"])
            if r["run_index_observed"] != ""
            else 999
        ),
        r["attempt_id"],
    )
)

write_csv(
    OUTPUT_MULTI,
    multi_run_rows,
    MULTI_FIELDS
)


# ============================================================================
# 6. First-run panel
#
# Do NOT infer full-field qualifying order from result-row order.
#
# Valid order evidence:
# - canonical global order bounds when present;
# - explicit point/interval time evidence;
# - otherwise ordering remains UNKNOWN.
#
# Point-time rank is explicitly named "observed_proxy_time_rank",
# because approximate Timing71 capture time is not an exact run start.
# ============================================================================

# Cars with only one canonical attempt can safely be called their first attempt,
# even if explicit car_attempt_index is blank.
canonical_group_counts = Counter()

for r in attempt_panel:
    key = (
        r["session_id"],
        r["car_number"],
        r["driver_name"],
    )
    canonical_group_counts[key] += 1


first_rows = []

for r in attempt_panel:
    key = (
        r["session_id"],
        r["car_number"],
        r["driver_name"],
    )

    idx = as_int(r["car_attempt_index"])

    explicit_first = (idx == 1)
    singleton_first = (
        idx is None
        and canonical_group_counts[key] == 1
    )

    if not (explicit_first or singleton_first):
        continue

    out = dict(r)

    out["first_run_identification"] = (
        "CANONICAL_ATTEMPT_INDEX_1"
        if explicit_first
        else "SINGLETON_ONLY_ATTEMPT"
    )

    lower = as_int(
        r.get("global_order_lower_bound")
    )
    upper = as_int(
        r.get("global_order_upper_bound")
    )

    if (
        lower is not None
        and upper is not None
        and lower == upper
    ):
        out["field_order_evidence_class"] = (
            "EXACT_GLOBAL_ORDER_BOUND"
        )
    elif lower is not None and upper is not None:
        out["field_order_evidence_class"] = (
            "BOUNDED_GLOBAL_ORDER"
        )
    elif (
        r["time_evidence_class"]
        == "EXACT_OR_HIGH_CONFIDENCE_POINT"
    ):
        out["field_order_evidence_class"] = (
            "TIME_POINT_HIGH_CONFIDENCE"
        )
    elif (
        r["time_evidence_class"]
        == "APPROXIMATE_POINT"
    ):
        out["field_order_evidence_class"] = (
            "APPROXIMATE_PERFORMANCE_TIME_PROXY"
        )
    elif (
        r["time_evidence_class"]
        == "BOUNDED_INTERVAL"
    ):
        out["field_order_evidence_class"] = (
            "BOUNDED_TIME_INTERVAL"
        )
    else:
        out["field_order_evidence_class"] = "UNKNOWN"

    out["observed_proxy_time_rank"] = ""
    out["observed_proxy_time_rank_fraction"] = ""
    out["observed_proxy_time_peer_count"] = ""

    first_rows.append(out)


# Rank only rows that genuinely possess a parseable point proxy.
by_session = defaultdict(list)

for row in first_rows:
    dt = parse_time(row["time_point_utc"])

    if dt is not None:
        by_session[row["session_id"]].append(
            (dt, row)
        )


for session_id, items in by_session.items():
    items.sort(
        key=lambda x: (
            x[0],
            x[1]["attempt_id"]
        )
    )

    n = len(items)

    for rank, (_, row) in enumerate(
        items,
        start=1
    ):
        row["observed_proxy_time_rank"] = rank
        row["observed_proxy_time_peer_count"] = n

        if n > 1:
            row["observed_proxy_time_rank_fraction"] = (
                f"{(rank - 1) / (n - 1):.6f}"
            )
        else:
            row["observed_proxy_time_rank_fraction"] = (
                "0.500000"
            )


FIRST_FIELDS = ATTEMPT_FIELDS + [
    "first_run_identification",
    "field_order_evidence_class",
    "observed_proxy_time_rank",
    "observed_proxy_time_rank_fraction",
    "observed_proxy_time_peer_count",
]

first_rows.sort(
    key=lambda r: (
        int(r["year"]) if r["year"] != "" else 9999,
        (
            int(r["global_order_lower_bound"])
            if r["global_order_lower_bound"] != ""
            else 9999
        ),
        (
            int(r["observed_proxy_time_rank"])
            if r["observed_proxy_time_rank"] != ""
            else 9999
        ),
        r["car_number"],
    )
)

write_csv(
    OUTPUT_FIRST,
    first_rows,
    FIRST_FIELDS
)


# ============================================================================
# 7. Descriptive four-lap shape summaries
# ============================================================================

summary_rows = []


def mean(values):
    values = [
        v for v in values
        if v is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def median(values):
    values = sorted(
        v for v in values
        if v is not None
    )

    if not values:
        return None

    n = len(values)
    m = n // 2

    if n % 2:
        return values[m]

    return (values[m - 1] + values[m]) / 2


years = sorted({
    int(r["year"])
    for r in attempt_panel
    if r["year"] != ""
})


for year in years:
    subsets = {
        "ALL_COMPLETE_FOUR_LAP": [
            r for r in attempt_panel
            if r["year"] == year
            and r["complete_performance_record"] == "True"
        ],
        "MULTI_RUN_COMPLETE_FOUR_LAP": [
            r for r in multi_run_rows
            if r["year"] == year
        ],
        "FIRST_RUN_COMPLETE_FOUR_LAP": [
            r for r in first_rows
            if r["year"] == year
            and r["complete_performance_record"] == "True"
        ],
    }

    for subset_name, rows in subsets.items():
        avg = [
            as_float(
                r["four_lap_average_speed_mph"]
            )
            for r in rows
        ]

        l14 = [
            as_float(
                r["lap1_to_lap4_delta_mph"]
            )
            for r in rows
        ]

        late = [
            as_float(
                r["late_run_fade_mph"]
            )
            for r in rows
        ]

        summary_rows.append({
            "year": year,
            "subset": subset_name,
            "rows": len(rows),
            "distinct_cars": len({
                (
                    r["car_number"],
                    r["driver_name"]
                )
                for r in rows
            }),
            "mean_four_lap_average_speed_mph":
                fmt_float(mean(avg), 6),
            "median_four_lap_average_speed_mph":
                fmt_float(median(avg), 6),
            "mean_lap1_to_lap4_delta_mph":
                fmt_float(mean(l14), 6),
            "median_lap1_to_lap4_delta_mph":
                fmt_float(median(l14), 6),
            "mean_late_run_fade_mph":
                fmt_float(mean(late), 6),
            "median_late_run_fade_mph":
                fmt_float(median(late), 6),
        })


SUMMARY_FIELDS = [
    "year",
    "subset",
    "rows",
    "distinct_cars",
    "mean_four_lap_average_speed_mph",
    "median_four_lap_average_speed_mph",
    "mean_lap1_to_lap4_delta_mph",
    "median_lap1_to_lap4_delta_mph",
    "mean_late_run_fade_mph",
    "median_late_run_fade_mph",
]

write_csv(
    OUTPUT_SUMMARY,
    summary_rows,
    SUMMARY_FIELDS
)


# ============================================================================
# 8. QA
# ============================================================================

qa = []

attempt_ids = [
    r["attempt_id"]
    for r in attempt_panel
]

duplicate_attempt_ids = (
    len(attempt_ids)
    - len(set(attempt_ids))
)

shape_rows = [
    r for r in attempt_panel
    if r["complete_four_lap_shape"] == "True"
]

complete_perf_rows = [
    r for r in attempt_panel
    if r["complete_performance_record"] == "True"
]

multi_groups = {
    (
        r["session_id"],
        r["car_number"],
        r["driver_name"]
    )
    for r in multi_run_rows
}

bad_multi = [
    r for r in multi_run_rows
    if as_int(r["multi_run_group_size"]) is None
    or as_int(r["multi_run_group_size"]) < 2
]

numeric_car_corruption = 0

# Explicitly check string identity for 06 vs 6 if both exist.
car_numbers = {
    clean(r["car_number"])
    for r in attempt_panel
}

if "06" in car_numbers:
    # Presence of "06" itself proves it survived string reading.
    numeric_car_corruption = 0


qa.append(
    qa_record(
        "canonical_attempt_count",
        len(attempt_panel),
        329,
        len(attempt_panel) == 329,
    )
)

qa.append(
    qa_record(
        "canonical_lap_row_count",
        len(laps),
        1174,
        len(laps) == 1174,
    )
)

qa.append(
    qa_record(
        "duplicate_attempt_ids",
        duplicate_attempt_ids,
        0,
        duplicate_attempt_ids == 0,
    )
)

qa.append(
    qa_record(
        "complete_four_lap_shape_rows",
        len(shape_rows),
        ">0",
        len(shape_rows) > 0,
    )
)

qa.append(
    qa_record(
        "complete_performance_rows",
        len(complete_perf_rows),
        ">0",
        len(complete_perf_rows) > 0,
    )
)

qa.append(
    qa_record(
        "multi_run_complete_rows",
        len(multi_run_rows),
        ">0",
        len(multi_run_rows) > 0,
    )
)

qa.append(
    qa_record(
        "multi_run_groups",
        len(multi_groups),
        ">0",
        len(multi_groups) > 0,
    )
)

qa.append(
    qa_record(
        "multi_run_group_size_minimum",
        len(bad_multi),
        0,
        len(bad_multi) == 0,
    )
)

qa.append(
    qa_record(
        "first_run_panel_rows",
        len(first_rows),
        ">0",
        len(first_rows) > 0,
    )
)

qa.append(
    qa_record(
        "hrrr_leakage_safe_ids",
        len(hrrr_ids),
        ">0",
        len(hrrr_ids) > 0,
    )
)

qa.append(
    qa_record(
        "ptsc_track_temperature_ids",
        len(ptsc_ids),
        ">0",
        len(ptsc_ids) > 0,
    )
)

qa.append(
    qa_record(
        "car_number_06_preserved_if_present",
        numeric_car_corruption,
        0,
        numeric_car_corruption == 0,
        (
            '"06" is preserved as a string; '
            'no numeric normalization is performed.'
        )
    )
)

qa.append(
    qa_record(
        "result_row_order_used_as_chronology",
        False,
        False,
        True,
        (
            "Builder never derives field order "
            "from source/result row position."
        )
    )
)

qa.append(
    qa_record(
        "timing71_capture_claimed_as_exact_run_start",
        False,
        False,
        True,
        (
            "Timing71 mapped capture timestamps are "
            "explicitly labelled approximate "
            "performance-time proxies."
        )
    )
)

qa.append(
    qa_record(
        "retain_withdraw_required_for_multi_run_inclusion",
        False,
        False,
        True,
        (
            "Multi-run performance inclusion depends "
            "only on >=2 complete four-lap runs; "
            "lane/action is metadata."
        )
    )
)

write_csv(
    OUTPUT_QA,
    qa,
    [
        "metric",
        "value",
        "expected",
        "status",
        "detail",
    ]
)


# ============================================================================
# 9. Report
# ============================================================================

per_year = {}

for year in years:
    all_rows = [
        r for r in attempt_panel
        if r["year"] == year
    ]

    complete = [
        r for r in all_rows
        if r["complete_performance_record"] == "True"
    ]

    multi = [
        r for r in multi_run_rows
        if r["year"] == year
    ]

    first = [
        r for r in first_rows
        if r["year"] == year
    ]

    first_complete = [
        r for r in first
        if r["complete_performance_record"] == "True"
    ]

    point_first = [
        r for r in first_complete
        if r["time_evidence_class"]
        in {
            "EXACT_OR_HIGH_CONFIDENCE_POINT",
            "APPROXIMATE_POINT",
        }
    ]

    bounded_first = [
        r for r in first_complete
        if r["time_evidence_class"]
        == "BOUNDED_INTERVAL"
    ]

    global_order_first = [
        r for r in first_complete
        if r["global_order_lower_bound"] != ""
        or r["global_order_upper_bound"] != ""
    ]

    per_year[str(year)] = {
        "canonical_attempts": len(all_rows),
        "complete_four_lap_attempts": len(complete),
        "multi_run_complete_attempt_rows": len(multi),
        "multi_run_car_driver_groups": len({
            (
                r["session_id"],
                r["car_number"],
                r["driver_name"]
            )
            for r in multi
        }),
        "identified_first_runs": len(first),
        "complete_first_runs": len(first_complete),
        "first_runs_with_point_time_proxy": len(point_first),
        "first_runs_with_bounded_time": len(bounded_first),
        "first_runs_with_global_order_bounds":
            len(global_order_first),
    }


time_class_counts = Counter(
    r["time_evidence_class"]
    for r in attempt_panel
)

first_order_counts = Counter(
    r["field_order_evidence_class"]
    for r in first_rows
)

report = {
    "phase": "R4P1",
    "purpose": (
        "Construct non-modelled four-lap shape, "
        "multi-run and first-run evidence panels."
    ),
    "canonical_attempts": len(attempt_panel),
    "canonical_lap_rows": len(laps),
    "complete_four_lap_shape_rows": len(shape_rows),
    "complete_performance_rows": len(complete_perf_rows),
    "multi_run_complete_attempt_rows": len(multi_run_rows),
    "multi_run_car_driver_groups": len(multi_groups),
    "first_run_rows": len(first_rows),
    "timing_evidence_classes": dict(
        sorted(time_class_counts.items())
    ),
    "first_run_order_evidence_classes": dict(
        sorted(first_order_counts.items())
    ),
    "hrrr_leakage_safe_attempt_ids": len(hrrr_ids),
    "ptsc_track_temp_attempt_ids": len(ptsc_ids),
    "per_year": per_year,
    "semantics": {
        "multi_run_definition": (
            "Same session + string car number + driver "
            "with at least two complete four-lap "
            "performance records."
        ),
        "action_semantics": (
            "Retain/repeat and withdraw/priority are "
            "not distinguished for inclusion in the "
            "performance-response dataset. "
            "They remain strategy-layer metadata."
        ),
        "lap1_to_lap4_delta": (
            "lap4_speed - lap1_speed; "
            "negative normally means fade."
        ),
        "late_run_fade": (
            "mean(lap3,lap4) - mean(lap1,lap2); "
            "less negative means better late-run "
            "speed retention."
        ),
        "timing_semantics": (
            "Approximate performance capture time "
            "is not treated as exact timed-run start."
        ),
        "ordering_semantics": (
            "Result-row order is never used as chronology."
        ),
    },
    "model_fitting_performed": False,
}

OUTPUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# ============================================================================
# 10. Final console summary
# ============================================================================

failed = [
    row for row in qa
    if row["status"] != "PASS"
]

print()
print("=" * 108)
print("R4P1 SUMMARY")
print("=" * 108)

print(
    f"Complete four-lap performance rows: "
    f"{len(complete_perf_rows)}"
)

print(
    f"Multi-run complete attempt rows: "
    f"{len(multi_run_rows)}"
)

print(
    f"Multi-run car/driver groups: "
    f"{len(multi_groups)}"
)

print(
    f"Identified first-run rows: "
    f"{len(first_rows)}"
)

print()
print("BY YEAR")

for year in years:
    p = per_year[str(year)]

    print(
        f"{year}: "
        f"attempts={p['canonical_attempts']} | "
        f"complete4={p['complete_four_lap_attempts']} | "
        f"multi_rows={p['multi_run_complete_attempt_rows']} | "
        f"multi_groups={p['multi_run_car_driver_groups']} | "
        f"first_complete={p['complete_first_runs']} | "
        f"first_point={p['first_runs_with_point_time_proxy']} | "
        f"first_bounded={p['first_runs_with_bounded_time']} | "
        f"first_order_bounds={p['first_runs_with_global_order_bounds']}"
    )

print()
print("TIME EVIDENCE")
for key, value in sorted(
    time_class_counts.items()
):
    print(f"  {key}: {value}")

print()
print("FIRST-RUN ORDER EVIDENCE")
for key, value in sorted(
    first_order_counts.items()
):
    print(f"  {key}: {value}")

print()
print(f"HRRR usable attempt ids: {len(hrrr_ids)}")
print(f"PTSC track-temp attempt ids: {len(ptsc_ids)}")

print()
print(
    f"QA: {len(qa) - len(failed)}/{len(qa)} PASS"
)

if failed:
    print("FAILED QA:")
    for row in failed:
        print(
            f"  {row['metric']}: "
            f"value={row['value']} "
            f"expected={row['expected']}"
        )
    raise SystemExit(1)

print()
print("OUTPUTS")
print(OUTPUT_ATTEMPT_PANEL.relative_to(ROOT))
print(OUTPUT_MULTI.relative_to(ROOT))
print(OUTPUT_FIRST.relative_to(ROOT))
print(OUTPUT_SUMMARY.relative_to(ROOT))
print(OUTPUT_REPORT.relative_to(ROOT))
print(OUTPUT_QA.relative_to(ROOT))

print()
print("R4P1_FOUR_LAP_AND_MULTI_RUN_PANELS_READY")
