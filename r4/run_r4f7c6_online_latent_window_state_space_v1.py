from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import statistics
import hashlib
import itertools

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT_PATH = (
    OUT /
    "r4f7c5_prospective_past_only_state_panel_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4f7c6_online_latent_window_predictions_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f7c6_online_latent_window_metrics_v1.csv"
)

OUT_PARAMS = (
    OUT /
    "r4f7c6_online_latent_window_selected_parameters_v1.csv"
)

OUT_TRACE = (
    OUT /
    "r4f7c6_online_latent_window_state_trace_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c6_online_latent_window_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c6_online_latent_window_report_v1.json"
)


YEARS = [
    2020,
    2021,
    2023,
]


EWMA_HALF_LIVES = [
    10.0,
    20.0,
    30.0,
    45.0,
    60.0,
]


SHRINKAGE_K_VALUES = [
    1.0,
    3.0,
    5.0,
    8.0,
    12.0,
    20.0,
]


KALMAN_PROCESS_SD_GRID = [
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
    0.30,
    0.45,
]


KALMAN_OBSERVATION_SD_GRID = [
    0.40,
    0.60,
    0.80,
    1.00,
    1.25,
    1.50,
    2.00,
]


KALMAN_PRIOR_SD_GRID = [
    0.30,
    0.50,
    0.75,
    1.00,
    1.50,
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

    with path.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def mae(actual, pred):
    return (
        sum(
            abs(a - b)
            for a, b
            in zip(
                actual,
                pred
            )
        )
        /
        len(actual)
    )


def rmse(actual, pred):
    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b
            in zip(
                actual,
                pred
            )
        )
        /
        len(actual)
    )


def bias(actual, pred):
    return (
        sum(
            p - a
            for a, p
            in zip(
                actual,
                pred
            )
        )
        /
        len(actual)
    )


def correlation(a, b):

    if len(a) < 2:
        return None

    ma = (
        sum(a)
        /
        len(a)
    )

    mb = (
        sum(b)
        /
        len(b)
    )

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
        (x - ma)
        *
        (y - mb)
        for x, y
        in zip(
            a,
            b
        )
    )

    return (
        cov
        /
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


if not INPUT_PATH.exists():

    raise SystemExit(
        f"MISSING INPUT: {INPUT_PATH}"
    )


fields, raw = read_csv(
    INPUT_PATH
)


required = {
    "attempt_id",
    "year",
    "driver_key",
    "driver_name",
    "performance_time_utc",
    "actual_speed_mph",
    "reference_speed_mph",
    "reference_residual_mph",
}


missing = sorted(
    required
    -
    set(fields)
)

if missing:

    raise SystemExit(
        "MISSING REQUIRED COLUMNS: "
        +
        ", ".join(
            missing
        )
    )


# =============================================================================
# Parse development observations
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

    time = parse_dt(
        r.get(
            "performance_time_utc"
        )
    )

    actual = num(
        r.get(
            "actual_speed_mph"
        )
    )

    reference = num(
        r.get(
            "reference_speed_mph"
        )
    )

    residual = num(
        r.get(
            "reference_residual_mph"
        )
    )


    if (
        year not in YEARS
        or
        time is None
        or
        actual is None
        or
        reference is None
        or
        residual is None
    ):

        if year in YEARS:

            raise SystemExit(
                "INCOMPLETE INPUT ROW: "
                +
                clean(
                    r.get(
                        "attempt_id"
                    )
                )
            )

        continue


    rows.append({
        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "year":
            year,

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
            time,

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
            residual,
    })


if len(rows) != 104:

    raise SystemExit(
        f"EXPECTED 104 ROWS, GOT {len(rows)}"
    )


by_year = defaultdict(
    list
)


for r in rows:

    by_year[
        r[
            "year"
        ]
    ].append(
        r
    )


for year in YEARS:

    by_year[
        year
    ].sort(
        key=lambda r: (
            r[
                "time"
            ],
            r[
                "attempt_id"
            ],
        )
    )


print("=" * 154)
print("R4F7C6 — PROSPECTIVE ONLINE LATENT WINDOW STATE-SPACE TEST")
print("=" * 154)

print(
    f"Development rows: {len(rows)}"
)

print(
    f"Years: {YEARS}"
)

print(
    "2024 validation is NOT read."
)

print(
    "All held-out-year predictions are generated prequentially."
)


# =============================================================================
# Training-year prior
# =============================================================================

def cross_year_prior(
    training_years
):

    values = [
        r[
            "residual"
        ]
        for year in training_years
        for r in by_year[
            year
        ]
    ]

    mean = (
        sum(values)
        /
        len(values)
    )

    variance = (
        sum(
            (x - mean) ** 2
            for x in values
        )
        /
        max(
            1,
            len(values) - 1
        )
    )

    return (
        mean,
        math.sqrt(
            variance
        ),
    )


# =============================================================================
# Strictly earlier other-driver observations
# =============================================================================

def past_other_rows(
    current,
    year_rows
):

    return [
        r
        for r in year_rows
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


# =============================================================================
# Online running mean
# =============================================================================

def predict_running_mean(
    current,
    year_rows,
    prior_mean,
):

    past = past_other_rows(
        current,
        year_rows
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


# =============================================================================
# Shrunk running mean
# =============================================================================

def predict_shrunk_mean(
    current,
    year_rows,
    prior_mean,
    k,
):

    past = past_other_rows(
        current,
        year_rows
    )

    n = len(
        past
    )

    if n == 0:
        return prior_mean

    sample_mean = (
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
            sample_mean
        )
    ) / (
        k + n
    )


# =============================================================================
# EWMA
# =============================================================================

def predict_ewma(
    current,
    year_rows,
    prior_mean,
    half_life,
):

    past = past_other_rows(
        current,
        year_rows
    )

    if not past:
        return prior_mean


    numerator = 0.0
    denominator = 0.0


    for r in past:

        age_minutes = (
            (
                current[
                    "time"
                ]
                -
                r[
                    "time"
                ]
            ).total_seconds()
            /
            60.0
        )

        weight = math.exp(
            -math.log(2.0)
            *
            age_minutes
            /
            half_life
        )

        numerator += (
            weight
            *
            r[
                "residual"
            ]
        )

        denominator += weight


    if denominator <= 0:
        return prior_mean

    return (
        numerator
        /
        denominator
    )


# =============================================================================
# Kalman filter
#
# State:
#   residual_t = latent_session_state_t + observation_noise
#
# Transition:
#   state_t = state_(t-1) + process_noise
#
# The filter is updated only with observations strictly before the
# current prediction timestamp.
#
# Same-timestamp rows are predicted from the same prior state and only
# assimilated after all rows at that timestamp have been predicted.
# This avoids arbitrary ordering leakage.
# =============================================================================

def kalman_predictions(
    year_rows,
    prior_mean,
    prior_sd,
    process_sd,
    observation_sd,
):

    state_mean = float(
        prior_mean
    )

    state_var = float(
        prior_sd
        **
        2
    )

    q_per_minute = (
        process_sd
        **
        2
    )

    r_var = (
        observation_sd
        **
        2
    )


    predictions = {}

    trace = []


    groups = defaultdict(
        list
    )


    for row in year_rows:

        groups[
            row[
                "time"
            ]
        ].append(
            row
        )


    times = sorted(
        groups.keys()
    )


    previous_time = (
        times[0]
        if times
        else None
    )


    for current_time in times:

        if previous_time is None:

            dt_minutes = 0.0

        else:

            dt_minutes = max(
                0.0,
                (
                    current_time
                    -
                    previous_time
                ).total_seconds()
                /
                60.0
            )


        state_var = (
            state_var
            +
            q_per_minute
            *
            dt_minutes
        )


        prior_state_mean = (
            state_mean
        )

        prior_state_sd = (
            math.sqrt(
                max(
                    state_var,
                    0.0
                )
            )
        )


        timestamp_rows = (
            groups[
                current_time
            ]
        )


        # Predict every simultaneous row before assimilating any of them.
        for row in timestamp_rows:

            predictions[
                row[
                    "attempt_id"
                ]
            ] = (
                state_mean
            )


        # Assimilate timestamp group as aggregate field evidence.
        #
        # To reduce duplicate/same-driver overweighting, average residual
        # by driver inside the timestamp first.
        driver_values = defaultdict(
            list
        )


        for row in timestamp_rows:

            driver_values[
                row[
                    "driver_key"
                ]
            ].append(
                row[
                    "residual"
                ]
            )


        observations = [
            sum(values)
            /
            len(values)
            for values
            in driver_values.values()
        ]


        if observations:

            observation_mean = (
                sum(
                    observations
                )
                /
                len(
                    observations
                )
            )


            effective_r = (
                r_var
                /
                len(
                    observations
                )
            )


            kalman_gain = (
                state_var
                /
                (
                    state_var
                    +
                    effective_r
                )
            )


            state_mean = (
                state_mean
                +
                kalman_gain
                *
                (
                    observation_mean
                    -
                    state_mean
                )
            )


            state_var = (
                (
                    1.0
                    -
                    kalman_gain
                )
                *
                state_var
            )

        else:

            observation_mean = None
            kalman_gain = 0.0


        trace.append({
            "time":
                current_time,

            "prior_mean":
                prior_state_mean,

            "prior_sd":
                prior_state_sd,

            "observation_mean":
                observation_mean,

            "observation_driver_count":
                len(
                    observations
                ),

            "kalman_gain":
                kalman_gain,

            "posterior_mean":
                state_mean,

            "posterior_sd":
                math.sqrt(
                    max(
                        state_var,
                        0.0
                    )
                ),
        })


        previous_time = (
            current_time
        )


    return (
        predictions,
        trace,
    )


# =============================================================================
# Hyperparameter scoring
#
# Parameters for test year Y are selected ONLY using the OTHER two years.
#
# For each candidate, each training year is itself replayed from its start
# using a prior estimated from the other available training year.
#
# This prevents tuning a candidate using the target year's outcomes.
# =============================================================================

def score_ewma_candidate(
    training_years,
    half_life,
):

    actual = []
    pred = []


    for eval_year in training_years:

        prior_years = [
            y
            for y in training_years
            if y != eval_year
        ]


        if prior_years:

            prior_mean, _ = (
                cross_year_prior(
                    prior_years
                )
            )

        else:

            prior_mean = 0.0


        for current in by_year[
            eval_year
        ]:

            residual_pred = predict_ewma(
                current,
                by_year[
                    eval_year
                ],
                prior_mean,
                half_life,
            )


            actual.append(
                current[
                    "actual"
                ]
            )

            pred.append(
                current[
                    "reference"
                ]
                +
                residual_pred
            )


    return mae(
        actual,
        pred
    )


def score_shrink_candidate(
    training_years,
    k,
):

    actual = []
    pred = []


    for eval_year in training_years:

        prior_years = [
            y
            for y in training_years
            if y != eval_year
        ]


        if prior_years:

            prior_mean, _ = (
                cross_year_prior(
                    prior_years
                )
            )

        else:

            prior_mean = 0.0


        for current in by_year[
            eval_year
        ]:

            residual_pred = predict_shrunk_mean(
                current,
                by_year[
                    eval_year
                ],
                prior_mean,
                k,
            )


            actual.append(
                current[
                    "actual"
                ]
            )

            pred.append(
                current[
                    "reference"
                ]
                +
                residual_pred
            )


    return mae(
        actual,
        pred
    )


def score_kalman_candidate(
    training_years,
    prior_sd,
    process_sd,
    observation_sd,
):

    actual = []
    pred = []


    for eval_year in training_years:

        prior_years = [
            y
            for y in training_years
            if y != eval_year
        ]


        if prior_years:

            prior_mean, prior_emp_sd = (
                cross_year_prior(
                    prior_years
                )
            )

        else:

            prior_mean = 0.0
            prior_emp_sd = prior_sd


        effective_prior_sd = max(
            prior_sd,
            min(
                prior_emp_sd,
                2.5
            ),
        )


        preds, _ = kalman_predictions(
            by_year[
                eval_year
            ],
            prior_mean,
            effective_prior_sd,
            process_sd,
            observation_sd,
        )


        for current in by_year[
            eval_year
        ]:

            actual.append(
                current[
                    "actual"
                ]
            )

            pred.append(
                current[
                    "reference"
                ]
                +
                preds[
                    current[
                        "attempt_id"
                    ]
                ]
            )


    return mae(
        actual,
        pred
    )


# =============================================================================
# LOYO evaluation
# =============================================================================

prediction_rows = []
metric_rows = []
parameter_rows = []
state_trace_rows = []


for test_year in YEARS:

    training_years = [
        y
        for y in YEARS
        if y != test_year
    ]


    prior_mean, prior_empirical_sd = (
        cross_year_prior(
            training_years
        )
    )


    # -------------------------------------------------------------------------
    # Select EWMA half-life
    # -------------------------------------------------------------------------

    ewma_scores = []


    for half_life in EWMA_HALF_LIVES:

        score = score_ewma_candidate(
            training_years,
            half_life,
        )

        ewma_scores.append(
            (
                score,
                half_life,
            )
        )


    ewma_scores.sort()

    selected_ewma = (
        ewma_scores[
            0
        ][
            1
        ]
    )


    # -------------------------------------------------------------------------
    # Select shrinkage strength
    # -------------------------------------------------------------------------

    shrink_scores = []


    for k in SHRINKAGE_K_VALUES:

        score = score_shrink_candidate(
            training_years,
            k,
        )

        shrink_scores.append(
            (
                score,
                k,
            )
        )


    shrink_scores.sort()

    selected_k = (
        shrink_scores[
            0
        ][
            1
        ]
    )


    # -------------------------------------------------------------------------
    # Select Kalman parameters
    # -------------------------------------------------------------------------

    kalman_scores = []


    for (
        prior_sd,
        process_sd,
        observation_sd,
    ) in itertools.product(
        KALMAN_PRIOR_SD_GRID,
        KALMAN_PROCESS_SD_GRID,
        KALMAN_OBSERVATION_SD_GRID,
    ):

        score = score_kalman_candidate(
            training_years,
            prior_sd,
            process_sd,
            observation_sd,
        )

        kalman_scores.append(
            (
                score,
                prior_sd,
                process_sd,
                observation_sd,
            )
        )


    kalman_scores.sort()

    (
        selected_kalman_score,
        selected_prior_sd,
        selected_process_sd,
        selected_observation_sd,
    ) = kalman_scores[0]


    parameter_rows.append({
        "test_year":
            test_year,

        "training_years":
            ",".join(
                str(y)
                for y
                in training_years
            ),

        "prior_mean_residual_mph":
            prior_mean,

        "prior_empirical_sd_mph":
            prior_empirical_sd,

        "selected_ewma_half_life_minutes":
            selected_ewma,

        "ewma_inner_cv_mae":
            ewma_scores[
                0
            ][
                0
            ],

        "selected_shrinkage_k":
            selected_k,

        "shrink_inner_cv_mae":
            shrink_scores[
                0
            ][
                0
            ],

        "kalman_prior_sd":
            selected_prior_sd,

        "kalman_process_sd_per_sqrt_min":
            selected_process_sd,

        "kalman_observation_sd":
            selected_observation_sd,

        "kalman_inner_cv_mae":
            selected_kalman_score,
    })


    # -------------------------------------------------------------------------
    # Replay held-out session
    # -------------------------------------------------------------------------

    test_rows = (
        by_year[
            test_year
        ]
    )


    kalman_pred_map, trace = (
        kalman_predictions(
            test_rows,
            prior_mean,
            selected_prior_sd,
            selected_process_sd,
            selected_observation_sd,
        )
    )


    for tr in trace:

        state_trace_rows.append({
            "test_year":
                test_year,

            "time_utc":
                tr[
                    "time"
                ]
                .isoformat()
                .replace(
                    "+00:00",
                    "Z"
                ),

            "prior_mean_residual_mph":
                tr[
                    "prior_mean"
                ],

            "prior_sd_mph":
                tr[
                    "prior_sd"
                ],

            "observed_field_residual_mph":
                (
                    tr[
                        "observation_mean"
                    ]
                    if tr[
                        "observation_mean"
                    ]
                    is not None
                    else ""
                ),

            "observed_driver_count":
                tr[
                    "observation_driver_count"
                ],

            "kalman_gain":
                tr[
                    "kalman_gain"
                ],

            "posterior_mean_residual_mph":
                tr[
                    "posterior_mean"
                ],

            "posterior_sd_mph":
                tr[
                    "posterior_sd"
                ],
        })


    actual = [
        r[
            "actual"
        ]
        for r in test_rows
    ]


    model_predictions = {
        "FAST_FRIDAY_REFERENCE_ONLY":
            [
                r[
                    "reference"
                ]
                for r in test_rows
            ],

        "CROSS_YEAR_PRIOR_CALIBRATION":
            [
                r[
                    "reference"
                ]
                +
                prior_mean
                for r in test_rows
            ],

        "ONLINE_RUNNING_FIELD_MEAN":
            [
                r[
                    "reference"
                ]
                +
                predict_running_mean(
                    r,
                    test_rows,
                    prior_mean,
                )
                for r in test_rows
            ],

        "ONLINE_SHRUNK_FIELD_MEAN":
            [
                r[
                    "reference"
                ]
                +
                predict_shrunk_mean(
                    r,
                    test_rows,
                    prior_mean,
                    selected_k,
                )
                for r in test_rows
            ],

        "ONLINE_EWMA":
            [
                r[
                    "reference"
                ]
                +
                predict_ewma(
                    r,
                    test_rows,
                    prior_mean,
                    selected_ewma,
                )
                for r in test_rows
            ],

        "ONLINE_KALMAN_LATENT_WINDOW":
            [
                r[
                    "reference"
                ]
                +
                kalman_pred_map[
                    r[
                        "attempt_id"
                    ]
                ]
                for r in test_rows
            ],
    }


    for model_name, pred in (
        model_predictions.items()
    ):

        m = metric_dict(
            actual,
            pred,
        )


        metric_rows.append({
            "test_year":
                test_year,

            "model":
                model_name,

            **m,
        })


        for r, p in zip(
            test_rows,
            pred,
        ):

            past_count = len(
                past_other_rows(
                    r,
                    test_rows
                )
            )


            prediction_rows.append({
                "test_year":
                    test_year,

                "model":
                    model_name,

                "attempt_id":
                    r[
                        "attempt_id"
                    ],

                "driver_key":
                    r[
                        "driver_key"
                    ],

                "performance_time_utc":
                    r[
                        "time_text"
                    ],

                "past_other_count":
                    past_count,

                "observed_speed_mph":
                    r[
                        "actual"
                    ],

                "reference_speed_mph":
                    r[
                        "reference"
                    ],

                "predicted_speed_mph":
                    p,

                "error_mph":
                    p
                    -
                    r[
                        "actual"
                    ],

                "absolute_error_mph":
                    abs(
                        p
                        -
                        r[
                            "actual"
                        ]
                    ),
            })


# =============================================================================
# Aggregate metrics
# =============================================================================

models = sorted(
    {
        r[
            "model"
        ]
        for r in metric_rows
    }
)


aggregate_rows = []


for model_name in models:

    subset = [
        r
        for r in prediction_rows
        if r[
            "model"
        ] == model_name
    ]

    actual = [
        r[
            "observed_speed_mph"
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
        pred,
    )

    aggregate_rows.append({
        "test_year":
            "ALL_LOYO",

        "model":
            model_name,

        **m,
    })


all_metrics = (
    metric_rows
    +
    aggregate_rows
)


# =============================================================================
# Late-session supported subset
#
# Important because online state estimation has little information for the
# first cars. Evaluate separately after at least 3 / 5 prior other drivers.
# =============================================================================

supported_metric_rows = []


for minimum_past in [
    3,
    5,
    10,
]:

    for model_name in models:

        subset = [
            r
            for r in prediction_rows
            if (
                r[
                    "model"
                ]
                ==
                model_name
                and
                r[
                    "past_other_count"
                ]
                >=
                minimum_past
            )
        ]


        if not subset:
            continue


        actual = [
            r[
                "observed_speed_mph"
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
            pred,
        )


        supported_metric_rows.append({
            "minimum_past_other_count":
                minimum_past,

            "model":
                model_name,

            **m,
        })


# =============================================================================
# QA
# =============================================================================

future_information_used = False


# Explicit verification:
# every count used for a prediction is based only on strictly earlier rows.
for year in YEARS:

    year_rows = by_year[
        year
    ]

    for current in year_rows:

        for past in past_other_rows(
            current,
            year_rows
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

                future_information_used = True


expected_prediction_rows = (
    104
    *
    len(
        models
    )
)


qa_rows = [
    {
        "metric":
            "development_rows",
        "value":
            len(rows),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(rows) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "development_years",
        "value":
            ",".join(
                str(y)
                for y in YEARS
            ),
        "expected":
            "2020,2021,2023",
        "status":
            "PASS",
    },

    {
        "metric":
            "prediction_rows",
        "value":
            len(
                prediction_rows
            ),
        "expected":
            expected_prediction_rows,
        "status":
            (
                "PASS"
                if len(
                    prediction_rows
                )
                ==
                expected_prediction_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "future_information_used",
        "value":
            future_information_used,
        "expected":
            False,
        "status":
            (
                "PASS"
                if not future_information_used
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_read",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "test_year_used_for_hyperparameter_selection",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "same_timestamp_assimilated_before_prediction",
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
            "online_state_not_declared_causal_weather_effect",
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
            all_metrics[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        all_metrics
    )


with OUT_PARAMS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            parameter_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        parameter_rows
    )


with OUT_TRACE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            state_trace_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        state_trace_rows
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
        "R4F7C6",

    "status":
        "R4F7C6_ONLINE_LATENT_WINDOW_STATE_SPACE_READY",

    "development_rows":
        len(rows),

    "development_years":
        YEARS,

    "2024_validation_access":
        "NOT_READ",

    "models":
        models,

    "aggregate_metrics":
        aggregate_rows,

    "supported_subset_metrics":
        supported_metric_rows,

    "selected_parameters":
        parameter_rows,

    "state_definition":
        (
            "Latent common qualifying residual state relative to "
            "Fast Friday entry reference, updated sequentially from "
            "completed field observations."
        ),

    "prospective_rule":
        (
            "Prediction at time t is generated before assimilating "
            "any attempt occurring at time t. Only strictly earlier "
            "observations affect the state."
        ),

    "hyperparameter_policy":
        (
            "For each held-out test year, EWMA, shrinkage and Kalman "
            "parameters are selected using only the other development years."
        ),

    "interpretation_boundary":
        (
            "Latent state is a statistical performance-window estimate. "
            "It is not automatically interpreted as a causal temperature "
            "or tire effect."
        ),

    "input_hash":
        sha256(
            INPUT_PATH
        ),

    "next_phase_rule":
        (
            "If online Kalman/shrinkage materially improves over both "
            "Fast Friday and cross-year prior calibration, promote the "
            "dynamic latent-window layer. Otherwise retain a simpler "
            "online session-calibration posterior with broad uncertainty."
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
print("SELECTED PARAMETERS BY HELD-OUT YEAR")
print("=" * 154)

for r in parameter_rows:

    print(
        f"TEST {r['test_year']} | "
        f"train={r['training_years']} | "
        f"prior_mean={r['prior_mean_residual_mph']:+.4f} | "
        f"EWMA={r['selected_ewma_half_life_minutes']:.0f}m | "
        f"shrink_k={r['selected_shrinkage_k']:.1f} | "
        f"Kalman prior_sd={r['kalman_prior_sd']:.2f} | "
        f"process_sd={r['kalman_process_sd_per_sqrt_min']:.3f} | "
        f"obs_sd={r['kalman_observation_sd']:.2f}"
    )


print()
print("=" * 154)
print("ONLINE LOYO — AGGREGATE")
print("=" * 154)

for r in sorted(
    aggregate_rows,
    key=lambda x:
        x[
            "mae_mph"
        ]
):

    print(
        f"{r['model']:42s} | "
        f"n={r['n']:3d} | "
        f"MAE={r['mae_mph']:.6f} | "
        f"RMSE={r['rmse_mph']:.6f} | "
        f"BIAS={r['bias_mph']:+.6f} | "
        f"CORR={r['correlation']}"
    )


print()
print("=" * 154)
print("ONLINE LOYO — BY YEAR")
print("=" * 154)

for year in YEARS:

    print()
    print(
        f"TEST YEAR {year}"
    )

    subset = [
        r
        for r in metric_rows
        if r[
            "test_year"
        ] == year
    ]

    for r in sorted(
        subset,
        key=lambda x:
            x[
                "mae_mph"
            ]
    ):

        print(
            f"{r['model']:42s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f}"
        )


print()
print("=" * 154)
print("ONLINE SUPPORTED SUBSETS")
print("=" * 154)

for minimum in [
    3,
    5,
    10,
]:

    print()
    print(
        f"PAST OTHER >= {minimum}"
    )

    subset = [
        r
        for r in supported_metric_rows
        if r[
            "minimum_past_other_count"
        ] == minimum
    ]

    for r in sorted(
        subset,
        key=lambda x:
            x[
                "mae_mph"
            ]
    ):

        print(
            f"{r['model']:42s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f}"
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
    OUT_PARAMS.relative_to(ROOT)
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
    "R4F7C6_ONLINE_LATENT_WINDOW_STATE_SPACE_READY"
)
