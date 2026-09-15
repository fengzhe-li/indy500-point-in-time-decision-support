from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


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

ROW_DIAGNOSTICS_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_row_diagnostics_v1.csv"
)

THRESHOLD_AUDIT_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_threshold_audit_v1.csv"
)

REGIME_SUMMARY_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_summary_v1.csv"
)

FEATURE_CORRELATION_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_feature_correlations_v1.csv"
)

OUTLIER_CONTRIBUTION_FILE = Path(
    "weather/output/"
    "repeat_delta_outlier_error_contribution_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_diagnosis_qa_v1.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_diagnosis_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

TARGET = "target_speed_delta_vs_best_prior_mph"

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

SENSITIVITY_YEAR = 2024

EXPECTED_TOTAL_ROWS = 40
EXPECTED_PRIMARY_ROWS = 39

FIXED_GAIN_THRESHOLDS = [
    0.5,
    1.0,
    1.5,
    2.0,
]

WEATHER_DELTA_FEATURES = [
    "delta_temp_c",
    "delta_relative_humidity_pct",
    "delta_wind_speed_10m_ms",
    "delta_pressure_hpa",
    "delta_cloud_cover_pct",
    "delta_shortwave_radiation_wm2",
    "delta_forecast_wind_direction_sin",
    "delta_forecast_wind_direction_cos",
]

CONTEXT_FEATURES = [
    "baseline_speed_mph",
    "seconds_since_baseline_attempt",
    "prior_supported_attempt_count",
]

ALL_DIAGNOSTIC_FEATURES = (
    CONTEXT_FEATURES
    + WEATHER_DELTA_FEATURES
)

POLICY_VERSION = (
    "REPEAT_DELTA_REGIME_DIAGNOSIS_V1"
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


def safe_pearson(a, b):

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


def safe_spearman(a, b):

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
        pair["a"].rank().corr(
            pair["b"].rank()
        )
    )


def rmse_from_zero(series):

    x = numeric(series).dropna()

    if x.empty:
        return np.nan

    return float(
        np.sqrt(
            np.mean(
                x ** 2
            )
        )
    )


def mae_from_zero(series):

    x = numeric(series).dropna()

    if x.empty:
        return np.nan

    return float(
        np.mean(
            np.abs(
                x
            )
        )
    )


def year_center(series, year):

    frame = pd.DataFrame(
        {
            "value": numeric(series),
            "year": numeric(year),
        }
    )

    means = (
        frame
        .groupby("year")["value"]
        .transform("mean")
    )

    return (
        frame["value"]
        - means
    )


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
        "PHASE 5B-3 — REPEAT-DELTA "
        "TARGET STRUCTURE / OUTLIER / REGIME DIAGNOSIS"
    )
    print("=" * 100)

    print()
    print(
        "Input rows:",
        len(df)
    )

    # ========================================================
    # Validate
    # ========================================================

    if len(df) != EXPECTED_TOTAL_ROWS:
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
    ] + ALL_DIAGNOSTIC_FEATURES

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required fields: "
            + ", ".join(missing)
        )

    if df[
        "current_attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate current_attempt_id."
        )

    work = df.copy()

    work["year"] = numeric(
        work["year"]
    ).astype(int)

    work[TARGET] = numeric(
        work[TARGET]
    )

    for feature in ALL_DIAGNOSTIC_FEATURES:

        work[feature] = numeric(
            work[feature]
        )

    if work[
        [TARGET]
        + ALL_DIAGNOSTIC_FEATURES
    ].isna().any().any():

        raise RuntimeError(
            "Missing diagnostic values."
        )

    primary = work[
        work["year"].isin(
            PRIMARY_YEARS
        )
    ].copy()

    sensitivity = work[
        work["year"]
        == SENSITIVITY_YEAR
    ].copy()

    if len(primary) != EXPECTED_PRIMARY_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_PRIMARY_ROWS} primary rows, "
            f"got {len(primary)}"
        )

    # ========================================================
    # Robust target structure
    # ========================================================

    target = primary[TARGET]

    q1 = float(
        target.quantile(0.25)
    )

    q2 = float(
        target.quantile(0.50)
    )

    q3 = float(
        target.quantile(0.75)
    )

    iqr = (
        q3 - q1
    )

    tukey_upper = (
        q3
        + 1.5 * iqr
    )

    median = q2

    abs_dev = (
        target
        - median
    ).abs()

    mad = float(
        abs_dev.median()
    )

    robust_sigma = (
        1.4826 * mad
    )

    mad_upper = (
        median
        + 3.0 * robust_sigma
    )

    # Diagnostic threshold:
    # conservative combination.
    #
    # Not a final model class definition.
    diagnostic_large_gain_threshold = max(
        1.0,
        tukey_upper,
        mad_upper,
    )

    # ========================================================
    # Row-level derived diagnostics
    # ========================================================

    primary[
        "baseline_speed_year_centered_mph"
    ] = year_center(
        primary[
            "baseline_speed_mph"
        ],
        primary[
            "year"
        ],
    )

    primary[
        "target_year_centered_mph"
    ] = year_center(
        primary[TARGET],
        primary["year"],
    )

    year_baseline_median = (
        primary
        .groupby("year")[
            "baseline_speed_mph"
        ]
        .transform("median")
    )

    primary[
        "baseline_below_year_median"
    ] = (
        primary[
            "baseline_speed_mph"
        ]
        < year_baseline_median
    )

    primary[
        "abs_delta_mph"
    ] = (
        primary[TARGET].abs()
    )

    primary[
        "positive_gain"
    ] = (
        primary[TARGET] > 0
    )

    primary[
        "gain_ge_0_5_mph"
    ] = (
        primary[TARGET] >= 0.5
    )

    primary[
        "gain_ge_1_0_mph"
    ] = (
        primary[TARGET] >= 1.0
    )

    primary[
        "diagnostic_large_gain"
    ] = (
        primary[TARGET]
        > diagnostic_large_gain_threshold
    )

    primary[
        "diagnostic_normal_regime"
    ] = ~primary[
        "diagnostic_large_gain"
    ]

    primary[
        "regime_label"
    ] = np.where(
        primary[
            "diagnostic_large_gain"
        ],
        "LARGE_GAIN_DIAGNOSTIC",
        "NORMAL_VARIATION_DIAGNOSTIC",
    )

    # ========================================================
    # Threshold sensitivity audit
    # ========================================================

    threshold_rows = []

    thresholds = []

    for value in FIXED_GAIN_THRESHOLDS:
        thresholds.append(
            (
                f"FIXED_{value:.1f}_MPH",
                float(value),
            )
        )

    thresholds.extend(
        [
            (
                "TUKEY_UPPER",
                float(
                    tukey_upper
                ),
            ),
            (
                "MAD_3SIGMA_UPPER",
                float(
                    mad_upper
                ),
            ),
            (
                "DIAGNOSTIC_COMBINED",
                float(
                    diagnostic_large_gain_threshold
                ),
            ),
        ]
    )

    for name, threshold in thresholds:

        mask = (
            primary[TARGET]
            > threshold
        )

        normal = primary[
            ~mask
        ]

        large = primary[
            mask
        ]

        total_abs_error = float(
            primary[
                "abs_delta_mph"
            ].sum()
        )

        large_abs_error = float(
            large[
                "abs_delta_mph"
            ].sum()
        )

        total_sq_error = float(
            (
                primary[TARGET] ** 2
            ).sum()
        )

        large_sq_error = float(
            (
                large[TARGET] ** 2
            ).sum()
        )

        threshold_rows.append(
            {
                "threshold_name":
                    name,

                "threshold_mph":
                    threshold,

                "large_gain_rows":
                    len(large),

                "large_gain_pct":
                    (
                        len(large)
                        / len(primary)
                        * 100.0
                    ),

                "normal_rows":
                    len(normal),

                "overall_zero_mae_mph":
                    mae_from_zero(
                        primary[TARGET]
                    ),

                "normal_zero_mae_mph":
                    mae_from_zero(
                        normal[TARGET]
                    ),

                "overall_zero_rmse_mph":
                    rmse_from_zero(
                        primary[TARGET]
                    ),

                "normal_zero_rmse_mph":
                    rmse_from_zero(
                        normal[TARGET]
                    ),

                "large_gain_share_of_total_abs_error_pct":
                    (
                        large_abs_error
                        / total_abs_error
                        * 100.0
                        if total_abs_error > 0
                        else np.nan
                    ),

                "large_gain_share_of_total_squared_error_pct":
                    (
                        large_sq_error
                        / total_sq_error
                        * 100.0
                        if total_sq_error > 0
                        else np.nan
                    ),

                "large_gain_mean_delta_mph":
                    (
                        float(
                            large[TARGET].mean()
                        )
                        if len(large)
                        else np.nan
                    ),

                "normal_mean_delta_mph":
                    (
                        float(
                            normal[TARGET].mean()
                        )
                        if len(normal)
                        else np.nan
                    ),
            }
        )

    threshold_audit = pd.DataFrame(
        threshold_rows
    )

    # ========================================================
    # Outlier contribution ranking
    # ========================================================

    contribution = primary[
        [
            "current_attempt_id",
            "year",
            "car_number",
            "driver_name",
            "baseline_speed_mph",
            TARGET,
            "abs_delta_mph",
        ]
    ].copy()

    contribution[
        "squared_error_vs_zero"
    ] = (
        contribution[TARGET] ** 2
    )

    contribution = contribution.sort_values(
        "abs_delta_mph",
        ascending=False,
    ).reset_index(
        drop=True
    )

    total_abs = float(
        contribution[
            "abs_delta_mph"
        ].sum()
    )

    total_sq = float(
        contribution[
            "squared_error_vs_zero"
        ].sum()
    )

    contribution[
        "cumulative_abs_error_share_pct"
    ] = (
        contribution[
            "abs_delta_mph"
        ]
        .cumsum()
        / total_abs
        * 100.0
    )

    contribution[
        "cumulative_squared_error_share_pct"
    ] = (
        contribution[
            "squared_error_vs_zero"
        ]
        .cumsum()
        / total_sq
        * 100.0
    )

    contribution[
        "error_rank"
    ] = (
        np.arange(
            1,
            len(contribution) + 1
        )
    )

    # ========================================================
    # Regime summaries
    # ========================================================

    regime_rows = []

    def add_summary(
        label,
        subset,
    ):

        if subset.empty:
            return

        regime_rows.append(
            {
                "group_type":
                    "REGIME",

                "group_value":
                    label,

                "rows":
                    len(subset),

                "mean_delta_mph":
                    float(
                        subset[TARGET].mean()
                    ),

                "median_delta_mph":
                    float(
                        subset[TARGET].median()
                    ),

                "std_delta_mph":
                    float(
                        subset[TARGET].std(
                            ddof=1
                        )
                    )
                    if len(subset) > 1
                    else np.nan,

                "zero_mae_mph":
                    mae_from_zero(
                        subset[TARGET]
                    ),

                "zero_rmse_mph":
                    rmse_from_zero(
                        subset[TARGET]
                    ),

                "gain_rate":
                    float(
                        (
                            subset[TARGET]
                            > 0
                        ).mean()
                    ),

                "mean_baseline_speed_mph":
                    float(
                        subset[
                            "baseline_speed_mph"
                        ].mean()
                    ),

                "median_baseline_speed_mph":
                    float(
                        subset[
                            "baseline_speed_mph"
                        ].median()
                    ),

                "mean_seconds_since_baseline":
                    float(
                        subset[
                            "seconds_since_baseline_attempt"
                        ].mean()
                    ),
            }
        )

    add_summary(
        "ALL_PRIMARY",
        primary,
    )

    add_summary(
        "NORMAL_VARIATION_DIAGNOSTIC",
        primary[
            primary[
                "diagnostic_normal_regime"
            ]
        ],
    )

    add_summary(
        "LARGE_GAIN_DIAGNOSTIC",
        primary[
            primary[
                "diagnostic_large_gain"
            ]
        ],
    )

    for year, group in (
        primary.groupby("year")
    ):

        regime_rows.append(
            {
                "group_type":
                    "YEAR",

                "group_value":
                    str(int(year)),

                "rows":
                    len(group),

                "mean_delta_mph":
                    float(
                        group[TARGET].mean()
                    ),

                "median_delta_mph":
                    float(
                        group[TARGET].median()
                    ),

                "std_delta_mph":
                    float(
                        group[TARGET].std(
                            ddof=1
                        )
                    )
                    if len(group) > 1
                    else np.nan,

                "zero_mae_mph":
                    mae_from_zero(
                        group[TARGET]
                    ),

                "zero_rmse_mph":
                    rmse_from_zero(
                        group[TARGET]
                    ),

                "gain_rate":
                    float(
                        (
                            group[TARGET]
                            > 0
                        ).mean()
                    ),

                "mean_baseline_speed_mph":
                    float(
                        group[
                            "baseline_speed_mph"
                        ].mean()
                    ),

                "median_baseline_speed_mph":
                    float(
                        group[
                            "baseline_speed_mph"
                        ].median()
                    ),

                "mean_seconds_since_baseline":
                    float(
                        group[
                            "seconds_since_baseline_attempt"
                        ].mean()
                    ),
            }
        )

    for low_baseline, group in (
        primary.groupby(
            "baseline_below_year_median"
        )
    ):

        regime_rows.append(
            {
                "group_type":
                    "BASELINE_RELATIVE_TO_YEAR_MEDIAN",

                "group_value":
                    (
                        "BELOW_YEAR_MEDIAN"
                        if low_baseline
                        else "AT_OR_ABOVE_YEAR_MEDIAN"
                    ),

                "rows":
                    len(group),

                "mean_delta_mph":
                    float(
                        group[TARGET].mean()
                    ),

                "median_delta_mph":
                    float(
                        group[TARGET].median()
                    ),

                "std_delta_mph":
                    float(
                        group[TARGET].std(
                            ddof=1
                        )
                    )
                    if len(group) > 1
                    else np.nan,

                "zero_mae_mph":
                    mae_from_zero(
                        group[TARGET]
                    ),

                "zero_rmse_mph":
                    rmse_from_zero(
                        group[TARGET]
                    ),

                "gain_rate":
                    float(
                        (
                            group[TARGET]
                            > 0
                        ).mean()
                    ),

                "mean_baseline_speed_mph":
                    float(
                        group[
                            "baseline_speed_mph"
                        ].mean()
                    ),

                "median_baseline_speed_mph":
                    float(
                        group[
                            "baseline_speed_mph"
                        ].median()
                    ),

                "mean_seconds_since_baseline":
                    float(
                        group[
                            "seconds_since_baseline_attempt"
                        ].mean()
                    ),
            }
        )

    regime_summary = pd.DataFrame(
        regime_rows
    )

    # ========================================================
    # Correlations
    # ========================================================

    correlation_rows = []

    scopes = {
        "ALL_PRIMARY":
            primary,

        "NORMAL_VARIATION_DIAGNOSTIC":
            primary[
                primary[
                    "diagnostic_normal_regime"
                ]
            ],

        "LARGE_GAIN_DIAGNOSTIC":
            primary[
                primary[
                    "diagnostic_large_gain"
                ]
            ],
    }

    for scope, subset in scopes.items():

        for feature in ALL_DIAGNOSTIC_FEATURES:

            correlation_rows.append(
                {
                    "scope":
                        scope,

                    "feature_name":
                        feature,

                    "rows":
                        len(subset),

                    "pearson_corr_feature_vs_delta":
                        safe_pearson(
                            subset[feature],
                            subset[TARGET],
                        ),

                    "spearman_corr_feature_vs_delta":
                        safe_spearman(
                            subset[feature],
                            subset[TARGET],
                        ),
                }
            )

    # Special year-centered baseline diagnostic

    correlation_rows.append(
        {
            "scope":
                "ALL_PRIMARY_YEAR_CENTERED",

            "feature_name":
                "baseline_speed_year_centered_mph",

            "rows":
                len(primary),

            "pearson_corr_feature_vs_delta":
                safe_pearson(
                    primary[
                        "baseline_speed_year_centered_mph"
                    ],
                    primary[TARGET],
                ),

            "spearman_corr_feature_vs_delta":
                safe_spearman(
                    primary[
                        "baseline_speed_year_centered_mph"
                    ],
                    primary[TARGET],
                ),
        }
    )

    feature_correlations = pd.DataFrame(
        correlation_rows
    )

    # ========================================================
    # Explicit baseline-recovery diagnostics
    # ========================================================

    baseline_pearson = safe_pearson(
        primary[
            "baseline_speed_year_centered_mph"
        ],
        primary[TARGET],
    )

    baseline_spearman = safe_spearman(
        primary[
            "baseline_speed_year_centered_mph"
        ],
        primary[TARGET],
    )

    low_group = primary[
        primary[
            "baseline_below_year_median"
        ]
    ]

    high_group = primary[
        ~primary[
            "baseline_below_year_median"
        ]
    ]

    low_gain_mean = float(
        low_group[TARGET].mean()
    )

    high_gain_mean = float(
        high_group[TARGET].mean()
    )

    low_large_gain_rate = float(
        low_group[
            "diagnostic_large_gain"
        ].mean()
    )

    high_large_gain_rate = float(
        high_group[
            "diagnostic_large_gain"
        ].mean()
    )

    # ========================================================
    # Top-k error concentration
    # ========================================================

    top_error_rows = []

    for k in [
        1,
        2,
        3,
        4,
        5,
        10,
    ]:

        top = contribution.head(k)

        remaining = contribution.iloc[k:]

        top_error_rows.append(
            {
                "top_k":
                    k,

                "top_k_abs_error_share_pct":
                    float(
                        top[
                            "abs_delta_mph"
                        ].sum()
                        / total_abs
                        * 100.0
                    ),

                "top_k_squared_error_share_pct":
                    float(
                        top[
                            "squared_error_vs_zero"
                        ].sum()
                        / total_sq
                        * 100.0
                    ),

                "remaining_rows":
                    len(remaining),

                "remaining_zero_mae_mph":
                    (
                        mae_from_zero(
                            remaining[TARGET]
                        )
                        if len(remaining)
                        else np.nan
                    ),

                "remaining_zero_rmse_mph":
                    (
                        rmse_from_zero(
                            remaining[TARGET]
                        )
                        if len(remaining)
                        else np.nan
                    ),
            }
        )

    outlier_contribution = pd.DataFrame(
        top_error_rows
    )

    # ========================================================
    # QA
    # ========================================================

    diagnostic_large_gain_rows = int(
        primary[
            "diagnostic_large_gain"
        ].sum()
    )

    normal_rows = int(
        primary[
            "diagnostic_normal_regime"
        ].sum()
    )

    checks = {
        "input_rows_equal_40":
            len(work)
            == 40,

        "primary_rows_equal_39":
            len(primary)
            == 39,

        "sensitivity_rows_equal_1":
            len(sensitivity)
            == 1,

        "primary_current_attempt_ids_unique":
            not primary[
                "current_attempt_id"
            ].duplicated().any(),

        "all_target_values_present":
            primary[TARGET].notna().all(),

        "all_diagnostic_features_present":
            not primary[
                ALL_DIAGNOSTIC_FEATURES
            ].isna().any().any(),

        "tukey_upper_finite":
            np.isfinite(
                tukey_upper
            ),

        "mad_upper_finite":
            np.isfinite(
                mad_upper
            ),

        "diagnostic_threshold_finite":
            np.isfinite(
                diagnostic_large_gain_threshold
            ),

        "regime_partition_complete":
            (
                diagnostic_large_gain_rows
                + normal_rows
                == len(primary)
            ),

        "threshold_audit_nonempty":
            len(
                threshold_audit
            ) >= 7,

        "outlier_contribution_rows_equal_6":
            len(
                outlier_contribution
            ) == 6,

        "feature_correlation_output_nonempty":
            len(
                feature_correlations
            ) > 0,
    }

    policy_payload = {
        "phase":
            "5B-3",

        "target":
            TARGET,

        "primary_years":
            PRIMARY_YEARS,

        "fixed_thresholds":
            FIXED_GAIN_THRESHOLDS,

        "tukey_upper":
            tukey_upper,

        "mad_upper":
            mad_upper,

        "diagnostic_large_gain_threshold":
            diagnostic_large_gain_threshold,

        "policy_version":
            POLICY_VERSION,
    }

    policy_hash = stable_hash(
        policy_payload
    )

    qa_rows = []

    for metric, passed in (
        checks.items()
    ):

        qa_rows.append(
            {
                "metric":
                    metric,

                "value":
                    int(
                        bool(passed)
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
                    "primary_target_mean_mph",

                "value":
                    float(
                        primary[TARGET].mean()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_target_median_mph",

                "value":
                    median,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_target_q1_mph",

                "value":
                    q1,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_target_q3_mph",

                "value":
                    q3,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_target_iqr_mph",

                "value":
                    iqr,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "tukey_upper_threshold_mph",

                "value":
                    tukey_upper,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "mad",

                "value":
                    mad,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "mad_3sigma_upper_threshold_mph",

                "value":
                    mad_upper,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "diagnostic_large_gain_threshold_mph",

                "value":
                    diagnostic_large_gain_threshold,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "diagnostic_large_gain_rows",

                "value":
                    diagnostic_large_gain_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "normal_regime_rows",

                "value":
                    normal_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "baseline_year_centered_pearson_vs_delta",

                "value":
                    baseline_pearson,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "baseline_year_centered_spearman_vs_delta",

                "value":
                    baseline_spearman,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "low_baseline_mean_delta_mph",

                "value":
                    low_gain_mean,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "high_baseline_mean_delta_mph",

                "value":
                    high_gain_mean,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "low_baseline_large_gain_rate",

                "value":
                    low_large_gain_rate,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "high_baseline_large_gain_rate",

                "value":
                    high_large_gain_rate,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "policy_hash",

                "value":
                    policy_hash,

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
    # Print
    # ========================================================

    print()
    print("ROBUST TARGET STRUCTURE")
    print("-" * 100)

    print(
        "Primary rows:",
        len(primary)
    )

    print(
        "Mean delta:",
        float(
            primary[TARGET].mean()
        ),
        "mph",
    )

    print(
        "Median delta:",
        median,
        "mph",
    )

    print(
        "Q1:",
        q1,
        "mph",
    )

    print(
        "Q3:",
        q3,
        "mph",
    )

    print(
        "IQR:",
        iqr,
        "mph",
    )

    print(
        "Tukey upper threshold:",
        tukey_upper,
        "mph",
    )

    print(
        "MAD 3-sigma upper threshold:",
        mad_upper,
        "mph",
    )

    print(
        "Diagnostic combined large-gain threshold:",
        diagnostic_large_gain_threshold,
        "mph",
    )

    print()
    print("THRESHOLD SENSITIVITY")
    print("-" * 160)

    print(
        threshold_audit.to_string(
            index=False
        )
    )

    print()
    print("TOP ERROR CONCENTRATION")
    print("-" * 120)

    print(
        outlier_contribution.to_string(
            index=False
        )
    )

    print()
    print("TOP 12 DELTA MAGNITUDES")
    print("-" * 140)

    print(
        contribution[
            [
                "error_rank",
                "year",
                "car_number",
                "driver_name",
                "baseline_speed_mph",
                TARGET,
                "abs_delta_mph",
                "cumulative_abs_error_share_pct",
                "cumulative_squared_error_share_pct",
            ]
        ]
        .head(12)
        .to_string(
            index=False
        )
    )

    print()
    print("REGIME SUMMARY")
    print("-" * 150)

    print(
        regime_summary.to_string(
            index=False
        )
    )

    print()
    print("BASELINE RECOVERY DIAGNOSTIC")
    print("-" * 100)

    print(
        "Year-centered baseline speed Pearson vs delta:",
        baseline_pearson,
    )

    print(
        "Year-centered baseline speed Spearman vs delta:",
        baseline_spearman,
    )

    print(
        "Below-year-median baseline mean delta:",
        low_gain_mean,
        "mph",
    )

    print(
        "At/above-year-median baseline mean delta:",
        high_gain_mean,
        "mph",
    )

    print(
        "Below-year-median large-gain rate:",
        low_large_gain_rate,
    )

    print(
        "At/above-year-median large-gain rate:",
        high_large_gain_rate,
    )

    print()
    print(
        "NORMAL-REGIME FEATURE CORRELATIONS"
    )
    print("-" * 140)

    normal_corr = (
        feature_correlations[
            feature_correlations[
                "scope"
            ]
            == "NORMAL_VARIATION_DIAGNOSTIC"
        ]
        .copy()
    )

    normal_corr[
        "abs_spearman"
    ] = (
        normal_corr[
            "spearman_corr_feature_vs_delta"
        ].abs()
    )

    print(
        normal_corr
        .sort_values(
            "abs_spearman",
            ascending=False,
        )[
            [
                "feature_name",
                "rows",
                "pearson_corr_feature_vs_delta",
                "spearman_corr_feature_vs_delta",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("DIAGNOSTIC LARGE-GAIN ROWS")
    print("-" * 160)

    large_rows = primary[
        primary[
            "diagnostic_large_gain"
        ]
    ].copy()

    if large_rows.empty:

        print(
            "No rows exceed diagnostic threshold."
        )

    else:

        print(
            large_rows[
                [
                    "year",
                    "car_number",
                    "driver_name",
                    "baseline_speed_mph",
                    TARGET,
                    "seconds_since_baseline_attempt",
                    "delta_temp_c",
                    "delta_relative_humidity_pct",
                    "delta_wind_speed_10m_ms",
                    "delta_shortwave_radiation_wm2",
                    "baseline_below_year_median",
                ]
            ]
            .sort_values(
                TARGET,
                ascending=False,
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
    # Write
    # ========================================================

    ROW_DIAGNOSTICS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    primary[
        "diagnostic_policy_hash"
    ] = policy_hash

    threshold_audit[
        "diagnostic_policy_hash"
    ] = policy_hash

    regime_summary[
        "diagnostic_policy_hash"
    ] = policy_hash

    feature_correlations[
        "diagnostic_policy_hash"
    ] = policy_hash

    outlier_contribution[
        "diagnostic_policy_hash"
    ] = policy_hash

    primary.to_csv(
        ROW_DIAGNOSTICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    threshold_audit.to_csv(
        THRESHOLD_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    regime_summary.to_csv(
        REGIME_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    feature_correlations.to_csv(
        FEATURE_CORRELATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    outlier_contribution.to_csv(
        OUTLIER_CONTRIBUTION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # Report
    # ========================================================

    report = []

    report.append(
        "# Repeat-Delta Regime Diagnosis V1"
    )

    report.append("")

    report.append(
        f"Primary rows: `{len(primary)}`"
    )

    report.append("")

    report.append(
        "## Robust target structure"
    )

    report.append("")

    report.append(
        f"- Median delta: `{median:.6f} mph`"
    )

    report.append(
        f"- IQR: `{iqr:.6f} mph`"
    )

    report.append(
        f"- Tukey upper threshold: "
        f"`{tukey_upper:.6f} mph`"
    )

    report.append(
        f"- MAD-based upper threshold: "
        f"`{mad_upper:.6f} mph`"
    )

    report.append(
        f"- Diagnostic combined threshold: "
        f"`{diagnostic_large_gain_threshold:.6f} mph`"
    )

    report.append(
        f"- Diagnostic large-gain rows: "
        f"`{diagnostic_large_gain_rows}`"
    )

    report.append("")

    report.append(
        "The large-gain label is diagnostic only. "
        "It is not yet a frozen predictive class."
    )

    report.append("")

    report.append(
        "## Baseline recovery diagnostic"
    )

    report.append("")

    report.append(
        f"- Year-centered baseline-speed Pearson correlation "
        f"with delta: `{baseline_pearson:.6f}`"
        if pd.notna(
            baseline_pearson
        )
        else "- Pearson correlation unavailable."
    )

    report.append(
        f"- Year-centered baseline-speed Spearman correlation "
        f"with delta: `{baseline_spearman:.6f}`"
        if pd.notna(
            baseline_spearman
        )
        else "- Spearman correlation unavailable."
    )

    report.append(
        f"- Mean delta below year-median baseline: "
        f"`{low_gain_mean:.6f} mph`"
    )

    report.append(
        f"- Mean delta at/above year-median baseline: "
        f"`{high_gain_mean:.6f} mph`"
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- No predictive model was trained."
    )

    report.append(
        "- No outlier was deleted."
    )

    report.append(
        "- No target row was excluded from the frozen delta layer."
    )

    report.append(
        "- Large-gain thresholds are sensitivity diagnostics only."
    )

    report.append(
        "- 2024 remains outside primary regime conclusions."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**REPEAT_DELTA_REGIME_DIAGNOSIS_COMPLETE**"
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
            "REPEAT_DELTA_REGIME_DIAGNOSIS_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO ROWS WERE REMOVED."
    )

    print(
        "NO NEW MODEL WAS TRAINED."
    )

    print(
        "NO REGIME CLASSIFICATION HAS BEEN FROZEN YET."
    )

    print()
    print("OUTPUTS")

    print(
        ROW_DIAGNOSTICS_FILE
    )

    print(
        THRESHOLD_AUDIT_FILE
    )

    print(
        REGIME_SUMMARY_FILE
    )

    print(
        FEATURE_CORRELATION_FILE
    )

    print(
        OUTLIER_CONTRIBUTION_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
