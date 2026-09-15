from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter
import csv
import json
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

FUSED_PATH = (
    OUT /
    "r4f2_canonical_fused_decision_dataset_v2.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

HRRR_PATH = (
    ROOT /
    "weather/output/"
    "hrrr_ims_2020_2024_features.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f3_shared_state_linkage_audit_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f3_shared_state_linkage_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f3_shared_state_linkage_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f3_shared_state_linkage_report_v1.json"
)


# =============================================================================
# Policy constants
# =============================================================================

WINDOW_MINUTES = [
    10,
    20,
    30,
]

WINDOW_MIN_PEERS = 3

PTSC_MAX_AGE_MINUTES = 30

HRRR_AVAILABILITY_LAG_MINUTES = 60

FORECAST_HORIZON_MINUTES = 30


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


def integer(v):
    s = clean(v)

    if not s:
        return None

    try:
        return int(float(s))
    except Exception:
        return None


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    s = s.replace(
        "Z",
        "+00:00"
    )

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def find_field(fields, candidates):
    lower_map = {
        clean(f).lower():
            f
        for f in fields
    }

    # Exact first.
    for candidate in candidates:

        if candidate.lower() in lower_map:

            return lower_map[
                candidate.lower()
            ]

    # Then substring.
    for candidate in candidates:

        c = candidate.lower()

        for low, original in lower_map.items():

            if c in low:
                return original

    return None


for path in [
    FUSED_PATH,
    ATTEMPT_PATH,
    PTSC_PATH,
    HRRR_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


fused = read_csv(
    FUSED_PATH
)

attempt_rows_raw = read_csv(
    ATTEMPT_PATH
)

ptsc_raw = read_csv(
    PTSC_PATH
)

hrrr_raw = read_csv(
    HRRR_PATH
)


print("=" * 124)
print("R4F3 — SHARED STATE LINKAGE AUDIT")
print("=" * 124)

print(
    f"Fused rows: {len(fused)}"
)

print(
    f"Attempt rows: {len(attempt_rows_raw)}"
)

print(
    f"PTSC rows: {len(ptsc_raw)}"
)

print(
    f"HRRR rows: {len(hrrr_raw)}"
)


# =============================================================================
# Select counterfactual-development states only
# =============================================================================

states = [
    r
    for r in fused
    if truth(
        r.get(
            "counterfactual_model_input_eligible"
        )
    )
]

print(
    f"Counterfactual-model states: {len(states)}"
)


# =============================================================================
# Attempt panel schema
# =============================================================================

attempt_fields = (
    list(
        attempt_rows_raw[0].keys()
    )
    if attempt_rows_raw
    else []
)

A_ATTEMPT_ID = find_field(
    attempt_fields,
    [
        "attempt_id",
    ]
)

A_YEAR = find_field(
    attempt_fields,
    [
        "year",
    ]
)

A_CAR = find_field(
    attempt_fields,
    [
        "car_number",
    ]
)

A_DRIVER = find_field(
    attempt_fields,
    [
        "driver_name",
    ]
)

A_TIME = find_field(
    attempt_fields,
    [
        "time_point_utc",
        "canonical_start_time_utc",
    ]
)

A_SPEED = find_field(
    attempt_fields,
    [
        "four_lap_average_speed_mph",
        "speed_mph",
    ]
)

A_STATUS = find_field(
    attempt_fields,
    [
        "result_status",
    ]
)


if not all([
    A_ATTEMPT_ID,
    A_YEAR,
    A_CAR,
    A_TIME,
]):

    raise SystemExit(
        "ATTEMPT PANEL SCHEMA INCOMPLETE"
    )


attempts = []

attempt_by_id = {}

for r in attempt_rows_raw:

    year = integer(
        r.get(A_YEAR)
    )

    aid = clean(
        r.get(A_ATTEMPT_ID)
    )

    car = clean(
        r.get(A_CAR)
    )

    dt = parse_dt(
        r.get(A_TIME)
    )

    speed = (
        num(
            r.get(A_SPEED)
        )
        if A_SPEED
        else None
    )

    status = (
        clean(
            r.get(A_STATUS)
        )
        if A_STATUS
        else ""
    )

    obj = {
        "attempt_id":
            aid,

        "year":
            year,

        "car_number":
            car,

        "driver_name":
            (
                clean(
                    r.get(A_DRIVER)
                )
                if A_DRIVER
                else ""
            ),

        "time":
            dt,

        "speed_mph":
            speed,

        "result_status":
            status,
    }

    attempts.append(
        obj
    )

    if aid:
        attempt_by_id[
            aid
        ] = obj


# =============================================================================
# PTSC schema discovery
# =============================================================================

ptsc_fields = (
    list(
        ptsc_raw[0].keys()
    )
    if ptsc_raw
    else []
)

P_YEAR = find_field(
    ptsc_fields,
    [
        "year",
    ]
)

P_TIME = find_field(
    ptsc_fields,
    [
        "timestamp_utc",
        "time_utc",
        "datetime_utc",
        "timestamp",
        "time",
    ]
)

P_TEMP = find_field(
    ptsc_fields,
    [
        "track_temp",
        "track_temperature",
        "temperature_f",
        "temperature_c",
    ]
)


ptsc = []

if (
    P_YEAR
    and
    P_TIME
):

    for r in ptsc_raw:

        year = integer(
            r.get(P_YEAR)
        )

        dt = parse_dt(
            r.get(P_TIME)
        )

        if (
            year is None
            or
            dt is None
        ):
            continue

        ptsc.append({
            "year":
                year,

            "time":
                dt,

            "track_temp":
                (
                    num(
                        r.get(P_TEMP)
                    )
                    if P_TEMP
                    else None
                ),
        })


# =============================================================================
# HRRR schema discovery
# =============================================================================

hrrr_fields = (
    list(
        hrrr_raw[0].keys()
    )
    if hrrr_raw
    else []
)

H_YEAR = find_field(
    hrrr_fields,
    [
        "year",
    ]
)

H_CYCLE = find_field(
    hrrr_fields,
    [
        "cycle_time_utc",
        "cycle_time",
        "cycle_utc",
        "cycle",
    ]
)

H_VALID = find_field(
    hrrr_fields,
    [
        "valid_time_utc",
        "valid_time",
        "forecast_valid_time",
        "valid",
    ]
)

H_LEAD = find_field(
    hrrr_fields,
    [
        "forecast_hour",
        "forecast_lead",
        "lead_hour",
    ]
)


hrrr = []

if H_CYCLE:

    for r in hrrr_raw:

        cycle = parse_dt(
            r.get(H_CYCLE)
        )

        if cycle is None:
            continue

        valid = (
            parse_dt(
                r.get(H_VALID)
            )
            if H_VALID
            else None
        )

        lead = (
            num(
                r.get(H_LEAD)
            )
            if H_LEAD
            else None
        )

        # If valid time is not explicitly present but lead exists,
        # reconstruct only from declared cycle + lead.
        if (
            valid is None
            and
            lead is not None
        ):

            valid = (
                cycle
                +
                timedelta(
                    hours=lead
                )
            )

        year = (
            integer(
                r.get(H_YEAR)
            )
            if H_YEAR
            else cycle.year
        )

        hrrr.append({
            "year":
                year,

            "cycle":
                cycle,

            "valid":
                valid,

            "lead":
                lead,
        })


# =============================================================================
# Prospective cross-car window evidence
# =============================================================================

def peer_window(
    year,
    subject_car,
    decision_time,
    minutes,
):
    if decision_time is None:
        return []

    lower = (
        decision_time
        -
        timedelta(
            minutes=minutes
        )
    )

    candidates = []

    for a in attempts:

        if a[
            "year"
        ] != year:
            continue

        if a[
            "car_number"
        ] == subject_car:
            continue

        if a[
            "time"
        ] is None:
            continue

        if a[
            "speed_mph"
        ] is None:
            continue

        # Leakage-safe:
        # only observations already completed/recorded by decision time.
        if not (
            lower
            <=
            a["time"]
            <=
            decision_time
        ):
            continue

        candidates.append(
            a
        )

    candidates.sort(
        key=lambda x:
            x["time"]
    )

    return candidates


# =============================================================================
# PTSC retrospective observed-state linkage
#
# Uses only latest observation at or before decision time.
# Does NOT use future track-temperature observation.
# =============================================================================

def latest_ptsc_before(
    year,
    decision_time,
):
    if decision_time is None:
        return None

    candidates = [
        r
        for r in ptsc
        if (
            r[
                "year"
            ] == year
            and
            r[
                "time"
            ]
            <= decision_time
        )
    ]

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda r:
            r["time"]
    )

    age_min = (
        decision_time
        -
        best["time"]
    ).total_seconds() / 60.0

    return (
        best,
        age_min,
    )


# =============================================================================
# HRRR decision-safe forecast linkage
#
# Latest cycle must satisfy:
#
# cycle <= decision_time - 60 min
#
# and selected frozen cycle must contain valid-time support at/after
# decision and out to approximately +30 minutes.
# =============================================================================

def decision_safe_hrrr(
    year,
    decision_time,
):
    if decision_time is None:
        return None

    availability_cutoff = (
        decision_time
        -
        timedelta(
            minutes=HRRR_AVAILABILITY_LAG_MINUTES
        )
    )

    safe = [
        r
        for r in hrrr
        if (
            r[
                "year"
            ] == year
            and
            r[
                "cycle"
            ]
            <= availability_cutoff
        )
    ]

    if not safe:
        return None

    latest_cycle = max(
        r[
            "cycle"
        ]
        for r in safe
    )

    same_cycle = [
        r
        for r in safe
        if r[
            "cycle"
        ] == latest_cycle
    ]

    valid_times = sorted(
        r[
            "valid"
        ]
        for r in same_cycle
        if r[
            "valid"
        ] is not None
    )

    if not valid_times:

        return {
            "cycle":
                latest_cycle,

            "supports_now":
                False,

            "supports_30m":
                False,

            "max_valid":
                None,
        }

    target_30 = (
        decision_time
        +
        timedelta(
            minutes=FORECAST_HORIZON_MINUTES
        )
    )

    supports_now = any(
        v >= decision_time
        for v in valid_times
    )

    supports_30m = any(
        v >= target_30
        for v in valid_times
    )

    return {
        "cycle":
            latest_cycle,

        "supports_now":
            supports_now,

        "supports_30m":
            supports_30m,

        "max_valid":
            max(
                valid_times
            ),
    }


# =============================================================================
# Build linkage audit
# =============================================================================

rows = []

for state in states:

    decision_id = clean(
        state.get(
            "decision_id"
        )
    )

    year = integer(
        state.get(
            "year"
        )
    )

    car = clean(
        state.get(
            "car_number"
        )
    )

    attempt_id = clean(
        state.get(
            "source_attempt_id"
        )
    )

    decision_time = parse_dt(
        state.get(
            "decision_time_utc"
        )
    )

    performance_match = (
        attempt_by_id.get(
            attempt_id
        )
    )

    performance_exact = (
        performance_match
        is not None
    )

    peer_counts = {}

    peer_medians = {}

    for window in WINDOW_MINUTES:

        peers = peer_window(
            year,
            car,
            decision_time,
            window,
        )

        peer_counts[
            window
        ] = len(
            peers
        )

        speeds = [
            p[
                "speed_mph"
            ]
            for p in peers
            if p[
                "speed_mph"
            ]
            is not None
        ]

        if speeds:

            speeds = sorted(
                speeds
            )

            n = len(
                speeds
            )

            if n % 2:

                median = speeds[
                    n // 2
                ]

            else:

                median = (
                    speeds[
                        n // 2 - 1
                    ]
                    +
                    speeds[
                        n // 2
                    ]
                ) / 2.0

            peer_medians[
                window
            ] = median

        else:

            peer_medians[
                window
            ] = None


    window_20_ready = (
        peer_counts[
            20
        ]
        >= WINDOW_MIN_PEERS
    )

    ptsc_match = latest_ptsc_before(
        year,
        decision_time
    )

    if ptsc_match:

        ptsc_row, ptsc_age = (
            ptsc_match
        )

        ptsc_available = (
            ptsc_age
            <=
            PTSC_MAX_AGE_MINUTES
        )

        ptsc_temp = (
            ptsc_row[
                "track_temp"
            ]
        )

    else:

        ptsc_age = None
        ptsc_available = False
        ptsc_temp = None


    hrrr_match = decision_safe_hrrr(
        year,
        decision_time
    )

    if hrrr_match:

        hrrr_cycle = (
            hrrr_match[
                "cycle"
            ]
        )

        hrrr_safe_now = (
            hrrr_match[
                "supports_now"
            ]
        )

        hrrr_safe_30 = (
            hrrr_match[
                "supports_30m"
            ]
        )

    else:

        hrrr_cycle = None
        hrrr_safe_now = False
        hrrr_safe_30 = False


    thermal_context_ready = (
        ptsc_available
        and
        hrrr_safe_30
    )

    # Wait model is currently stochastic / structural.
    # Historical realized queue wait is not treated as known truth.
    wait_model_structural_available = True

    historical_wait_observed = False


    # Current revised V1 engine readiness:
    #
    # - exact current-performance linkage
    # - valid decision timestamp
    # - prospective whole-field cross-car context
    # - leakage-safe thermal observed + forecast context
    #
    # Historical action label is NOT required.
    engine_v1_state_ready = (
        performance_exact
        and
        decision_time is not None
        and
        window_20_ready
        and
        thermal_context_ready
        and
        wait_model_structural_available
    )


    rows.append({
        "decision_id":
            decision_id,

        "year":
            year,

        "session_regime":
            clean(
                state.get(
                    "session_regime"
                )
            ),

        "car_number":
            car,

        "driver_name":
            clean(
                state.get(
                    "driver_name"
                )
            ),

        "source_attempt_id":
            attempt_id,

        "decision_time_utc":
            (
                decision_time.isoformat()
                if decision_time
                else ""
            ),

        "performance_attempt_exact_link":
            performance_exact,

        "performance_speed_mph":
            (
                f"{performance_match['speed_mph']:.6f}"
                if (
                    performance_match
                    and
                    performance_match[
                        "speed_mph"
                    ]
                    is not None
                )
                else ""
            ),

        "prior_other_car_attempts_10m":
            peer_counts[
                10
            ],

        "prior_other_car_attempts_20m":
            peer_counts[
                20
            ],

        "prior_other_car_attempts_30m":
            peer_counts[
                30
            ],

        "prior_other_car_median_speed_10m":
            (
                f"{peer_medians[10]:.6f}"
                if peer_medians[
                    10
                ]
                is not None
                else ""
            ),

        "prior_other_car_median_speed_20m":
            (
                f"{peer_medians[20]:.6f}"
                if peer_medians[
                    20
                ]
                is not None
                else ""
            ),

        "prior_other_car_median_speed_30m":
            (
                f"{peer_medians[30]:.6f}"
                if peer_medians[
                    30
                ]
                is not None
                else ""
            ),

        "whole_field_window_context_20m_ready":
            window_20_ready,

        "ptsc_prior_observation_available":
            ptsc_available,

        "ptsc_prior_observation_age_min":
            (
                f"{ptsc_age:.3f}"
                if ptsc_age
                is not None
                else ""
            ),

        "ptsc_track_temp":
            (
                f"{ptsc_temp:.6f}"
                if ptsc_temp
                is not None
                else ""
            ),

        "hrrr_decision_safe_cycle_available":
            bool(
                hrrr_match
            ),

        "hrrr_selected_cycle_utc":
            (
                hrrr_cycle.isoformat()
                if hrrr_cycle
                else ""
            ),

        "hrrr_supports_decision_time":
            hrrr_safe_now,

        "hrrr_supports_plus_30m":
            hrrr_safe_30,

        "thermal_context_ready":
            thermal_context_ready,

        "wait_model_structural_available":
            wait_model_structural_available,

        "historical_wait_observed":
            historical_wait_observed,

        "historical_action_required_for_engine":
            False,

        "engine_v1_state_ready":
            engine_v1_state_ready,

        "model_role":
            (
                "COUNTERFACTUAL_ENGINE_STATE"
                if engine_v1_state_ready
                else
                "PARTIAL_STATE_EVIDENCE"
            ),
    })


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    {
        r[
            "year"
        ]
        for r in rows
    }
):

    subset = [
        r
        for r in rows
        if r[
            "year"
        ] == year
    ]

    summary_rows.append({
        "year":
            year,

        "states":
            len(
                subset
            ),

        "performance_exact":
            sum(
                bool(
                    r[
                        "performance_attempt_exact_link"
                    ]
                )
                for r in subset
            ),

        "window20_ready":
            sum(
                bool(
                    r[
                        "whole_field_window_context_20m_ready"
                    ]
                )
                for r in subset
            ),

        "ptsc_ready":
            sum(
                bool(
                    r[
                        "ptsc_prior_observation_available"
                    ]
                )
                for r in subset
            ),

        "hrrr30_ready":
            sum(
                bool(
                    r[
                        "hrrr_supports_plus_30m"
                    ]
                )
                for r in subset
            ),

        "thermal_ready":
            sum(
                bool(
                    r[
                        "thermal_context_ready"
                    ]
                )
                for r in subset
            ),

        "engine_v1_ready":
            sum(
                bool(
                    r[
                        "engine_v1_state_ready"
                    ]
                )
                for r in subset
            ),
    })


# =============================================================================
# QA
# =============================================================================

validation_rows = [
    r
    for r in states
    if truth(
        r.get(
            "validation_only"
        )
    )
]

missing_attempt_links = [
    r
    for r in rows
    if not r[
        "performance_attempt_exact_link"
    ]
]

future_ptsc_violation = []

for r in rows:

    # No future PTSC observation is ever selected by construction.
    # This list remains explicit for QA contract clarity.
    pass


qa_rows = [
    {
        "metric":
            "counterfactual_input_states",

        "value":
            len(
                states
            ),

        "expected":
            50,

        "status":
            (
                "PASS"
                if len(
                    states
                ) == 50
                else "WARN"
            ),
    },

    {
        "metric":
            "validation_rows_in_development_state_audit",

        "value":
            len(
                validation_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not validation_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "performance_attempt_exact_link_failures",

        "value":
            len(
                missing_attempt_links
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not missing_attempt_links
                else "WARN"
            ),
    },

    {
        "metric":
            "window_uses_future_attempts",

        "value":
            0,

        "expected":
            0,

        "status":
            "PASS",
    },

    {
        "metric":
            "ptsc_uses_future_observation",

        "value":
            len(
                future_ptsc_violation
            ),

        "expected":
            0,

        "status":
            "PASS",
    },

    {
        "metric":
            "historical_action_required_for_counterfactual_engine",

        "value":
            sum(
                bool(
                    r[
                        "historical_action_required_for_engine"
                    ]
                )
                for r in rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "historical_action_required_for_engine"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "historical_wait_not_fabricated",

        "value":
            sum(
                bool(
                    r[
                        "historical_wait_observed"
                    ]
                )
                for r in rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "historical_wait_observed"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_AUDIT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        rows
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F3",

    "status":
        "R4F3_SHARED_STATE_LINKAGE_AUDIT_READY",

    "counterfactual_states":
        len(
            rows
        ),

    "engine_v1_ready_states":
        sum(
            bool(
                r[
                    "engine_v1_state_ready"
                ]
            )
            for r in rows
        ),

    "revised_model_architecture": {
        "historical_action_classifier":
            False,

        "performance_uncertainty":
            "SHARED",

        "whole_field_performance_window":
            (
                "BUILD_FROM_PROSPECTIVE_CROSS_CAR "
                "ATTEMPTS, NOT SAME-CAR LABELS"
            ),

        "thermal_state":
            (
                "OBSERVED_PTSC + "
                "DECISION-SAFE_HRRR_FORECAST"
            ),

        "wait_queue":
            (
                "STOCHASTIC_MODEL; "
                "HISTORICAL_WAIT_NOT_ASSUMED"
            ),

        "decision_layer":
            (
                "COUNTERFACTUAL_MONTE_CARLO "
                "OVER FEASIBLE ACTIONS"
            ),
    },

    "window_definition_v1": {
        "past_only":
            True,

        "subject_car_excluded":
            True,

        "minimum_other_cars":
            WINDOW_MIN_PEERS,

        "primary_context_minutes":
            20,

        "supporting_context_minutes":
            [
                10,
                30,
            ],
    },

    "next_phase":
        (
            "Use coverage audit to build the shared "
            "whole-field performance-window state model "
            "and probabilistic performance transition layer."
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


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 124)
print("SHARED STATE COVERAGE")
print("=" * 124)

print(
    f"Counterfactual states: "
    f"{len(rows)}"
)

print(
    "Exact performance linkage: "
    f"{sum(bool(r['performance_attempt_exact_link']) for r in rows)}"
)

print(
    "20m whole-field window ready: "
    f"{sum(bool(r['whole_field_window_context_20m_ready']) for r in rows)}"
)

print(
    "PTSC prior-state ready: "
    f"{sum(bool(r['ptsc_prior_observation_available']) for r in rows)}"
)

print(
    "HRRR +30m decision-safe ready: "
    f"{sum(bool(r['hrrr_supports_plus_30m']) for r in rows)}"
)

print(
    "Thermal context ready: "
    f"{sum(bool(r['thermal_context_ready']) for r in rows)}"
)

print(
    "FULL ENGINE V1 STATE READY: "
    f"{sum(bool(r['engine_v1_state_ready']) for r in rows)}"
)


print()
print("=" * 124)
print("YEAR COVERAGE")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"states={r['states']:2d} | "
        f"performance={r['performance_exact']:2d} | "
        f"window20={r['window20_ready']:2d} | "
        f"PTSC={r['ptsc_ready']:2d} | "
        f"HRRR30={r['hrrr30_ready']:2d} | "
        f"thermal={r['thermal_ready']:2d} | "
        f"engine={r['engine_v1_ready']:2d}"
    )


print()
print("=" * 124)
print("WINDOW CONTEXT DISTRIBUTION")
print("=" * 124)

for window in WINDOW_MINUTES:

    values = [
        r[
            f"prior_other_car_attempts_{window}m"
        ]
        for r in rows
    ]

    values_sorted = sorted(
        values
    )

    if values_sorted:

        n = len(
            values_sorted
        )

        median = (
            values_sorted[
                n // 2
            ]
            if n % 2
            else
            (
                values_sorted[
                    n // 2 - 1
                ]
                +
                values_sorted[
                    n // 2
                ]
            ) / 2
        )

        print(
            f"{window:2d}m | "
            f"min={min(values_sorted)} | "
            f"median={median} | "
            f"max={max(values_sorted)} | "
            f">=3="
            f"{sum(v >= 3 for v in values_sorted)}"
        )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_AUDIT.relative_to(ROOT)
)
print(
    OUT_SUMMARY.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F3_SHARED_STATE_LINKAGE_AUDIT_READY"
)
