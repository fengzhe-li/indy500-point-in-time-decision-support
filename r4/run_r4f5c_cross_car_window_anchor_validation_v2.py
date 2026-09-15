from pathlib import Path
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

INPUT = (
    OUT /
    "r4f5c_cross_car_window_anchor_validation_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f5c_cross_car_window_anchor_metrics_v2.csv"
)

OUT_YEAR = (
    OUT /
    "r4f5c_cross_car_window_anchor_year_metrics_v2.csv"
)

OUT_QA = (
    OUT /
    "r4f5c_cross_car_window_anchor_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4f5c_cross_car_window_anchor_report_v2.json"
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


def integer(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def mae(actual, pred):
    if not actual:
        return None

    return statistics.mean(
        abs(a - p)
        for a, p in zip(
            actual,
            pred
        )
    )


def rmse(actual, pred):
    if not actual:
        return None

    return math.sqrt(
        statistics.mean(
            (a - p) ** 2
            for a, p in zip(
                actual,
                pred
            )
        )
    )


def corr(actual, pred):
    if len(actual) < 3:
        return None

    ma = statistics.mean(
        actual
    )

    mp = statistics.mean(
        pred
    )

    numerator = sum(
        (a - ma)
        *
        (p - mp)
        for a, p in zip(
            actual,
            pred
        )
    )

    da = math.sqrt(
        sum(
            (a - ma) ** 2
            for a in actual
        )
    )

    dp = math.sqrt(
        sum(
            (p - mp) ** 2
            for p in pred
        )
    )

    if (
        da == 0
        or
        dp == 0
    ):
        return None

    return numerator / (
        da * dp
    )


def sign_accuracy(actual, pred):
    if not actual:
        return None

    correct = 0

    for a, p in zip(
        actual,
        pred
    ):

        if (
            a > 0
            and
            p > 0
        ):
            correct += 1

        elif (
            a < 0
            and
            p < 0
        ):
            correct += 1

        elif (
            a == 0
            and
            p == 0
        ):
            correct += 1

    return correct / len(
        actual
    )


if not INPUT.exists():
    raise SystemExit(
        f"MISSING INPUT: {INPUT}"
    )


rows = read_csv(
    INPUT
)


print("=" * 126)
print("R4F5C-v2 — FAIR CROSS-CAR WINDOW VALIDATION")
print("=" * 126)

print(
    f"Validation rows: {len(rows)}"
)


# =============================================================================
# Parse canonical targets
# =============================================================================

parsed = []

for r in rows:

    actual = num(
        r.get(
            "actual_repeat_residual_mph"
        )
    )

    year = integer(
        r.get(
            "year"
        )
    )

    if (
        actual is None
        or
        year is None
    ):
        continue

    parsed.append({
        "year":
            year,

        "actual":
            actual,

        "row":
            r,
    })


global_positive_rate = (
    sum(
        r[
            "actual"
        ] > 0
        for r in parsed
    )
    /
    len(
        parsed
    )
)


print()
print("=" * 126)
print("TARGET BASE RATE")
print("=" * 126)

print(
    f"Targets: {len(parsed)}"
)

print(
    f"Observed improve rate: "
    f"{global_positive_rate:.6f}"
)

print(
    f"ALWAYS_IMPROVE sign baseline: "
    f"{global_positive_rate:.6f}"
)


# =============================================================================
# Leave-one-out baseline helpers
# =============================================================================

def global_loo_mean(index):
    values = [
        r[
            "actual"
        ]
        for j, r in enumerate(
            parsed
        )
        if j != index
    ]

    if not values:
        return None

    return statistics.mean(
        values
    )


def year_loo_mean(index):
    target_year = parsed[
        index
    ][
        "year"
    ]

    values = [
        r[
            "actual"
        ]
        for j, r in enumerate(
            parsed
        )
        if (
            j != index
            and
            r[
                "year"
            ]
            == target_year
        )
    ]

    if not values:
        return None

    return statistics.mean(
        values
    )


# =============================================================================
# Fair common-support evaluation
# =============================================================================

metric_rows = []

for window in WINDOWS:

    support = []

    for i, item in enumerate(
        parsed
    ):

        pooled = num(
            item[
                "row"
            ].get(
                f"pooled_cross_car_signal_{window}m"
            )
        )

        if pooled is None:
            continue

        first_only = num(
            item[
                "row"
            ].get(
                f"first_only_signal_{window}m"
            )
        )

        support.append({
            "index":
                i,

            "year":
                item[
                    "year"
                ],

            "actual":
                item[
                    "actual"
                ],

            "pooled":
                pooled,

            "first_only":
                first_only,

            "global_loo_mean":
                global_loo_mean(
                    i
                ),

            "year_loo_mean":
                year_loo_mean(
                    i
                ),
        })


    actual = [
        r[
            "actual"
        ]
        for r in support
    ]


    models = {
        "ZERO_COMMON_SUPPORT":
            [
                0.0
                for _ in support
            ],

        "GLOBAL_LOO_MEAN":
            [
                r[
                    "global_loo_mean"
                ]
                for r in support
            ],

        "YEAR_LOO_MEAN":
            [
                r[
                    "year_loo_mean"
                ]
                for r in support
            ],

        "CROSS_CAR_POOLED":
            [
                r[
                    "pooled"
                ]
                for r in support
            ],
    }


    for model_name, pred_raw in models.items():

        common_pairs = [
            (
                a,
                p
            )
            for a, p in zip(
                actual,
                pred_raw
            )
            if p is not None
        ]

        y = [
            a
            for a, _ in common_pairs
        ]

        p = [
            pred
            for _, pred in common_pairs
        ]


        metric_rows.append({
            "window_minutes":
                window,

            "model":
                model_name,

            "n":
                len(
                    y
                ),

            "mae_mph":
                (
                    f"{mae(y, p):.6f}"
                    if y
                    else ""
                ),

            "rmse_mph":
                (
                    f"{rmse(y, p):.6f}"
                    if y
                    else ""
                ),

            "pearson":
                (
                    f"{corr(y, p):.6f}"
                    if corr(
                        y,
                        p
                    )
                    is not None
                    else ""
                ),

            "sign_accuracy":
                (
                    f"{sign_accuracy(y, p):.6f}"
                    if y
                    else ""
                ),
        })


    # First-run-only has different support and is therefore reported
    # separately rather than compared as if n were identical.
    first_pairs = [
        (
            r[
                "actual"
            ],
            r[
                "first_only"
            ]
        )
        for r in support
        if r[
            "first_only"
        ]
        is not None
    ]

    y_first = [
        a
        for a, _ in first_pairs
    ]

    p_first = [
        p
        for _, p in first_pairs
    ]


    metric_rows.append({
        "window_minutes":
            window,

        "model":
            "FIRST_RUN_ONLY_DIAGNOSTIC",

        "n":
            len(
                y_first
            ),

        "mae_mph":
            (
                f"{mae(y_first, p_first):.6f}"
                if y_first
                else ""
            ),

        "rmse_mph":
            (
                f"{rmse(y_first, p_first):.6f}"
                if y_first
                else ""
            ),

        "pearson":
            (
                f"{corr(y_first, p_first):.6f}"
                if corr(
                    y_first,
                    p_first
                )
                is not None
                else ""
            ),

        "sign_accuracy":
            (
                f"{sign_accuracy(y_first, p_first):.6f}"
                if y_first
                else ""
            ),
    })


# =============================================================================
# Direction baseline on same support
# =============================================================================

direction_rows = []

for window in WINDOWS:

    available = [
        item
        for item in parsed
        if num(
            item[
                "row"
            ].get(
                f"pooled_cross_car_signal_{window}m"
            )
        )
        is not None
    ]


    actual_positive = [
        item[
            "actual"
        ] > 0
        for item in available
    ]

    pooled_positive = [
        num(
            item[
                "row"
            ].get(
                f"pooled_cross_car_signal_{window}m"
            )
        ) > 0
        for item in available
    ]


    always_improve_accuracy = (
        sum(
            actual_positive
        )
        /
        len(
            actual_positive
        )
        if actual_positive
        else None
    )


    pooled_accuracy = (
        sum(
            a == p
            for a, p in zip(
                actual_positive,
                pooled_positive
            )
        )
        /
        len(
            actual_positive
        )
        if actual_positive
        else None
    )


    direction_rows.append({
        "window_minutes":
            window,

        "n":
            len(
                available
            ),

        "actual_improve_rate":
            (
                f"{always_improve_accuracy:.6f}"
                if always_improve_accuracy
                is not None
                else ""
            ),

        "always_improve_accuracy":
            (
                f"{always_improve_accuracy:.6f}"
                if always_improve_accuracy
                is not None
                else ""
            ),

        "cross_car_direction_accuracy":
            (
                f"{pooled_accuracy:.6f}"
                if pooled_accuracy
                is not None
                else ""
            ),

        "direction_accuracy_gain":
            (
                f"{pooled_accuracy - always_improve_accuracy:.6f}"
                if (
                    pooled_accuracy
                    is not None
                    and
                    always_improve_accuracy
                    is not None
                )
                else ""
            ),
    })


# =============================================================================
# By-year diagnostic for 30m
# =============================================================================

year_metrics = []

for year in sorted(
    {
        r[
            "year"
        ]
        for r in parsed
    }
):

    subset = [
        r
        for r in parsed
        if (
            r[
                "year"
            ] == year
            and
            num(
                r[
                    "row"
                ].get(
                    "pooled_cross_car_signal_30m"
                )
            )
            is not None
        )
    ]

    actual = [
        r[
            "actual"
        ]
        for r in subset
    ]

    pooled = [
        num(
            r[
                "row"
            ].get(
                "pooled_cross_car_signal_30m"
            )
        )
        for r in subset
    ]

    zero = [
        0.0
        for _ in subset
    ]


    if actual:

        improve_rate = (
            sum(
                a > 0
                for a in actual
            )
            /
            len(
                actual
            )
        )

        pooled_direction = (
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
                    pooled
                )
            )
            /
            len(
                actual
            )
        )

    else:

        improve_rate = None
        pooled_direction = None


    year_metrics.append({
        "year":
            year,

        "n":
            len(
                actual
            ),

        "zero_mae":
            (
                f"{mae(actual, zero):.6f}"
                if actual
                else ""
            ),

        "pooled_mae":
            (
                f"{mae(actual, pooled):.6f}"
                if actual
                else ""
            ),

        "pooled_corr":
            (
                f"{corr(actual, pooled):.6f}"
                if corr(
                    actual,
                    pooled
                )
                is not None
                else ""
            ),

        "actual_improve_rate":
            (
                f"{improve_rate:.6f}"
                if improve_rate
                is not None
                else ""
            ),

        "pooled_direction_accuracy":
            (
                f"{pooled_direction:.6f}"
                if pooled_direction
                is not None
                else ""
            ),
    })


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "validation_targets",

        "value":
            len(
                parsed
            ),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(
                    parsed
                ) == 40
                else "WARN"
            ),
    },

    {
        "metric":
            "fair_metric_rows",

        "value":
            len(
                metric_rows
            ),

        "expected":
            15,

        "status":
            (
                "PASS"
                if len(
                    metric_rows
                ) == 15
                else "FAIL"
            ),
    },

    {
        "metric":
            "direction_rows",

        "value":
            len(
                direction_rows
            ),

        "expected":
            3,

        "status":
            (
                "PASS"
                if len(
                    direction_rows
                ) == 3
                else "FAIL"
            ),
    },

    {
        "metric":
            "global_positive_rate_valid",

        "value":
            f"{global_positive_rate:.6f}",

        "expected":
            "0_to_1",

        "status":
            (
                "PASS"
                if 0.0
                <= global_positive_rate
                <= 1.0
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

all_metric_rows = []

for r in metric_rows:

    x = dict(
        r
    )

    x[
        "metric_type"
    ] = (
        "MAGNITUDE"
    )

    all_metric_rows.append(
        x
    )


for r in direction_rows:

    all_metric_rows.append({
        "window_minutes":
            r[
                "window_minutes"
            ],

        "model":
            "DIRECTION_BASELINE_AUDIT",

        "n":
            r[
                "n"
            ],

        "mae_mph":
            "",

        "rmse_mph":
            "",

        "pearson":
            "",

        "sign_accuracy":
            r[
                "cross_car_direction_accuracy"
            ],

        "metric_type":
            (
                "DIRECTION | "
                f"base={r['always_improve_accuracy']} | "
                f"gain={r['direction_accuracy_gain']}"
            ),
    })


with OUT_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            all_metric_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        all_metric_rows
    )


with OUT_YEAR.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            year_metrics[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        year_metrics
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
        "R4F5C_V2",

    "status":
        "R4F5C_V2_FAIR_BASELINE_VALIDATION_READY",

    "target_count":
        len(
            parsed
        ),

    "global_repeat_improve_rate":
        global_positive_rate,

    "evaluation_corrections": [
        (
            "Magnitude models are compared on identical "
            "cross-car-prediction support."
        ),

        (
            "Direction accuracy is compared against an "
            "ALWAYS_IMPROVE base-rate baseline rather than "
            "a zero-valued prediction."
        ),

        (
            "Leave-one-out global and year-specific mean "
            "repeat baselines are included."
        ),
    ],

    "decision_rule":
        (
            "Do not promote the current cross-car field-median "
            "normalization into the main model unless it adds "
            "material predictive value over fair baselines."
        ),

    "next_phase_if_weak":
        (
            "Build stronger pre-session hierarchical entry "
            "references using Fast Friday first, then Indy / "
            "same-technical-regime oval evidence where appropriate."
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
print("=" * 126)
print("FAIR COMMON-SUPPORT MAGNITUDE METRICS")
print("=" * 126)

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
            f"{r['model']:30s} | "
            f"n={r['n']:2d} | "
            f"MAE={r['mae_mph'] or '-':>9s} | "
            f"RMSE={r['rmse_mph'] or '-':>9s} | "
            f"corr={r['pearson'] or '-':>9s} | "
            f"sign={r['sign_accuracy'] or '-':>9s}"
        )


print()
print("=" * 126)
print("DIRECTION BASE-RATE AUDIT")
print("=" * 126)

for r in direction_rows:

    print(
        f"{r['window_minutes']}m | "
        f"n={r['n']:2d} | "
        f"improve_rate="
        f"{r['actual_improve_rate']} | "
        f"always_improve="
        f"{r['always_improve_accuracy']} | "
        f"cross_car="
        f"{r['cross_car_direction_accuracy']} | "
        f"gain="
        f"{r['direction_accuracy_gain']}"
    )


print()
print("=" * 126)
print("30M YEAR DIAGNOSTIC")
print("=" * 126)

for r in year_metrics:

    print(
        f"{r['year']} | "
        f"n={r['n']:2d} | "
        f"zero_MAE={r['zero_mae'] or '-'} | "
        f"pooled_MAE={r['pooled_mae'] or '-'} | "
        f"corr={r['pooled_corr'] or '-'} | "
        f"improve_base={r['actual_improve_rate'] or '-'} | "
        f"direction={r['pooled_direction_accuracy'] or '-'}"
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
    OUT_METRICS.relative_to(ROOT)
)
print(
    OUT_YEAR.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F5C_V2_FAIR_BASELINE_VALIDATION_READY"
)
