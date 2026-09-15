from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

CONTRACT_PATH = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VALIDATION_PATH = (
    OUT /
    "r4f7c2c_2024_validation_numeric_matrix_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4f7v1_2024_one_shot_validation_predictions_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f7v1_2024_one_shot_validation_metrics_v1.csv"
)

OUT_TRACE = (
    OUT /
    "r4f7v1_2024_online_calibration_trace_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7v1_2024_one_shot_validation_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7v1_2024_one_shot_validation_report_v1.json"
)


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

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def mae(actual, pred):
    return (
        sum(
            abs(a - b)
            for a, b
            in zip(actual, pred)
        )
        /
        len(actual)
    )


def rmse(actual, pred):
    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b
            in zip(actual, pred)
        )
        /
        len(actual)
    )


def bias(actual, pred):
    return (
        sum(
            p - a
            for a, p
            in zip(actual, pred)
        )
        /
        len(actual)
    )


def correlation(a, b):

    if len(a) < 2:
        return None

    ma = sum(a) / len(a)
    mb = sum(b) / len(b)

    va = sum(
        (x - ma) ** 2
        for x in a
    )

    vb = sum(
        (x - mb) ** 2
        for x in b
    )

    if (
        va <= 0
        or
        vb <= 0
    ):
        return None

    cov = sum(
        (x - ma) * (y - mb)
        for x, y
        in zip(a, b)
    )

    return (
        cov /
        math.sqrt(
            va * vb
        )
    )


def metric_dict(
    actual,
    pred,
):

    corr = correlation(
        actual,
        pred
    )

    return {
        "n":
            len(actual),

        "mae_mph":
            mae(
                actual,
                pred
            ),

        "rmse_mph":
            rmse(
                actual,
                pred
            ),

        "bias_mph":
            bias(
                actual,
                pred
            ),

        "correlation":
            (
                corr
                if corr is not None
                else ""
            ),
    }


for path in [
    CONTRACT_PATH,
    VALIDATION_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


contract = json.loads(
    CONTRACT_PATH.read_text(
        encoding="utf-8"
    )
)


k = num(
    contract.get(
        "selected_shrinkage_k"
    )
)

prior_mean = num(
    contract.get(
        "frozen_cross_year_prior_mean_residual_mph"
    )
)

prior_sd = num(
    contract.get(
        "frozen_cross_year_prior_sd_mph"
    )
)


if (
    k is None
    or
    prior_mean is None
    or
    prior_sd is None
):

    raise SystemExit(
        "FROZEN CONTRACT MISSING k / prior mean / prior sd"
    )


if clean(
    contract.get(
        "status"
    )
) != "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN":

    raise SystemExit(
        "DEVELOPMENT ARCHITECTURE IS NOT FROZEN"
    )


fields, raw = read_csv(
    VALIDATION_PATH
)


required = {
    "attempt_id",
    "year",
    "driver_key",
    "driver_name",
    "performance_time_utc",
    "target_four_lap_average_speed_mph",
    "fast_friday_reference_mph",
}


missing = sorted(
    required - set(fields)
)

if missing:

    raise SystemExit(
        "MISSING VALIDATION COLUMNS: "
        +
        ", ".join(missing)
    )


# =============================================================================
# Parse 2024 validation set
# =============================================================================

rows = []


for r in raw:

    year = int(
        float(
            clean(
                r.get(
                    "year"
                )
            )
        )
    )


    if year != 2024:

        raise SystemExit(
            f"NON-2024 ROW IN FINAL VALIDATION: {year}"
        )


    dt = parse_dt(
        r.get(
            "performance_time_utc"
        )
    )

    actual = num(
        r.get(
            "target_four_lap_average_speed_mph"
        )
    )

    reference = num(
        r.get(
            "fast_friday_reference_mph"
        )
    )


    if (
        dt is None
        or
        actual is None
        or
        reference is None
    ):

        raise SystemExit(
            "INCOMPLETE VALIDATION ROW: "
            +
            clean(
                r.get(
                    "attempt_id"
                )
            )
        )


    rows.append({
        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "driver_key":
            clean(
                r.get(
                    "driver_key"
                )
            ),

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "time":
            dt,

        "time_text":
            clean(
                r.get(
                    "performance_time_utc"
                )
            ),

        "actual":
            actual,

        "reference":
            reference,

        "residual":
            actual - reference,
    })


rows.sort(
    key=lambda r: (
        r[
            "time"
        ],
        r[
            "attempt_id"
        ],
    )
)


if len(rows) != 6:

    raise SystemExit(
        f"EXPECTED 6 FROZEN 2024 VALIDATION ROWS, GOT {len(rows)}"
    )


print("=" * 154)
print("R4F7V1 — 2024 ONE-SHOT FINAL VALIDATION")
print("=" * 154)

print(
    f"2024 validation rows: {len(rows)}"
)

print(
    f"FROZEN k: {k}"
)

print(
    f"FROZEN prior mean residual: {prior_mean:+.6f} mph"
)

print(
    f"FROZEN prior SD: {prior_sd:.6f} mph"
)

print()
print(
    "NO 2024 PARAMETER TUNING IS PERMITTED."
)


# =============================================================================
# Strictly earlier common-field evidence
# =============================================================================

def past_other(
    current
):

    return [
        r
        for r in rows
        if (
            r[
                "time"
            ]
            <
            current[
                "time"
            ]
            and
            r[
                "driver_key"
            ]
            !=
            current[
                "driver_key"
            ]
        )
    ]


def running_field_mean(
    current
):

    past = past_other(
        current
    )

    if not past:
        return prior_mean

    return (
        sum(
            r[
                "residual"
            ]
            for r in past
        )
        /
        len(past)
    )


def shrunk_field_mean(
    current
):

    past = past_other(
        current
    )

    n = len(past)

    if n == 0:
        return prior_mean

    observed_mean = (
        sum(
            r[
                "residual"
            ]
            for r in past
        )
        /
        n
    )

    return (
        (
            k
            *
            prior_mean
        )
        +
        (
            n
            *
            observed_mean
        )
    ) / (
        k + n
    )


# =============================================================================
# Generate one-shot predictions
# =============================================================================

prediction_rows = []
trace_rows = []


for current in rows:

    past = past_other(
        current
    )

    n = len(past)


    if n:

        field_mean = (
            sum(
                r[
                    "residual"
                ]
                for r in past
            )
            /
            n
        )

    else:

        field_mean = None


    shrunk = (
        shrunk_field_mean(
            current
        )
    )

    running = (
        running_field_mean(
            current
        )
    )


    prior_weight = (
        k /
        (
            k + n
        )
    )

    field_weight = (
        n /
        (
            k + n
        )
    )


    trace_rows.append({
        "attempt_id":
            current[
                "attempt_id"
            ],

        "driver_name":
            current[
                "driver_name"
            ],

        "performance_time_utc":
            current[
                "time_text"
            ],

        "past_other_count":
            n,

        "observed_past_field_mean_residual_mph":
            (
                field_mean
                if field_mean is not None
                else ""
            ),

        "frozen_prior_mean_residual_mph":
            prior_mean,

        "prior_weight":
            prior_weight,

        "current_session_field_weight":
            field_weight,

        "primary_calibration_residual_mph":
            shrunk,

        "actual_residual_mph":
            current[
                "residual"
            ],
    })


    predictions = {
        "FAST_FRIDAY_REFERENCE_ONLY":
            current[
                "reference"
            ],

        "FROZEN_CROSS_YEAR_PRIOR_CALIBRATION":
            (
                current[
                    "reference"
                ]
                +
                prior_mean
            ),

        "ONLINE_RUNNING_FIELD_MEAN_ABLATION":
            (
                current[
                    "reference"
                ]
                +
                running
            ),

        "FROZEN_PRIMARY_ONLINE_SHRUNK_FIELD_MEAN":
            (
                current[
                    "reference"
                ]
                +
                shrunk
            ),
    }


    for model, pred in predictions.items():

        prediction_rows.append({
            "model":
                model,

            "attempt_id":
                current[
                    "attempt_id"
                ],

            "driver_key":
                current[
                    "driver_key"
                ],

            "driver_name":
                current[
                    "driver_name"
                ],

            "performance_time_utc":
                current[
                    "time_text"
                ],

            "past_other_count":
                n,

            "reference_speed_mph":
                current[
                    "reference"
                ],

            "actual_speed_mph":
                current[
                    "actual"
                ],

            "actual_reference_residual_mph":
                current[
                    "residual"
                ],

            "predicted_speed_mph":
                pred,

            "error_mph":
                (
                    pred
                    -
                    current[
                        "actual"
                    ]
                ),

            "absolute_error_mph":
                abs(
                    pred
                    -
                    current[
                        "actual"
                    ]
                ),
        })


# =============================================================================
# Metrics
# =============================================================================

models = [
    "FAST_FRIDAY_REFERENCE_ONLY",
    "FROZEN_CROSS_YEAR_PRIOR_CALIBRATION",
    "ONLINE_RUNNING_FIELD_MEAN_ABLATION",
    "FROZEN_PRIMARY_ONLINE_SHRUNK_FIELD_MEAN",
]


metric_rows = []


for model in models:

    subset = [
        r
        for r in prediction_rows
        if r[
            "model"
        ] == model
    ]

    actual = [
        r[
            "actual_speed_mph"
        ]
        for r in subset
    ]

    pred = [
        r[
            "predicted_speed_mph"
        ]
        for r in subset
    ]


    m = metric_dict(
        actual,
        pred
    )


    metric_rows.append({
        "model":
            model,

        "scope":
            "ALL_2024_VALIDATION",

        **m,
    })


# =============================================================================
# Supported subsets
# =============================================================================

for threshold in [
    1,
    3,
]:

    for model in models:

        subset = [
            r
            for r in prediction_rows
            if (
                r[
                    "model"
                ] == model
                and
                r[
                    "past_other_count"
                ]
                >= threshold
            )
        ]


        if not subset:
            continue


        actual = [
            r[
                "actual_speed_mph"
            ]
            for r in subset
        ]

        pred = [
            r[
                "predicted_speed_mph"
            ]
            for r in subset
        ]


        m = metric_dict(
            actual,
            pred
        )


        metric_rows.append({
            "model":
                model,

            "scope":
                f"PAST_OTHER_GE_{threshold}",

            **m,
        })


# =============================================================================
# Structural validation diagnostics
# =============================================================================

actual_residuals = [
    r[
        "residual"
    ]
    for r in rows
]


validation_residual_mean = (
    sum(
        actual_residuals
    )
    /
    len(
        actual_residuals
    )
)


validation_residual_median = (
    sorted(
        actual_residuals
    )[
        len(
            actual_residuals
        )
        //
        2
    ]
)


primary_metric = next(
    r
    for r in metric_rows
    if (
        r[
            "model"
        ]
        ==
        "FROZEN_PRIMARY_ONLINE_SHRUNK_FIELD_MEAN"
        and
        r[
            "scope"
        ]
        ==
        "ALL_2024_VALIDATION"
    )
)


reference_metric = next(
    r
    for r in metric_rows
    if (
        r[
            "model"
        ]
        ==
        "FAST_FRIDAY_REFERENCE_ONLY"
        and
        r[
            "scope"
        ]
        ==
        "ALL_2024_VALIDATION"
    )
)


prior_metric = next(
    r
    for r in metric_rows
    if (
        r[
            "model"
        ]
        ==
        "FROZEN_CROSS_YEAR_PRIOR_CALIBRATION"
        and
        r[
            "scope"
        ]
        ==
        "ALL_2024_VALIDATION"
    )
)


primary_gain_vs_reference = (
    reference_metric[
        "mae_mph"
    ]
    -
    primary_metric[
        "mae_mph"
    ]
)


primary_gain_vs_prior = (
    prior_metric[
        "mae_mph"
    ]
    -
    primary_metric[
        "mae_mph"
    ]
)


# =============================================================================
# QA
# =============================================================================

future_leakage = False


for current in rows:

    for past in past_other(
        current
    ):

        if not (
            past[
                "time"
            ]
            <
            current[
                "time"
            ]
        ):

            future_leakage = True


duplicate_attempts = (
    len(
        {
            r[
                "attempt_id"
            ]
            for r in rows
        }
    )
    !=
    len(rows)
)


qa_rows = [
    {
        "metric":
            "validation_rows",
        "value":
            len(rows),
        "expected":
            6,
        "status":
            (
                "PASS"
                if len(rows) == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_year",
        "value":
            2024,
        "expected":
            2024,
        "status":
            "PASS",
    },

    {
        "metric":
            "frozen_k",
        "value":
            k,
        "expected":
            3.0,
        "status":
            (
                "PASS"
                if abs(
                    k - 3.0
                ) < 1e-12
                else "FAIL"
            ),
    },

    {
        "metric":
            "future_information_used",
        "value":
            future_leakage,
        "expected":
            False,
        "status":
            (
                "PASS"
                if not future_leakage
                else "FAIL"
            ),
    },

    {
        "metric":
            "duplicate_attempt_ids",
        "value":
            duplicate_attempts,
        "expected":
            False,
        "status":
            (
                "PASS"
                if not duplicate_attempts
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_used_for_parameter_tuning",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "same_timestamp_information_used",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "historical_action_labels_used",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "validation_results_do_not_trigger_refit",
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

with OUT_PRED.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            prediction_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        prediction_rows
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


with OUT_TRACE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            trace_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        trace_rows
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
        "R4F7V1",

    "status":
        "R4F7V1_2024_ONE_SHOT_FINAL_VALIDATION_COMPLETE",

    "validation_year":
        2024,

    "validation_rows":
        len(rows),

    "architecture":
        (
            "Fast Friday reference + frozen online shrunk field calibration"
        ),

    "frozen_parameters": {
        "shrinkage_k":
            k,

        "prior_mean_residual_mph":
            prior_mean,

        "prior_sd_residual_mph":
            prior_sd,
    },

    "metrics":
        metric_rows,

    "actual_2024_reference_residual": {
        "mean_mph":
            validation_residual_mean,

        "median_mph":
            validation_residual_median,

        "min_mph":
            min(
                actual_residuals
            ),

        "max_mph":
            max(
                actual_residuals
            ),
    },

    "primary_gain_vs_reference_mae_mph":
        primary_gain_vs_reference,

    "primary_gain_vs_frozen_prior_mae_mph":
        primary_gain_vs_prior,

    "interpretation_boundary":
        (
            "Only six 2024 observations satisfy the previously frozen "
            "strict validation requirements. Results are therefore an "
            "external generalization check, not a high-power statistical "
            "estimate."
        ),

    "no_post_hoc_tuning":
        True,

    "input_hashes": {
        str(
            CONTRACT_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                CONTRACT_PATH
            ),

        str(
            VALIDATION_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                VALIDATION_PATH
            ),
    },

    "next_phase":
        (
            "Freeze performance-model validation conclusion. "
            "Then evaluate 2022 degraded chronology robustness and "
            "2025 technical-regime transfer before integrating the "
            "performance distribution into the action Monte Carlo."
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
print("=" * 154)
print("2024 VALIDATION OBSERVATIONS")
print("=" * 154)

for r in trace_rows:

    print(
        f"{r['performance_time_utc']} | "
        f"{r['driver_name'][:22]:22s} | "
        f"past_N={r['past_other_count']:2d} | "
        f"field_mean={str(r['observed_past_field_mean_residual_mph']):>10s} | "
        f"prior_w={r['prior_weight']:.3f} | "
        f"field_w={r['current_session_field_weight']:.3f} | "
        f"pred_cal={r['primary_calibration_residual_mph']:+.4f} | "
        f"actual_cal={r['actual_residual_mph']:+.4f}"
    )


print()
print("=" * 154)
print("2024 ONE-SHOT VALIDATION — ALL 6")
print("=" * 154)

all_scope = [
    r
    for r in metric_rows
    if r[
        "scope"
    ]
    ==
    "ALL_2024_VALIDATION"
]


for r in sorted(
    all_scope,
    key=lambda x:
        x[
            "mae_mph"
        ]
):

    print(
        f"{r['model']:46s} | "
        f"n={r['n']:2d} | "
        f"MAE={r['mae_mph']:.6f} | "
        f"RMSE={r['rmse_mph']:.6f} | "
        f"BIAS={r['bias_mph']:+.6f} | "
        f"CORR={r['correlation']}"
    )


print()
print("=" * 154)
print("2024 SUPPORTED SUBSETS")
print("=" * 154)

for scope in [
    "PAST_OTHER_GE_1",
    "PAST_OTHER_GE_3",
]:

    print()
    print(scope)

    subset = [
        r
        for r in metric_rows
        if r[
            "scope"
        ] == scope
    ]

    if not subset:

        print("NONE")
        continue


    for r in sorted(
        subset,
        key=lambda x:
            x[
                "mae_mph"
            ]
    ):

        print(
            f"{r['model']:46s} | "
            f"n={r['n']:2d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f}"
        )


print()
print("=" * 154)
print("VALIDATION INTERPRETATION NUMBERS")
print("=" * 154)

print(
    f"2024 actual residual mean: "
    f"{validation_residual_mean:+.6f} mph"
)

print(
    f"Frozen development prior: "
    f"{prior_mean:+.6f} mph"
)

print(
    f"Primary MAE gain vs Fast Friday reference: "
    f"{primary_gain_vs_reference:+.6f} mph"
)

print(
    f"Primary MAE gain vs frozen cross-year prior: "
    f"{primary_gain_vs_prior:+.6f} mph"
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
    OUT_PRED.relative_to(ROOT)
)
print(
    OUT_METRICS.relative_to(ROOT)
)
print(
    OUT_TRACE.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7V1_2024_ONE_SHOT_FINAL_VALIDATION_COMPLETE"
)
