from pathlib import Path
import json
import hashlib

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

MODEL_MATRIX_FILE = Path(
    "weather/output/attempt_performance_model_matrix_v1.csv"
)

PREDICTIONS_FILE = Path(
    "weather/output/attempt_performance_baseline_predictions_v1.csv"
)

FOLD_METRICS_FILE = Path(
    "weather/output/attempt_performance_baseline_fold_metrics_v1.csv"
)

AGGREGATE_METRICS_FILE = Path(
    "weather/output/attempt_performance_baseline_aggregate_metrics_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

RESIDUAL_DIAGNOSTICS_FILE = Path(
    "weather/output/attempt_performance_residual_diagnostics_v1.csv"
)

GROUP_SUMMARY_FILE = Path(
    "weather/output/attempt_performance_residual_group_summary_v1.csv"
)

FEATURE_CORRELATION_FILE = Path(
    "weather/output/attempt_performance_residual_feature_correlations_v1.csv"
)

TARGET_STRUCTURE_FILE = Path(
    "weather/output/attempt_performance_target_structure_v1.csv"
)

PRIOR_DIAGNOSTICS_FILE = Path(
    "weather/output/attempt_performance_prior_speed_diagnostics_v1.csv"
)

QA_FILE = Path(
    "weather/output/attempt_performance_residual_stability_qa_v1.csv"
)

REPORT_FILE = Path(
    "weather/output/attempt_performance_residual_stability_v1.md"
)


# ============================================================
# FROZEN DESIGN
# ============================================================

TARGET = "four_lap_average_speed_mph"

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

EXPECTED_MODEL_ROWS = 123
EXPECTED_PRIMARY_ROWS_PER_MODEL = 116

EXPECTED_MODELS = [
    "MEAN_BASELINE",
    "RIDGE",
    "ELASTIC_NET",
    "RANDOM_FOREST",
    "HIST_GRADIENT_BOOSTING",
]

WEATHER_FEATURES = [
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_wind_direction_sin",
    "forecast_wind_direction_cos",
    "forecast_pressure_hpa",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
]

PRIOR_FEATURES = [
    "prior_supported_attempt_count",
    "seconds_since_prior_supported_attempt",
    "best_prior_supported_average_speed_mph",
    "has_prior_supported_attempt",
]

ALL_MODEL_FEATURES = (
    WEATHER_FEATURES
    + PRIOR_FEATURES
)


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


def safe_corr(a, b):
    pair = pd.DataFrame(
        {
            "a": numeric(a),
            "b": numeric(b),
        }
    ).dropna()

    if len(pair) < 3:
        return np.nan

    if (
        pair["a"].nunique() < 2
        or pair["b"].nunique() < 2
    ):
        return np.nan

    return float(
        pair["a"].corr(
            pair["b"]
        )
    )


def mae(a, b):
    pair = pd.DataFrame(
        {
            "a": numeric(a),
            "b": numeric(b),
        }
    ).dropna()

    if pair.empty:
        return np.nan

    return float(
        np.mean(
            np.abs(
                pair["a"] - pair["b"]
            )
        )
    )


def rmse(a, b):
    pair = pd.DataFrame(
        {
            "a": numeric(a),
            "b": numeric(b),
        }
    ).dropna()

    if pair.empty:
        return np.nan

    return float(
        np.sqrt(
            np.mean(
                (
                    pair["a"] - pair["b"]
                ) ** 2
            )
        )
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


def year_center(series, years):
    frame = pd.DataFrame(
        {
            "value": numeric(series),
            "year": numeric(years),
        }
    )

    group_mean = (
        frame
        .groupby(
            "year",
            dropna=False,
        )["value"]
        .transform("mean")
    )

    return (
        frame["value"]
        - group_mean
    )


def resolve_merged_column(
    df,
    candidates,
    label,
):
    for col in candidates:
        if col in df.columns:
            return col

    raise RuntimeError(
        f"Unable to resolve merged column for {label}. "
        f"Tried: {candidates}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    matrix = read_required(
        MODEL_MATRIX_FILE
    )

    predictions = read_required(
        PREDICTIONS_FILE
    )

    fold_metrics = read_required(
        FOLD_METRICS_FILE
    )

    aggregate = read_required(
        AGGREGATE_METRICS_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5B-1 — RESIDUAL / STABILITY / "
        "MISSING-BASELINE DIAGNOSIS"
    )
    print("=" * 100)

    # ========================================================
    # Validate matrix
    # ========================================================

    if len(matrix) != EXPECTED_MODEL_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_MODEL_ROWS} model rows, "
            f"got {len(matrix)}"
        )

    if matrix["attempt_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in model matrix."
        )

    required_matrix = [
        "attempt_id",
        "session_id",
        "year",
        "car_number",
        "driver_name",
        TARGET,
    ] + ALL_MODEL_FEATURES

    missing_matrix = [
        c
        for c in required_matrix
        if c not in matrix.columns
    ]

    if missing_matrix:
        raise RuntimeError(
            "Missing model-matrix fields: "
            + ", ".join(missing_matrix)
        )

    required_prediction = [
        "fold_id",
        "fold_role",
        "model_name",
        "test_year",
        "attempt_id",
        "actual_speed_mph",
        "predicted_speed_mph",
        "residual_pred_minus_actual_mph",
        "absolute_error_mph",
    ]

    missing_prediction = [
        c
        for c in required_prediction
        if c not in predictions.columns
    ]

    if missing_prediction:
        raise RuntimeError(
            "Missing prediction fields: "
            + ", ".join(missing_prediction)
        )

    matrix = matrix.copy()

    matrix["year"] = numeric(
        matrix["year"]
    ).astype(int)

    matrix[TARGET] = numeric(
        matrix[TARGET]
    )

    for feature in ALL_MODEL_FEATURES:
        matrix[feature] = numeric(
            matrix[feature]
        )

    predictions = predictions.copy()

    predictions["test_year"] = numeric(
        predictions["test_year"]
    ).astype(int)

    for col in [
        "actual_speed_mph",
        "predicted_speed_mph",
        "residual_pred_minus_actual_mph",
        "absolute_error_mph",
    ]:
        predictions[col] = numeric(
            predictions[col]
        )

    # ========================================================
    # Best model from 5B-0
    # ========================================================

    aggregate = (
        aggregate
        .sort_values(
            [
                "primary_mae_rank",
                "pooled_primary_mae_mph",
            ]
        )
        .reset_index(drop=True)
    )

    best_model = str(
        aggregate.iloc[0][
            "model_name"
        ]
    )

    print()
    print(
        "Aggregate-best baseline-ladder model:",
        best_model
    )

    # ========================================================
    # Merge predictions + matrix
    # ========================================================

    matrix_join = matrix[
        [
            "attempt_id",
            "year",
            "car_number",
            "driver_name",
            TARGET,
        ]
        + ALL_MODEL_FEATURES
    ].copy()

    residuals = predictions.merge(
        matrix_join,
        on="attempt_id",
        how="left",
        suffixes=(
            "_prediction",
            "_matrix",
        ),
        validate="many_to_one",
    )

    # --------------------------------------------------------
    # Resolve suffix-sensitive columns
    # --------------------------------------------------------

    year_col = resolve_merged_column(
        residuals,
        [
            "year",
            "year_matrix",
            "year_prediction",
        ],
        "year",
    )

    car_col = resolve_merged_column(
        residuals,
        [
            "car_number",
            "car_number_matrix",
            "car_number_prediction",
        ],
        "car_number",
    )

    driver_col = resolve_merged_column(
        residuals,
        [
            "driver_name",
            "driver_name_matrix",
            "driver_name_prediction",
        ],
        "driver_name",
    )

    target_col = resolve_merged_column(
        residuals,
        [
            TARGET,
            f"{TARGET}_matrix",
            f"{TARGET}_prediction",
        ],
        TARGET,
    )

    residuals["_resolved_year"] = numeric(
        residuals[year_col]
    )

    residuals["_resolved_car_number"] = (
        residuals[car_col]
    )

    residuals["_resolved_driver_name"] = (
        residuals[driver_col]
    )

    residuals["_resolved_target"] = numeric(
        residuals[target_col]
    )

    if residuals[
        "_resolved_year"
    ].isna().any():
        raise RuntimeError(
            "At least one prediction failed matrix join."
        )

    # ========================================================
    # Target structure by year
    # ========================================================

    primary_matrix = matrix[
        matrix["year"].isin(
            PRIMARY_YEARS
        )
    ].copy()

    target_structure_rows = []

    overall_primary_mean = float(
        primary_matrix[TARGET].mean()
    )

    overall_primary_std = float(
        primary_matrix[TARGET].std(
            ddof=1
        )
    )

    for year in sorted(
        matrix["year"].unique()
    ):

        subset = matrix[
            matrix["year"] == year
        ]

        target_structure_rows.append(
            {
                "scope":
                    "YEAR",

                "year":
                    int(year),

                "rows":
                    len(subset),

                "mean_speed_mph":
                    float(
                        subset[TARGET].mean()
                    ),

                "median_speed_mph":
                    float(
                        subset[TARGET].median()
                    ),

                "std_speed_mph":
                    float(
                        subset[TARGET].std(
                            ddof=1
                        )
                    )
                    if len(subset) > 1
                    else np.nan,

                "min_speed_mph":
                    float(
                        subset[TARGET].min()
                    ),

                "max_speed_mph":
                    float(
                        subset[TARGET].max()
                    ),

                "mean_minus_primary_overall_mean_mph":
                    float(
                        subset[TARGET].mean()
                        - overall_primary_mean
                    ),
            }
        )

    primary_year_means = (
        primary_matrix
        .groupby("year")[TARGET]
        .mean()
    )

    primary_year_mean_range = float(
        primary_year_means.max()
        - primary_year_means.min()
    )

    grand_mean = float(
        primary_matrix[TARGET].mean()
    )

    ss_total = float(
        (
            (
                primary_matrix[TARGET]
                - grand_mean
            ) ** 2
        ).sum()
    )

    ss_between = 0.0

    for year, group in (
        primary_matrix.groupby("year")
    ):

        group_mean = float(
            group[TARGET].mean()
        )

        ss_between += (
            len(group)
            * (
                group_mean
                - grand_mean
            ) ** 2
        )

    eta_squared_year = (
        ss_between / ss_total
        if ss_total > 0
        else np.nan
    )

    target_structure_rows.append(
        {
            "scope":
                "PRIMARY_COMBINED",

            "year":
                np.nan,

            "rows":
                len(primary_matrix),

            "mean_speed_mph":
                grand_mean,

            "median_speed_mph":
                float(
                    primary_matrix[TARGET].median()
                ),

            "std_speed_mph":
                overall_primary_std,

            "min_speed_mph":
                float(
                    primary_matrix[TARGET].min()
                ),

            "max_speed_mph":
                float(
                    primary_matrix[TARGET].max()
                ),

            "mean_minus_primary_overall_mean_mph":
                0.0,

            "primary_year_mean_range_mph":
                primary_year_mean_range,

            "eta_squared_descriptive_year":
                eta_squared_year,
        }
    )

    target_structure = pd.DataFrame(
        target_structure_rows
    )

    # ========================================================
    # Primary residuals
    # ========================================================

    primary_residuals = residuals[
        residuals["fold_role"]
        == "PRIMARY"
    ].copy()

    # ========================================================
    # Group summaries
    # ========================================================

    group_rows = []

    for model_name in EXPECTED_MODELS:

        model_subset = primary_residuals[
            primary_residuals[
                "model_name"
            ]
            == model_name
        ]

        group_rows.append(
            {
                "model_name":
                    model_name,

                "group_type":
                    "PRIMARY_OVERALL",

                "group_value":
                    "ALL",

                "rows":
                    len(model_subset),

                "mean_actual_speed_mph":
                    float(
                        model_subset[
                            "actual_speed_mph"
                        ].mean()
                    ),

                "mean_predicted_speed_mph":
                    float(
                        model_subset[
                            "predicted_speed_mph"
                        ].mean()
                    ),

                "mean_residual_pred_minus_actual_mph":
                    float(
                        model_subset[
                            "residual_pred_minus_actual_mph"
                        ].mean()
                    ),

                "mae_mph":
                    float(
                        model_subset[
                            "absolute_error_mph"
                        ].mean()
                    ),

                "rmse_mph":
                    float(
                        np.sqrt(
                            np.mean(
                                model_subset[
                                    "residual_pred_minus_actual_mph"
                                ] ** 2
                            )
                        )
                    ),
            }
        )

        for year, group in (
            model_subset.groupby(
                "test_year"
            )
        ):

            group_rows.append(
                {
                    "model_name":
                        model_name,

                    "group_type":
                        "TEST_YEAR",

                    "group_value":
                        str(
                            int(year)
                        ),

                    "rows":
                        len(group),

                    "mean_actual_speed_mph":
                        float(
                            group[
                                "actual_speed_mph"
                            ].mean()
                        ),

                    "mean_predicted_speed_mph":
                        float(
                            group[
                                "predicted_speed_mph"
                            ].mean()
                        ),

                    "mean_residual_pred_minus_actual_mph":
                        float(
                            group[
                                "residual_pred_minus_actual_mph"
                            ].mean()
                        ),

                    "mae_mph":
                        float(
                            group[
                                "absolute_error_mph"
                            ].mean()
                        ),

                    "rmse_mph":
                        float(
                            np.sqrt(
                                np.mean(
                                    group[
                                        "residual_pred_minus_actual_mph"
                                    ] ** 2
                                )
                            )
                        ),
                }
            )

        for has_prior, group in (
            model_subset.groupby(
                "has_prior_supported_attempt"
            )
        ):

            group_rows.append(
                {
                    "model_name":
                        model_name,

                    "group_type":
                        "HAS_PRIOR_SUPPORTED_ATTEMPT",

                    "group_value":
                        str(
                            int(has_prior)
                        ),

                    "rows":
                        len(group),

                    "mean_actual_speed_mph":
                        float(
                            group[
                                "actual_speed_mph"
                            ].mean()
                        ),

                    "mean_predicted_speed_mph":
                        float(
                            group[
                                "predicted_speed_mph"
                            ].mean()
                        ),

                    "mean_residual_pred_minus_actual_mph":
                        float(
                            group[
                                "residual_pred_minus_actual_mph"
                            ].mean()
                        ),

                    "mae_mph":
                        float(
                            group[
                                "absolute_error_mph"
                            ].mean()
                        ),

                    "rmse_mph":
                        float(
                            np.sqrt(
                                np.mean(
                                    group[
                                        "residual_pred_minus_actual_mph"
                                    ] ** 2
                                )
                            )
                        ),
                }
            )

    group_summary = pd.DataFrame(
        group_rows
    )

    # ========================================================
    # Feature ↔ residual correlations
    # ========================================================

    correlation_rows = []

    for model_name in EXPECTED_MODELS:

        model_subset = primary_residuals[
            primary_residuals[
                "model_name"
            ]
            == model_name
        ].copy()

        residual_pooled = model_subset[
            "residual_pred_minus_actual_mph"
        ]

        residual_centered = year_center(
            residual_pooled,
            model_subset["test_year"],
        )

        actual_centered = year_center(
            model_subset[
                "actual_speed_mph"
            ],
            model_subset["test_year"],
        )

        for feature in ALL_MODEL_FEATURES:

            feature_pooled = model_subset[
                feature
            ]

            feature_centered = year_center(
                feature_pooled,
                model_subset["test_year"],
            )

            pooled_residual_corr = safe_corr(
                feature_pooled,
                residual_pooled,
            )

            within_year_residual_corr = safe_corr(
                feature_centered,
                residual_centered,
            )

            pooled_target_corr = safe_corr(
                feature_pooled,
                model_subset[
                    "actual_speed_mph"
                ],
            )

            within_year_target_corr = safe_corr(
                feature_centered,
                actual_centered,
            )

            correlation_rows.append(
                {
                    "model_name":
                        model_name,

                    "feature_name":
                        feature,

                    "pooled_corr_feature_vs_residual":
                        pooled_residual_corr,

                    "abs_pooled_corr_feature_vs_residual":
                        abs(
                            pooled_residual_corr
                        )
                        if pd.notna(
                            pooled_residual_corr
                        )
                        else np.nan,

                    "within_year_corr_feature_vs_residual":
                        within_year_residual_corr,

                    "abs_within_year_corr_feature_vs_residual":
                        abs(
                            within_year_residual_corr
                        )
                        if pd.notna(
                            within_year_residual_corr
                        )
                        else np.nan,

                    "pooled_corr_feature_vs_actual_target":
                        pooled_target_corr,

                    "within_year_corr_feature_vs_actual_target":
                        within_year_target_corr,
                }
            )

    feature_correlations = pd.DataFrame(
        correlation_rows
    )

    # ========================================================
    # Prior-speed persistence
    # ========================================================

    repeat_matrix = matrix[
        matrix[
            "has_prior_supported_attempt"
        ]
        == 1
    ].copy()

    repeat_matrix = repeat_matrix[
        repeat_matrix[
            "best_prior_supported_average_speed_mph"
        ]
        > 0
    ].copy()

    repeat_matrix[
        "current_minus_best_prior_speed_mph"
    ] = (
        repeat_matrix[TARGET]
        - repeat_matrix[
            "best_prior_supported_average_speed_mph"
        ]
    )

    prior_speed_corr = safe_corr(
        repeat_matrix[TARGET],
        repeat_matrix[
            "best_prior_supported_average_speed_mph"
        ],
    )

    prior_speed_mae = mae(
        repeat_matrix[TARGET],
        repeat_matrix[
            "best_prior_supported_average_speed_mph"
        ],
    )

    prior_speed_rmse = rmse(
        repeat_matrix[TARGET],
        repeat_matrix[
            "best_prior_supported_average_speed_mph"
        ],
    )

    prior_rows = [
        {
            "scope":
                "ALL_REPEAT_TARGET_ROWS",

            "year":
                np.nan,

            "rows":
                len(repeat_matrix),

            "corr_current_vs_best_prior_speed":
                prior_speed_corr,

            "mae_if_best_prior_used_as_naive_prediction_mph":
                prior_speed_mae,

            "rmse_if_best_prior_used_as_naive_prediction_mph":
                prior_speed_rmse,

            "mean_current_minus_best_prior_speed_mph":
                float(
                    repeat_matrix[
                        "current_minus_best_prior_speed_mph"
                    ].mean()
                )
                if len(repeat_matrix)
                else np.nan,

            "median_current_minus_best_prior_speed_mph":
                float(
                    repeat_matrix[
                        "current_minus_best_prior_speed_mph"
                    ].median()
                )
                if len(repeat_matrix)
                else np.nan,

            "std_current_minus_best_prior_speed_mph":
                float(
                    repeat_matrix[
                        "current_minus_best_prior_speed_mph"
                    ].std(ddof=1)
                )
                if len(repeat_matrix) > 1
                else np.nan,
        }
    ]

    for year, group in (
        repeat_matrix.groupby("year")
    ):

        prior_rows.append(
            {
                "scope":
                    "REPEAT_TARGET_ROWS_BY_YEAR",

                "year":
                    int(year),

                "rows":
                    len(group),

                "corr_current_vs_best_prior_speed":
                    safe_corr(
                        group[TARGET],
                        group[
                            "best_prior_supported_average_speed_mph"
                        ],
                    ),

                "mae_if_best_prior_used_as_naive_prediction_mph":
                    mae(
                        group[TARGET],
                        group[
                            "best_prior_supported_average_speed_mph"
                        ],
                    ),

                "rmse_if_best_prior_used_as_naive_prediction_mph":
                    rmse(
                        group[TARGET],
                        group[
                            "best_prior_supported_average_speed_mph"
                        ],
                    ),

                "mean_current_minus_best_prior_speed_mph":
                    float(
                        group[
                            "current_minus_best_prior_speed_mph"
                        ].mean()
                    ),

                "median_current_minus_best_prior_speed_mph":
                    float(
                        group[
                            "current_minus_best_prior_speed_mph"
                        ].median()
                    ),

                "std_current_minus_best_prior_speed_mph":
                    float(
                        group[
                            "current_minus_best_prior_speed_mph"
                        ].std(ddof=1)
                    )
                    if len(group) > 1
                    else np.nan,
            }
        )

    prior_diagnostics = pd.DataFrame(
        prior_rows
    )

    # ========================================================
    # Repeated-car diagnostic for best model
    # ========================================================

    best_primary = primary_residuals[
        primary_residuals[
            "model_name"
        ]
        == best_model
    ].copy()

    car_summary = (
        best_primary
        .groupby(
            [
                "test_year",
                "_resolved_car_number",
                "_resolved_driver_name",
            ],
            dropna=False,
        )
        .agg(
            rows=(
                "attempt_id",
                "size",
            ),
            mean_actual_speed_mph=(
                "actual_speed_mph",
                "mean",
            ),
            mean_residual_pred_minus_actual_mph=(
                "residual_pred_minus_actual_mph",
                "mean",
            ),
            mean_absolute_error_mph=(
                "absolute_error_mph",
                "mean",
            ),
        )
        .reset_index()
    )

    car_summary = car_summary[
        car_summary["rows"] >= 2
    ].copy()

    if not car_summary.empty:

        car_group_rows = []

        for _, row in (
            car_summary.iterrows()
        ):

            car_group_rows.append(
                {
                    "model_name":
                        best_model,

                    "group_type":
                        "REPEATED_CAR_WITHIN_TEST_YEAR",

                    "group_value":
                        (
                            f"{int(row['test_year'])}:"
                            f"car{row['_resolved_car_number']}:"
                            f"{row['_resolved_driver_name']}"
                        ),

                    "rows":
                        int(
                            row["rows"]
                        ),

                    "mean_actual_speed_mph":
                        float(
                            row[
                                "mean_actual_speed_mph"
                            ]
                        ),

                    "mean_predicted_speed_mph":
                        np.nan,

                    "mean_residual_pred_minus_actual_mph":
                        float(
                            row[
                                "mean_residual_pred_minus_actual_mph"
                            ]
                        ),

                    "mae_mph":
                        float(
                            row[
                                "mean_absolute_error_mph"
                            ]
                        ),

                    "rmse_mph":
                        np.nan,
                }
            )

        group_summary = pd.concat(
            [
                group_summary,
                pd.DataFrame(
                    car_group_rows
                ),
            ],
            ignore_index=True,
        )

    # ========================================================
    # Best-model residual correlations
    # ========================================================

    best_corr = (
        feature_correlations[
            feature_correlations[
                "model_name"
            ]
            == best_model
        ]
        .copy()
        .sort_values(
            "abs_within_year_corr_feature_vs_residual",
            ascending=False,
        )
    )

    # ========================================================
    # Mean baseline year bias
    # ========================================================

    mean_baseline_year = group_summary[
        (
            group_summary[
                "model_name"
            ]
            == "MEAN_BASELINE"
        )
        &
        (
            group_summary[
                "group_type"
            ]
            == "TEST_YEAR"
        )
    ].copy()

    max_abs_mean_baseline_year_bias = float(
        mean_baseline_year[
            "mean_residual_pred_minus_actual_mph"
        ]
        .abs()
        .max()
    )

    first_repeat_best = group_summary[
        (
            group_summary[
                "model_name"
            ]
            == best_model
        )
        &
        (
            group_summary[
                "group_type"
            ]
            == "HAS_PRIOR_SUPPORTED_ATTEMPT"
        )
    ].copy()

    # ========================================================
    # QA
    # ========================================================

    primary_model_counts = (
        primary_residuals
        .groupby("model_name")
        .size()
        .to_dict()
    )

    checks = {
        "model_matrix_rows_equal_123":
            len(matrix) == 123,

        "primary_years_exact":
            set(
                primary_matrix["year"].unique()
            )
            == set(PRIMARY_YEARS),

        "primary_matrix_rows_equal_116":
            len(primary_matrix) == 116,

        "expected_five_models_present":
            set(EXPECTED_MODELS)
            == set(
                primary_model_counts.keys()
            ),

        "each_model_has_116_primary_predictions":
            all(
                primary_model_counts.get(
                    model,
                    0,
                )
                == EXPECTED_PRIMARY_ROWS_PER_MODEL
                for model in EXPECTED_MODELS
            ),

        "aggregate_best_model_present":
            best_model in EXPECTED_MODELS,

        "target_structure_created":
            len(target_structure) >= 5,

        "feature_correlation_rows_equal_60":
            len(feature_correlations)
            == (
                len(EXPECTED_MODELS)
                * len(ALL_MODEL_FEATURES)
            ),

        "repeat_prior_diagnostic_nonempty":
            len(repeat_matrix) > 0,

        "all_best_primary_residuals_finite":
            np.isfinite(
                best_primary[
                    "residual_pred_minus_actual_mph"
                ]
            ).all(),

        "year_eta_squared_finite":
            np.isfinite(
                eta_squared_year
            ),

        "year_mean_range_finite":
            np.isfinite(
                primary_year_mean_range
            ),

        "resolved_car_column_present":
            "_resolved_car_number"
            in residuals.columns,

        "resolved_driver_column_present":
            "_resolved_driver_name"
            in residuals.columns,
    }

    diagnostic_policy = {
        "phase":
            "5B-1",

        "best_model_from_phase_5B0":
            best_model,

        "primary_years":
            PRIMARY_YEARS,

        "features":
            ALL_MODEL_FEATURES,

        "analyses":
            [
                "year_target_structure",
                "anova_style_descriptive_eta_squared",
                "pooled_residual_feature_correlation",
                "within_year_centered_residual_feature_correlation",
                "first_vs_repeat_error",
                "prior_speed_persistence",
                "repeated_car_residual_diagnostic",
            ],
    }

    diagnostic_policy_hash = (
        stable_hash(
            diagnostic_policy
        )
    )

    qa_rows = []

    for name, passed in (
        checks.items()
    ):

        qa_rows.append(
            {
                "metric":
                    name,

                "value":
                    int(bool(passed)),

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
                    "aggregate_best_model",

                "value":
                    best_model,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_year_mean_range_mph",

                "value":
                    primary_year_mean_range,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "descriptive_year_eta_squared",

                "value":
                    eta_squared_year,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "max_abs_mean_baseline_year_bias_mph",

                "value":
                    max_abs_mean_baseline_year_bias,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "repeat_target_rows",

                "value":
                    len(repeat_matrix),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "corr_current_vs_best_prior_speed",

                "value":
                    prior_speed_corr,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "best_prior_naive_mae_mph_on_repeat_rows",

                "value":
                    prior_speed_mae,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "diagnostic_policy_hash",

                "value":
                    diagnostic_policy_hash,

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
    print("TARGET STRUCTURE BY YEAR")
    print("-" * 120)

    print(
        target_structure.to_string(
            index=False
        )
    )

    print()
    print("PRIMARY YEAR-LEVEL DIAGNOSTICS")
    print("-" * 100)

    print(
        "Primary year mean range:",
        primary_year_mean_range,
        "mph",
    )

    print(
        "Descriptive year eta-squared:",
        eta_squared_year,
    )

    print(
        "Maximum absolute Mean-Baseline year bias:",
        max_abs_mean_baseline_year_bias,
        "mph",
    )

    print()
    print(
        "BEST-MODEL FIRST VS REPEAT ERROR:",
        best_model
    )
    print("-" * 120)

    if first_repeat_best.empty:

        print(
            "No first/repeat grouping available."
        )

    else:

        print(
            first_repeat_best[
                [
                    "group_value",
                    "rows",
                    "mean_actual_speed_mph",
                    "mean_residual_pred_minus_actual_mph",
                    "mae_mph",
                    "rmse_mph",
                ]
            ].to_string(
                index=False
            )
        )

    print()
    print("PRIOR-SPEED PERSISTENCE DIAGNOSTIC")
    print("-" * 120)

    print(
        prior_diagnostics.to_string(
            index=False
        )
    )

    print()
    print(
        "TOP WITHIN-YEAR RESIDUAL CORRELATIONS "
        f"FOR {best_model}"
    )
    print("-" * 140)

    print(
        best_corr[
            [
                "feature_name",
                "within_year_corr_feature_vs_residual",
                "abs_within_year_corr_feature_vs_residual",
                "within_year_corr_feature_vs_actual_target",
                "pooled_corr_feature_vs_residual",
            ]
        ]
        .head(12)
        .to_string(
            index=False
        )
    )

    print()
    print("MEAN BASELINE YEAR BIAS")
    print("-" * 120)

    print(
        mean_baseline_year[
            [
                "group_value",
                "rows",
                "mean_actual_speed_mph",
                "mean_predicted_speed_mph",
                "mean_residual_pred_minus_actual_mph",
                "mae_mph",
                "rmse_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print(
        "REPEATED CAR RESIDUAL SAMPLE "
        f"FOR {best_model}"
    )
    print("-" * 140)

    repeated_car_output = group_summary[
        group_summary[
            "group_type"
        ]
        == "REPEATED_CAR_WITHIN_TEST_YEAR"
    ].copy()

    if repeated_car_output.empty:

        print(
            "No repeated-car groups with >=2 target rows."
        )

    else:

        print(
            repeated_car_output[
                [
                    "group_value",
                    "rows",
                    "mean_actual_speed_mph",
                    "mean_residual_pred_minus_actual_mph",
                    "mae_mph",
                ]
            ]
            .sort_values(
                "mae_mph",
                ascending=False,
            )
            .head(20)
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
    # WRITE OUTPUTS
    # ========================================================

    RESIDUAL_DIAGNOSTICS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    residuals[
        "diagnostic_policy_hash"
    ] = diagnostic_policy_hash

    group_summary[
        "diagnostic_policy_hash"
    ] = diagnostic_policy_hash

    feature_correlations[
        "diagnostic_policy_hash"
    ] = diagnostic_policy_hash

    target_structure[
        "diagnostic_policy_hash"
    ] = diagnostic_policy_hash

    prior_diagnostics[
        "diagnostic_policy_hash"
    ] = diagnostic_policy_hash

    residuals.to_csv(
        RESIDUAL_DIAGNOSTICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    group_summary.to_csv(
        GROUP_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    feature_correlations.to_csv(
        FEATURE_CORRELATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    target_structure.to_csv(
        TARGET_STRUCTURE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    prior_diagnostics.to_csv(
        PRIOR_DIAGNOSTICS_FILE,
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
        "# Attempt-Performance Residual / Stability Diagnosis V1"
    )

    report.append("")

    report.append(
        f"Aggregate-best Phase 5B-0 model: `{best_model}`"
    )

    report.append("")

    report.append(
        "## Year-level target structure"
    )

    report.append("")

    report.append(
        f"- Primary year mean range: "
        f"`{primary_year_mean_range:.6f} mph`"
    )

    report.append(
        f"- Descriptive year eta-squared: "
        f"`{eta_squared_year:.6f}`"
    )

    report.append(
        f"- Maximum absolute Mean-Baseline year bias: "
        f"`{max_abs_mean_baseline_year_bias:.6f} mph`"
    )

    report.append("")

    report.append(
        "The eta-squared quantity is descriptive only. "
        "It measures observed target variation associated "
        "with year-level mean differences."
    )

    report.append("")

    report.append(
        "## Prior-speed persistence"
    )

    report.append("")

    report.append(
        f"- Repeat target rows: `{len(repeat_matrix)}`"
    )

    if pd.notna(
        prior_speed_corr
    ):
        report.append(
            f"- Correlation current vs best prior speed: "
            f"`{prior_speed_corr:.6f}`"
        )

    if pd.notna(
        prior_speed_mae
    ):
        report.append(
            f"- Naive best-prior-speed MAE on repeat rows: "
            f"`{prior_speed_mae:.6f} mph`"
        )

    report.append("")

    report.append(
        "This is diagnostic evidence only, not a promoted model."
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- No new predictive model was trained."
    )

    report.append(
        "- No hyperparameter tuning was performed."
    )

    report.append(
        "- No feature or target definition was changed."
    )

    report.append(
        "- Car identity is descriptive only."
    )

    report.append(
        "- 2024 remains sensitivity-only."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**RESIDUAL_STABILITY_DIAGNOSIS_COMPLETE**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    REPORT_FILE.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ========================================================
    # Final
    # ========================================================

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "RESIDUAL_STABILITY_DIAGNOSIS_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO NEW MODEL WAS TRAINED."
    )

    print(
        "NO FEATURE SET OR TARGET DEFINITION WAS CHANGED."
    )

    print()
    print("OUTPUTS")

    print(
        RESIDUAL_DIAGNOSTICS_FILE
    )

    print(
        GROUP_SUMMARY_FILE
    )

    print(
        FEATURE_CORRELATION_FILE
    )

    print(
        TARGET_STRUCTURE_FILE
    )

    print(
        PRIOR_DIAGNOSTICS_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
