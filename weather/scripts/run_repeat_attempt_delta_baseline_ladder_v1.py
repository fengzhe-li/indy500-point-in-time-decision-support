from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


# ============================================================
# INPUT
# ============================================================

INPUT_FILE = Path(
    "weather/output/"
    "attempt_performance_repeat_delta_context_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

PREDICTIONS_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_baseline_predictions_v1.csv"
)

FOLD_METRICS_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_baseline_fold_metrics_v1.csv"
)

AGGREGATE_METRICS_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_baseline_aggregate_metrics_v1.csv"
)

COEFFICIENT_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_model_coefficients_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_baseline_qa_v1.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "repeat_attempt_delta_baseline_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

TARGET = (
    "target_speed_delta_vs_best_prior_mph"
)

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

SENSITIVITY_YEAR = 2024

EXPECTED_PRIMARY_ROWS = 39
EXPECTED_TOTAL_ROWS = 40

RANDOM_STATE = 500


FEATURES = [
    "baseline_speed_mph",
    "seconds_since_baseline_attempt",
    "prior_supported_attempt_count",
    "delta_temp_c",
    "delta_relative_humidity_pct",
    "delta_wind_speed_10m_ms",
    "delta_pressure_hpa",
    "delta_cloud_cover_pct",
    "delta_shortwave_radiation_wm2",
    "delta_forecast_wind_direction_sin",
    "delta_forecast_wind_direction_cos",
]


MODEL_NAMES = [
    "ZERO_DELTA_BASELINE",
    "TRAIN_MEAN_DELTA",
    "RIDGE",
    "HUBER",
    "ELASTIC_NET",
]


# ============================================================
# HELPERS
# ============================================================

def read_required(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def rmse(
    y_true,
    y_pred,
):

    return float(
        np.sqrt(
            mean_squared_error(
                y_true,
                y_pred,
            )
        )
    )


def safe_r2(
    y_true,
    y_pred,
):

    if len(
        y_true
    ) < 2:
        return np.nan

    return float(
        r2_score(
            y_true,
            y_pred,
        )
    )


def metric_bundle(
    y_true,
    y_pred,
):

    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    residual = (
        y_pred
        - y_true
    )

    actual_positive = (
        y_true > 0
    )

    predicted_positive = (
        y_pred > 0
    )

    sign_accuracy = float(
        np.mean(
            actual_positive
            == predicted_positive
        )
    )

    return {
        "mae_mph":
            float(
                mean_absolute_error(
                    y_true,
                    y_pred,
                )
            ),

        "rmse_mph":
            rmse(
                y_true,
                y_pred,
            ),

        "r2":
            safe_r2(
                y_true,
                y_pred,
            ),

        "mean_error_pred_minus_actual_mph":
            float(
                residual.mean()
            ),

        "median_absolute_error_mph":
            float(
                np.median(
                    np.abs(
                        residual
                    )
                )
            ),

        "max_absolute_error_mph":
            float(
                np.max(
                    np.abs(
                        residual
                    )
                )
            ),

        "gain_loss_sign_accuracy":
            sign_accuracy,

        "actual_gain_rate":
            float(
                actual_positive.mean()
            ),

        "predicted_gain_rate":
            float(
                predicted_positive.mean()
            ),
    }


def stable_hash(payload):

    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def build_models():

    return {
        "RIDGE":
            Pipeline(
                [
                    (
                        "scale",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        Ridge(
                            alpha=3.0,
                        ),
                    ),
                ]
            ),

        "HUBER":
            Pipeline(
                [
                    (
                        "scale",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        HuberRegressor(
                            epsilon=1.35,
                            alpha=1.0,
                            max_iter=10000,
                        ),
                    ),
                ]
            ),

        "ELASTIC_NET":
            Pipeline(
                [
                    (
                        "scale",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        ElasticNet(
                            alpha=0.10,
                            l1_ratio=0.5,
                            max_iter=100000,
                            random_state=RANDOM_STATE,
                        ),
                    ),
                ]
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    df = read_required(
        INPUT_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5B-2B — REPEAT-ATTEMPT "
        "DELTA BASELINE MODEL LADDER V1"
    )
    print("=" * 100)

    print()
    print(
        "Input rows:",
        len(df)
    )

    # ========================================================
    # Validate input
    # ========================================================

    if len(
        df
    ) != EXPECTED_TOTAL_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_ROWS} rows, "
            f"got {len(df)}"
        )

    required = [
        "current_attempt_id",
        "baseline_attempt_id",
        "session_id",
        "year",
        "car_number",
        "driver_name",
        TARGET,
    ] + FEATURES

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(
                missing
            )
        )

    if df[
        "current_attempt_id"
    ].duplicated().any():

        raise RuntimeError(
            "Duplicate current_attempt_id."
        )

    work = df.copy()

    work[
        "year"
    ] = numeric(
        work[
            "year"
        ]
    ).astype(int)

    work[
        TARGET
    ] = numeric(
        work[
            TARGET
        ]
    )

    for feature in FEATURES:

        work[
            feature
        ] = numeric(
            work[
                feature
            ]
        )

    if work[
        FEATURES
    ].isna().any().any():

        missing_counts = (
            work[
                FEATURES
            ]
            .isna()
            .sum()
        )

        print()
        print(
            missing_counts[
                missing_counts > 0
            ]
        )

        raise RuntimeError(
            "Missing model features."
        )

    if work[
        TARGET
    ].isna().any():

        raise RuntimeError(
            "Missing delta target."
        )

    primary = work[
        work[
            "year"
        ].isin(
            PRIMARY_YEARS
        )
    ].copy()

    sensitivity = work[
        work[
            "year"
        ]
        == SENSITIVITY_YEAR
    ].copy()

    if len(
        primary
    ) != EXPECTED_PRIMARY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_PRIMARY_ROWS} primary rows, "
            f"got {len(primary)}"
        )

    # ========================================================
    # Print feature set
    # ========================================================

    print()
    print("DELTA MODEL FEATURES")
    print("-" * 100)

    for feature in FEATURES:
        print(feature)

    print()
    print("PRIMARY ROWS BY YEAR")
    print("-" * 70)

    print(
        primary[
            "year"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ========================================================
    # Model definitions
    # ========================================================

    model_templates = build_models()

    policy_payload = {
        "phase":
            "5B-2B",

        "target":
            TARGET,

        "features":
            FEATURES,

        "primary_years":
            PRIMARY_YEARS,

        "models":
            {
                "ZERO_DELTA_BASELINE":
                    "always_predict_zero",

                "TRAIN_MEAN_DELTA":
                    "training_fold_target_mean",

                "RIDGE":
                    {
                        "alpha":
                            3.0,
                    },

                "HUBER":
                    {
                        "epsilon":
                            1.35,

                        "alpha":
                            1.0,
                    },

                "ELASTIC_NET":
                    {
                        "alpha":
                            0.10,

                        "l1_ratio":
                            0.5,
                    },
            },
    }

    model_policy_hash = stable_hash(
        policy_payload
    )

    prediction_rows = []
    metric_rows = []
    coefficient_rows = []

    # ========================================================
    # LOYO primary evaluation
    # ========================================================

    for test_year in PRIMARY_YEARS:

        train_years = [
            year
            for year in PRIMARY_YEARS
            if year != test_year
        ]

        train = primary[
            primary[
                "year"
            ].isin(
                train_years
            )
        ].copy()

        test = primary[
            primary[
                "year"
            ]
            == test_year
        ].copy()

        X_train = (
            train[
                FEATURES
            ]
            .astype(float)
        )

        y_train = (
            train[
                TARGET
            ]
            .astype(float)
        )

        X_test = (
            test[
                FEATURES
            ]
            .astype(float)
        )

        y_test = (
            test[
                TARGET
            ]
            .astype(float)
        )

        fold_id = (
            f"DELTA_LOYO_{test_year}"
        )

        # ----------------------------------------------------
        # ZERO baseline
        # ----------------------------------------------------

        zero_pred = np.zeros(
            len(test),
            dtype=float,
        )

        metrics = metric_bundle(
            y_test,
            zero_pred,
        )

        metric_rows.append(
            {
                "fold_id":
                    fold_id,

                "test_year":
                    test_year,

                "train_years":
                    ",".join(
                        str(y)
                        for y in train_years
                    ),

                "model_name":
                    "ZERO_DELTA_BASELINE",

                "train_rows":
                    len(train),

                "test_rows":
                    len(test),

                **metrics,
            }
        )

        # ----------------------------------------------------
        # Train-mean baseline
        # ----------------------------------------------------

        train_mean = float(
            y_train.mean()
        )

        mean_pred = np.full(
            len(test),
            train_mean,
            dtype=float,
        )

        metrics_mean = metric_bundle(
            y_test,
            mean_pred,
        )

        metric_rows.append(
            {
                "fold_id":
                    fold_id,

                "test_year":
                    test_year,

                "train_years":
                    ",".join(
                        str(y)
                        for y in train_years
                    ),

                "model_name":
                    "TRAIN_MEAN_DELTA",

                "train_rows":
                    len(train),

                "test_rows":
                    len(test),

                **metrics_mean,
            }
        )

        # ----------------------------------------------------
        # Store baseline predictions
        # ----------------------------------------------------

        for model_name, preds in [
            (
                "ZERO_DELTA_BASELINE",
                zero_pred,
            ),
            (
                "TRAIN_MEAN_DELTA",
                mean_pred,
            ),
        ]:

            for (
                current_attempt_id,
                baseline_attempt_id,
                car_number,
                driver_name,
                actual,
                pred,
            ) in zip(
                test[
                    "current_attempt_id"
                ],
                test[
                    "baseline_attempt_id"
                ],
                test[
                    "car_number"
                ],
                test[
                    "driver_name"
                ],
                y_test,
                preds,
            ):

                prediction_rows.append(
                    {
                        "fold_id":
                            fold_id,

                        "test_year":
                            test_year,

                        "model_name":
                            model_name,

                        "current_attempt_id":
                            current_attempt_id,

                        "baseline_attempt_id":
                            baseline_attempt_id,

                        "car_number":
                            car_number,

                        "driver_name":
                            driver_name,

                        "actual_delta_mph":
                            float(actual),

                        "predicted_delta_mph":
                            float(pred),

                        "residual_pred_minus_actual_mph":
                            float(
                                pred - actual
                            ),

                        "absolute_error_mph":
                            float(
                                abs(
                                    pred - actual
                                )
                            ),

                        "actual_gain":
                            bool(
                                actual > 0
                            ),

                        "predicted_gain":
                            bool(
                                pred > 0
                            ),
                    }
                )

        # ----------------------------------------------------
        # Trained models
        # ----------------------------------------------------

        for (
            model_name,
            template,
        ) in model_templates.items():

            model = clone(
                template
            )

            model.fit(
                X_train,
                y_train,
            )

            pred = model.predict(
                X_test
            )

            metrics_model = metric_bundle(
                y_test,
                pred,
            )

            metric_rows.append(
                {
                    "fold_id":
                        fold_id,

                    "test_year":
                        test_year,

                    "train_years":
                        ",".join(
                            str(y)
                            for y in train_years
                        ),

                    "model_name":
                        model_name,

                    "train_rows":
                        len(train),

                    "test_rows":
                        len(test),

                    **metrics_model,
                }
            )

            for (
                current_attempt_id,
                baseline_attempt_id,
                car_number,
                driver_name,
                actual,
                predicted,
            ) in zip(
                test[
                    "current_attempt_id"
                ],
                test[
                    "baseline_attempt_id"
                ],
                test[
                    "car_number"
                ],
                test[
                    "driver_name"
                ],
                y_test,
                pred,
            ):

                prediction_rows.append(
                    {
                        "fold_id":
                            fold_id,

                        "test_year":
                            test_year,

                        "model_name":
                            model_name,

                        "current_attempt_id":
                            current_attempt_id,

                        "baseline_attempt_id":
                            baseline_attempt_id,

                        "car_number":
                            car_number,

                        "driver_name":
                            driver_name,

                        "actual_delta_mph":
                            float(actual),

                        "predicted_delta_mph":
                            float(predicted),

                        "residual_pred_minus_actual_mph":
                            float(
                                predicted
                                - actual
                            ),

                        "absolute_error_mph":
                            float(
                                abs(
                                    predicted
                                    - actual
                                )
                            ),

                        "actual_gain":
                            bool(
                                actual > 0
                            ),

                        "predicted_gain":
                            bool(
                                predicted > 0
                            ),
                    }
                )

            fitted = model.named_steps[
                "model"
            ]

            coef = getattr(
                fitted,
                "coef_",
                None,
            )

            if coef is not None:

                for feature, value in zip(
                    FEATURES,
                    coef,
                ):

                    coefficient_rows.append(
                        {
                            "fold_id":
                                fold_id,

                            "test_year":
                                test_year,

                            "model_name":
                                model_name,

                            "feature_name":
                                feature,

                            "standardized_coefficient":
                                float(value),
                        }
                    )

    predictions = pd.DataFrame(
        prediction_rows
    )

    fold_metrics = pd.DataFrame(
        metric_rows
    )

    coefficients = pd.DataFrame(
        coefficient_rows
    )

    # ========================================================
    # Aggregate pooled primary results
    # ========================================================

    aggregate_rows = []

    for model_name in MODEL_NAMES:

        subset = predictions[
            predictions[
                "model_name"
            ]
            == model_name
        ].copy()

        if len(
            subset
        ) != EXPECTED_PRIMARY_ROWS:

            raise RuntimeError(
                f"{model_name}: expected "
                f"{EXPECTED_PRIMARY_ROWS} predictions, "
                f"got {len(subset)}"
            )

        bundle = metric_bundle(
            subset[
                "actual_delta_mph"
            ],
            subset[
                "predicted_delta_mph"
            ],
        )

        fold_subset = fold_metrics[
            fold_metrics[
                "model_name"
            ]
            == model_name
        ]

        aggregate_rows.append(
            {
                "model_name":
                    model_name,

                "prediction_rows":
                    len(subset),

                "pooled_mae_mph":
                    bundle[
                        "mae_mph"
                    ],

                "pooled_rmse_mph":
                    bundle[
                        "rmse_mph"
                    ],

                "pooled_r2":
                    bundle[
                        "r2"
                    ],

                "pooled_mean_error_pred_minus_actual_mph":
                    bundle[
                        "mean_error_pred_minus_actual_mph"
                    ],

                "pooled_gain_loss_sign_accuracy":
                    bundle[
                        "gain_loss_sign_accuracy"
                    ],

                "mean_fold_mae_mph":
                    float(
                        fold_subset[
                            "mae_mph"
                        ].mean()
                    ),

                "worst_fold_mae_mph":
                    float(
                        fold_subset[
                            "mae_mph"
                        ].max()
                    ),

                "best_fold_mae_mph":
                    float(
                        fold_subset[
                            "mae_mph"
                        ].min()
                    ),
            }
        )

    aggregate = pd.DataFrame(
        aggregate_rows
    )

    zero_mae = float(
        aggregate.loc[
            aggregate[
                "model_name"
            ]
            == "ZERO_DELTA_BASELINE",
            "pooled_mae_mph",
        ].iloc[0]
    )

    aggregate[
        "mae_improvement_vs_zero_mph"
    ] = (
        zero_mae
        - aggregate[
            "pooled_mae_mph"
        ]
    )

    aggregate[
        "mae_relative_improvement_vs_zero_pct"
    ] = (
        aggregate[
            "mae_improvement_vs_zero_mph"
        ]
        / zero_mae
        * 100.0
    )

    aggregate = (
        aggregate
        .sort_values(
            [
                "pooled_mae_mph",
                "pooled_rmse_mph",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    aggregate[
        "mae_rank"
    ] = (
        np.arange(
            1,
            len(
                aggregate
            ) + 1,
        )
    )

    # ========================================================
    # 2024 one-row sensitivity
    # ========================================================

    sensitivity_rows = []

    if len(
        sensitivity
    ) == 1:

        train = primary.copy()

        X_train = train[
            FEATURES
        ].astype(float)

        y_train = train[
            TARGET
        ].astype(float)

        X_test = sensitivity[
            FEATURES
        ].astype(float)

        actual = float(
            sensitivity[
                TARGET
            ].iloc[0]
        )

        sensitivity_predictions = {
            "ZERO_DELTA_BASELINE":
                0.0,

            "TRAIN_MEAN_DELTA":
                float(
                    y_train.mean()
                ),
        }

        for (
            model_name,
            template,
        ) in model_templates.items():

            model = clone(
                template
            )

            model.fit(
                X_train,
                y_train,
            )

            sensitivity_predictions[
                model_name
            ] = float(
                model.predict(
                    X_test
                )[0]
            )

        for (
            model_name,
            predicted,
        ) in sensitivity_predictions.items():

            sensitivity_rows.append(
                {
                    "year":
                        2024,

                    "model_name":
                        model_name,

                    "actual_delta_mph":
                        actual,

                    "predicted_delta_mph":
                        predicted,

                    "absolute_error_mph":
                        abs(
                            predicted
                            - actual
                        ),

                    "interpretation":
                        "ONE_ROW_SENSITIVITY_ONLY",
                }
            )

    sensitivity_result = pd.DataFrame(
        sensitivity_rows
    )

    # ========================================================
    # Best model diagnostics
    # ========================================================

    best_model = str(
        aggregate.iloc[0][
            "model_name"
        ]
    )

    best_predictions = (
        predictions[
            predictions[
                "model_name"
            ]
            == best_model
        ]
        .sort_values(
            "absolute_error_mph",
            ascending=False,
        )
    )

    # ========================================================
    # QA
    # ========================================================

    expected_prediction_rows = (
        EXPECTED_PRIMARY_ROWS
        * len(
            MODEL_NAMES
        )
    )

    expected_metric_rows = (
        len(
            PRIMARY_YEARS
        )
        * len(
            MODEL_NAMES
        )
    )

    checks = {
        "input_rows_equal_40":
            len(
                work
            ) == 40,

        "primary_rows_equal_39":
            len(
                primary
            ) == 39,

        "feature_count_equal_11":
            len(
                FEATURES
            ) == 11,

        "all_features_complete":
            not work[
                FEATURES
            ].isna().any().any(),

        "prediction_rows_match_expected":
            len(
                predictions
            )
            == expected_prediction_rows,

        "fold_metric_rows_match_expected":
            len(
                fold_metrics
            )
            == expected_metric_rows,

        "five_models_present":
            set(
                aggregate[
                    "model_name"
                ]
            )
            == set(
                MODEL_NAMES
            ),

        "all_predictions_finite":
            np.isfinite(
                predictions[
                    "predicted_delta_mph"
                ]
            ).all(),

        "all_primary_metrics_finite":
            np.isfinite(
                aggregate[
                    [
                        "pooled_mae_mph",
                        "pooled_rmse_mph",
                        "pooled_r2",
                    ]
                ].to_numpy(
                    dtype=float
                )
            ).all(),

        "zero_baseline_mae_matches_frozen_primary_data":
            np.isclose(
                zero_mae,
                float(
                    primary[
                        TARGET
                    ].abs().mean()
                ),
                atol=1e-12,
                rtol=0.0,
            ),
    }

    qa_rows = []

    for (
        metric,
        passed,
    ) in checks.items():

        qa_rows.append(
            {
                "metric":
                    metric,

                "value":
                    int(
                        bool(
                            passed
                        )
                    ),

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    qa_rows.extend(
        [
            {
                "metric":
                    "primary_zero_delta_mae_mph",

                "value":
                    zero_mae,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "aggregate_best_model",

                "value":
                    best_model,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "aggregate_best_mae_mph",

                "value":
                    float(
                        aggregate.iloc[0][
                            "pooled_mae_mph"
                        ]
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "aggregate_best_improvement_vs_zero_mph",

                "value":
                    float(
                        aggregate.iloc[0][
                            "mae_improvement_vs_zero_mph"
                        ]
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "model_policy_hash",

                "value":
                    model_policy_hash,

                "status":
                    "INFO",
            },
        ]
    )

    qa = pd.DataFrame(
        qa_rows
    )

    all_pass = all(
        checks.values()
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("PRIMARY FOLD METRICS")
    print("-" * 150)

    print(
        fold_metrics[
            [
                "test_year",
                "model_name",
                "train_rows",
                "test_rows",
                "mae_mph",
                "rmse_mph",
                "r2",
                "mean_error_pred_minus_actual_mph",
                "gain_loss_sign_accuracy",
            ]
        ]
        .sort_values(
            [
                "test_year",
                "mae_mph",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print("AGGREGATE PRIMARY DELTA RESULTS")
    print("-" * 160)

    print(
        aggregate[
            [
                "mae_rank",
                "model_name",
                "pooled_mae_mph",
                "pooled_rmse_mph",
                "pooled_r2",
                "pooled_mean_error_pred_minus_actual_mph",
                "pooled_gain_loss_sign_accuracy",
                "mean_fold_mae_mph",
                "worst_fold_mae_mph",
                "mae_improvement_vs_zero_mph",
                "mae_relative_improvement_vs_zero_pct",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("BEST MODEL BY TEST YEAR")
    print("-" * 100)

    best_by_year = (
        fold_metrics
        .sort_values(
            [
                "test_year",
                "mae_mph",
            ]
        )
        .groupby(
            "test_year",
            as_index=False,
        )
        .head(1)
    )

    print(
        best_by_year[
            [
                "test_year",
                "model_name",
                "mae_mph",
                "rmse_mph",
                "gain_loss_sign_accuracy",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print(
        "WORST 15 PRIMARY DELTA PREDICTIONS "
        f"FOR AGGREGATE-BEST MODEL: {best_model}"
    )
    print("-" * 150)

    print(
        best_predictions[
            [
                "test_year",
                "car_number",
                "driver_name",
                "actual_delta_mph",
                "predicted_delta_mph",
                "absolute_error_mph",
                "actual_gain",
                "predicted_gain",
            ]
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    print()
    print("2024 ONE-ROW SENSITIVITY")
    print("-" * 120)

    if sensitivity_result.empty:

        print(
            "No 2024 sensitivity row."
        )

    else:

        print(
            sensitivity_result
            .sort_values(
                "absolute_error_mph"
            )
            .to_string(
                index=False
            )
        )

    print()
    print("QA")
    print("-" * 120)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    predictions[
        "model_policy_hash"
    ] = model_policy_hash

    fold_metrics[
        "model_policy_hash"
    ] = model_policy_hash

    aggregate[
        "model_policy_hash"
    ] = model_policy_hash

    if not coefficients.empty:

        coefficients[
            "model_policy_hash"
        ] = model_policy_hash

    PREDICTIONS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    predictions.to_csv(
        PREDICTIONS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    fold_metrics.to_csv(
        FOLD_METRICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    aggregate.to_csv(
        AGGREGATE_METRICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    coefficients.to_csv(
        COEFFICIENT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # REPORT
    # ========================================================

    zero_row = aggregate[
        aggregate[
            "model_name"
        ]
        == "ZERO_DELTA_BASELINE"
    ].iloc[0]

    best_row = aggregate.iloc[0]

    report = []

    report.append(
        "# Repeat-Attempt Delta Baseline Ladder V1"
    )

    report.append("")

    report.append(
        f"Primary rows: `{len(primary)}`"
    )

    report.append(
        f"Target: `{TARGET}`"
    )

    report.append("")

    report.append(
        "## Reference baseline"
    )

    report.append("")

    report.append(
        "`ZERO_DELTA_BASELINE` assumes the next attempt "
        "matches the best prior supported speed."
    )

    report.append(
        f"Primary pooled MAE: "
        f"`{float(zero_row['pooled_mae_mph']):.6f} mph`"
    )

    report.append("")

    report.append(
        "## Aggregate result"
    )

    report.append("")

    report.append(
        f"Best model: `{best_model}`"
    )

    report.append(
        f"Best pooled MAE: "
        f"`{float(best_row['pooled_mae_mph']):.6f} mph`"
    )

    report.append(
        f"Improvement vs zero-delta baseline: "
        f"`{float(best_row['mae_improvement_vs_zero_mph']):.6f} mph`"
    )

    report.append(
        f"Relative improvement: "
        f"`{float(best_row['mae_relative_improvement_vs_zero_pct']):.3f}%`"
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- This predicts repeat-attempt performance delta only."
    )

    report.append(
        "- It does not model queue waiting."
    )

    report.append(
        "- It does not yet produce retain/withdraw expected utility."
    )

    report.append(
        "- 2024 has one supported row and is sensitivity-only."
    )

    report.append(
        "- No hyperparameter search was performed."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**REPEAT_DELTA_BASELINE_LADDER_COMPLETE**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "REPEAT_DELTA_BASELINE_LADDER_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "IMPORTANT: no winning delta model is frozen yet."
    )

    print(
        "Promotion requires improvement over ZERO_DELTA_BASELINE "
        "plus acceptable cross-year stability."
    )

    print()
    print("OUTPUTS")

    print(
        PREDICTIONS_FILE
    )

    print(
        FOLD_METRICS_FILE
    )

    print(
        AGGREGATE_METRICS_FILE
    )

    print(
        COEFFICIENT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
