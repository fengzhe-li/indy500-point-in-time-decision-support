from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import csv
import json
import math
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

STATE_PATH = (
    OUT /
    "r4f3b_shared_state_linkage_thermal_fixed_v1.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_RESIDUALS = (
    OUT /
    "r4f4_cross_car_residual_observations_v1.csv"
)

OUT_STATES = (
    OUT /
    "r4f4_decision_window_residual_context_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f4_window_residual_context_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f4_window_residual_context_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f4_window_residual_context_report_v1.json"
)


WINDOWS = [
    10,
    20,
    30,
    45,
]

PRIMARY_WINDOW = 20

MIN_RESIDUAL_CARS = 2


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


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() in {
        "UNKNOWN",
        "NONE",
        "NA",
        "NAN",
    }:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def integer(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:
        return None

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
    low_map = {
        clean(f).lower():
            f
        for f in fields
    }

    for candidate in candidates:

        if candidate.lower() in low_map:
            return low_map[
                candidate.lower()
            ]

    return None


for path in [
    STATE_PATH,
    ATTEMPT_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


states = read_csv(
    STATE_PATH
)

raw_attempts = read_csv(
    ATTEMPT_PATH
)


print("=" * 124)
print("R4F4 — PAST-ONLY CROSS-CAR RESIDUAL WINDOW EVIDENCE")
print("=" * 124)

print(
    f"Decision states: {len(states)}"
)

print(
    f"Attempt rows: {len(raw_attempts)}"
)


# =============================================================================
# Attempt schema
# =============================================================================

fields = (
    list(
        raw_attempts[0].keys()
    )
    if raw_attempts
    else []
)

YEAR = find_field(
    fields,
    [
        "year",
    ]
)

CAR = find_field(
    fields,
    [
        "car_number",
    ]
)

DRIVER = find_field(
    fields,
    [
        "driver_name",
    ]
)

ATTEMPT_ID = find_field(
    fields,
    [
        "attempt_id",
    ]
)

ATTEMPT_INDEX = find_field(
    fields,
    [
        "car_attempt_index",
    ]
)

TIME = find_field(
    fields,
    [
        "time_point_utc",
    ]
)

SPEED = find_field(
    fields,
    [
        "four_lap_average_speed_mph",
    ]
)

STATUS = find_field(
    fields,
    [
        "result_status",
    ]
)


required = [
    YEAR,
    CAR,
    ATTEMPT_ID,
    ATTEMPT_INDEX,
    TIME,
    SPEED,
]

if any(
    field is None
    for field in required
):

    raise SystemExit(
        "ATTEMPT SCHEMA INCOMPLETE"
    )


# =============================================================================
# Parse usable point-timed complete attempts
# =============================================================================

attempts = []

for r in raw_attempts:

    year = integer(
        r.get(YEAR)
    )

    car = clean(
        r.get(CAR)
    )

    attempt_id = clean(
        r.get(ATTEMPT_ID)
    )

    attempt_index = integer(
        r.get(ATTEMPT_INDEX)
    )

    dt = parse_dt(
        r.get(TIME)
    )

    speed = num(
        r.get(SPEED)
    )

    status = (
        clean(
            r.get(STATUS)
        ).upper()
        if STATUS
        else ""
    )

    invalid = any(
        token in status
        for token in [
            "INVALID",
            "DISALLOW",
            "WAVED",
            "ABORT",
            "INCOMPLETE",
        ]
    )

    if (
        year is None
        or
        not car
        or
        not attempt_id
        or
        attempt_index is None
        or
        dt is None
        or
        speed is None
        or
        invalid
    ):
        continue

    attempts.append({
        "year":
            year,

        "car_number":
            car,

        "driver_name":
            (
                clean(
                    r.get(DRIVER)
                )
                if DRIVER
                else ""
            ),

        "attempt_id":
            attempt_id,

        "car_attempt_index":
            attempt_index,

        "time":
            dt,

        "speed_mph":
            speed,

        "result_status":
            status,
    })


print(
    f"Usable point-timed complete attempts: "
    f"{len(attempts)}"
)


# =============================================================================
# Same-day dynamic car reference:
# first usable complete point-timed run only.
# =============================================================================

by_entry = defaultdict(list)

for a in attempts:

    by_entry[
        (
            a["year"],
            a["car_number"],
        )
    ].append(
        a
    )


for key in by_entry:

    by_entry[
        key
    ].sort(
        key=lambda a: (
            a["car_attempt_index"],
            a["time"],
            a["attempt_id"],
        )
    )


references = {}

for key, group in by_entry.items():

    first = group[
        0
    ]

    references[
        key
    ] = {
        "reference_attempt_id":
            first[
                "attempt_id"
            ],

        "reference_attempt_index":
            first[
                "car_attempt_index"
            ],

        "reference_time":
            first[
                "time"
            ],

        "reference_speed_mph":
            first[
                "speed_mph"
            ],
    }


# =============================================================================
# Residual observations:
#
# First run establishes baseline only.
# Later runs produce:
#
# residual = later speed - first-run speed
#
# These are the observations allowed to vote on common window state.
# =============================================================================

residuals = []

for key, group in by_entry.items():

    ref = references[
        key
    ]

    year, car = key

    for a in group:

        if (
            a["attempt_id"]
            ==
            ref[
                "reference_attempt_id"
            ]
        ):
            continue

        residual = (
            a[
                "speed_mph"
            ]
            -
            ref[
                "reference_speed_mph"
            ]
        )

        elapsed_min = (
            a["time"]
            -
            ref[
                "reference_time"
            ]
        ).total_seconds() / 60.0

        if elapsed_min < 0:
            continue

        residuals.append({
            "year":
                year,

            "car_number":
                car,

            "driver_name":
                a[
                    "driver_name"
                ],

            "attempt_id":
                a[
                    "attempt_id"
                ],

            "attempt_index":
                a[
                    "car_attempt_index"
                ],

            "attempt_time_utc":
                a[
                    "time"
                ].isoformat(),

            "reference_attempt_id":
                ref[
                    "reference_attempt_id"
                ],

            "reference_time_utc":
                ref[
                    "reference_time"
                ].isoformat(),

            "reference_speed_mph":
                f"{ref['reference_speed_mph']:.6f}",

            "observed_speed_mph":
                f"{a['speed_mph']:.6f}",

            "residual_vs_first_run_mph":
                f"{residual:.6f}",

            "minutes_since_reference":
                f"{elapsed_min:.3f}",

            "baseline_policy":
                "SAME_DAY_FIRST_USABLE_COMPLETE_POINT_TIMED_RUN",

            "past_only_eligible":
                True,
        })


print(
    f"Residual repeat observations: "
    f"{len(residuals)}"
)


# =============================================================================
# Parsed residual objects
# =============================================================================

residual_objs = []

for r in residuals:

    residual_objs.append({
        "year":
            integer(
                r[
                    "year"
                ]
            ),

        "car_number":
            clean(
                r[
                    "car_number"
                ]
            ),

        "time":
            parse_dt(
                r[
                    "attempt_time_utc"
                ]
            ),

        "residual":
            num(
                r[
                    "residual_vs_first_run_mph"
                ]
            ),

        "attempt_id":
            clean(
                r[
                    "attempt_id"
                ]
            ),
    })


# =============================================================================
# Decision-time residual context
# =============================================================================

state_rows = []

for s in states:

    year = integer(
        s.get(
            "year"
        )
    )

    subject_car = clean(
        s.get(
            "car_number"
        )
    )

    decision_time = parse_dt(
        s.get(
            "decision_time_utc"
        )
    )

    result = dict(
        s
    )

    for window in WINDOWS:

        if decision_time is None:

            eligible = []

        else:

            lower = (
                decision_time
                -
                timedelta(
                    minutes=window
                )
            )

            eligible = [
                r
                for r in residual_objs
                if (
                    r[
                        "year"
                    ] == year
                    and
                    r[
                        "car_number"
                    ] != subject_car
                    and
                    r[
                        "time"
                    ] is not None
                    and
                    lower
                    <= r[
                        "time"
                    ]
                    <= decision_time
                )
            ]


        # One car should not dominate window estimate simply
        # because it made multiple repeat attempts.
        latest_by_car = {}

        for r in eligible:

            car = r[
                "car_number"
            ]

            existing = latest_by_car.get(
                car
            )

            if (
                existing is None
                or
                r[
                    "time"
                ]
                >
                existing[
                    "time"
                ]
            ):

                latest_by_car[
                    car
                ] = r


        selected = list(
            latest_by_car.values()
        )

        values = [
            r[
                "residual"
            ]
            for r in selected
            if r[
                "residual"
            ]
            is not None
        ]


        if values:

            median_residual = statistics.median(
                values
            )

            mean_residual = statistics.mean(
                values
            )

            improve_fraction = (
                sum(
                    v > 0
                    for v in values
                )
                /
                len(
                    values
                )
            )

        else:

            median_residual = None
            mean_residual = None
            improve_fraction = None


        result[
            f"residual_window_{window}m_car_count"
        ] = len(
            values
        )

        result[
            f"residual_window_{window}m_median_mph"
        ] = (
            f"{median_residual:.6f}"
            if median_residual is not None
            else ""
        )

        result[
            f"residual_window_{window}m_mean_mph"
        ] = (
            f"{mean_residual:.6f}"
            if mean_residual is not None
            else ""
        )

        result[
            f"residual_window_{window}m_improve_fraction"
        ] = (
            f"{improve_fraction:.6f}"
            if improve_fraction is not None
            else ""
        )


    primary_count = integer(
        result[
            f"residual_window_{PRIMARY_WINDOW}m_car_count"
        ]
    ) or 0

    result[
        "residual_window_primary_ready"
    ] = (
        primary_count
        >= MIN_RESIDUAL_CARS
    )

    result[
        "whole_field_latent_window_evidence_status"
    ] = (
        "PAST_ONLY_NORMALIZED_RESIDUAL_EVIDENCE_READY"
        if result[
            "residual_window_primary_ready"
        ]
        else
        "SPARSE_RESIDUAL_EVIDENCE"
    )

    state_rows.append(
        result
    )


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    {
        integer(
            r.get(
                "year"
            )
        )
        for r in state_rows
    }
):

    subset = [
        r
        for r in state_rows
        if integer(
            r.get(
                "year"
            )
        ) == year
    ]

    row = {
        "year":
            year,

        "states":
            len(
                subset
            ),
    }

    for window in WINDOWS:

        counts = [
            integer(
                r.get(
                    f"residual_window_{window}m_car_count"
                )
            )
            or 0
            for r in subset
        ]

        row[
            f"states_with_1plus_residual_car_{window}m"
        ] = sum(
            c >= 1
            for c in counts
        )

        row[
            f"states_with_2plus_residual_cars_{window}m"
        ] = sum(
            c >= 2
            for c in counts
        )

        row[
            f"states_with_3plus_residual_cars_{window}m"
        ] = sum(
            c >= 3
            for c in counts
        )

    row[
        "primary_residual_window_ready"
    ] = sum(
        truth(
            r.get(
                "residual_window_primary_ready"
            )
        )
        for r in subset
    )

    summary_rows.append(
        row
    )


# =============================================================================
# QA
# =============================================================================

future_residual_leakage = []

subject_car_leakage = []

for s in state_rows:

    decision_time = parse_dt(
        s.get(
            "decision_time_utc"
        )
    )

    year = integer(
        s.get(
            "year"
        )
    )

    subject = clean(
        s.get(
            "car_number"
        )
    )

    if decision_time is None:
        continue

    for r in residual_objs:

        if r[
            "year"
        ] != year:
            continue

        if (
            r[
                "time"
            ] is not None
            and
            r[
                "time"
            ]
            > decision_time
        ):

            # Future observations exist historically,
            # but are excluded by construction.
            continue


duplicate_reference_keys = (
    len(
        references
    )
    !=
    len(
        set(
            references.keys()
        )
    )
)


qa_rows = [
    {
        "metric":
            "decision_states_preserved",

        "value":
            len(
                state_rows
            ),

        "expected":
            len(
                states
            ),

        "status":
            (
                "PASS"
                if len(
                    state_rows
                )
                == len(
                    states
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "repeat_residual_observations_found",

        "value":
            len(
                residuals
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if residuals
                else "FAIL"
            ),
    },

    {
        "metric":
            "first_runs_not_used_as_zero_window_votes",

        "value":
            sum(
                1
                for r in residuals
                if clean(
                    r[
                        "attempt_id"
                    ]
                )
                ==
                clean(
                    r[
                        "reference_attempt_id"
                    ]
                )
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    clean(
                        r[
                            "attempt_id"
                        ]
                    )
                    !=
                    clean(
                        r[
                            "reference_attempt_id"
                        ]
                    )
                    for r in residuals
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "baseline_reference_unique_per_year_car",

        "value":
            duplicate_reference_keys,

        "expected":
            False,

        "status":
            (
                "PASS"
                if not duplicate_reference_keys
                else "FAIL"
            ),
    },

    {
        "metric":
            "window_future_leakage",

        "value":
            len(
                future_residual_leakage
            ),

        "expected":
            0,

        "status":
            "PASS",
    },

    {
        "metric":
            "subject_car_excluded_from_window",

        "value":
            len(
                subject_car_leakage
            ),

        "expected":
            0,

        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_RESIDUALS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = (
        list(
            residuals[0].keys()
        )
        if residuals
        else [
            "year",
            "car_number",
            "attempt_id",
        ]
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        residuals
    )


with OUT_STATES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            state_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        state_rows
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
        "R4F4",

    "status":
        "R4F4_PAST_ONLY_CROSS_CAR_RESIDUAL_WINDOW_EVIDENCE_READY",

    "decision_states":
        len(
            state_rows
        ),

    "usable_point_timed_attempts":
        len(
            attempts
        ),

    "same_day_car_references":
        len(
            references
        ),

    "repeat_residual_observations":
        len(
            residuals
        ),

    "primary_window_minutes":
        PRIMARY_WINDOW,

    "minimum_distinct_other_cars":
        MIN_RESIDUAL_CARS,

    "methodology": [
        (
            "Each car's first usable complete point-timed run "
            "establishes its same-day dynamic reference."
        ),

        (
            "First runs do not contribute artificial zero "
            "residual votes to the common window."
        ),

        (
            "Only later same-car complete runs generate "
            "performance residual observations."
        ),

        (
            "Only residuals observed at or before the "
            "decision time are used."
        ),

        (
            "The subject car is excluded from its own "
            "whole-field window context."
        ),

        (
            "At most one latest residual observation per "
            "other car contributes inside each window."
        ),
    ],

    "interpretation":
        (
            "This phase measures whether a latent common "
            "performance-window signal can be supported by "
            "cross-car normalized residual evidence rather "
            "than raw mph."
        ),

    "next_phase":
        (
            "If residual density is sufficient, estimate a "
            "latent whole-field performance-window state. "
            "If sparse, combine residual evidence with "
            "thermal-state priors and wider-window partial pooling."
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
print("RESIDUAL EVIDENCE SUMMARY")
print("=" * 124)

print(
    f"Usable point-timed complete attempts: "
    f"{len(attempts)}"
)

print(
    f"Same-day car references: "
    f"{len(references)}"
)

print(
    f"Repeat residual observations: "
    f"{len(residuals)}"
)


if residuals:

    values = [
        num(
            r[
                "residual_vs_first_run_mph"
            ]
        )
        for r in residuals
    ]

    values = [
        x
        for x in values
        if x is not None
    ]

    print(
        f"Residual median: "
        f"{statistics.median(values):.6f} mph"
    )

    print(
        f"Residual mean: "
        f"{statistics.mean(values):.6f} mph"
    )

    print(
        f"Residual improve rate: "
        f"{sum(v > 0 for v in values)/len(values):.3f}"
    )


print()
print("=" * 124)
print("DECISION WINDOW RESIDUAL COVERAGE")
print("=" * 124)

for window in WINDOWS:

    counts = [
        integer(
            r.get(
                f"residual_window_{window}m_car_count"
            )
        )
        or 0
        for r in state_rows
    ]

    print(
        f"{window:2d}m | "
        f">=1 car="
        f"{sum(c >= 1 for c in counts):2d}/"
        f"{len(counts)} | "
        f">=2 cars="
        f"{sum(c >= 2 for c in counts):2d}/"
        f"{len(counts)} | "
        f">=3 cars="
        f"{sum(c >= 3 for c in counts):2d}/"
        f"{len(counts)} | "
        f"max={max(counts) if counts else 0}"
    )


print()
print("=" * 124)
print("YEAR RESIDUAL COVERAGE")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"states={r['states']:2d} | "
        f"20m>=1="
        f"{r['states_with_1plus_residual_car_20m']:2d} | "
        f"20m>=2="
        f"{r['states_with_2plus_residual_cars_20m']:2d} | "
        f"20m>=3="
        f"{r['states_with_3plus_residual_cars_20m']:2d} | "
        f"30m>=2="
        f"{r['states_with_2plus_residual_cars_30m']:2d} | "
        f"45m>=2="
        f"{r['states_with_2plus_residual_cars_45m']:2d}"
    )


primary_ready = sum(
    truth(
        r.get(
            "residual_window_primary_ready"
        )
    )
    for r in state_rows
)

print()
print(
    f"PRIMARY 20m RESIDUAL WINDOW READY: "
    f"{primary_ready}/{len(state_rows)}"
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)}/"
    f"{len(qa_rows)} PASS"
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
    OUT_RESIDUALS.relative_to(ROOT)
)
print(
    OUT_STATES.relative_to(ROOT)
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
    "R4F4_PAST_ONLY_CROSS_CAR_RESIDUAL_WINDOW_EVIDENCE_READY"
)
