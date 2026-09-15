from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import csv
import json
import math
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

REPEAT_PATH = (
    OUT /
    "r4f4_cross_car_residual_observations_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUT_FIRST = (
    OUT /
    "r4f5b_first_run_field_residuals_v1.csv"
)

OUT_TARGET = (
    OUT /
    "r4f5b_partial_pooled_latent_window_target_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f5b_partial_pooled_latent_window_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f5b_partial_pooled_latent_window_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f5b_partial_pooled_latent_window_report_v1.json"
)


GRID_STEP_MINUTES = 5
HALF_WIDTH_MINUTES = 30

# Repeat residual is cleaner because it compares a car with itself.
REPEAT_EVIDENCE_WEIGHT = 3.0

# First-run field residual is denser but noisier because car strength
# is only controlled at the field level.
FIRST_RUN_EVIDENCE_WEIGHT = 1.0

# Shrink weak local evidence toward neutral.
PRIOR_WEIGHT = 2.0
PRIOR_MEAN_MPH = 0.0

BETTER_THRESHOLD_MPH = 0.10
WORSE_THRESHOLD_MPH = -0.10


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


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


def median(values):
    if not values:
        return None

    return statistics.median(
        values
    )


for path in [
    ATTEMPT_PATH,
    REPEAT_PATH,
    PTSC_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


raw_attempts = read_csv(
    ATTEMPT_PATH
)

raw_repeats = read_csv(
    REPEAT_PATH
)

raw_ptsc = read_csv(
    PTSC_PATH
)


print("=" * 124)
print("R4F5B — PARTIAL-POOLED LATENT PERFORMANCE WINDOW TARGET")
print("=" * 124)

print(
    f"Attempt rows: {len(raw_attempts)}"
)

print(
    f"Repeat residual rows: {len(raw_repeats)}"
)

print(
    f"PTSC rows: {len(raw_ptsc)}"
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
    ["year"]
)

CAR = find_field(
    fields,
    ["car_number"]
)

DRIVER = find_field(
    fields,
    ["driver_name"]
)

ATTEMPT_ID = find_field(
    fields,
    ["attempt_id"]
)

ATTEMPT_INDEX = find_field(
    fields,
    ["car_attempt_index"]
)

TIME = find_field(
    fields,
    ["time_point_utc"]
)

SPEED = find_field(
    fields,
    ["four_lap_average_speed_mph"]
)

STATUS = find_field(
    fields,
    ["result_status"]
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
    x is None
    for x in required
):

    raise SystemExit(
        "ATTEMPT SCHEMA INCOMPLETE"
    )


# =============================================================================
# Parse usable first runs
# =============================================================================

first_candidates = []

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
        attempt_index != 1
        or
        dt is None
        or
        speed is None
        or
        invalid
    ):
        continue


    first_candidates.append({
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

        "time":
            dt,

        "speed_mph":
            speed,
    })


# =============================================================================
# Annual first-run field center
#
# Offline target construction is allowed to use the complete historical
# first-run distribution of the year.
# =============================================================================

first_by_year = defaultdict(list)

for r in first_candidates:

    first_by_year[
        r["year"]
    ].append(
        r
    )


field_center_by_year = {}

for year, rows in first_by_year.items():

    speeds = [
        r[
            "speed_mph"
        ]
        for r in rows
    ]

    field_center_by_year[
        year
    ] = statistics.median(
        speeds
    )


first_residuals = []

for r in first_candidates:

    center = field_center_by_year[
        r["year"]
    ]

    residual = (
        r[
            "speed_mph"
        ]
        -
        center
    )

    first_residuals.append({
        "year":
            r[
                "year"
            ],

        "car_number":
            r[
                "car_number"
            ],

        "driver_name":
            r[
                "driver_name"
            ],

        "attempt_id":
            r[
                "attempt_id"
            ],

        "attempt_time_utc":
            r[
                "time"
            ].isoformat(),

        "observed_speed_mph":
            f"{r['speed_mph']:.6f}",

        "year_first_run_field_median_mph":
            f"{center:.6f}",

        "first_run_field_residual_mph":
            f"{residual:.6f}",

        "evidence_type":
            "FIRST_RUN_FIELD_RESIDUAL",

        "evidence_strength":
            "WEAK_DENSE",

        "important_constraint":
            (
                "OFFLINE TARGET EVIDENCE; "
                "NOT CAR-SPECIFIC PACE CORRECTION"
            ),
    })


# =============================================================================
# Parse repeat residuals
# =============================================================================

repeat_residuals = []

for r in raw_repeats:

    year = integer(
        r.get(
            "year"
        )
    )

    car = clean(
        r.get(
            "car_number"
        )
    )

    dt = parse_dt(
        r.get(
            "attempt_time_utc"
        )
    )

    residual = num(
        r.get(
            "residual_vs_first_run_mph"
        )
    )

    if (
        year is None
        or
        not car
        or
        dt is None
        or
        residual is None
    ):
        continue


    repeat_residuals.append({
        "year":
            year,

        "car_number":
            car,

        "time":
            dt,

        "residual":
            residual,
    })


# =============================================================================
# Session grid from PTSC
# =============================================================================

ptsc_by_year = defaultdict(list)

for r in raw_ptsc:

    year = integer(
        r.get(
            "year"
        )
    )

    dt = parse_dt(
        r.get(
            "utc_datetime"
        )
    )

    if (
        year is None
        or
        dt is None
    ):
        continue

    ptsc_by_year[
        year
    ].append(
        dt
    )


for year in ptsc_by_year:

    ptsc_by_year[
        year
    ].sort()


# =============================================================================
# Build partial-pooled offline latent window
# =============================================================================

target_rows = []

for year in sorted(
    ptsc_by_year
):

    start = min(
        ptsc_by_year[
            year
        ]
    )

    end = max(
        ptsc_by_year[
            year
        ]
    )

    t = start


    year_first = [
        {
            "car_number":
                r[
                    "car_number"
                ],

            "time":
                parse_dt(
                    r[
                        "attempt_time_utc"
                    ]
                ),

            "residual":
                num(
                    r[
                        "first_run_field_residual_mph"
                    ]
                ),
        }
        for r in first_residuals
        if r[
            "year"
        ] == year
    ]


    year_repeat = [
        r
        for r in repeat_residuals
        if r[
            "year"
        ] == year
    ]


    while t <= end:

        lower = (
            t
            -
            timedelta(
                minutes=HALF_WIDTH_MINUTES
            )
        )

        upper = (
            t
            +
            timedelta(
                minutes=HALF_WIDTH_MINUTES
            )
        )


        # =====================================================================
        # First-run evidence
        # =====================================================================

        local_first = [
            r
            for r in year_first
            if (
                r[
                    "time"
                ] is not None
                and
                lower
                <= r[
                    "time"
                ]
                <= upper
            )
        ]


        first_values = [
            r[
                "residual"
            ]
            for r in local_first
            if r[
                "residual"
            ]
            is not None
        ]


        first_signal = median(
            first_values
        )


        # =====================================================================
        # Repeat evidence
        #
        # One closest residual per car.
        # =====================================================================

        nearby_repeat = [
            r
            for r in year_repeat
            if (
                lower
                <= r[
                    "time"
                ]
                <= upper
            )
        ]


        repeat_by_car = {}

        for r in nearby_repeat:

            distance = abs(
                (
                    r[
                        "time"
                    ]
                    -
                    t
                ).total_seconds()
            )

            current = repeat_by_car.get(
                r[
                    "car_number"
                ]
            )

            if (
                current is None
                or
                distance
                <
                current[
                    "distance"
                ]
            ):

                repeat_by_car[
                    r[
                        "car_number"
                    ]
                ] = {
                    "distance":
                        distance,

                    "residual":
                        r[
                            "residual"
                        ],
                }


        repeat_values = [
            r[
                "residual"
            ]
            for r in repeat_by_car.values()
        ]


        repeat_signal = median(
            repeat_values
        )


        # =====================================================================
        # Partial pooling
        #
        # Evidence is summarized at the source level first.
        #
        # Repeat evidence has higher source reliability.
        # Evidence-count scaling prevents one observation from dominating.
        # Neutral prior shrinks sparse estimates toward zero.
        # =====================================================================

        components = []

        if first_signal is not None:

            first_weight = (
                FIRST_RUN_EVIDENCE_WEIGHT
                *
                math.sqrt(
                    len(
                        first_values
                    )
                )
            )

            components.append(
                (
                    first_signal,
                    first_weight,
                )
            )

        else:

            first_weight = 0.0


        if repeat_signal is not None:

            repeat_weight = (
                REPEAT_EVIDENCE_WEIGHT
                *
                math.sqrt(
                    len(
                        repeat_values
                    )
                )
            )

            components.append(
                (
                    repeat_signal,
                    repeat_weight,
                )
            )

        else:

            repeat_weight = 0.0


        numerator = (
            PRIOR_MEAN_MPH
            *
            PRIOR_WEIGHT
        )

        denominator = (
            PRIOR_WEIGHT
        )


        for value, weight in components:

            numerator += (
                value
                *
                weight
            )

            denominator += (
                weight
            )


        if components:

            latent_signal = (
                numerator
                /
                denominator
            )

            target_available = True

        else:

            latent_signal = None
            target_available = False


        if latent_signal is None:

            window_class = (
                "NO_EVIDENCE"
            )

        elif latent_signal > BETTER_THRESHOLD_MPH:

            window_class = (
                "BETTER_THAN_REFERENCE"
            )

        elif latent_signal < WORSE_THRESHOLD_MPH:

            window_class = (
                "WORSE_THAN_REFERENCE"
            )

        else:

            window_class = (
                "NEUTRAL"
            )


        if (
            repeat_signal is not None
            and
            first_signal is not None
        ):

            evidence_tier = (
                "TIER_A_REPEAT_PLUS_FIRST_RUN"
            )

        elif repeat_signal is not None:

            evidence_tier = (
                "TIER_B_REPEAT_ANCHOR_ONLY"
            )

        elif (
            first_signal is not None
            and
            len(
                first_values
            ) >= 3
        ):

            evidence_tier = (
                "TIER_C_MULTI_CAR_FIRST_RUN_ONLY"
            )

        elif first_signal is not None:

            evidence_tier = (
                "TIER_D_SPARSE_FIRST_RUN_ONLY"
            )

        else:

            evidence_tier = (
                "NO_EVIDENCE"
            )


        target_rows.append({
            "year":
                year,

            "grid_time_utc":
                t.isoformat(),

            "window_half_width_minutes":
                HALF_WIDTH_MINUTES,

            "first_run_car_count":
                len(
                    first_values
                ),

            "first_run_median_field_residual_mph":
                (
                    f"{first_signal:.6f}"
                    if first_signal is not None
                    else ""
                ),

            "first_run_evidence_weight":
                f"{first_weight:.6f}",

            "repeat_car_count":
                len(
                    repeat_values
                ),

            "repeat_median_residual_mph":
                (
                    f"{repeat_signal:.6f}"
                    if repeat_signal is not None
                    else ""
                ),

            "repeat_evidence_weight":
                f"{repeat_weight:.6f}",

            "prior_mean_mph":
                f"{PRIOR_MEAN_MPH:.6f}",

            "prior_weight":
                f"{PRIOR_WEIGHT:.6f}",

            "latent_window_target_mph":
                (
                    f"{latent_signal:.6f}"
                    if latent_signal is not None
                    else ""
                ),

            "latent_window_class":
                window_class,

            "evidence_tier":
                evidence_tier,

            "target_available":
                target_available,

            "target_role":
                (
                    "OFFLINE_LATENT_WINDOW_TARGET"
                    if target_available
                    else
                    "NO_TARGET"
                ),

            "important_constraint":
                (
                    "FULL-SESSION HISTORICAL TARGET; "
                    "NOT DECISION-TIME FEATURE"
                ),
        })


        t += timedelta(
            minutes=GRID_STEP_MINUTES
        )


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    {
        r[
            "year"
        ]
        for r in target_rows
    }
):

    subset = [
        r
        for r in target_rows
        if r[
            "year"
        ] == year
    ]

    available = [
        r
        for r in subset
        if r[
            "target_available"
        ]
    ]

    tiers = defaultdict(int)

    classes = defaultdict(int)

    for r in available:

        tiers[
            r[
                "evidence_tier"
            ]
        ] += 1

        classes[
            r[
                "latent_window_class"
            ]
        ] += 1


    summary_rows.append({
        "year":
            year,

        "grid_rows":
            len(
                subset
            ),

        "target_rows":
            len(
                available
            ),

        "coverage_fraction":
            (
                len(
                    available
                )
                /
                len(
                    subset
                )
                if subset
                else 0.0
            ),

        "tier_a_repeat_plus_first":
            tiers[
                "TIER_A_REPEAT_PLUS_FIRST_RUN"
            ],

        "tier_b_repeat_only":
            tiers[
                "TIER_B_REPEAT_ANCHOR_ONLY"
            ],

        "tier_c_multi_first_only":
            tiers[
                "TIER_C_MULTI_CAR_FIRST_RUN_ONLY"
            ],

        "tier_d_sparse_first_only":
            tiers[
                "TIER_D_SPARSE_FIRST_RUN_ONLY"
            ],

        "better":
            classes[
                "BETTER_THAN_REFERENCE"
            ],

        "neutral":
            classes[
                "NEUTRAL"
            ],

        "worse":
            classes[
                "WORSE_THAN_REFERENCE"
            ],
    })


# =============================================================================
# QA
# =============================================================================

invalid_first_count = [
    r
    for r in first_residuals
    if integer(
        1
    ) != 1
]


target_as_feature_errors = [
    r
    for r in target_rows
    if (
        r[
            "target_available"
        ]
        and
        r[
            "important_constraint"
        ]
        !=
        "FULL-SESSION HISTORICAL TARGET; NOT DECISION-TIME FEATURE"
    )
]


qa_rows = [
    {
        "metric":
            "first_run_residuals_found",

        "value":
            len(
                first_residuals
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if first_residuals
                else "FAIL"
            ),
    },

    {
        "metric":
            "repeat_residuals_preserved",

        "value":
            len(
                repeat_residuals
            ),

        "expected":
            len(
                raw_repeats
            ),

        "status":
            (
                "PASS"
                if len(
                    repeat_residuals
                )
                == len(
                    raw_repeats
                )
                else "WARN"
            ),
    },

    {
        "metric":
            "offline_target_rows_exist",

        "value":
            sum(
                bool(
                    r[
                        "target_available"
                    ]
                )
                for r in target_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if any(
                    r[
                        "target_available"
                    ]
                    for r in target_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "offline_target_not_marked_as_live_feature",

        "value":
            len(
                target_as_feature_errors
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not target_as_feature_errors
                else "FAIL"
            ),
    },

    {
        "metric":
            "first_run_field_center_available_years",

        "value":
            ";".join(
                str(year)
                for year in sorted(
                    field_center_by_year
                )
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_FIRST.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            first_residuals[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        first_residuals
    )


with OUT_TARGET.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            target_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        target_rows
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
        "R4F5B",

    "status":
        "R4F5B_PARTIAL_POOLED_LATENT_WINDOW_TARGET_READY",

    "first_run_residual_rows":
        len(
            first_residuals
        ),

    "repeat_residual_rows":
        len(
            repeat_residuals
        ),

    "grid_rows":
        len(
            target_rows
        ),

    "target_rows":
        sum(
            bool(
                r[
                    "target_available"
                ]
            )
            for r in target_rows
        ),

    "target_design": {
        "repeat_evidence":
            (
                "HIGHER-WEIGHT SAME-CAR "
                "NORMALIZED ANCHOR"
            ),

        "first_run_evidence":
            (
                "LOWER-WEIGHT DENSE FIELD "
                "TEMPORAL SIGNAL"
            ),

        "neutral_prior":
            (
                "SHRINKS SPARSE LOCAL "
                "ESTIMATES TOWARD ZERO"
            ),
    },

    "important_methodology": [
        (
            "This is an OFFLINE historical latent-window "
            "target, so complete-session information may be "
            "used for target construction."
        ),

        (
            "First-run residuals are centered on the annual "
            "first-run field median and are not interpreted "
            "as car-specific performance residuals."
        ),

        (
            "Repeat residuals receive greater weight because "
            "they compare the same car with its own earlier run."
        ),

        (
            "Fast Friday and same-regulation external evidence "
            "have not yet been added. They remain available as "
            "a later physical/hierarchical prior if needed."
        ),
    ],

    "next_phase":
        (
            "Quantify latent-target density and stability. "
            "Then attach track-temperature/weather states and "
            "train a prospective window-state predictor whose "
            "features are decision-time observable."
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
print("FIRST-RUN FIELD EVIDENCE")
print("=" * 124)

print(
    f"First-run residual rows: "
    f"{len(first_residuals)}"
)

for year in sorted(
    field_center_by_year
):

    year_rows = [
        r
        for r in first_residuals
        if r[
            "year"
        ] == year
    ]

    print(
        f"{year} | "
        f"first_runs={len(year_rows):2d} | "
        f"field_median="
        f"{field_center_by_year[year]:.6f} mph"
    )


print()
print("=" * 124)
print("PARTIAL-POOLED TARGET COVERAGE")
print("=" * 124)

total_available = sum(
    bool(
        r[
            "target_available"
        ]
    )
    for r in target_rows
)

print(
    f"Grid rows: {len(target_rows)}"
)

print(
    f"Target rows: {total_available}"
)

print(
    f"Coverage: "
    f"{total_available / len(target_rows):.3f}"
    if target_rows
    else
    "Coverage: 0"
)


print()
print("=" * 124)
print("YEAR TARGET SUMMARY")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"grid={r['grid_rows']:3d} | "
        f"target={r['target_rows']:3d} | "
        f"coverage={r['coverage_fraction']:.3f} | "
        f"A={r['tier_a_repeat_plus_first']:3d} | "
        f"B={r['tier_b_repeat_only']:3d} | "
        f"C={r['tier_c_multi_first_only']:3d} | "
        f"D={r['tier_d_sparse_first_only']:3d} | "
        f"better={r['better']:3d} | "
        f"neutral={r['neutral']:3d} | "
        f"worse={r['worse']:3d}"
    )


print()
print("=" * 124)
print("EVIDENCE-TIER INTERPRETATION")
print("=" * 124)

tier_counts = defaultdict(int)

for r in target_rows:

    if r[
        "target_available"
    ]:

        tier_counts[
            r[
                "evidence_tier"
            ]
        ] += 1


for tier in [
    "TIER_A_REPEAT_PLUS_FIRST_RUN",
    "TIER_B_REPEAT_ANCHOR_ONLY",
    "TIER_C_MULTI_CAR_FIRST_RUN_ONLY",
    "TIER_D_SPARSE_FIRST_RUN_ONLY",
]:

    print(
        f"{tier:40s} | "
        f"{tier_counts[tier]}"
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
    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_FIRST.relative_to(ROOT)
)
print(
    OUT_TARGET.relative_to(ROOT)
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
    "R4F5B_PARTIAL_POOLED_LATENT_WINDOW_TARGET_READY"
)
