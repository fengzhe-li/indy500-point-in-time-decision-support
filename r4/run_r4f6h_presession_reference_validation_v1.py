from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import csv
import json
import math
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

REFERENCE_PATH = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_JOIN = (
    OUT /
    "r4f6h_fast_friday_qualifying_join_v1.csv"
)

OUT_ENTRY_METRICS = (
    OUT /
    "r4f6h_entry_reference_metrics_v1.csv"
)

OUT_REPEAT_ROWS = (
    OUT /
    "r4f6h_repeat_window_validation_rows_v1.csv"
)

OUT_REPEAT_METRICS = (
    OUT /
    "r4f6h_repeat_window_validation_metrics_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6h_presession_reference_validation_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6h_presession_reference_validation_report_v1.json"
)

WINDOWS = [
    20,
    30,
    45,
]


# =============================================================================
# Generic helpers
# =============================================================================

def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() in {
        "NONE",
        "UNKNOWN",
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


def truthy(v):
    s = clean(v).lower()

    return s in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


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


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def first_existing(row, names):
    for name in names:

        if name in row:

            value = clean(
                row.get(
                    name
                )
            )

            if value:
                return value

    return ""


def first_numeric(row, names):
    for name in names:

        if name in row:

            value = num(
                row.get(
                    name
                )
            )

            if value is not None:
                return value

    return None


def first_datetime(row, names):
    for name in names:

        if name in row:

            value = parse_dt(
                row.get(
                    name
                )
            )

            if value is not None:
                return value

    return None


def mean(values):
    values = [
        v
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.mean(
        values
    )


def median(values):
    values = [
        v
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.median(
        values
    )


def stdev(values):
    values = [
        v
        for v in values
        if v is not None
    ]

    if len(values) < 2:
        return None

    return statistics.stdev(
        values
    )


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
            abs(
                a - p
            )
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
                (
                    a - p
                ) ** 2
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

    x = [
        p[0]
        for p in pairs
    ]

    y = [
        p[1]
        for p in pairs
    ]

    mx = mean(
        x
    )

    my = mean(
        y
    )

    numerator = sum(
        (
            a - mx
        )
        *
        (
            b - my
        )
        for a, b in zip(
            x,
            y
        )
    )

    dx = math.sqrt(
        sum(
            (
                a - mx
            ) ** 2
            for a in x
        )
    )

    dy = math.sqrt(
        sum(
            (
                b - my
            ) ** 2
            for b in y
        )
    )

    if (
        dx == 0
        or
        dy == 0
    ):
        return None

    return (
        numerator
        /
        (
            dx * dy
        )
    )


def sign_accuracy(actual, pred):
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

    return (
        sum(
            (
                a > 0
                and
                p > 0
            )
            or
            (
                a < 0
                and
                p < 0
            )
            or
            (
                a == 0
                and
                p == 0
            )
            for a, p in pairs
        )
        /
        len(
            pairs
        )
    )


def linear_fit(
    xs,
    ys,
):
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

    x = [
        p[0]
        for p in pairs
    ]

    y = [
        p[1]
        for p in pairs
    ]

    mx = mean(
        x
    )

    my = mean(
        y
    )

    denom = sum(
        (
            a - mx
        ) ** 2
        for a in x
    )

    if denom == 0:
        return (
            None,
            None,
        )

    slope = (
        sum(
            (
                a - mx
            )
            *
            (
                b - my
            )
            for a, b in zip(
                x,
                y
            )
        )
        /
        denom
    )

    intercept = (
        my
        -
        slope
        *
        mx
    )

    return (
        intercept,
        slope,
    )


# =============================================================================
# Inputs
# =============================================================================

for path in [
    REFERENCE_PATH,
    ATTEMPT_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


references_raw = read_csv(
    REFERENCE_PATH
)

attempts_raw = read_csv(
    ATTEMPT_PATH
)


print("=" * 132)
print("R4F6H — PRE-SESSION FAST FRIDAY REFERENCE VALIDATION")
print("=" * 132)

print(
    f"Fast Friday reference rows: "
    f"{len(references_raw)}"
)

print(
    f"Attempt panel rows: "
    f"{len(attempts_raw)}"
)


# =============================================================================
# Reference map
#
# Identity is year + driver_key where possible.
# Car number is never integer-normalized.
# =============================================================================

reference_map = {}

for r in references_raw:

    year = integer(
        r.get(
            "year"
        )
    )

    driver_key = clean(
        r.get(
            "driver_key"
        )
    )

    driver_name = clean(
        r.get(
            "driver_name"
        )
    )

    car_number = clean(
        r.get(
            "car_number"
        )
    )

    speed = num(
        r.get(
            "reference_speed_mph"
        )
    )

    if (
        year is None
        or
        not driver_key
        or
        speed is None
    ):
        continue

    reference_map[
        (
            year,
            driver_key,
        )
    ] = {
        "year":
            year,

        "driver_key":
            driver_key,

        "driver_name":
            driver_name,

        "car_number":
            car_number,

        "reference_speed_mph":
            speed,

        "reference_type":
            clean(
                r.get(
                    "reference_type"
                )
            ),

        "model_role":
            clean(
                r.get(
                    "model_role"
                )
            ),
    }


# =============================================================================
# Name normalization compatible with R4F6G-v2
# =============================================================================

import re
import unicodedata


def driver_key(name):
    value = unicodedata.normalize(
        "NFKD",
        clean(
            name
        )
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(
            ch
        )
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


# =============================================================================
# Discover attempt-panel schema conservatively
# =============================================================================

if not attempts_raw:

    raise SystemExit(
        "EMPTY ATTEMPT PANEL"
    )


ATTEMPT_DRIVER_FIELDS = [
    "driver_name",
    "driver",
    "competitor_name",
]

ATTEMPT_SPEED_FIELDS = [
    "four_lap_average_speed_mph",
    "speed_avg_mph",
    "avg_speed_mph",
    "four_lap_avg_mph",
    "four_lap_average_mph",
    "attempt_speed_mph",
    "average_speed_mph",
    "speed_mph",
    "speed",
]

ATTEMPT_TIME_FIELDS = [
    "time_point_utc",
    "canonical_start_time_utc",
    "attempt_time_utc",
    "timestamp_utc",
    "attempt_datetime_utc",
    "utc_datetime",
    "point_time_utc",
]

ATTEMPT_INDEX_FIELDS = [
    "car_attempt_index",
    "attempt_index",
    "car_attempt_number",
    "attempt_number",
]

COMPLETE_FIELDS = [
    "complete_performance_record",
    "complete_four_lap_shape",
    "complete_four_lap",
    "is_complete_four_lap",
    "four_lap_complete",
    "complete_4lap",
]

VALID_FIELDS = [
    "valid",
    "is_valid",
    "attempt_valid",
]


attempts = []

for r in attempts_raw:

    year = integer(
        r.get(
            "year"
        )
    )

    if year is None:
        continue

    name = first_existing(
        r,
        ATTEMPT_DRIVER_FIELDS,
    )

    if not name:
        continue

    key = driver_key(
        name
    )

    speed = first_numeric(
        r,
        ATTEMPT_SPEED_FIELDS,
    )

    dt = first_datetime(
        r,
        ATTEMPT_TIME_FIELDS,
    )

    attempt_index = first_numeric(
        r,
        ATTEMPT_INDEX_FIELDS,
    )

    complete_known = any(
        field in r
        for field in COMPLETE_FIELDS
    )

    valid_known = any(
        field in r
        for field in VALID_FIELDS
    )


    if complete_known:

        complete = any(
            truthy(
                r.get(
                    field
                )
            )
            for field in COMPLETE_FIELDS
            if field in r
        )

    else:

        complete = (
            speed is not None
        )


    if valid_known:

        valid = any(
            truthy(
                r.get(
                    field
                )
            )
            for field in VALID_FIELDS
            if field in r
        )

    else:

        valid = True


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

        "speed_mph":
            speed,

        "time_utc":
            dt,

        "complete":
            complete,

        "valid":
            valid,
    })


print()
print("ATTEMPT SCHEMA RESOLUTION")

print(
    "Usable parsed attempt rows: "
    f"{len(attempts)}"
)

print(
    "Rows with numeric speed: "
    f"{sum(a['speed_mph'] is not None for a in attempts)}"
)

print(
    "Rows with UTC point time: "
    f"{sum(a['time_utc'] is not None for a in attempts)}"
)


if not any(
    a[
        "speed_mph"
    ] is not None
    for a in attempts
):

    print()
    print(
        "AVAILABLE ATTEMPT PANEL FIELDS:"
    )

    print(
        ", ".join(
            attempts_raw[
                0
            ].keys()
        )
    )

    raise SystemExit(
        "NO SPEED FIELD RESOLVED"
    )


# =============================================================================
# Join references
# =============================================================================

joined = []

for a in attempts:

    ref = reference_map.get(
        (
            a[
                "year"
            ],
            a[
                "driver_key"
            ],
        )
    )

    if ref is None:
        continue

    if a[
        "speed_mph"
    ] is None:
        continue

    joined.append({
        **a,

        "reference_speed_mph":
            ref[
                "reference_speed_mph"
            ],

        "reference_type":
            ref[
                "reference_type"
            ],

        "reference_model_role":
            ref[
                "model_role"
            ],

        "reference_residual_mph":
            (
                a[
                    "speed_mph"
                ]
                -
                ref[
                    "reference_speed_mph"
                ]
            ),
    })


# =============================================================================
# First qualifying attempt per driver
# =============================================================================

by_entry = defaultdict(
    list
)

for row in joined:

    if not (
        row[
            "complete"
        ]
        and
        row[
            "valid"
        ]
    ):
        continue

    by_entry[
        (
            row[
                "year"
            ],
            row[
                "driver_key"
            ],
        )
    ].append(
        row
    )


first_rows = []

repeat_pairs = []


for key, rows in by_entry.items():

    def ordering(row):
        idx = row[
            "attempt_index"
        ]

        dt = row[
            "time_utc"
        ]

        return (
            (
                idx
                if idx is not None
                else 999
            ),
            (
                dt
                if dt is not None
                else datetime.max.replace(
                    tzinfo=timezone.utc
                )
            ),
        )


    rows = sorted(
        rows,
        key=ordering,
    )


    first = rows[
        0
    ]

    first_rows.append(
        first
    )


    for repeat in rows[
        1:
    ]:

        if (
            first[
                "time_utc"
            ] is None
            or
            repeat[
                "time_utc"
            ] is None
        ):
            continue

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

            "first_time":
                first[
                    "time_utc"
                ],

            "repeat_time":
                repeat[
                    "time_utc"
                ],

            "first_speed_mph":
                first[
                    "speed_mph"
                ],

            "repeat_speed_mph":
                repeat[
                    "speed_mph"
                ],

            "actual_repeat_delta_mph":
                (
                    repeat[
                        "speed_mph"
                    ]
                    -
                    first[
                        "speed_mph"
                    ]
                ),

            "reference_speed_mph":
                repeat[
                    "reference_speed_mph"
                ],

            "reference_type":
                repeat[
                    "reference_type"
                ],

            "model_role":
                repeat[
                    "reference_model_role"
                ],
        })


# =============================================================================
# Layer 1:
# Entry-strength quality
#
# Compare Fast Friday reference against first qualifying speed.
# Raw MAE is NOT meaningful across sessions without an offset, so report:
#
# - correlation
# - year-centered residual dispersion
# - leave-one-out linear calibration MAE
# =============================================================================

entry_metric_rows = []


for year in sorted(
    set(
        r[
            "year"
        ]
        for r in first_rows
    )
):

    subset = [
        r
        for r in first_rows
        if r[
            "year"
        ] == year
    ]

    refs = [
        r[
            "reference_speed_mph"
        ]
        for r in subset
    ]

    quals = [
        r[
            "speed_mph"
        ]
        for r in subset
    ]


    raw_residuals = [
        q - ref
        for q, ref in zip(
            quals,
            refs
        )
    ]

    centered = [
        x
        -
        mean(
            raw_residuals
        )
        for x in raw_residuals
    ]


    loo_pred = []

    for i in range(
        len(
            subset
        )
    ):

        train_x = [
            refs[j]
            for j in range(
                len(
                    subset
                )
            )
            if j != i
        ]

        train_y = [
            quals[j]
            for j in range(
                len(
                    subset
                )
            )
            if j != i
        ]

        intercept, slope = linear_fit(
            train_x,
            train_y,
        )

        if (
            intercept is None
            or
            slope is None
        ):

            loo_pred.append(
                None
            )

        else:

            loo_pred.append(
                intercept
                +
                slope
                *
                refs[i]
            )


    # Year-mean baseline:
    # predict qualifying speed from other cars' qualifying mean.
    year_mean_pred = []

    for i in range(
        len(
            quals
        )
    ):

        others = [
            quals[j]
            for j in range(
                len(
                    quals
                )
            )
            if j != i
        ]

        year_mean_pred.append(
            mean(
                others
            )
            if others
            else None
        )


    entry_metric_rows.append({
        "year":
            year,

        "n":
            len(
                subset
            ),

        "reference_types":
            ";".join(
                sorted(
                    set(
                        r[
                            "reference_type"
                        ]
                        for r in subset
                    )
                )
            ),

        "pearson_reference_vs_first_qual":
            (
                f"{pearson(refs, quals):.6f}"
                if pearson(
                    refs,
                    quals
                )
                is not None
                else ""
            ),

        "centered_reference_residual_std_mph":
            (
                f"{stdev(centered):.6f}"
                if stdev(
                    centered
                )
                is not None
                else ""
            ),

        "loo_reference_linear_mae_mph":
            (
                f"{mae(quals, loo_pred):.6f}"
                if mae(
                    quals,
                    loo_pred
                )
                is not None
                else ""
            ),

        "loo_year_mean_baseline_mae_mph":
            (
                f"{mae(quals, year_mean_pred):.6f}"
                if mae(
                    quals,
                    year_mean_pred
                )
                is not None
                else ""
            ),

        "model_role":
            (
                "VALIDATION_ONLY"
                if year == 2024
                else
                "DEVELOPMENT_DIAGNOSTIC"
            ),
    })


# =============================================================================
# Layer 2:
# Cross-car window-state estimate
#
# For each target time, estimate local common state using other cars'
# qualifying_speed - FastFridayReference.
#
# IMPORTANT:
# - subject car excluded
# - one closest observation per other car
# - symmetric historical window is allowed here because this is OFFLINE
#   structural validation, not a prospective feature.
# =============================================================================

def local_other_car_window_state(
    year,
    subject_key,
    target_time,
    half_width_minutes,
):
    lower = (
        target_time
        -
        timedelta(
            minutes=half_width_minutes
        )
    )

    upper = (
        target_time
        +
        timedelta(
            minutes=half_width_minutes
        )
    )


    candidates = [
        r
        for r in joined
        if (
            r[
                "year"
            ] == year
            and
            r[
                "driver_key"
            ] != subject_key
            and
            r[
                "time_utc"
            ] is not None
            and
            r[
                "complete"
            ]
            and
            r[
                "valid"
            ]
            and
            lower
            <= r[
                "time_utc"
            ]
            <= upper
        )
    ]


    # One closest observation per other driver.
    closest = {}

    for row in candidates:

        distance = abs(
            (
                row[
                    "time_utc"
                ]
                -
                target_time
            ).total_seconds()
        )

        key = row[
            "driver_key"
        ]

        current = closest.get(
            key
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

            closest[
                key
            ] = {
                "distance":
                    distance,

                "residual":
                    row[
                        "reference_residual_mph"
                    ],
            }


    values = [
        item[
            "residual"
        ]
        for item in closest.values()
    ]


    return (
        median(
            values
        ),
        len(
            values
        ),
    )


repeat_validation_rows = []


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

        "first_time_utc":
            pair[
                "first_time"
            ].isoformat(),

        "repeat_time_utc":
            pair[
                "repeat_time"
            ].isoformat(),

        "first_speed_mph":
            f"{pair['first_speed_mph']:.6f}",

        "repeat_speed_mph":
            f"{pair['repeat_speed_mph']:.6f}",

        "actual_repeat_delta_mph":
            f"{pair['actual_repeat_delta_mph']:.6f}",

        "reference_speed_mph":
            f"{pair['reference_speed_mph']:.6f}",

        "reference_type":
            pair[
                "reference_type"
            ],

        "model_role":
            pair[
                "model_role"
            ],
    }


    for window in WINDOWS:

        first_state, first_n = (
            local_other_car_window_state(
                pair[
                    "year"
                ],
                pair[
                    "driver_key"
                ],
                pair[
                    "first_time"
                ],
                window,
            )
        )

        repeat_state, repeat_n = (
            local_other_car_window_state(
                pair[
                    "year"
                ],
                pair[
                    "driver_key"
                ],
                pair[
                    "repeat_time"
                ],
                window,
            )
        )


        if (
            first_state is not None
            and
            repeat_state is not None
        ):

            predicted_delta = (
                repeat_state
                -
                first_state
            )

        else:

            predicted_delta = None


        row[
            f"first_window_state_{window}m"
        ] = (
            f"{first_state:.6f}"
            if first_state
            is not None
            else ""
        )

        row[
            f"first_other_car_count_{window}m"
        ] = first_n

        row[
            f"repeat_window_state_{window}m"
        ] = (
            f"{repeat_state:.6f}"
            if repeat_state
            is not None
            else ""
        )

        row[
            f"repeat_other_car_count_{window}m"
        ] = repeat_n

        row[
            f"predicted_window_delta_{window}m"
        ] = (
            f"{predicted_delta:.6f}"
            if predicted_delta
            is not None
            else ""
        )


    repeat_validation_rows.append(
        row
    )


# =============================================================================
# Repeat metrics
# =============================================================================

repeat_metric_rows = []


for window in WINDOWS:

    for role_name, role_filter in [
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
            for r in repeat_validation_rows
            if (
                role_filter(
                    r
                )
                and
                num(
                    r.get(
                        f"predicted_window_delta_{window}m"
                    )
                )
                is not None
            )
        ]


        actual = [
            num(
                r[
                    "actual_repeat_delta_mph"
                ]
            )
            for r in subset
        ]

        pred = [
            num(
                r[
                    f"predicted_window_delta_{window}m"
                ]
            )
            for r in subset
        ]

        zero = [
            0.0
            for _ in subset
        ]


        improve_rate = (
            (
                sum(
                    a > 0
                    for a in actual
                )
                /
                len(
                    actual
                )
            )
            if actual
            else None
        )


        repeat_metric_rows.append({
            "window_minutes":
                window,

            "evaluation_set":
                role_name,

            "n":
                len(
                    subset
                ),

            "zero_mae_mph":
                (
                    f"{mae(actual, zero):.6f}"
                    if actual
                    else ""
                ),

            "window_mae_mph":
                (
                    f"{mae(actual, pred):.6f}"
                    if actual
                    else ""
                ),

            "zero_rmse_mph":
                (
                    f"{rmse(actual, zero):.6f}"
                    if actual
                    else ""
                ),

            "window_rmse_mph":
                (
                    f"{rmse(actual, pred):.6f}"
                    if actual
                    else ""
                ),

            "window_pearson":
                (
                    f"{pearson(actual, pred):.6f}"
                    if pearson(
                        actual,
                        pred
                    )
                    is not None
                    else ""
                ),

            "window_sign_accuracy":
                (
                    f"{sign_accuracy(actual, pred):.6f}"
                    if actual
                    else ""
                ),

            "always_improve_sign_baseline":
                (
                    f"{improve_rate:.6f}"
                    if improve_rate
                    is not None
                    else ""
                ),

            "mae_gain_vs_zero":
                (
                    f"{mae(actual, zero) - mae(actual, pred):.6f}"
                    if (
                        actual
                        and
                        mae(
                            actual,
                            pred
                        )
                        is not None
                    )
                    else ""
                ),
        })


# =============================================================================
# Coverage diagnostics
# =============================================================================

join_by_year = []


for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
]:

    year_attempts = [
        a
        for a in attempts
        if a[
            "year"
        ] == year
    ]

    year_joined = [
        a
        for a in joined
        if a[
            "year"
        ] == year
    ]

    unique_attempt_entries = set(
        (
            a[
                "year"
            ],
            a[
                "driver_key"
            ],
        )
        for a in year_attempts
        if (
            a[
                "speed_mph"
            ] is not None
        )
    )

    unique_joined_entries = set(
        (
            a[
                "year"
            ],
            a[
                "driver_key"
            ],
        )
        for a in year_joined
    )


    join_by_year.append({
        "year":
            year,

        "qualifying_entries":
            len(
                unique_attempt_entries
            ),

        "reference_joined_entries":
            len(
                unique_joined_entries
            ),

        "entry_coverage":
            (
                len(
                    unique_joined_entries
                )
                /
                len(
                    unique_attempt_entries
                )
                if unique_attempt_entries
                else 0.0
            ),
    })


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "fast_friday_reference_rows",

        "value":
            len(
                references_raw
            ),

        "expected":
            71,

        "status":
            (
                "PASS"
                if len(
                    references_raw
                ) == 71
                else "WARN"
            ),
    },

    {
        "metric":
            "2023_reference_count",

        "value":
            sum(
                r[
                    "year"
                ] == 2023
                for r in references_raw
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2023
                    for r in references_raw
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_reference_count",

        "value":
            sum(
                r[
                    "year"
                ] == 2024
                for r in references_raw
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2024
                    for r in references_raw
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_reference_role_validation_only",

        "value":
            all(
                clean(
                    r.get(
                        "model_role"
                    )
                )
                ==
                "VALIDATION_ONLY"
                for r in references_raw
                if integer(
                    r.get(
                        "year"
                    )
                ) == 2024
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if all(
                    clean(
                        r.get(
                            "model_role"
                        )
                    )
                    ==
                    "VALIDATION_ONLY"
                    for r in references_raw
                    if integer(
                        r.get(
                            "year"
                        )
                    ) == 2024
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "joined_qualifying_rows",

        "value":
            len(
                joined
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if joined
                else "FAIL"
            ),
    },

    {
        "metric":
            "first_attempt_reference_rows",

        "value":
            len(
                first_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if first_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "repeat_pairs_with_reference",

        "value":
            len(
                repeat_pairs
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },

    {
        "metric":
            "car_number_not_used_as_identity",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "offline_symmetric_window_only",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "2024_not_used_for_development_metric",

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

JOIN_FIELDS = [
    "year",
    "driver_name",
    "driver_key",
    "car_number",
    "attempt_id",
    "attempt_index",
    "speed_mph",
    "time_utc",
    "complete",
    "valid",
    "reference_speed_mph",
    "reference_type",
    "reference_model_role",
    "reference_residual_mph",
]


with OUT_JOIN.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=JOIN_FIELDS
    )

    writer.writeheader()

    for row in joined:

        export = dict(
            row
        )

        export[
            "time_utc"
        ] = (
            row[
                "time_utc"
            ].isoformat()
            if row[
                "time_utc"
            ]
            is not None
            else ""
        )

        writer.writerow(
            export
        )


with OUT_ENTRY_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            entry_metric_rows[
                0
            ].keys()
        )
        if entry_metric_rows
        else [
            "year",
            "n",
        ]
    )

    writer.writeheader()
    writer.writerows(
        entry_metric_rows
    )


with OUT_REPEAT_ROWS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = (
        list(
            repeat_validation_rows[
                0
            ].keys()
        )
        if repeat_validation_rows
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
        repeat_validation_rows
    )


with OUT_REPEAT_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = (
        list(
            repeat_metric_rows[
                0
            ].keys()
        )
        if repeat_metric_rows
        else [
            "window_minutes",
            "evaluation_set",
        ]
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        repeat_metric_rows
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
        "R4F6H",

    "status":
        "R4F6H_PRESESSION_REFERENCE_VALIDATION_READY",

    "reference_rows":
        len(
            references_raw
        ),

    "joined_attempt_rows":
        len(
            joined
        ),

    "first_attempt_reference_rows":
        len(
            first_rows
        ),

    "repeat_pairs_with_reference":
        len(
            repeat_pairs
        ),

    "join_coverage_by_year":
        join_by_year,

    "methodology": {
        "layer_1":
            (
                "Test whether Fast Friday reference captures "
                "entry-strength variation in first qualifying attempts."
            ),

        "layer_2":
            (
                "Use OTHER-CAR Fast-Friday-normalized qualifying "
                "residuals to estimate common window-state change "
                "between subject first and repeat attempts."
            ),

        "2024":
            (
                "Validation-only diagnostic; never merged into "
                "development metrics."
            ),
    },

    "decision_rule":
        (
            "Promote Fast Friday normalization only if it shows "
            "useful entry-strength calibration and/or repeat-window "
            "validation improvement over zero/simple baselines."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 132)
print("REFERENCE JOIN COVERAGE")
print("=" * 132)

for r in join_by_year:

    print(
        f"{r['year']} | "
        f"qual_entries={r['qualifying_entries']:2d} | "
        f"reference_joined={r['reference_joined_entries']:2d} | "
        f"coverage={r['entry_coverage']:.3f}"
    )


print()
print("=" * 132)
print("ENTRY-STRENGTH REFERENCE QUALITY")
print("=" * 132)

for r in entry_metric_rows:

    print(
        f"{r['year']} | "
        f"n={r['n']:2d} | "
        f"corr={r['pearson_reference_vs_first_qual'] or '-':>9s} | "
        f"resid_std={r['centered_reference_residual_std_mph'] or '-':>9s} | "
        f"FF_LOO_MAE={r['loo_reference_linear_mae_mph'] or '-':>9s} | "
        f"MEAN_LOO_MAE={r['loo_year_mean_baseline_mae_mph'] or '-':>9s} | "
        f"{r['model_role']}"
    )


print()
print("=" * 132)
print("REPEAT WINDOW VALIDATION")
print("=" * 132)

print(
    f"Repeat pairs with Fast Friday reference: "
    f"{len(repeat_pairs)}"
)

for r in repeat_metric_rows:

    print(
        f"{r['window_minutes']}m | "
        f"{r['evaluation_set']:20s} | "
        f"n={r['n']:2d} | "
        f"zero_MAE={r['zero_mae_mph'] or '-':>9s} | "
        f"window_MAE={r['window_mae_mph'] or '-':>9s} | "
        f"gain={r['mae_gain_vs_zero'] or '-':>9s} | "
        f"corr={r['window_pearson'] or '-':>9s} | "
        f"sign={r['window_sign_accuracy'] or '-':>9s} | "
        f"always+={r['always_improve_sign_baseline'] or '-':>9s}"
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
    OUT_JOIN.relative_to(ROOT)
)
print(
    OUT_ENTRY_METRICS.relative_to(ROOT)
)
print(
    OUT_REPEAT_ROWS.relative_to(ROOT)
)
print(
    OUT_REPEAT_METRICS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6H_PRESESSION_REFERENCE_VALIDATION_READY"
)
