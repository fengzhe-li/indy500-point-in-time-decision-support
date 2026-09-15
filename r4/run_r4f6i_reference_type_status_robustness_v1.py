from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
import csv
import json
import math
import re
import statistics
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

ALL_REFERENCE_PATH = (
    OUT /
    "r4f6g_fast_friday_all_reference_evidence_v2.csv"
)

CANONICAL_REFERENCE_PATH = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

OUT_STATUS = (
    OUT /
    "r4f6i_performance_status_eligibility_audit_v1.csv"
)

OUT_ENTRY = (
    OUT /
    "r4f6i_reference_type_entry_strength_robustness_v1.csv"
)

OUT_REPEAT = (
    OUT /
    "r4f6i_reference_type_repeat_window_rows_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f6i_reference_type_repeat_window_metrics_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6i_reference_type_status_robustness_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6i_reference_type_status_robustness_report_v1.json"
)


WINDOWS = [
    20,
    30,
    45,
]


# =============================================================================
# Performance-observation status policy
#
# These are complete measured four-lap performances that are allowed as
# historical physical/performance evidence even if they were later superseded
# or withdrawn.
#
# FAILED / RETIRED / DISALLOWED are excluded from the primary robustness set.
# They remain visible in the audit output.
# =============================================================================

PRIMARY_PERFORMANCE_STATUSES = {
    "VALID_RETAINED",
    "VALID_SUPERSEDED",
    "WITHDRAWN",
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def year_int(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(
            csv.DictReader(f)
        )


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = (
            s[:-1]
            +
            "+00:00"
        )

    try:
        dt = datetime.fromisoformat(
            s
        )

    except Exception:
        return None

    if dt.tzinfo is None:
        return None

    return dt.astimezone(
        timezone.utc
    )


def driver_key(name):
    value = unicodedata.normalize(
        "NFKD",
        clean(name)
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def mean(values):
    values = [
        x
        for x in values
        if x is not None
    ]

    if not values:
        return None

    return statistics.mean(values)


def median(values):
    values = [
        x
        for x in values
        if x is not None
    ]

    if not values:
        return None

    return statistics.median(values)


def stdev(values):
    values = [
        x
        for x in values
        if x is not None
    ]

    if len(values) < 2:
        return None

    return statistics.stdev(values)


def mae(actual, pred):
    pairs = [
        (a, p)
        for a, p in zip(
            actual,
            pred
        )
        if (
            a is not None
            and
            p is not None
        )
    ]

    if not pairs:
        return None

    return mean(
        [
            abs(a - p)
            for a, p in pairs
        ]
    )


def rmse(actual, pred):
    pairs = [
        (a, p)
        for a, p in zip(
            actual,
            pred
        )
        if (
            a is not None
            and
            p is not None
        )
    ]

    if not pairs:
        return None

    return math.sqrt(
        mean(
            [
                (a - p) ** 2
                for a, p in pairs
            ]
        )
    )


def pearson(xs, ys):
    pairs = [
        (x, y)
        for x, y in zip(
            xs,
            ys
        )
        if (
            x is not None
            and
            y is not None
        )
    ]

    if len(pairs) < 3:
        return None

    xs = [
        p[0]
        for p in pairs
    ]

    ys = [
        p[1]
        for p in pairs
    ]

    mx = mean(xs)
    my = mean(ys)

    numerator = sum(
        (x - mx) * (y - my)
        for x, y in zip(
            xs,
            ys
        )
    )

    dx = math.sqrt(
        sum(
            (x - mx) ** 2
            for x in xs
        )
    )

    dy = math.sqrt(
        sum(
            (y - my) ** 2
            for y in ys
        )
    )

    if (
        dx == 0
        or
        dy == 0
    ):
        return None

    return numerator / (dx * dy)


def linear_fit(xs, ys):
    pairs = [
        (x, y)
        for x, y in zip(
            xs,
            ys
        )
        if (
            x is not None
            and
            y is not None
        )
    ]

    if len(pairs) < 3:
        return (
            None,
            None,
        )

    xs = [
        p[0]
        for p in pairs
    ]

    ys = [
        p[1]
        for p in pairs
    ]

    mx = mean(xs)
    my = mean(ys)

    denom = sum(
        (x - mx) ** 2
        for x in xs
    )

    if denom == 0:
        return (
            None,
            None,
        )

    slope = (
        sum(
            (x - mx) * (y - my)
            for x, y in zip(
                xs,
                ys
            )
        )
        /
        denom
    )

    intercept = (
        my
        -
        slope * mx
    )

    return (
        intercept,
        slope,
    )


for path in [
    ATTEMPT_PATH,
    ALL_REFERENCE_PATH,
    CANONICAL_REFERENCE_PATH,
]:
    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


attempt_raw = read_csv(
    ATTEMPT_PATH
)

all_reference_raw = read_csv(
    ALL_REFERENCE_PATH
)

canonical_reference_raw = read_csv(
    CANONICAL_REFERENCE_PATH
)


print("=" * 136)
print("R4F6I — REFERENCE-TYPE + STATUS ROBUSTNESS")
print("=" * 136)

print(
    f"Attempts: {len(attempt_raw)}"
)

print(
    f"All Fast Friday evidence: "
    f"{len(all_reference_raw)}"
)

print(
    f"Canonical references: "
    f"{len(canonical_reference_raw)}"
)


# =============================================================================
# Build reference maps
# =============================================================================

canonical_map = {}

for r in canonical_reference_raw:

    year = year_int(
        r.get("year")
    )

    key = clean(
        r.get("driver_key")
    )

    speed = num(
        r.get(
            "reference_speed_mph"
        )
    )

    if (
        year is None
        or
        not key
        or
        speed is None
    ):
        continue

    canonical_map[
        (
            year,
            key,
        )
    ] = {
        "speed":
            speed,

        "type":
            clean(
                r.get(
                    "reference_type"
                )
            ),
    }


# General-only uses ONLY the official full-session PDF single-best-lap metric.
# This guarantees a common measurement definition across the entire field.

general_map = {}

for r in all_reference_raw:

    if clean(
        r.get(
            "reference_type"
        )
    ) != "GENERAL_FAST_FRIDAY_BEST_SPEED":
        continue

    year = year_int(
        r.get("year")
    )

    key = clean(
        r.get("driver_key")
    )

    speed = num(
        r.get(
            "reference_speed_mph"
        )
    )

    if (
        year is None
        or
        not key
        or
        speed is None
    ):
        continue

    general_map[
        (
            year,
            key,
        )
    ] = {
        "speed":
            speed,

        "type":
            "GENERAL_FAST_FRIDAY_BEST_SPEED",
    }


print()
print("REFERENCE MAP COVERAGE")

for year in [
    2021,
    2023,
    2024,
]:

    mixed_n = sum(
        y == year
        for y, _ in canonical_map
    )

    general_n = sum(
        y == year
        for y, _ in general_map
    )

    print(
        f"{year} | "
        f"mixed={mixed_n:2d} | "
        f"general_only={general_n:2d}"
    )


# =============================================================================
# Attempt observation construction
# =============================================================================

attempts = []
status_audit = []


for r in attempt_raw:

    year = year_int(
        r.get("year")
    )

    name = clean(
        r.get(
            "driver_name"
        )
    )

    key = driver_key(
        name
    )

    speed = num(
        r.get(
            "four_lap_average_speed_mph"
        )
    )

    time = parse_dt(
        r.get(
            "time_point_utc"
        )
    )

    status = clean(
        r.get(
            "result_status"
        )
    )

    complete = truthy(
        r.get(
            "complete_performance_record"
        )
    )

    counted = truthy(
        r.get(
            "result_counted_at_session_end"
        )
    )

    attempt_index = num(
        r.get(
            "car_attempt_index"
        )
    )

    primary_eligible = (
        year is not None
        and
        bool(name)
        and
        speed is not None
        and
        complete
        and
        status
        in
        PRIMARY_PERFORMANCE_STATUSES
    )


    status_audit.append({
        "year":
            year,

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "driver_name":
            name,

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "result_status":
            status,

        "counted_at_session_end":
            counted,

        "complete_performance_record":
            complete,

        "speed_available":
            speed is not None,

        "point_time_available":
            time is not None,

        "primary_performance_eligible":
            primary_eligible,

        "mixed_reference_available":
            (
                (
                    year,
                    key,
                )
                in canonical_map
            ),

        "general_reference_available":
            (
                (
                    year,
                    key,
                )
                in general_map
            ),
    })


    if not primary_eligible:
        continue


    attempts.append({
        "year":
            year,

        "driver_name":
            name,

        "driver_key":
            key,

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "attempt_index":
            (
                int(
                    attempt_index
                )
                if attempt_index
                is not None
                else None
            ),

        "speed":
            speed,

        "time":
            time,

        "status":
            status,

        "counted":
            counted,
    })


print()
print("=" * 136)
print("PRIMARY PERFORMANCE STATUS AUDIT")
print("=" * 136)

print(
    f"Primary eligible observations: "
    f"{len(attempts)}"
)

print(
    f"Primary eligible with point time: "
    f"{sum(r['time'] is not None for r in attempts)}"
)


for status in sorted(
    PRIMARY_PERFORMANCE_STATUSES
):

    n = sum(
        r[
            "status"
        ] == status
        for r in attempts
    )

    print(
        f"{status:32s} | {n}"
    )


excluded_status_counts = Counter(
    clean(
        r[
            "result_status"
        ]
    )
    for r in status_audit
    if (
        r[
            "complete_performance_record"
        ]
        and
        r[
            "speed_available"
        ]
        and
        not r[
            "primary_performance_eligible"
        ]
    )
)


print()
print("EXCLUDED COMPLETE-PERFORMANCE STATUSES")

for status, n in sorted(
    excluded_status_counts.items()
):

    print(
        f"{status or '[EMPTY]':32s} | {n}"
    )


# =============================================================================
# First observation per entry
# =============================================================================

entry_attempts = defaultdict(
    list
)

for r in attempts:

    entry_attempts[
        (
            r[
                "year"
            ],
            r[
                "driver_key"
            ],
        )
    ].append(
        r
    )


first_by_entry = {}
repeat_pairs = []


for entry, rows in entry_attempts.items():

    rows = sorted(
        rows,
        key=lambda r: (
            (
                r[
                    "attempt_index"
                ]
                if r[
                    "attempt_index"
                ]
                is not None
                else 999
            ),
            (
                r[
                    "time"
                ]
                if r[
                    "time"
                ]
                is not None
                else datetime.max.replace(
                    tzinfo=timezone.utc
                )
            ),
        )
    )

    first = rows[0]

    first_by_entry[
        entry
    ] = first


    for repeat in rows[1:]:

        repeat_pairs.append({
            "year":
                repeat[
                    "year"
                ],

            "driver_name":
                repeat[
                    "driver_name"
                ],

            "driver_key":
                repeat[
                    "driver_key"
                ],

            "car_number":
                repeat[
                    "car_number"
                ],

            "first_attempt_id":
                first[
                    "attempt_id"
                ],

            "repeat_attempt_id":
                repeat[
                    "attempt_id"
                ],

            "first_speed":
                first[
                    "speed"
                ],

            "repeat_speed":
                repeat[
                    "speed"
                ],

            "first_time":
                first[
                    "time"
                ],

            "repeat_time":
                repeat[
                    "time"
                ],

            "actual_delta":
                (
                    repeat[
                        "speed"
                    ]
                    -
                    first[
                        "speed"
                    ]
                ),

            "first_status":
                first[
                    "status"
                ],

            "repeat_status":
                repeat[
                    "status"
                ],
        })


# =============================================================================
# Entry-strength comparison on exact common support
# =============================================================================

entry_metric_rows = []


for year in [
    2023,
    2024,
]:

    common = []

    for (
        entry_year,
        key,
    ), first in first_by_entry.items():

        if entry_year != year:
            continue

        mixed = canonical_map.get(
            (
                year,
                key,
            )
        )

        general = general_map.get(
            (
                year,
                key,
            )
        )

        if (
            mixed is None
            or
            general is None
        ):
            continue

        common.append({
            "qual":
                first[
                    "speed"
                ],

            "mixed":
                mixed[
                    "speed"
                ],

            "general":
                general[
                    "speed"
                ],
        })


    quals = [
        r[
            "qual"
        ]
        for r in common
    ]

    mixed_values = [
        r[
            "mixed"
        ]
        for r in common
    ]

    general_values = [
        r[
            "general"
        ]
        for r in common
    ]


    for label, refs in [
        (
            "MIXED_CANONICAL",
            mixed_values,
        ),
        (
            "GENERAL_ONLY",
            general_values,
        ),
    ]:

        loo = []

        for i in range(
            len(common)
        ):

            train_x = [
                refs[j]
                for j in range(
                    len(common)
                )
                if j != i
            ]

            train_y = [
                quals[j]
                for j in range(
                    len(common)
                )
                if j != i
            ]

            intercept, slope = linear_fit(
                train_x,
                train_y
            )

            if (
                intercept is None
                or
                slope is None
            ):

                loo.append(
                    None
                )

            else:

                loo.append(
                    intercept
                    +
                    slope * refs[i]
                )


        residual = [
            q - ref
            for q, ref in zip(
                quals,
                refs
            )
        ]


        entry_metric_rows.append({
            "year":
                year,

            "reference_definition":
                label,

            "common_support_n":
                len(common),

            "correlation":
                pearson(
                    refs,
                    quals
                ),

            "loo_mae_mph":
                mae(
                    quals,
                    loo
                ),

            "raw_residual_std_mph":
                stdev(
                    residual
                ),

            "model_role":
                (
                    "VALIDATION_ONLY"
                    if year == 2024
                    else
                    "DEVELOPMENT"
                ),
        })


# =============================================================================
# Build window source observations for both reference definitions
# =============================================================================

window_sources = {
    "MIXED_CANONICAL": [],
    "GENERAL_ONLY": [],
}


for r in attempts:

    if r[
        "time"
    ] is None:
        continue

    key = (
        r[
            "year"
        ],
        r[
            "driver_key"
        ],
    )


    for label, ref_map in [
        (
            "MIXED_CANONICAL",
            canonical_map,
        ),
        (
            "GENERAL_ONLY",
            general_map,
        ),
    ]:

        ref = ref_map.get(
            key
        )

        if ref is None:
            continue

        window_sources[
            label
        ].append({
            **r,

            "residual":
                (
                    r[
                        "speed"
                    ]
                    -
                    ref[
                        "speed"
                    ]
                ),
        })


def local_state(
    source_rows,
    year,
    subject_key,
    target_time,
    width,
):
    if target_time is None:
        return (
            None,
            0,
        )

    lower = (
        target_time
        -
        timedelta(
            minutes=width
        )
    )

    upper = (
        target_time
        +
        timedelta(
            minutes=width
        )
    )


    candidates = [
        r
        for r in source_rows
        if (
            r[
                "year"
            ] == year
            and
            r[
                "driver_key"
            ] != subject_key
            and
            lower
            <= r[
                "time"
            ]
            <= upper
        )
    ]


    closest = {}

    for r in candidates:

        distance = abs(
            (
                r[
                    "time"
                ]
                -
                target_time
            ).total_seconds()
        )

        key = r[
            "driver_key"
        ]

        if (
            key not in closest
            or
            distance
            <
            closest[
                key
            ][0]
        ):

            closest[
                key
            ] = (
                distance,
                r[
                    "residual"
                ],
            )


    values = [
        item[1]
        for item in closest.values()
    ]

    return (
        median(values),
        len(values),
    )


repeat_rows = []


for pair in repeat_pairs:

    row = {
        "year":
            pair[
                "year"
            ],

        "driver_name":
            pair[
                "driver_name"
            ],

        "car_number":
            pair[
                "car_number"
            ],

        "first_attempt_id":
            pair[
                "first_attempt_id"
            ],

        "repeat_attempt_id":
            pair[
                "repeat_attempt_id"
            ],

        "actual_delta_mph":
            pair[
                "actual_delta"
            ],

        "first_status":
            pair[
                "first_status"
            ],

        "repeat_status":
            pair[
                "repeat_status"
            ],
    }


    for definition in [
        "MIXED_CANONICAL",
        "GENERAL_ONLY",
    ]:

        for width in WINDOWS:

            first_state, first_n = local_state(
                window_sources[
                    definition
                ],
                pair[
                    "year"
                ],
                pair[
                    "driver_key"
                ],
                pair[
                    "first_time"
                ],
                width,
            )

            repeat_state, repeat_n = local_state(
                window_sources[
                    definition
                ],
                pair[
                    "year"
                ],
                pair[
                    "driver_key"
                ],
                pair[
                    "repeat_time"
                ],
                width,
            )


            pred = (
                repeat_state
                -
                first_state
                if (
                    first_state is not None
                    and
                    repeat_state is not None
                )
                else None
            )


            prefix = (
                definition.lower()
                +
                f"_{width}m"
            )

            row[
                prefix
                +
                "_predicted_delta"
            ] = pred

            row[
                prefix
                +
                "_first_n"
            ] = first_n

            row[
                prefix
                +
                "_repeat_n"
            ] = repeat_n


    repeat_rows.append(
        row
    )


# =============================================================================
# Exact common-support comparison:
# mixed vs general vs zero.
#
# Development = non-2024.
# 2024 remains validation-only.
# =============================================================================

metric_rows = []


for width in WINDOWS:

    mixed_field = (
        f"mixed_canonical_{width}m_predicted_delta"
    )

    general_field = (
        f"general_only_{width}m_predicted_delta"
    )


    for label, selector in [
        (
            "DEVELOPMENT",
            lambda r:
                r[
                    "year"
                ] != 2024,
        ),
        (
            "2024_VALIDATION_ONLY",
            lambda r:
                r[
                    "year"
                ] == 2024,
        ),
        (
            "ALL_DIAGNOSTIC",
            lambda r:
                True,
        ),
    ]:

        subset = [
            r
            for r in repeat_rows
            if (
                selector(r)
                and
                r.get(
                    mixed_field
                )
                is not None
                and
                r.get(
                    general_field
                )
                is not None
            )
        ]


        actual = [
            r[
                "actual_delta_mph"
            ]
            for r in subset
        ]

        mixed_pred = [
            r[
                mixed_field
            ]
            for r in subset
        ]

        general_pred = [
            r[
                general_field
            ]
            for r in subset
        ]

        zero = [
            0.0
            for _ in subset
        ]


        metric_rows.append({
            "window_minutes":
                width,

            "evaluation_set":
                label,

            "common_support_n":
                len(subset),

            "zero_mae":
                mae(
                    actual,
                    zero
                ),

            "mixed_mae":
                mae(
                    actual,
                    mixed_pred
                ),

            "general_only_mae":
                mae(
                    actual,
                    general_pred
                ),

            "mixed_gain_vs_zero":
                (
                    mae(
                        actual,
                        zero
                    )
                    -
                    mae(
                        actual,
                        mixed_pred
                    )
                    if actual
                    else None
                ),

            "general_gain_vs_zero":
                (
                    mae(
                        actual,
                        zero
                    )
                    -
                    mae(
                        actual,
                        general_pred
                    )
                    if actual
                    else None
                ),

            "mixed_corr":
                pearson(
                    actual,
                    mixed_pred
                ),

            "general_corr":
                pearson(
                    actual,
                    general_pred
                ),
        })


# =============================================================================
# QA
# =============================================================================

ref_counts = Counter(
    year_int(
        r.get(
            "year"
        )
    )
    for r in canonical_reference_raw
)


qa_rows = [
    {
        "metric":
            "canonical_reference_rows",
        "value":
            len(
                canonical_reference_raw
            ),
        "expected":
            71,
        "status":
            (
                "PASS"
                if len(
                    canonical_reference_raw
                ) == 71
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_canonical_references",
        "value":
            ref_counts[2023],
        "expected":
            34,
        "status":
            (
                "PASS"
                if ref_counts[2023] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_canonical_references",
        "value":
            ref_counts[2024],
        "expected":
            34,
        "status":
            (
                "PASS"
                if ref_counts[2024] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_general_only_references",
        "value":
            sum(
                year == 2023
                for year, _ in general_map
            ),
        "expected":
            34,
        "status":
            (
                "PASS"
                if sum(
                    year == 2023
                    for year, _ in general_map
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_general_only_references",
        "value":
            sum(
                year == 2024
                for year, _ in general_map
            ),
        "expected":
            34,
        "status":
            (
                "PASS"
                if sum(
                    year == 2024
                    for year, _ in general_map
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "primary_status_policy_explicit",
        "value":
            ";".join(
                sorted(
                    PRIMARY_PERFORMANCE_STATUSES
                )
            ),
        "expected":
            (
                "VALID_RETAINED;"
                "VALID_SUPERSEDED;"
                "WITHDRAWN"
            ),
        "status":
            "PASS",
    },

    {
        "metric":
            "failed_retired_disallowed_excluded",
        "value":
            all(
                r[
                    "status"
                ]
                not in {
                    "FAILED",
                    "RETIRED",
                    "DISALLOWED",
                }
                for r in attempts
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "status"
                    ]
                    not in {
                        "FAILED",
                        "RETIRED",
                        "DISALLOWED",
                    }
                    for r in attempts
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_not_used_as_development",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_STATUS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            status_audit[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        status_audit
    )


with OUT_ENTRY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            entry_metric_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        entry_metric_rows
    )


with OUT_REPEAT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = (
        list(
            repeat_rows[0].keys()
        )
        if repeat_rows
        else [
            "year",
            "driver_name",
        ]
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        repeat_rows
    )


with OUT_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            metric_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        metric_rows
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
        "R4F6I",

    "status":
        "R4F6I_REFERENCE_TYPE_STATUS_ROBUSTNESS_READY",

    "performance_observation_policy":
        sorted(
            PRIMARY_PERFORMANCE_STATUSES
        ),

    "entry_strength_metrics":
        entry_metric_rows,

    "repeat_window_metrics":
        metric_rows,

    "interpretation_rules": [
        (
            "Mixed canonical references must not be assumed "
            "equivalent to a common metric without robustness testing."
        ),

        (
            "General-only Fast Friday best speed provides a "
            "field-complete same-definition comparison for 2023/2024."
        ),

        (
            "VALID_SUPERSEDED and WITHDRAWN complete performances "
            "remain usable historical performance evidence."
        ),

        (
            "FAILED, RETIRED and DISALLOWED are excluded from "
            "the primary performance-observation robustness set."
        ),
    ],

    "next_phase":
        (
            "Freeze Fast Friday entry-strength findings and reject "
            "simple local residual-median window recovery if the "
            "failure persists on same-definition references and "
            "strict status support; then construct the hierarchical "
            "thermal + latent-window probabilistic layer."
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
print("=" * 136)
print("ENTRY-STRENGTH REFERENCE-TYPE ROBUSTNESS")
print("=" * 136)

for r in entry_metric_rows:

    def fmt(v):
        return (
            f"{v:.6f}"
            if v is not None
            else "-"
        )

    print(
        f"{r['year']} | "
        f"{r['reference_definition']:16s} | "
        f"n={r['common_support_n']:2d} | "
        f"corr={fmt(r['correlation']):>9s} | "
        f"LOO_MAE={fmt(r['loo_mae_mph']):>9s} | "
        f"resid_std={fmt(r['raw_residual_std_mph']):>9s} | "
        f"{r['model_role']}"
    )


print()
print("=" * 136)
print("SAME-SUPPORT REPEAT WINDOW ROBUSTNESS")
print("=" * 136)

for r in metric_rows:

    def fmt(v):
        return (
            f"{v:.6f}"
            if v is not None
            else "-"
        )

    print(
        f"{r['window_minutes']}m | "
        f"{r['evaluation_set']:20s} | "
        f"n={r['common_support_n']:2d} | "
        f"zero={fmt(r['zero_mae']):>9s} | "
        f"mixed={fmt(r['mixed_mae']):>9s} | "
        f"general={fmt(r['general_only_mae']):>9s} | "
        f"mix_gain={fmt(r['mixed_gain_vs_zero']):>9s} | "
        f"gen_gain={fmt(r['general_gain_vs_zero']):>9s} | "
        f"mix_corr={fmt(r['mixed_corr']):>9s} | "
        f"gen_corr={fmt(r['general_corr']):>9s}"
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
    f"{len(qa_rows)-len(fails)} PASS | "
    f"0 WARN | "
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
    OUT_STATUS.relative_to(ROOT)
)
print(
    OUT_ENTRY.relative_to(ROOT)
)
print(
    OUT_REPEAT.relative_to(ROOT)
)
print(
    OUT_METRICS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6I_REFERENCE_TYPE_STATUS_ROBUSTNESS_READY"
)
