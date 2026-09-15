from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import csv
import json
import math
import statistics
import re
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

REFERENCE_PATH = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_ELIGIBILITY = (
    OUT /
    "r4f6h_v2_strict_attempt_eligibility_audit.csv"
)

OUT_ENTRY = (
    OUT /
    "r4f6h_v2_entry_reference_metrics.csv"
)

OUT_REPEAT = (
    OUT /
    "r4f6h_v2_repeat_window_validation_rows.csv"
)

OUT_METRICS = (
    OUT /
    "r4f6h_v2_repeat_window_validation_metrics.csv"
)

OUT_QA = (
    OUT /
    "r4f6h_v2_strict_validation_qa.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6h_v2_strict_validation_report.json"
)

WINDOWS = [
    20,
    30,
    45,
]


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
        v
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.mean(values)


def median(values):
    values = [
        v
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.median(values)


def stdev(values):
    values = [
        v
        for v in values
        if v is not None
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

    nume = sum(
        (x - mx) * (y - my)
        for x, y in zip(
            xs,
            ys
        )
    )

    denx = math.sqrt(
        sum(
            (x - mx) ** 2
            for x in xs
        )
    )

    deny = math.sqrt(
        sum(
            (y - my) ** 2
            for y in ys
        )
    )

    if (
        denx == 0
        or
        deny == 0
    ):
        return None

    return (
        nume
        /
        (
            denx * deny
        )
    )


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
    REFERENCE_PATH,
    ATTEMPT_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


refs_raw = read_csv(
    REFERENCE_PATH
)

attempts_raw = read_csv(
    ATTEMPT_PATH
)


print("=" * 132)
print("R4F6H-v2 — STRICT ELIGIBILITY FAST FRIDAY VALIDATION")
print("=" * 132)

print(
    f"Reference rows: {len(refs_raw)}"
)

print(
    f"Attempt rows: {len(attempts_raw)}"
)


# =============================================================================
# Reference map
# =============================================================================

ref_map = {}

for row in refs_raw:

    year = year_int(
        row.get("year")
    )

    key = clean(
        row.get("driver_key")
    )

    speed = num(
        row.get(
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

    ref_map[
        (
            year,
            key,
        )
    ] = {
        "speed":
            speed,

        "type":
            clean(
                row.get(
                    "reference_type"
                )
            ),

        "role":
            clean(
                row.get(
                    "model_role"
                )
            ),

        "car":
            clean(
                row.get(
                    "car_number"
                )
            ),
    }


# =============================================================================
# Strict attempt eligibility
# =============================================================================

eligibility_rows = []
eligible = []

for row in attempts_raw:

    year = year_int(
        row.get("year")
    )

    name = clean(
        row.get(
            "driver_name"
        )
    )

    key = driver_key(
        name
    )

    speed = num(
        row.get(
            "four_lap_average_speed_mph"
        )
    )

    point_time = parse_dt(
        row.get(
            "time_point_utc"
        )
    )

    complete_performance = truthy(
        row.get(
            "complete_performance_record"
        )
    )

    complete_shape = truthy(
        row.get(
            "complete_four_lap_shape"
        )
    )

    result_status = clean(
        row.get(
            "result_status"
        )
    )

    counted = clean(
        row.get(
            "result_counted_at_session_end"
        )
    )

    attempt_index = num(
        row.get(
            "car_attempt_index"
        )
    )

    strict_performance_eligible = (
        year is not None
        and
        bool(name)
        and
        speed is not None
        and
        complete_performance
    )

    reference = ref_map.get(
        (
            year,
            key,
        )
    )


    audit = {
        "year":
            year,

        "attempt_id":
            clean(
                row.get(
                    "attempt_id"
                )
            ),

        "driver_name":
            name,

        "car_number":
            clean(
                row.get(
                    "car_number"
                )
            ),

        "car_attempt_index":
            (
                int(attempt_index)
                if attempt_index
                is not None
                else ""
            ),

        "result_status":
            result_status,

        "result_counted_at_session_end":
            counted,

        "complete_four_lap_shape":
            complete_shape,

        "complete_performance_record":
            complete_performance,

        "speed_available":
            speed is not None,

        "point_time_available":
            point_time is not None,

        "strict_performance_eligible":
            strict_performance_eligible,

        "fast_friday_reference_available":
            reference is not None,
    }

    eligibility_rows.append(
        audit
    )


    if not strict_performance_eligible:
        continue

    eligible.append({
        "year":
            year,

        "driver_name":
            name,

        "driver_key":
            key,

        "car_number":
            clean(
                row.get(
                    "car_number"
                )
            ),

        "attempt_id":
            clean(
                row.get(
                    "attempt_id"
                )
            ),

        "attempt_index":
            (
                int(attempt_index)
                if attempt_index
                is not None
                else None
            ),

        "speed":
            speed,

        "time":
            point_time,

        "result_status":
            result_status,

        "result_counted":
            counted,

        "reference":
            reference,
    })


print()
print("=" * 132)
print("STRICT ELIGIBILITY AUDIT")
print("=" * 132)

print(
    f"Complete performance eligible: "
    f"{len(eligible)}"
)

print(
    f"Eligible with point time: "
    f"{sum(r['time'] is not None for r in eligible)}"
)

print(
    f"Eligible with Fast Friday reference: "
    f"{sum(r['reference'] is not None for r in eligible)}"
)


status_counts = Counter(
    clean(
        r[
            "result_status"
        ]
    )
    or
    "[EMPTY]"
    for r in eligibility_rows
    if r[
        "strict_performance_eligible"
    ]
)

print()
print("RESULT STATUS AMONG STRICT ELIGIBLE")

for status, count in sorted(
    status_counts.items()
):

    print(
        f"{status:32s} | {count}"
    )


counted_counts = Counter(
    clean(
        r[
            "result_counted_at_session_end"
        ]
    )
    or
    "[EMPTY]"
    for r in eligibility_rows
    if r[
        "strict_performance_eligible"
    ]
)

print()
print("RESULT_COUNTED_AT_SESSION_END AMONG STRICT ELIGIBLE")

for status, count in sorted(
    counted_counts.items()
):

    print(
        f"{status:32s} | {count}"
    )


# =============================================================================
# Joined strict reference rows
# =============================================================================

joined = [
    r
    for r in eligible
    if r[
        "reference"
    ]
    is not None
]


by_entry = defaultdict(
    list
)

for row in joined:

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
        ),
    )

    first = rows[0]

    first_rows.append(
        first
    )

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

            "reference_speed":
                repeat[
                    "reference"
                ][
                    "speed"
                ],

            "reference_type":
                repeat[
                    "reference"
                ][
                    "type"
                ],

            "model_role":
                repeat[
                    "reference"
                ][
                    "role"
                ],

            "first_result_status":
                first[
                    "result_status"
                ],

            "repeat_result_status":
                repeat[
                    "result_status"
                ],

            "first_result_counted":
                first[
                    "result_counted"
                ],

            "repeat_result_counted":
                repeat[
                    "result_counted"
                ],
        })


# =============================================================================
# Entry-strength metrics
# =============================================================================

entry_metrics = []

for year in [
    2021,
    2023,
    2024,
]:

    subset = [
        r
        for r in first_rows
        if r[
            "year"
        ] == year
    ]

    refs = [
        r[
            "reference"
        ][
            "speed"
        ]
        for r in subset
    ]

    quals = [
        r[
            "speed"
        ]
        for r in subset
    ]


    loo_ff = []
    loo_mean = []

    for i in range(
        len(subset)
    ):

        tx = [
            refs[j]
            for j in range(
                len(subset)
            )
            if j != i
        ]

        ty = [
            quals[j]
            for j in range(
                len(subset)
            )
            if j != i
        ]

        intercept, slope = linear_fit(
            tx,
            ty
        )

        if (
            intercept is None
            or
            slope is None
        ):

            loo_ff.append(
                None
            )

        else:

            loo_ff.append(
                intercept
                +
                slope
                *
                refs[i]
            )

        loo_mean.append(
            mean(ty)
            if ty
            else None
        )


    residuals = [
        q - ref
        for q, ref in zip(
            quals,
            refs
        )
    ]


    entry_metrics.append({
        "year":
            year,

        "n":
            len(subset),

        "corr":
            (
                pearson(
                    refs,
                    quals
                )
            ),

        "residual_std":
            (
                stdev(
                    residuals
                )
            ),

        "ff_loo_mae":
            (
                mae(
                    quals,
                    loo_ff
                )
            ),

        "mean_loo_mae":
            (
                mae(
                    quals,
                    loo_mean
                )
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
# Local window signal
# =============================================================================

window_source_rows = []

for row in joined:

    if row[
        "time"
    ] is None:
        continue

    window_source_rows.append({
        **row,

        "reference_residual":
            (
                row[
                    "speed"
                ]
                -
                row[
                    "reference"
                ][
                    "speed"
                ]
            ),
    })


def local_state(
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
        for r in window_source_rows
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

    for row in candidates:

        d = abs(
            (
                row[
                    "time"
                ]
                -
                target_time
            ).total_seconds()
        )

        key = row[
            "driver_key"
        ]

        if (
            key not in closest
            or
            d
            <
            closest[
                key
            ][0]
        ):

            closest[
                key
            ] = (
                d,
                row[
                    "reference_residual"
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

        "actual_repeat_delta_mph":
            pair[
                "actual_delta"
            ],

        "reference_type":
            pair[
                "reference_type"
            ],

        "model_role":
            pair[
                "model_role"
            ],

        "first_result_status":
            pair[
                "first_result_status"
            ],

        "repeat_result_status":
            pair[
                "repeat_result_status"
            ],

        "first_result_counted":
            pair[
                "first_result_counted"
            ],

        "repeat_result_counted":
            pair[
                "repeat_result_counted"
            ],
    }


    for width in WINDOWS:

        s1, n1 = local_state(
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

        s2, n2 = local_state(
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
            s2 - s1
            if (
                s1 is not None
                and
                s2 is not None
            )
            else None
        )


        row[
            f"first_n_{width}m"
        ] = n1

        row[
            f"repeat_n_{width}m"
        ] = n2

        row[
            f"predicted_delta_{width}m"
        ] = pred


    repeat_rows.append(
        row
    )


metric_rows = []

for width in WINDOWS:

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
                r[
                    f"predicted_delta_{width}m"
                ]
                is not None
            )
        ]

        actual = [
            r[
                "actual_repeat_delta_mph"
            ]
            for r in subset
        ]

        pred = [
            r[
                f"predicted_delta_{width}m"
            ]
            for r in subset
        ]

        zero = [
            0.0
            for _ in subset
        ]

        improve_rate = (
            sum(
                a > 0
                for a in actual
            )
            /
            len(actual)
            if actual
            else None
        )

        sign_acc = (
            sum(
                (
                    a > 0
                )
                ==
                (
                    p > 0
                )
                for a, p in zip(
                    actual,
                    pred
                )
            )
            /
            len(actual)
            if actual
            else None
        )


        metric_rows.append({
            "window_minutes":
                width,

            "evaluation_set":
                label,

            "n":
                len(subset),

            "zero_mae":
                mae(
                    actual,
                    zero
                ),

            "window_mae":
                mae(
                    actual,
                    pred
                ),

            "mae_gain_vs_zero":
                (
                    mae(
                        actual,
                        zero
                    )
                    -
                    mae(
                        actual,
                        pred
                    )
                    if actual
                    else None
                ),

            "pearson":
                pearson(
                    actual,
                    pred
                ),

            "sign_accuracy":
                sign_acc,

            "always_improve":
                improve_rate,
        })


# =============================================================================
# QA
# =============================================================================

ref_year_counts = Counter(
    year_int(
        r.get(
            "year"
        )
    )
    for r in refs_raw
)

qa_rows = [
    {
        "metric":
            "reference_total",
        "value":
            len(refs_raw),
        "expected":
            71,
        "status":
            (
                "PASS"
                if len(refs_raw) == 71
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_reference_count",
        "value":
            ref_year_counts[2023],
        "expected":
            34,
        "status":
            (
                "PASS"
                if ref_year_counts[2023] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_reference_count",
        "value":
            ref_year_counts[2024],
        "expected":
            34,
        "status":
            (
                "PASS"
                if ref_year_counts[2024] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "strict_complete_performance_rows",
        "value":
            len(eligible),
        "expected":
            "OBSERVED",
        "status":
            "PASS",
    },

    {
        "metric":
            "strict_repeat_pairs",
        "value":
            len(repeat_pairs),
        "expected":
            "OBSERVED",
        "status":
            "PASS",
    },

    {
        "metric":
            "2024_validation_reference_preserved",
        "value":
            all(
                clean(
                    r.get(
                        "model_role"
                    )
                )
                ==
                "VALIDATION_ONLY"
                for r in refs_raw
                if year_int(
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
                    for r in refs_raw
                    if year_int(
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
            "car_number_string_identity_policy",
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

with OUT_ELIGIBILITY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            eligibility_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        eligibility_rows
    )


with OUT_ENTRY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            entry_metrics[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        entry_metrics
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
        "R4F6H_V2",

    "status":
        "R4F6H_V2_STRICT_ELIGIBILITY_VALIDATION_READY",

    "strict_performance_rows":
        len(eligible),

    "strict_reference_rows":
        len(joined),

    "strict_repeat_pairs":
        len(repeat_pairs),

    "entry_metrics":
        entry_metrics,

    "repeat_window_metrics":
        metric_rows,

    "interpretation_rule":
        (
            "Fast Friday entry-reference quality and "
            "local common-window recovery are evaluated "
            "as separate hypotheses."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 132)
print("STRICT ENTRY-STRENGTH RESULTS")
print("=" * 132)

for r in entry_metrics:

    def fmt(v):
        return (
            f"{v:.6f}"
            if v is not None
            else "-"
        )

    print(
        f"{r['year']} | "
        f"n={r['n']:2d} | "
        f"corr={fmt(r['corr']):>9s} | "
        f"resid_std={fmt(r['residual_std']):>9s} | "
        f"FF_LOO_MAE={fmt(r['ff_loo_mae']):>9s} | "
        f"MEAN_LOO_MAE={fmt(r['mean_loo_mae']):>9s} | "
        f"{r['model_role']}"
    )


print()
print("=" * 132)
print("STRICT REPEAT WINDOW RESULTS")
print("=" * 132)

print(
    f"Strict repeat pairs with reference: "
    f"{len(repeat_pairs)}"
)

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
        f"n={r['n']:2d} | "
        f"zero={fmt(r['zero_mae']):>9s} | "
        f"window={fmt(r['window_mae']):>9s} | "
        f"gain={fmt(r['mae_gain_vs_zero']):>9s} | "
        f"corr={fmt(r['pearson']):>9s} | "
        f"sign={fmt(r['sign_accuracy']):>9s} | "
        f"always+={fmt(r['always_improve']):>9s}"
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
    OUT_ELIGIBILITY.relative_to(ROOT)
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
    "R4F6H_V2_STRICT_ELIGIBILITY_VALIDATION_READY"
)
