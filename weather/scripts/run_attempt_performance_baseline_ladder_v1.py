from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd


# ============================================================
# SKLEARN IMPORTS
# ============================================================

try:
    from sklearn.base import clone

    from sklearn.pipeline import Pipeline

    from sklearn.preprocessing import StandardScaler

    from sklearn.linear_model import (
        Ridge,
        ElasticNet,
    )

    from sklearn.ensemble import (
        RandomForestRegressor,
        HistGradientBoostingRegressor,
    )

    from sklearn.metrics import (
        mean_absolute_error,
        mean_squared_error,
        r2_score,
    )

except ImportError as exc:

    raise RuntimeError(
        "scikit-learn is required for Phase 5B-0. "
        "Do not modify the project data. "
        f"Import error: {exc}"
    )


# ============================================================
# INPUTS
# ============================================================

MODEL_MATRIX_FILE = Path(
    "weather/output/"
    "attempt_performance_model_matrix_v1.csv"
)

FEATURE_MANIFEST_FILE = Path(
    "weather/output/"
    "attempt_performance_feature_manifest_v1.csv"
)

VALIDATION_FOLDS_FILE = Path(
    "weather/output/"
    "attempt_performance_validation_folds_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

PREDICTIONS_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_predictions_v1.csv"
)

FOLD_METRICS_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_fold_metrics_v1.csv"
)

AGGREGATE_METRICS_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_aggregate_metrics_v1.csv"
)

MODEL_DIAGNOSTICS_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_model_diagnostics_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_v1.md"
)


# ============================================================
# FROZEN DESIGN
# ============================================================

TARGET = (
    "four_lap_average_speed_mph"
)

EXPECTED_MODEL_ROWS = 123

EXPECTED_FEATURE_COUNT = 12

EXPECTED_YEAR_COUNTS = {
    2020: 39,
    2021: 49,
    2023: 28,
    2024: 7,
}

FEATURE_SET_ID = (
    "ATTEMPT_PERFORMANCE_FEATURE_SET_V1"
)

VALIDATION_PROTOCOL_ID = (
    "YEAR_GROUPED_LOYO_V1"
)

RANDOM_STATE = 500


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


def parse_years(value):

    if pd.isna(value):
        return []

    parts = str(
        value
    ).split(",")

    output = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        output.append(
            int(
                float(
                    part
                )
            )
        )

    return output


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
            float(
                r2_score(
                    y_true,
                    y_pred,
                )
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
    }


# ============================================================
# MODELS
# ============================================================

def build_models():

    models = {}

    models[
        "RIDGE"
    ] = Pipeline(
        steps=[
            (
                "scale",
                StandardScaler(),
            ),
            (
                "model",
                Ridge(
                    alpha=1.0,
                ),
            ),
        ]
    )

    models[
        "ELASTIC_NET"
    ] = Pipeline(
        steps=[
            (
                "scale",
                StandardScaler(),
            ),
            (
                "model",
                ElasticNet(
                    alpha=0.05,
                    l1_ratio=0.5,
                    max_iter=100000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )

    models[
        "RANDOM_FOREST"
    ] = RandomForestRegressor(
        n_estimators=500,
        max_depth=4,
        min_samples_leaf=3,
        max_features="sqrt",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    models[
        "HIST_GRADIENT_BOOSTING"
    ] = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=250,
        max_leaf_nodes=7,
        min_samples_leaf=8,
        l2_regularization=1.0,
        random_state=RANDOM_STATE,
    )

    return models


# ============================================================
# MAIN
# ============================================================

def main():

    matrix = read_required(
        MODEL_MATRIX_FILE
    )

    manifest = read_required(
        FEATURE_MANIFEST_FILE
    )

    folds = read_required(
        VALIDATION_FOLDS_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5B-0 — ATTEMPT-PERFORMANCE "
        "BASELINE MODEL LADDER V1"
    )
    print("=" * 100)

    print()
    print(
        "Model matrix rows:",
        len(matrix)
    )

    print(
        "Feature manifest rows:",
        len(manifest)
    )

    print(
        "Validation folds:",
        len(folds)
    )

    # ========================================================
    # Validate frozen design
    # ========================================================

    if len(
        matrix
    ) != EXPECTED_MODEL_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_MODEL_ROWS} model rows, "
            f"got {len(matrix)}"
        )

    if TARGET not in matrix.columns:

        raise RuntimeError(
            f"Missing target: {TARGET}"
        )

    if matrix[
        "attempt_id"
    ].duplicated().any():

        raise RuntimeError(
            "Duplicate attempt_id in model matrix."
        )

    if (
        "included_v1"
        not in manifest.columns
    ):

        raise RuntimeError(
            "Feature manifest missing included_v1."
        )

    included_mask = (
        manifest[
            "included_v1"
        ]
        .astype(str)
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )

    features = (
        manifest.loc[
            included_mask,
            "feature_name",
        ]
        .astype(str)
        .tolist()
    )

    if len(
        features
    ) != EXPECTED_FEATURE_COUNT:

        raise RuntimeError(
            f"Expected {EXPECTED_FEATURE_COUNT} features, "
            f"got {len(features)}"
        )

    missing_features = [
        feature
        for feature in features
        if feature not in matrix.columns
    ]

    if missing_features:

        raise RuntimeError(
            "Frozen features missing from model matrix: "
            + ", ".join(
                missing_features
            )
        )

    if matrix[
        features
    ].isna().any().any():

        raise RuntimeError(
            "Frozen model matrix contains feature missingness."
        )

    if matrix[
        TARGET
    ].isna().any():

        raise RuntimeError(
            "Model matrix contains missing targets."
        )

    matrix[
        "year"
    ] = pd.to_numeric(
        matrix[
            "year"
        ],
        errors="raise",
    ).astype(int)

    actual_counts = (
        matrix[
            "year"
        ]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    if (
        actual_counts
        != EXPECTED_YEAR_COUNTS
    ):

        raise RuntimeError(
            "Year counts differ from frozen design.\n"
            f"Expected: {EXPECTED_YEAR_COUNTS}\n"
            f"Actual:   {actual_counts}"
        )

    # ========================================================
    # Print frozen inputs
    # ========================================================

    print()
    print("FROZEN FEATURES")
    print("-" * 100)

    for feature in features:
        print(
            feature
        )

    print()
    print("TARGET ROWS BY YEAR")
    print("-" * 70)

    print(
        matrix[
            "year"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ========================================================
    # Model definitions
    # ========================================================

    model_templates = (
        build_models()
    )

    print()
    print("MODEL LADDER")
    print("-" * 70)

    print(
        "MEAN_BASELINE"
    )

    for model_name in (
        model_templates.keys()
    ):
        print(
            model_name
        )

    # ========================================================
    # Evaluation
    # ========================================================

    prediction_rows = []
    fold_metric_rows = []
    diagnostic_rows = []

    primary_fold_ids = []

    sensitivity_fold_ids = []

    for _, fold in (
        folds.iterrows()
    ):

        fold_id = str(
            fold[
                "fold_id"
            ]
        )

        fold_role = str(
            fold[
                "fold_role"
            ]
        )

        test_year = int(
            fold[
                "test_year"
            ]
        )

        train_years = (
            parse_years(
                fold[
                    "train_years"
                ]
            )
        )

        if (
            fold_role
            == "PRIMARY"
        ):
            primary_fold_ids.append(
                fold_id
            )

        elif (
            fold_role
            == "SENSITIVITY_ONLY"
        ):
            sensitivity_fold_ids.append(
                fold_id
            )

        train = matrix[
            matrix[
                "year"
            ].isin(
                train_years
            )
        ].copy()

        test = matrix[
            matrix[
                "year"
            ]
            == test_year
        ].copy()

        expected_train_rows = int(
            fold[
                "train_rows"
            ]
        )

        expected_test_rows = int(
            fold[
                "test_rows"
            ]
        )

        if len(
            train
        ) != expected_train_rows:

            raise RuntimeError(
                f"{fold_id}: expected "
                f"{expected_train_rows} training rows, "
                f"got {len(train)}"
            )

        if len(
            test
        ) != expected_test_rows:

            raise RuntimeError(
                f"{fold_id}: expected "
                f"{expected_test_rows} test rows, "
                f"got {len(test)}"
            )

        X_train = (
            train[
                features
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
                features
            ]
            .astype(float)
        )

        y_test = (
            test[
                TARGET
            ]
            .astype(float)
        )

        # ----------------------------------------------------
        # Mean baseline
        # ----------------------------------------------------

        train_mean = float(
            y_train.mean()
        )

        mean_pred = np.full(
            shape=len(
                test
            ),
            fill_value=train_mean,
            dtype=float,
        )

        metrics = metric_bundle(
            y_test,
            mean_pred,
        )

        fold_metric_rows.append(
            {
                "fold_id":
                    fold_id,

                "fold_role":
                    fold_role,

                "test_year":
                    test_year,

                "train_years":
                    ",".join(
                        str(year)
                        for year in train_years
                    ),

                "model_name":
                    "MEAN_BASELINE",

                "train_rows":
                    len(train),

                "test_rows":
                    len(test),

                **metrics,
            }
        )

        for (
            attempt_id,
            session_id,
            car_number,
            driver_name,
            actual,
            predicted,
        ) in zip(
            test[
                "attempt_id"
            ],
            test[
                "session_id"
            ],
            test[
                "car_number"
            ],
            test[
                "driver_name"
            ],
            y_test,
            mean_pred,
        ):

            prediction_rows.append(
                {
                    "fold_id":
                        fold_id,

                    "fold_role":
                        fold_role,

                    "model_name":
                        "MEAN_BASELINE",

                    "test_year":
                        test_year,

                    "attempt_id":
                        attempt_id,

                    "session_id":
                        session_id,

                    "car_number":
                        car_number,

                    "driver_name":
                        driver_name,

                    "actual_speed_mph":
                        float(
                            actual
                        ),

                    "predicted_speed_mph":
                        float(
                            predicted
                        ),

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
                }
            )

        # ----------------------------------------------------
        # Trained models
        # ----------------------------------------------------

        for (
            model_name,
            model_template,
        ) in model_templates.items():

            model = clone(
                model_template
            )

            model.fit(
                X_train,
                y_train,
            )

            prediction = (
                model.predict(
                    X_test
                )
            )

            metrics = metric_bundle(
                y_test,
                prediction,
            )

            fold_metric_rows.append(
                {
                    "fold_id":
                        fold_id,

                    "fold_role":
                        fold_role,

                    "test_year":
                        test_year,

                    "train_years":
                        ",".join(
                            str(year)
                            for year
                            in train_years
                        ),

                    "model_name":
                        model_name,

                    "train_rows":
                        len(train),

                    "test_rows":
                        len(test),

                    **metrics,
                }
            )

            for (
                attempt_id,
                session_id,
                car_number,
                driver_name,
                actual,
                predicted,
            ) in zip(
                test[
                    "attempt_id"
                ],
                test[
                    "session_id"
                ],
                test[
                    "car_number"
                ],
                test[
                    "driver_name"
                ],
                y_test,
                prediction,
            ):

                prediction_rows.append(
                    {
                        "fold_id":
                            fold_id,

                        "fold_role":
                            fold_role,

                        "model_name":
                            model_name,

                        "test_year":
                            test_year,

                        "attempt_id":
                            attempt_id,

                        "session_id":
                            session_id,

                        "car_number":
                            car_number,

                        "driver_name":
                            driver_name,

                        "actual_speed_mph":
                            float(
                                actual
                            ),

                        "predicted_speed_mph":
                            float(
                                predicted
                            ),

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
                    }
                )

            # ------------------------------------------------
            # Basic model diagnostics
            # ------------------------------------------------

            if model_name in [
                "RIDGE",
                "ELASTIC_NET",
            ]:

                fitted_linear = (
                    model.named_steps[
                        "model"
                    ]
                )

                coefficients = (
                    fitted_linear.coef_
                )

                for (
                    feature,
                    coefficient,
                ) in zip(
                    features,
                    coefficients,
                ):

                    diagnostic_rows.append(
                        {
                            "fold_id":
                                fold_id,

                            "fold_role":
                                fold_role,

                            "test_year":
                                test_year,

                            "model_name":
                                model_name,

                            "diagnostic_type":
                                "STANDARDIZED_COEFFICIENT",

                            "feature_name":
                                feature,

                            "value":
                                float(
                                    coefficient
                                ),
                        }
                    )

            elif (
                model_name
                == "RANDOM_FOREST"
            ):

                importances = (
                    model.feature_importances_
                )

                for (
                    feature,
                    importance,
                ) in zip(
                    features,
                    importances,
                ):

                    diagnostic_rows.append(
                        {
                            "fold_id":
                                fold_id,

                            "fold_role":
                                fold_role,

                            "test_year":
                                test_year,

                            "model_name":
                                model_name,

                            "diagnostic_type":
                                "IMPURITY_FEATURE_IMPORTANCE",

                            "feature_name":
                                feature,

                            "value":
                                float(
                                    importance
                                ),
                        }
                    )

    predictions = pd.DataFrame(
        prediction_rows
    )

    fold_metrics = pd.DataFrame(
        fold_metric_rows
    )

    diagnostics = pd.DataFrame(
        diagnostic_rows
    )

    # ========================================================
    # Aggregate PRIMARY metrics
    #
    # Pool out-of-year predictions across 2020/21/23.
    # Each attempt appears exactly once for each model.
    # ========================================================

    primary_predictions = predictions[
        predictions[
            "fold_role"
        ]
        == "PRIMARY"
    ].copy()

    aggregate_rows = []

    model_names = [
        "MEAN_BASELINE",
        "RIDGE",
        "ELASTIC_NET",
        "RANDOM_FOREST",
        "HIST_GRADIENT_BOOSTING",
    ]

    for model_name in model_names:

        model_pred = (
            primary_predictions[
                primary_predictions[
                    "model_name"
                ]
                == model_name
            ]
            .copy()
        )

        if len(
            model_pred
        ) != 116:

            raise RuntimeError(
                f"{model_name}: expected 116 pooled "
                f"primary predictions, got {len(model_pred)}"
            )

        metrics = metric_bundle(
            model_pred[
                "actual_speed_mph"
            ],
            model_pred[
                "predicted_speed_mph"
            ],
        )

        mean_baseline_mae = (
            fold_metrics.loc[
                (
                    fold_metrics[
                        "fold_role"
                    ]
                    == "PRIMARY"
                )
                &
                (
                    fold_metrics[
                        "model_name"
                    ]
                    == "MEAN_BASELINE"
                ),
                "mae_mph",
            ]
            .mean()
        )

        model_fold_mean_mae = (
            fold_metrics.loc[
                (
                    fold_metrics[
                        "fold_role"
                    ]
                    == "PRIMARY"
                )
                &
                (
                    fold_metrics[
                        "model_name"
                    ]
                    == model_name
                ),
                "mae_mph",
            ]
            .mean()
        )

        aggregate_rows.append(
            {
                "model_name":
                    model_name,

                "primary_prediction_rows":
                    len(
                        model_pred
                    ),

                "pooled_primary_mae_mph":
                    metrics[
                        "mae_mph"
                    ],

                "pooled_primary_rmse_mph":
                    metrics[
                        "rmse_mph"
                    ],

                "pooled_primary_r2":
                    metrics[
                        "r2"
                    ],

                "pooled_primary_mean_error_pred_minus_actual_mph":
                    metrics[
                        "mean_error_pred_minus_actual_mph"
                    ],

                "mean_primary_fold_mae_mph":
                    float(
                        model_fold_mean_mae
                    ),

                "mean_baseline_primary_fold_mae_mph":
                    float(
                        mean_baseline_mae
                    ),

                "mean_fold_mae_improvement_vs_mean_baseline_mph":
                    float(
                        mean_baseline_mae
                        - model_fold_mean_mae
                    ),
            }
        )

    aggregate_metrics = pd.DataFrame(
        aggregate_rows
    )

    aggregate_metrics = (
        aggregate_metrics
        .sort_values(
            [
                "pooled_primary_mae_mph",
                "pooled_primary_rmse_mph",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    aggregate_metrics[
        "primary_mae_rank"
    ] = np.arange(
        1,
        len(
            aggregate_metrics
        )
        + 1,
    )

    # ========================================================
    # Sensitivity 2024
    # ========================================================

    sensitivity_metrics = fold_metrics[
        fold_metrics[
            "fold_role"
        ]
        == "SENSITIVITY_ONLY"
    ].copy()

    # ========================================================
    # QA
    # ========================================================

    expected_prediction_rows = (
        (
            39
            + 49
            + 28
            + 7
        )
        * len(
            model_names
        )
    )

    expected_fold_metric_rows = (
        4
        * len(
            model_names
        )
    )

    primary_counts = (
        primary_predictions
        .groupby(
            "model_name"
        )
        .size()
        .to_dict()
    )

    sensitivity_counts = (
        predictions[
            predictions[
                "fold_role"
            ]
            == "SENSITIVITY_ONLY"
        ]
        .groupby(
            "model_name"
        )
        .size()
        .to_dict()
    )

    prediction_finite = (
        np.isfinite(
            predictions[
                "predicted_speed_mph"
            ].astype(float)
        )
        .all()
    )

    metric_finite = (
        np.isfinite(
            fold_metrics[
                [
                    "mae_mph",
                    "rmse_mph",
                    "r2",
                    "mean_error_pred_minus_actual_mph",
                ]
            ]
            .astype(float)
            .to_numpy()
        )
        .all()
    )

    checks = {
        "model_matrix_rows_equal_123":
            len(
                matrix
            )
            == 123,

        "frozen_feature_count_equal_12":
            len(
                features
            )
            == 12,

        "primary_fold_count_equal_3":
            len(
                primary_fold_ids
            )
            == 3,

        "sensitivity_fold_count_equal_1":
            len(
                sensitivity_fold_ids
            )
            == 1,

        "prediction_rows_match_expected":
            len(
                predictions
            )
            == expected_prediction_rows,

        "fold_metric_rows_match_expected":
            len(
                fold_metrics
            )
            == expected_fold_metric_rows,

        "each_model_has_116_primary_predictions":
            all(
                primary_counts.get(
                    model_name,
                    0,
                )
                == 116
                for model_name
                in model_names
            ),

        "each_model_has_7_sensitivity_predictions":
            all(
                sensitivity_counts.get(
                    model_name,
                    0,
                )
                == 7
                for model_name
                in model_names
            ),

        "all_predictions_finite":
            bool(
                prediction_finite
            ),

        "all_fold_metrics_finite":
            bool(
                metric_finite
            ),

        "aggregate_model_count_equal_5":
            len(
                aggregate_metrics
            )
            == 5,
    }

    # ========================================================
    # Reproducibility hash
    # ========================================================

    model_policy = {
        "phase":
            "5B-0",

        "target":
            TARGET,

        "features":
            features,

        "validation_protocol":
            VALIDATION_PROTOCOL_ID,

        "models":
            {
                "MEAN_BASELINE":
                    {
                        "type":
                            "training_target_mean",
                    },

                "RIDGE":
                    {
                        "alpha":
                            1.0,

                        "standardized":
                            True,
                    },

                "ELASTIC_NET":
                    {
                        "alpha":
                            0.05,

                        "l1_ratio":
                            0.5,

                        "standardized":
                            True,
                    },

                "RANDOM_FOREST":
                    {
                        "n_estimators":
                            500,

                        "max_depth":
                            4,

                        "min_samples_leaf":
                            3,

                        "max_features":
                            "sqrt",

                        "random_state":
                            RANDOM_STATE,
                    },

                "HIST_GRADIENT_BOOSTING":
                    {
                        "learning_rate":
                            0.05,

                        "max_iter":
                            250,

                        "max_leaf_nodes":
                            7,

                        "min_samples_leaf":
                            8,

                        "l2_regularization":
                            1.0,

                        "random_state":
                            RANDOM_STATE,
                    },
            },
    }

    model_policy_hash = (
        stable_hash(
            model_policy
        )
    )

    predictions[
        "model_policy_hash"
    ] = model_policy_hash

    fold_metrics[
        "model_policy_hash"
    ] = model_policy_hash

    aggregate_metrics[
        "model_policy_hash"
    ] = model_policy_hash

    if not diagnostics.empty:

        diagnostics[
            "model_policy_hash"
        ] = model_policy_hash

    # ========================================================
    # Print results
    # ========================================================

    print()
    print("PRIMARY FOLD METRICS")
    print("-" * 140)

    primary_metrics_print = (
        fold_metrics[
            fold_metrics[
                "fold_role"
            ]
            == "PRIMARY"
        ]
        .sort_values(
            [
                "test_year",
                "mae_mph",
            ]
        )
    )

    print(
        primary_metrics_print[
            [
                "test_year",
                "model_name",
                "train_rows",
                "test_rows",
                "mae_mph",
                "rmse_mph",
                "r2",
                "mean_error_pred_minus_actual_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("AGGREGATE PRIMARY RESULTS")
    print("-" * 140)

    print(
        aggregate_metrics[
            [
                "primary_mae_rank",
                "model_name",
                "pooled_primary_mae_mph",
                "pooled_primary_rmse_mph",
                "pooled_primary_r2",
                "pooled_primary_mean_error_pred_minus_actual_mph",
                "mean_primary_fold_mae_mph",
                "mean_fold_mae_improvement_vs_mean_baseline_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("2024 SENSITIVITY HOLDOUT")
    print("-" * 140)

    print(
        sensitivity_metrics[
            [
                "model_name",
                "train_rows",
                "test_rows",
                "mae_mph",
                "rmse_mph",
                "r2",
                "mean_error_pred_minus_actual_mph",
            ]
        ]
        .sort_values(
            "mae_mph"
        )
        .to_string(
            index=False
        )
    )

    # ========================================================
    # Per-year best model
    # ========================================================

    print()
    print("BEST MODEL BY PRIMARY TEST YEAR")
    print("-" * 100)

    best_by_year = (
        primary_metrics_print
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
                "r2",
            ]
        ]
        .to_string(
            index=False
        )
    )

    # ========================================================
    # Worst prediction diagnostics
    # ========================================================

    best_model_name = str(
        aggregate_metrics
        .iloc[0][
            "model_name"
        ]
    )

    best_predictions = (
        primary_predictions[
            primary_predictions[
                "model_name"
            ]
            == best_model_name
        ]
        .copy()
        .sort_values(
            "absolute_error_mph",
            ascending=False,
        )
    )

    print()
    print(
        "WORST 15 PRIMARY PREDICTIONS "
        f"FOR AGGREGATE-BEST MODEL: {best_model_name}"
    )
    print("-" * 140)

    print(
        best_predictions[
            [
                "test_year",
                "car_number",
                "driver_name",
                "actual_speed_mph",
                "predicted_speed_mph",
                "residual_pred_minus_actual_mph",
                "absolute_error_mph",
            ]
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # QA print
    # ========================================================

    qa_rows = []

    for (
        name,
        passed,
    ) in checks.items():

        qa_rows.append(
            {
                "metric":
                    name,

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
                    "prediction_rows",
                "value":
                    len(
                        predictions
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "fold_metric_rows",
                "value":
                    len(
                        fold_metrics
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "aggregate_best_model",
                "value":
                    best_model_name,
                "status":
                    "INFO",
            },

            {
                "metric":
                    "aggregate_best_primary_mae_mph",
                "value":
                    float(
                        aggregate_metrics
                        .iloc[0][
                            "pooled_primary_mae_mph"
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

    print()
    print("QA")
    print("-" * 120)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # Result classification
    # ========================================================

    mean_row = (
        aggregate_metrics[
            aggregate_metrics[
                "model_name"
            ]
            == "MEAN_BASELINE"
        ]
        .iloc[0]
    )

    best_row = (
        aggregate_metrics
        .iloc[0]
    )

    best_beats_mean = (
        best_model_name
        != "MEAN_BASELINE"
        and float(
            best_row[
                "pooled_primary_mae_mph"
            ]
        )
        < float(
            mean_row[
                "pooled_primary_mae_mph"
            ]
        )
    )

    improvement = (
        float(
            mean_row[
                "pooled_primary_mae_mph"
            ]
        )
        - float(
            best_row[
                "pooled_primary_mae_mph"
            ]
        )
    )

    relative_improvement_pct = (
        (
            improvement
            / float(
                mean_row[
                    "pooled_primary_mae_mph"
                ]
            )
        )
        * 100.0
        if float(
            mean_row[
                "pooled_primary_mae_mph"
            ]
        )
        != 0
        else np.nan
    )

    print()
    print("BASELINE INTERPRETATION")
    print("-" * 100)

    print(
        "Mean baseline pooled primary MAE:",
        float(
            mean_row[
                "pooled_primary_mae_mph"
            ]
        ),
        "mph",
    )

    print(
        "Best model:",
        best_model_name,
    )

    print(
        "Best pooled primary MAE:",
        float(
            best_row[
                "pooled_primary_mae_mph"
            ]
        ),
        "mph",
    )

    print(
        "Absolute MAE improvement vs mean:",
        improvement,
        "mph",
    )

    print(
        "Relative MAE improvement vs mean:",
        relative_improvement_pct,
        "%",
    )

    # ========================================================
    # Write outputs
    # ========================================================

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

    aggregate_metrics.to_csv(
        AGGREGATE_METRICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    diagnostics.to_csv(
        MODEL_DIAGNOSTICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # Markdown report
    # ========================================================

    report = []

    report.append(
        "# Attempt-Performance Baseline Ladder V1"
    )

    report.append("")

    report.append(
        f"Target: `{TARGET}`"
    )

    report.append("")

    report.append(
        f"Feature set: `{FEATURE_SET_ID}`"
    )

    report.append(
        f"Validation protocol: `{VALIDATION_PROTOCOL_ID}`"
    )

    report.append(
        f"Model policy hash: `{model_policy_hash}`"
    )

    report.append("")

    report.append(
        "## Models"
    )

    report.append("")

    for model_name in model_names:

        report.append(
            f"- `{model_name}`"
        )

    report.append("")

    report.append(
        "## Primary validation"
    )

    report.append("")

    report.append(
        "Leave-one-year-out across 2020, 2021, and 2023."
    )

    report.append("")

    report.append(
        "2024 remains sensitivity-only because the supported "
        "target subset contains only seven attempts."
    )

    report.append("")

    report.append(
        "## Aggregate result"
    )

    report.append("")

    report.append(
        f"Best model: `{best_model_name}`"
    )

    report.append(
        f"Best pooled primary MAE: "
        f"`{float(best_row['pooled_primary_mae_mph']):.6f} mph`"
    )

    report.append(
        f"Mean baseline pooled primary MAE: "
        f"`{float(mean_row['pooled_primary_mae_mph']):.6f} mph`"
    )

    report.append(
        f"MAE improvement: "
        f"`{improvement:.6f} mph`"
    )

    report.append(
        f"Relative MAE improvement: "
        f"`{relative_improvement_pct:.3f}%`"
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- This is a baseline comparison, not final model selection."
    )

    report.append(
        "- No hyperparameter tuning was performed."
    )

    report.append(
        "- No random row split was used for primary evaluation."
    )

    report.append(
        "- 2022 remains unavailable in the timing-dependent "
        "performance-context layer."
    )

    report.append(
        "- The seven 2024 rows are sensitivity evidence only."
    )

    report.append("")

    report.append(
        "## Readiness"
    )

    report.append("")

    if all(
        checks.values()
    ):

        report.append(
            "**BASELINE_MODEL_LADDER_COMPLETE**"
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
    # Final status
    # ========================================================

    print()
    print("=" * 100)

    if all(
        checks.values()
    ):

        print(
            "FINAL STATUS: "
            "BASELINE_MODEL_LADDER_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "IMPORTANT: this does NOT freeze a winning model yet."
    )

    print(
        "The next step is residual/stability analysis before "
        "any model promotion or tuning."
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
        MODEL_DIAGNOSTICS_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
