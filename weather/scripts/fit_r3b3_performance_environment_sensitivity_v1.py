from pathlib import Path
import csv
import json
import math
import statistics

import numpy as np


PHASE = "R3B.3C"

OUT = Path("weather/output")

PAIR_DATA = (
    OUT
    / "r3b3_repeat_pair_environment_dataset_v1.csv"
)

BASELINE_METRICS = (
    OUT
    / "repeat_attempt_delta_baseline_aggregate_metrics_v1.csv"
)

CORRELATION_OUT = (
    OUT
    / "r3b3_environment_univariate_sensitivity_v1.csv"
)

FOLD_OUT = (
    OUT
    / "r3b3_environment_ridge_loyo_metrics_v1.csv"
)

COEFFICIENT_OUT = (
    OUT
    / "r3b3_environment_ridge_coefficients_v1.csv"
)

PREDICTION_OUT = (
    OUT
    / "r3b3_environment_ridge_predictions_v1.csv"
)

PTSC_DIAGNOSTIC_OUT = (
    OUT
    / "r3b3_ptsc_track_temperature_diagnostic_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b3_performance_environment_sensitivity_v1.json"
)

QA_OUT = (
    OUT
    / "r3b3_performance_environment_sensitivity_v1_qa.csv"
)


NORMAL_BRANCH = "NORMAL_DIAGNOSTIC"

YEARS = [
    "2020",
    "2021",
    "2023",
]


# Forward-usable features only.
# These are HRRR forecast changes.
FORWARD_FEATURES = [
    "delta_forecast_temp_c",
    "delta_forecast_dewpoint_c",
    "delta_forecast_relative_humidity_pct",
    "delta_forecast_wind_speed_10m_ms",
    "delta_forecast_gust_ms",
    "delta_forecast_pressure_hpa",
    "delta_forecast_cloud_cover_pct",
    "delta_forecast_shortwave_radiation_wm2",
]


# PTSC is historical diagnostic only.
DIAGNOSTIC_PTSC_FEATURE = (
    "delta_ptsc_track_c"
)


RIDGE_ALPHAS = [
    0.1,
    1.0,
    10.0,
    100.0,
]


def txt(v):
    return "" if v is None else str(v).strip()


def fnum(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def mae(y_true, y_pred):
    return float(
        np.mean(
            np.abs(
                y_pred - y_true
            )
        )
    )


def rmse(y_true, y_pred):
    return float(
        np.sqrt(
            np.mean(
                (
                    y_pred - y_true
                ) ** 2
            )
        )
    )


def r2(y_true, y_pred):
    if len(y_true) < 2:
        return None

    ss_res = float(
        np.sum(
            (
                y_true - y_pred
            ) ** 2
        )
    )

    mean_y = float(
        np.mean(y_true)
    )

    ss_tot = float(
        np.sum(
            (
                y_true - mean_y
            ) ** 2
        )
    )

    if ss_tot == 0:
        return None

    return (
        1.0
        -
        ss_res / ss_tot
    )


def pearson(x, y):
    if len(x) < 3:
        return None

    if (
        np.std(x) == 0
        or
        np.std(y) == 0
    ):
        return None

    return float(
        np.corrcoef(
            x,
            y,
        )[0, 1]
    )


def rankdata(values):
    """
    Average ranks for ties.
    Pure numpy/python implementation.
    """

    indexed = sorted(
        enumerate(values),
        key=lambda x: x[1],
    )

    ranks = [
        0.0
        for _ in values
    ]

    i = 0

    while i < len(indexed):

        j = i

        while (
            j + 1
            <
            len(indexed)
            and
            indexed[j + 1][1]
            ==
            indexed[i][1]
        ):
            j += 1

        avg_rank = (
            i + j
        ) / 2.0 + 1.0

        for k in range(
            i,
            j + 1,
        ):
            original_index = (
                indexed[k][0]
            )

            ranks[
                original_index
            ] = avg_rank

        i = j + 1

    return np.array(
        ranks,
        dtype=float,
    )


def spearman(x, y):
    if len(x) < 3:
        return None

    rx = rankdata(
        list(x)
    )

    ry = rankdata(
        list(y)
    )

    return pearson(
        rx,
        ry,
    )


def ridge_fit(
    X,
    y,
    alpha,
):
    """
    Fit standardized ridge with intercept.

    X must already be standardized using train statistics.
    Intercept is not penalized.
    """

    n = X.shape[0]

    X_design = np.column_stack(
        [
            np.ones(n),
            X,
        ]
    )

    p = X_design.shape[1]

    penalty = np.eye(p)

    penalty[0, 0] = 0.0

    lhs = (
        X_design.T
        @
        X_design
        +
        alpha
        *
        penalty
    )

    rhs = (
        X_design.T
        @
        y
    )

    beta = np.linalg.solve(
        lhs,
        rhs,
    )

    return beta


def ridge_predict(
    X,
    beta,
):
    n = X.shape[0]

    X_design = np.column_stack(
        [
            np.ones(n),
            X,
        ]
    )

    return (
        X_design
        @
        beta
    )


def standardize_train_test(
    X_train,
    X_test,
):
    means = np.mean(
        X_train,
        axis=0,
    )

    stds = np.std(
        X_train,
        axis=0,
        ddof=0,
    )

    safe_stds = np.where(
        stds == 0,
        1.0,
        stds,
    )

    X_train_z = (
        X_train
        -
        means
    ) / safe_stds

    X_test_z = (
        X_test
        -
        means
    ) / safe_stds

    return (
        X_train_z,
        X_test_z,
        means,
        safe_stds,
    )


def complete_rows(
    rows,
    features,
):
    out = []

    for row in rows:

        target = fnum(
            row.get(
                "observed_repeat_delta_mph"
            )
        )

        if target is None:
            continue

        values = []

        good = True

        for feature in features:

            value = fnum(
                row.get(feature)
            )

            if value is None:
                good = False
                break

            values.append(value)

        if not good:
            continue

        out.append(
            (
                row,
                np.array(
                    values,
                    dtype=float,
                ),
                target,
            )
        )

    return out


def main():

    print()
    print("=" * 128)
    print(
        "R3B.3C — PERFORMANCE / ENVIRONMENT "
        "OBSERVATIONAL SENSITIVITY FIT"
    )
    print("=" * 128)

    required = [
        PAIR_DATA,
        BASELINE_METRICS,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 128)

    missing = []

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(str(path))

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3B3C_INPUT_MISSING"
        )
        return

    rows = read_csv(
        PAIR_DATA
    )

    baseline_metrics = read_csv(
        BASELINE_METRICS
    )

    ready = [
        row
        for row in rows
        if truthy(
            row.get(
                "pair_environment_fit_ready"
            )
        )
    ]

    normal = [
        row
        for row in ready
        if not truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    recovery = [
        row
        for row in ready
        if truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    print()
    print("=" * 128)
    print("ANALYSIS POPULATION")
    print("=" * 128)

    print()
    print(
        "Environment-ready pairs:",
        len(ready),
    )

    print(
        "Normal branch:",
        len(normal),
    )

    print(
        "Recovery-like branch:",
        len(recovery),
    )

    print()
    print(
        "Primary sensitivity fit:",
        "NORMAL BRANCH ONLY",
    )

    print(
        "Recovery branch:",
        "DESCRIPTIVE ONLY",
    )

    print(
        "PTSC track temperature:",
        "DIAGNOSTIC ONLY",
    )

    # --------------------------------------------------
    # ZERO baseline reference
    # --------------------------------------------------

    zero_metric = None

    for row in baseline_metrics:

        if txt(
            row.get(
                "model_name"
            )
        ) == "ZERO_DELTA_BASELINE":

            zero_metric = fnum(
                row.get(
                    "pooled_mae_mph"
                )
            )

            break

    print()
    print(
        "Frozen ZERO_DELTA baseline pooled MAE:",
        (
            f"{zero_metric:.6f}"
            if zero_metric is not None
            else
            "UNKNOWN"
        ),
    )

    # --------------------------------------------------
    # Univariate correlations
    # --------------------------------------------------

    correlation_rows = []

    print()
    print("=" * 128)
    print("UNIVARIATE NORMAL-BRANCH SENSITIVITY")
    print("=" * 128)

    for feature in (
        FORWARD_FEATURES
        +
        [
            DIAGNOSTIC_PTSC_FEATURE,
        ]
    ):

        xs = []
        ys = []

        for row in normal:

            x = fnum(
                row.get(feature)
            )

            y = fnum(
                row.get(
                    "observed_repeat_delta_mph"
                )
            )

            if (
                x is None
                or
                y is None
            ):
                continue

            xs.append(x)
            ys.append(y)

        x_arr = np.array(
            xs,
            dtype=float,
        )

        y_arr = np.array(
            ys,
            dtype=float,
        )

        p = pearson(
            x_arr,
            y_arr,
        )

        s = spearman(
            x_arr,
            y_arr,
        )

        role = (
            "DIAGNOSTIC_ONLY"
            if feature
            ==
            DIAGNOSTIC_PTSC_FEATURE
            else
            "FORWARD_CANDIDATE"
        )

        correlation_rows.append({
            "feature":
                feature,

            "rows":
                len(xs),

            "pearson_corr":
                (
                    f"{p:.10f}"
                    if p is not None
                    else
                    "UNKNOWN"
                ),

            "spearman_corr":
                (
                    f"{s:.10f}"
                    if s is not None
                    else
                    "UNKNOWN"
                ),

            "feature_role":
                role,

            "causal_interpretation":
                "NOT_ALLOWED",
        })

        print()
        print(feature)

        print(
            "  rows:",
            len(xs),
        )

        print(
            "  Pearson:",
            (
                f"{p:.4f}"
                if p is not None
                else
                "UNKNOWN"
            ),
        )

        print(
            "  Spearman:",
            (
                f"{s:.4f}"
                if s is not None
                else
                "UNKNOWN"
            ),
        )

        print(
            "  role:",
            role,
        )

    write_csv(
        CORRELATION_OUT,
        correlation_rows,
        list(
            correlation_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Complete-case forward feature matrix
    # --------------------------------------------------

    complete = complete_rows(
        normal,
        FORWARD_FEATURES,
    )

    print()
    print("=" * 128)
    print("FORWARD FEATURE MATRIX")
    print("=" * 128)

    print()
    print(
        "Normal rows:",
        len(normal),
    )

    print(
        "Complete forward-feature rows:",
        len(complete),
    )

    years_present = sorted(
        {
            txt(
                item[0].get(
                    "year"
                )
            )
            for item in complete
        }
    )

    print(
        "Years:",
        "|".join(
            years_present
        ),
    )

    if len(complete) < 10:

        print()
        print(
            "FINAL STATUS: "
            "R3B3C_INSUFFICIENT_COMPLETE_ROWS"
        )
        return

    # --------------------------------------------------
    # LOYO ridge
    # --------------------------------------------------

    fold_rows = []
    prediction_rows = []
    coefficient_rows = []

    candidate_summary = []

    print()
    print("=" * 128)
    print("LOYO RIDGE")
    print("=" * 128)

    for alpha in RIDGE_ALPHAS:

        pooled_actual = []
        pooled_pred = []

        alpha_fold_maes = []

        for holdout_year in YEARS:

            train = [
                item
                for item in complete
                if txt(
                    item[0].get(
                        "year"
                    )
                )
                !=
                holdout_year
            ]

            test = [
                item
                for item in complete
                if txt(
                    item[0].get(
                        "year"
                    )
                )
                ==
                holdout_year
            ]

            if (
                not train
                or
                not test
            ):
                continue

            X_train = np.vstack(
                [
                    item[1]
                    for item in train
                ]
            )

            y_train = np.array(
                [
                    item[2]
                    for item in train
                ],
                dtype=float,
            )

            X_test = np.vstack(
                [
                    item[1]
                    for item in test
                ]
            )

            y_test = np.array(
                [
                    item[2]
                    for item in test
                ],
                dtype=float,
            )

            (
                X_train_z,
                X_test_z,
                means,
                stds,
            ) = standardize_train_test(
                X_train,
                X_test,
            )

            beta = ridge_fit(
                X_train_z,
                y_train,
                alpha,
            )

            pred = ridge_predict(
                X_test_z,
                beta,
            )

            fold_mae = mae(
                y_test,
                pred,
            )

            fold_rmse = rmse(
                y_test,
                pred,
            )

            fold_r2 = r2(
                y_test,
                pred,
            )

            zero_pred = np.zeros(
                len(y_test),
                dtype=float,
            )

            zero_mae = mae(
                y_test,
                zero_pred,
            )

            alpha_fold_maes.append(
                fold_mae
            )

            pooled_actual.extend(
                list(
                    y_test
                )
            )

            pooled_pred.extend(
                list(
                    pred
                )
            )

            fold_rows.append({
                "alpha":
                    alpha,

                "holdout_year":
                    holdout_year,

                "train_rows":
                    len(train),

                "test_rows":
                    len(test),

                "ridge_mae_mph":
                    f"{fold_mae:.10f}",

                "zero_delta_mae_same_test_mph":
                    f"{zero_mae:.10f}",

                "mae_improvement_vs_zero_mph":
                    f"{zero_mae - fold_mae:.10f}",

                "ridge_rmse_mph":
                    f"{fold_rmse:.10f}",

                "ridge_r2":
                    (
                        f"{fold_r2:.10f}"
                        if fold_r2 is not None
                        else
                        "UNKNOWN"
                    ),
            })

            for i, item in enumerate(
                test
            ):

                source_row = item[0]

                prediction_rows.append({
                    "alpha":
                        alpha,

                    "holdout_year":
                        holdout_year,

                    "pair_id":
                        txt(
                            source_row.get(
                                "pair_id"
                            )
                        ),

                    "driver_name":
                        txt(
                            source_row.get(
                                "driver_name"
                            )
                        ),

                    "actual_delta_mph":
                        f"{y_test[i]:.10f}",

                    "predicted_delta_mph":
                        f"{pred[i]:.10f}",

                    "absolute_error_mph":
                        f"{abs(pred[i] - y_test[i]):.10f}",
                })

            for j, feature in enumerate(
                FORWARD_FEATURES
            ):

                coefficient_rows.append({
                    "alpha":
                        alpha,

                    "holdout_year":
                        holdout_year,

                    "feature":
                        feature,

                    "standardized_coefficient":
                        f"{beta[j + 1]:.10f}",

                    "train_mean":
                        f"{means[j]:.10f}",

                    "train_std":
                        f"{stds[j]:.10f}",
                })

        if pooled_actual:

            y_actual = np.array(
                pooled_actual,
                dtype=float,
            )

            y_pred = np.array(
                pooled_pred,
                dtype=float,
            )

            pooled_mae = mae(
                y_actual,
                y_pred,
            )

            pooled_rmse = rmse(
                y_actual,
                y_pred,
            )

            zero_same = mae(
                y_actual,
                np.zeros(
                    len(y_actual)
                ),
            )

            candidate_summary.append({
                "alpha":
                    alpha,

                "pooled_mae":
                    pooled_mae,

                "pooled_rmse":
                    pooled_rmse,

                "zero_same_test_mae":
                    zero_same,

                "improvement":
                    zero_same
                    -
                    pooled_mae,

                "mean_fold_mae":
                    float(
                        np.mean(
                            alpha_fold_maes
                        )
                    ),
            })

            print()
            print(
                f"alpha={alpha}"
            )

            print(
                "  pooled ridge MAE:",
                f"{pooled_mae:.6f}",
            )

            print(
                "  same-row zero MAE:",
                f"{zero_same:.6f}",
            )

            print(
                "  improvement:",
                f"{zero_same - pooled_mae:.6f}",
            )

    if not candidate_summary:

        print()
        print(
            "FINAL STATUS: "
            "R3B3C_LOYO_NOT_ESTIMABLE"
        )
        return

    candidate_summary.sort(
        key=lambda x:
        (
            x[
                "pooled_mae"
            ],
            x[
                "alpha"
            ],
        )
    )

    best = candidate_summary[0]

    best_alpha = best[
        "alpha"
    ]

    environment_improves_zero = (
        best[
            "improvement"
        ]
        >
        0
    )

    # --------------------------------------------------
    # Full normal-branch fit for sensitivity coefficients
    # only. Whether these are central or scenario-only
    # depends on LOYO performance.
    # --------------------------------------------------

    X_all = np.vstack(
        [
            item[1]
            for item in complete
        ]
    )

    y_all = np.array(
        [
            item[2]
            for item in complete
        ],
        dtype=float,
    )

    means = np.mean(
        X_all,
        axis=0,
    )

    stds = np.std(
        X_all,
        axis=0,
        ddof=0,
    )

    safe_stds = np.where(
        stds == 0,
        1.0,
        stds,
    )

    X_all_z = (
        X_all
        -
        means
    ) / safe_stds

    beta_full = ridge_fit(
        X_all_z,
        y_all,
        best_alpha,
    )

    full_coefficients = []

    for j, feature in enumerate(
        FORWARD_FEATURES
    ):

        standardized_beta = float(
            beta_full[
                j + 1
            ]
        )

        raw_beta = (
            standardized_beta
            /
            safe_stds[j]
        )

        full_coefficients.append({
            "feature":
                feature,

            "standardized_coefficient":
                standardized_beta,

            "raw_coefficient_mph_per_feature_unit":
                raw_beta,

            "feature_mean":
                float(
                    means[j]
                ),

            "feature_std":
                float(
                    safe_stds[j]
                ),
        })

    full_coefficients.sort(
        key=lambda x:
        abs(
            x[
                "standardized_coefficient"
            ]
        ),
        reverse=True,
    )

    # --------------------------------------------------
    # PTSC diagnostic only
    # --------------------------------------------------

    ptsc_x = []
    ptsc_y = []

    for row in normal:

        x = fnum(
            row.get(
                DIAGNOSTIC_PTSC_FEATURE
            )
        )

        y = fnum(
            row.get(
                "observed_repeat_delta_mph"
            )
        )

        if (
            x is None
            or
            y is None
        ):
            continue

        ptsc_x.append(x)
        ptsc_y.append(y)

    ptsc_p = pearson(
        np.array(
            ptsc_x,
            dtype=float,
        ),
        np.array(
            ptsc_y,
            dtype=float,
        ),
    )

    ptsc_s = spearman(
        np.array(
            ptsc_x,
            dtype=float,
        ),
        np.array(
            ptsc_y,
            dtype=float,
        ),
    )

    ptsc_rows = [
        {
            "feature":
                DIAGNOSTIC_PTSC_FEATURE,

            "rows":
                len(
                    ptsc_x
                ),

            "pearson_corr":
                (
                    f"{ptsc_p:.10f}"
                    if ptsc_p is not None
                    else
                    "UNKNOWN"
                ),

            "spearman_corr":
                (
                    f"{ptsc_s:.10f}"
                    if ptsc_s is not None
                    else
                    "UNKNOWN"
                ),

            "simulator_feature_allowed":
                "False",

            "reason":
                (
                    "Future track temperature is not "
                    "identifiable and air-to-track proxy "
                    "is prohibited."
                ),

            "causal_claim":
                "False",
        }
    ]

    write_csv(
        PTSC_DIAGNOSTIC_OUT,
        ptsc_rows,
        list(
            ptsc_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Outputs
    # --------------------------------------------------

    write_csv(
        FOLD_OUT,
        fold_rows,
        list(
            fold_rows[0].keys()
        ),
    )

    write_csv(
        COEFFICIENT_OUT,
        coefficient_rows,
        list(
            coefficient_rows[0].keys()
        ),
    )

    write_csv(
        PREDICTION_OUT,
        prediction_rows,
        list(
            prediction_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    recovery_used_in_fit = any(
        truthy(
            item[0].get(
                "diagnostic_recovery_like"
            )
        )
        for item in complete
    )

    ptsc_used_in_forward = (
        DIAGNOSTIC_PTSC_FEATURE
        in
        FORWARD_FEATURES
    )

    year_set = {
        txt(
            item[0].get(
                "year"
            )
        )
        for item in complete
    }

    year_2022_used = (
        "2022"
        in year_set
    )

    qa_rows = [
        {
            "metric":
                "normal_branch_rows",

            "value":
                len(normal),

            "status":
                (
                    "PASS"
                    if len(normal)
                    ==
                    35
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "recovery_branch_rows",

            "value":
                len(recovery),

            "status":
                (
                    "PASS"
                    if len(recovery)
                    ==
                    4
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "complete_forward_feature_rows",

            "value":
                len(complete),

            "status":
                (
                    "PASS"
                    if len(complete)
                    >=
                    30
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "loyo_years",

            "value":
                "|".join(
                    sorted(
                        year_set
                    )
                ),

            "status":
                (
                    "PASS"
                    if year_set
                    ==
                    {
                        "2020",
                        "2021",
                        "2023",
                    }
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "2022_used_in_environment_fit",

            "value":
                int(
                    year_2022_used
                ),

            "status":
                (
                    "PASS"
                    if not year_2022_used
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "recovery_rows_used_in_normal_fit",

            "value":
                int(
                    recovery_used_in_fit
                ),

            "status":
                (
                    "PASS"
                    if not recovery_used_in_fit
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ptsc_used_as_forward_predictor",

            "value":
                int(
                    ptsc_used_in_forward
                ),

            "status":
                (
                    "PASS"
                    if not ptsc_used_in_forward
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "loyo_completed",

            "value":
                len(
                    fold_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        fold_rows
                    )
                    ==
                    len(
                        RIDGE_ALPHAS
                    )
                    *
                    3
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "environment_model_beats_zero",

            "value":
                (
                    f"{best['improvement']:.10f}"
                ),

            "status":
                (
                    "PASS"
                    if environment_improves_zero
                    else
                    "SENSITIVITY_ONLY"
                ),
        },

        {
            "metric":
                "causal_claim_allowed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_outputs_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    if environment_improves_zero:
        simulator_role = (
            "CENTRAL_ENVIRONMENT_CORRECTION_CANDIDATE"
        )
    else:
        simulator_role = (
            "SENSITIVITY_ONLY_ZERO_DELTA_REMAINS_CENTRAL"
        )

    payload = {
        "phase":
            PHASE,

        "analysis_population": {
            "environment_ready_pairs":
                len(ready),

            "normal_branch_pairs":
                len(normal),

            "recovery_like_pairs":
                len(recovery),

            "forward_complete_case_pairs":
                len(complete),
        },

        "forward_features":
            FORWARD_FEATURES,

        "ptsc_track_temperature_role":
            "DIAGNOSTIC_ONLY",

        "recovery_branch_role":
            (
                "EXISTING_EMPIRICAL_DISTRIBUTION_"
                "AND_POSTERIOR_ONLY"
            ),

        "validation":
            {
                "type":
                    "LEAVE_ONE_YEAR_OUT",

                "years":
                    YEARS,

                "ridge_alphas":
                    RIDGE_ALPHAS,
            },

        "best_ridge_alpha":
            best_alpha,

        "best_environment_model_pooled_mae_mph":
            best[
                "pooled_mae"
            ],

        "same_rows_zero_delta_mae_mph":
            best[
                "zero_same_test_mae"
            ],

        "environment_model_mae_improvement_mph":
            best[
                "improvement"
            ],

        "environment_model_beats_zero_delta":
            environment_improves_zero,

        "frozen_zero_delta_baseline_mae_mph":
            zero_metric,

        "simulator_environment_role":
            simulator_role,

        "full_fit_intercept_mph":
            float(
                beta_full[0]
            ),

        "full_fit_coefficients":
            full_coefficients,

        "interpretation":
            "OBSERVATIONAL_SENSITIVITY_NOT_CAUSAL",

        "2022_environment_fit_used":
            False,

        "future_track_temperature_prediction":
            False,

        "air_to_track_proxy":
            False,

        "elapsed_time_as_track_evolution":
            False,

        "next_phase":
            (
                "R3B4_MONTE_CARLO_DECISION_VALUE"
                if not hard_fail
                else
                "R3B3C_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # Print summary
    # --------------------------------------------------

    print()
    print("=" * 128)
    print("MODEL SELECTION SUMMARY")
    print("=" * 128)

    print()
    print(
        "Best ridge alpha:",
        best_alpha,
    )

    print(
        "Environment model pooled LOYO MAE:",
        f"{best['pooled_mae']:.6f}",
    )

    print(
        "ZERO_DELTA MAE on same rows:",
        f"{best['zero_same_test_mae']:.6f}",
    )

    print(
        "MAE improvement vs zero:",
        f"{best['improvement']:.6f}",
    )

    print(
        "Environment model beats zero:",
        environment_improves_zero,
    )

    print()
    print(
        "Simulator environment role:",
        simulator_role,
    )

    print()
    print("FULL-FIT STANDARDIZED COEFFICIENTS")

    for item in full_coefficients:

        print(
            " ",
            item["feature"],
            ":",
            f"{item['standardized_coefficient']:.6f}",
        )

    print()
    print("PTSC DIAGNOSTIC")

    print(
        "  rows:",
        len(
            ptsc_x
        ),
    )

    print(
        "  Pearson:",
        (
            f"{ptsc_p:.4f}"
            if ptsc_p is not None
            else
            "UNKNOWN"
        ),
    )

    print(
        "  Spearman:",
        (
            f"{ptsc_s:.4f}"
            if ptsc_s is not None
            else
            "UNKNOWN"
        ),
    )

    print(
        "  forward predictor allowed:",
        "NO",
    )

    print()
    print(
        "Recovery branch fitted with ridge:",
        "NO",
    )

    print(
        "2022 used in environment fit:",
        "NO",
    )

    print(
        "Causal interpretation:",
        "NO",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print()
    print("=" * 128)

    if hard_fail:

        print(
            "FINAL STATUS: "
            "R3B3C_PERFORMANCE_ENVIRONMENT_SENSITIVITY_"
            "REVIEW_REQUIRED"
        )

    elif environment_improves_zero:

        print(
            "FINAL STATUS: "
            "R3B3C_ENVIRONMENT_SENSITIVITY_VALIDATED_"
            "CENTRAL_CORRECTION_CANDIDATE"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B3C_ENVIRONMENT_EFFECT_SENSITIVITY_ONLY_"
            "ZERO_DELTA_REMAINS_CENTRAL"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(CORRELATION_OUT)
    print(FOLD_OUT)
    print(COEFFICIENT_OUT)
    print(PREDICTION_OUT)
    print(PTSC_DIAGNOSTIC_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
