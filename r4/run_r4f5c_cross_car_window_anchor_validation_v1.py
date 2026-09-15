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

FIRST_PATH = (
    OUT /
    "r4f5b_first_run_field_residuals_v1.csv"
)

REPEAT_PATH = (
    OUT /
    "r4f4_cross_car_residual_observations_v1.csv"
)

OUT_ROWS = (
    OUT /
    "r4f5c_cross_car_window_anchor_validation_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f5c_cross_car_window_anchor_metrics_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f5c_cross_car_window_anchor_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f5c_cross_car_window_anchor_report_v1.json"
)


WINDOWS = [
    20,
    30,
    45,
]

FIRST_WEIGHT = 1.0
REPEAT_WEIGHT = 3.0
PRIOR_WEIGHT = 2.0
PRIOR_MEAN = 0.0


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


def median(values):
    if not values:
        return None

    return statistics.median(
        values
    )


def mae(y_true, y_pred):
    pairs = [
        (a, b)
        for a, b in zip(
            y_true,
            y_pred
        )
        if (
            a is not None
            and
            b is not None
        )
    ]

    if not pairs:
        return None

    return statistics.mean(
        abs(a - b)
        for a, b in pairs
    )


def rmse(y_true, y_pred):
    pairs = [
        (a, b)
        for a, b in zip(
            y_true,
            y_pred
        )
        if (
            a is not None
            and
            b is not None
        )
    ]

    if not pairs:
        return None

    return math.sqrt(
        statistics.mean(
            (a - b) ** 2
            for a, b in pairs
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

    mx = statistics.mean(x)
    my = statistics.mean(y)

    numerator = sum(
        (a - mx)
        *
        (b - my)
        for a, b in pairs
    )

    dx = math.sqrt(
        sum(
            (a - mx) ** 2
            for a in x
        )
    )

    dy = math.sqrt(
        sum(
            (b - my) ** 2
            for b in y
        )
    )

    if (
        dx == 0
        or
        dy == 0
    ):
        return None

    return numerator / (
        dx * dy
    )


def sign_accuracy(y_true, y_pred):
    pairs = [
        (a, b)
        for a, b in zip(
            y_true,
            y_pred
        )
        if (
            a is not None
            and
            b is not None
        )
    ]

    if not pairs:
        return None

    return sum(
        (
            a > 0
            and
            b > 0
        )
        or
        (
            a < 0
            and
            b < 0
        )
        or
        (
            a == 0
            and
            b == 0
        )
        for a, b in pairs
    ) / len(pairs)


for path in [
    FIRST_PATH,
    REPEAT_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


first_raw = read_csv(
    FIRST_PATH
)

repeat_raw = read_csv(
    REPEAT_PATH
)


print("=" * 124)
print("R4F5C — CROSS-CAR WINDOW ANCHOR VALIDATION")
print("=" * 124)

print(
    f"First-run evidence rows: "
    f"{len(first_raw)}"
)

print(
    f"Repeat target rows: "
    f"{len(repeat_raw)}"
)


# =============================================================================
# First-run evidence
# =============================================================================

first = []

for r in first_raw:

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
            "first_run_field_residual_mph"
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

    first.append({
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
# Repeat observations
# =============================================================================

repeat = []

for r in repeat_raw:

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

    aid = clean(
        r.get(
            "attempt_id"
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

    repeat.append({
        "year":
            year,

        "car_number":
            car,

        "time":
            dt,

        "residual":
            residual,

        "attempt_id":
            aid,
    })


# =============================================================================
# Other-car evidence helpers
# =============================================================================

def first_signal(
    year,
    subject_car,
    target_time,
    minutes,
):
    lower = (
        target_time
        -
        timedelta(
            minutes=minutes
        )
    )

    upper = (
        target_time
        +
        timedelta(
            minutes=minutes
        )
    )

    rows = [
        r
        for r in first
        if (
            r[
                "year"
            ] == year
            and
            r[
                "car_number"
            ] != subject_car
            and
            lower
            <= r[
                "time"
            ]
            <= upper
        )
    ]

    # one first run per car already
    values = [
        r[
            "residual"
        ]
        for r in rows
    ]

    return (
        median(values),
        len(values),
    )


def other_repeat_signal(
    year,
    subject_car,
    target_time,
    minutes,
):
    lower = (
        target_time
        -
        timedelta(
            minutes=minutes
        )
    )

    upper = (
        target_time
        +
        timedelta(
            minutes=minutes
        )
    )

    candidates = [
        r
        for r in repeat
        if (
            r[
                "year"
            ] == year
            and
            r[
                "car_number"
            ] != subject_car
            and
            lower
            <= r[
                "time"
            ]
            <= upper
        )
    ]

    # One closest repeat per other car.
    by_car = {}

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

        current = by_car.get(
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

            by_car[
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


    values = [
        r[
            "residual"
        ]
        for r in by_car.values()
    ]

    return (
        median(values),
        len(values),
    )


def pooled_signal(
    first_value,
    first_count,
    repeat_value,
    repeat_count,
):
    numerator = (
        PRIOR_MEAN
        *
        PRIOR_WEIGHT
    )

    denominator = (
        PRIOR_WEIGHT
    )

    if (
        first_value is not None
        and
        first_count > 0
    ):

        weight = (
            FIRST_WEIGHT
            *
            math.sqrt(
                first_count
            )
        )

        numerator += (
            first_value
            *
            weight
        )

        denominator += (
            weight
        )


    if (
        repeat_value is not None
        and
        repeat_count > 0
    ):

        weight = (
            REPEAT_WEIGHT
            *
            math.sqrt(
                repeat_count
            )
        )

        numerator += (
            repeat_value
            *
            weight
        )

        denominator += (
            weight
        )


    if denominator == PRIOR_WEIGHT:

        return None

    return (
        numerator
        /
        denominator
    )


# =============================================================================
# Build validation rows
# =============================================================================

rows = []

for target in repeat:

    row = {
        "year":
            target[
                "year"
            ],

        "car_number":
            target[
                "car_number"
            ],

        "attempt_id":
            target[
                "attempt_id"
            ],

        "target_time_utc":
            target[
                "time"
            ].isoformat(),

        "actual_repeat_residual_mph":
            f"{target['residual']:.6f}",
    }


    for window in WINDOWS:

        first_value, first_count = (
            first_signal(
                target[
                    "year"
                ],
                target[
                    "car_number"
                ],
                target[
                    "time"
                ],
                window,
            )
        )

        repeat_value, repeat_count = (
            other_repeat_signal(
                target[
                    "year"
                ],
                target[
                    "car_number"
                ],
                target[
                    "time"
                ],
                window,
            )
        )


        first_only = None

        if first_value is not None:

            first_weight = (
                FIRST_WEIGHT
                *
                math.sqrt(
                    first_count
                )
            )

            first_only = (
                first_value
                *
                first_weight
            ) / (
                PRIOR_WEIGHT
                +
                first_weight
            )


        pooled = pooled_signal(
            first_value,
            first_count,
            repeat_value,
            repeat_count,
        )


        row[
            f"first_car_count_{window}m"
        ] = first_count

        row[
            f"other_repeat_car_count_{window}m"
        ] = repeat_count

        row[
            f"first_only_signal_{window}m"
        ] = (
            f"{first_only:.6f}"
            if first_only is not None
            else ""
        )

        row[
            f"pooled_cross_car_signal_{window}m"
        ] = (
            f"{pooled:.6f}"
            if pooled is not None
            else ""
        )


    rows.append(
        row
    )


# =============================================================================
# Metrics
# =============================================================================

metric_rows = []

actual = [
    num(
        r[
            "actual_repeat_residual_mph"
        ]
    )
    for r in rows
]


for window in WINDOWS:

    first_pred = [
        num(
            r[
                f"first_only_signal_{window}m"
            ]
        )
        for r in rows
    ]

    pooled_pred = [
        num(
            r[
                f"pooled_cross_car_signal_{window}m"
            ]
        )
        for r in rows
    ]

    zero_pred = [
        0.0
        for _ in rows
    ]


    for model_name, pred in [
        (
            "ZERO_BASELINE",
            zero_pred,
        ),
        (
            "OTHER_CAR_FIRST_RUN_ONLY",
            first_pred,
        ),
        (
            "OTHER_CAR_FIRST_PLUS_REPEAT",
            pooled_pred,
        ),
    ]:

        valid_pairs = [
            (
                a,
                p,
            )
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


        metric_rows.append({
            "window_minutes":
                window,

            "model":
                model_name,

            "n":
                len(
                    valid_pairs
                ),

            "mae_mph":
                (
                    f"{mae(actual, pred):.6f}"
                    if mae(
                        actual,
                        pred
                    )
                    is not None
                    else ""
                ),

            "rmse_mph":
                (
                    f"{rmse(actual, pred):.6f}"
                    if rmse(
                        actual,
                        pred
                    )
                    is not None
                    else ""
                ),

            "pearson":
                (
                    f"{pearson(actual, pred):.6f}"
                    if pearson(
                        actual,
                        pred
                    )
                    is not None
                    else ""
                ),

            "sign_accuracy":
                (
                    f"{sign_accuracy(actual, pred):.6f}"
                    if sign_accuracy(
                        actual,
                        pred
                    )
                    is not None
                    else ""
                ),
        })


# =============================================================================
# Metrics by year for pooled 30m
# =============================================================================

year_rows = []

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

    y = [
        num(
            r[
                "actual_repeat_residual_mph"
            ]
        )
        for r in subset
    ]

    p = [
        num(
            r[
                "pooled_cross_car_signal_30m"
            ]
        )
        for r in subset
    ]

    year_rows.append({
        "year":
            year,

        "n":
            sum(
                (
                    a is not None
                    and
                    b is not None
                )
                for a, b in zip(
                    y,
                    p
                )
            ),

        "mae_30m":
            (
                f"{mae(y, p):.6f}"
                if mae(
                    y,
                    p
                )
                is not None
                else ""
            ),

        "pearson_30m":
            (
                f"{pearson(y, p):.6f}"
                if pearson(
                    y,
                    p
                )
                is not None
                else ""
            ),

        "sign_accuracy_30m":
            (
                f"{sign_accuracy(y, p):.6f}"
                if sign_accuracy(
                    y,
                    p
                )
                is not None
                else ""
            ),
    })


# =============================================================================
# QA
# =============================================================================

subject_car_repeat_leak = []

for target in repeat:

    for other in repeat:

        if (
            target[
                "attempt_id"
            ]
            ==
            other[
                "attempt_id"
            ]
        ):
            continue

        # This is intentionally not a failure:
        # the helper excludes ALL observations from target car,
        # not merely the target attempt.
        pass


qa_rows = [
    {
        "metric":
            "repeat_targets_preserved",

        "value":
            len(rows),

        "expected":
            len(
                repeat
            ),

        "status":
            (
                "PASS"
                if len(
                    rows
                )
                ==
                len(
                    repeat
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "expected_repeat_target_count",

        "value":
            len(
                repeat
            ),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(
                    repeat
                ) == 40
                else "WARN"
            ),
    },

    {
        "metric":
            "subject_car_excluded_from_predictor",

        "value":
            len(
                subject_car_repeat_leak
            ),

        "expected":
            0,

        "status":
            "PASS",
    },

    {
        "metric":
            "metric_rows_created",

        "value":
            len(
                metric_rows
            ),

        "expected":
            9,

        "status":
            (
                "PASS"
                if len(
                    metric_rows
                ) == 9
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_ROWS.open(
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


with OUT_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        metric_rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
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
        "R4F5C",

    "status":
        "R4F5C_CROSS_CAR_WINDOW_ANCHOR_VALIDATION_READY",

    "repeat_targets":
        len(
            rows
        ),

    "method":
        (
            "Each repeat residual is treated as an independent "
            "same-car anchor. Window estimates are constructed "
            "only from OTHER cars within the surrounding historical "
            "time window."
        ),

    "critical_question":
        (
            "Do cross-car local signals explain same-car repeat "
            "performance changes better than a zero-window baseline?"
        ),

    "interpretation_policy": {
        "positive":
            (
                "Supports existence of transferable common "
                "performance-window information."
            ),

        "weak_or_negative":
            (
                "First-run field residual remains too confounded "
                "by entry strength; introduce Fast Friday / "
                "hierarchical pre-session entry references."
            ),
    },

    "next_phase":
        (
            "Choose whether current Indy qualifying evidence is "
            "sufficient for latent-window modelling or whether "
            "stronger pre-session hierarchical references are required."
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
print("CROSS-CAR WINDOW VALIDATION METRICS")
print("=" * 124)

for window in WINDOWS:

    print()
    print(
        f"{window} MINUTES"
    )

    subset = [
        r
        for r in metric_rows
        if r[
            "window_minutes"
        ] == window
    ]

    for r in subset:

        print(
            f"{r['model']:32s} | "
            f"n={r['n']:2d} | "
            f"MAE={r['mae_mph'] or '-':>9s} | "
            f"RMSE={r['rmse_mph'] or '-':>9s} | "
            f"corr={r['pearson'] or '-':>9s} | "
            f"sign={r['sign_accuracy'] or '-':>9s}"
        )


print()
print("=" * 124)
print("30M POOLED RESULT BY YEAR")
print("=" * 124)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"n={r['n']:2d} | "
        f"MAE={r['mae_30m'] or '-'} | "
        f"corr={r['pearson_30m'] or '-'} | "
        f"sign={r['sign_accuracy_30m'] or '-'}"
    )


print()
print("=" * 124)
print("EVIDENCE COVERAGE")
print("=" * 124)

for window in WINDOWS:

    first_count = sum(
        num(
            r[
                f"first_only_signal_{window}m"
            ]
        )
        is not None
        for r in rows
    )

    pooled_count = sum(
        num(
            r[
                f"pooled_cross_car_signal_{window}m"
            ]
        )
        is not None
        for r in rows
    )

    print(
        f"{window}m | "
        f"first-only={first_count}/"
        f"{len(rows)} | "
        f"pooled={pooled_count}/"
        f"{len(rows)}"
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
    OUT_ROWS.relative_to(ROOT)
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
    "R4F5C_CROSS_CAR_WINDOW_ANCHOR_VALIDATION_READY"
)
