from pathlib import Path
import math
import pandas as pd
import numpy as np


# ============================================================
# INPUT
# ============================================================

INPUT_FILE = Path(
    "weather/output/performance_context_features.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

COLUMN_AUDIT_FILE = Path(
    "weather/output/"
    "attempt_performance_modeling_column_audit.csv"
)

CORRELATION_AUDIT_FILE = Path(
    "weather/output/"
    "attempt_performance_modeling_correlation_audit.csv"
)

FEATURE_SET_FILE = Path(
    "weather/output/"
    "attempt_performance_baseline_feature_set_v1.csv"
)

SUMMARY_FILE = Path(
    "weather/output/"
    "attempt_performance_modeling_readiness_summary.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "attempt_performance_modeling_readiness.md"
)


# ============================================================
# TARGET
# ============================================================

TARGET = "four_lap_average_speed_mph"


# ============================================================
# HARD LEAKAGE / EXCLUSION POLICY
# ============================================================

# Current-attempt outcomes. These are only known after the
# attempt has happened and therefore cannot be predictors of
# that same attempt's performance.
CURRENT_OUTCOME_FORBIDDEN = {
    "four_lap_average_speed_mph",
    "four_lap_total_seconds",
    "result_status",
    "result_counted_at_session_end",
    "attempt_class",
    "speed_change_vs_prior_supported_attempt_mph",
    "speed_change_vs_best_prior_supported_mph",
}


# Identity / provenance / bookkeeping fields that should not
# enter a baseline numerical performance model as predictors.
NON_MODEL_METADATA = {
    "attempt_id",
    "session_id",
    "entry_key",
    "attempt_key",
    "driver_name",
    "performance_time_utc",
    "performance_time_semantic",
    "performance_timing_source",
    "timing_class",
    "timing_basis",
    "performance_alignment_usable",
    "decision_state_usable",
    "leaderboard_state_complete",
    "queue_state_available",
    "derivation_rule_version",
    "input_lineage_hash",
    "forecast_selection_class",
    "availability_policy_id",
    "availability_policy_hash",
    "semantic_note",
    "leakage_safe",
    "forecast_available_before_target",
    "forecast_available_after_target",
}


# Forecast interpolation mechanics / provenance. They describe
# how the feature was generated rather than the weather itself.
FORECAST_MECHANICS = {
    "selected_issue_time_utc",
    "selected_issue_age_minutes",
    "before_forecast_snapshot_id",
    "after_forecast_snapshot_id",
    "before_valid_time_utc",
    "after_valid_time_utc",
    "before_forecast_lead_hours",
    "after_forecast_lead_hours",
    "before_valid_offset_minutes",
    "after_valid_offset_minutes",
    "interpolation_weight_after",
    "availability_lag_minutes",
}


# Raw HRRR fields are retained for QA/provenance but derived
# human-readable fields are preferred for V1 baseline.
RAW_HRRR_VARIABLES = {
    "forecast_TMP_2m",
    "forecast_DPT_2m",
    "forecast_UGRD_10m",
    "forecast_VGRD_10m",
    "forecast_GUST_surface",
    "forecast_PRES_surface",
    "forecast_TCDC_atmosphere",
    "forecast_DSWRF_surface",
}


# Raw-before / raw-after / interpolation-method fields are
# never baseline predictors.
def is_forecast_interpolation_detail(col):
    return (
        col.endswith("_before")
        or col.endswith("_after")
        or col.endswith("_interpolation_method")
    )


# Preferred derived HRRR variables.
DERIVED_HRRR_BASELINE = [
    "forecast_temp_c",
    "forecast_dewpoint_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_wind_direction_deg",
    "forecast_pressure_hpa",
    "forecast_gust_ms",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
]


# Same-car historical features that are genuinely pre-attempt
# context and therefore can be used.
PRIOR_HISTORY_CANDIDATES = [
    "prior_supported_attempt_count",
    "seconds_since_prior_supported_attempt",
    "prior_supported_attempt_average_speed_mph",
    "prior_supported_attempt_total_seconds",
    "best_prior_supported_average_speed_mph",
    "best_prior_supported_total_seconds",
]


# Car attempt index can encode repeated-attempt context.
STRUCTURAL_CANDIDATES = [
    "car_attempt_index",
    "car_number",
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


def infer_year_from_session(series):
    return pd.to_numeric(
        series
        .astype(str)
        .str.extract(
            r"(20\d{2})",
            expand=False,
        ),
        errors="coerce",
    )


def numeric_convertible_fraction(series):
    converted = pd.to_numeric(
        series,
        errors="coerce",
    )

    nonnull_original = series.notna().sum()

    if nonnull_original == 0:
        return 0.0

    return (
        converted.notna().sum()
        / nonnull_original
    )


def classify_column(
    col,
    df,
):
    if col == TARGET:
        return (
            "TARGET",
            "EXCLUDE",
            "Current-attempt prediction target.",
        )

    if col in CURRENT_OUTCOME_FORBIDDEN:
        return (
            "POST_OUTCOME_LEAKAGE",
            "EXCLUDE",
            "Current-attempt outcome or derivative of current outcome.",
        )

    if col in NON_MODEL_METADATA:
        return (
            "METADATA_PROVENANCE",
            "EXCLUDE",
            "Identity/provenance/bookkeeping field.",
        )

    if col in FORECAST_MECHANICS:
        return (
            "FORECAST_MECHANICS",
            "EXCLUDE",
            "Forecast-selection mechanics rather than environmental state.",
        )

    if is_forecast_interpolation_detail(
        col
    ):
        return (
            "FORECAST_INTERPOLATION_DETAIL",
            "EXCLUDE",
            "Before/after/interpolation-method diagnostic field.",
        )

    if col in RAW_HRRR_VARIABLES:
        return (
            "RAW_HRRR_REDUNDANT",
            "EXCLUDE_V1",
            "Raw HRRR representation retained for QA; derived form preferred.",
        )

    if col in DERIVED_HRRR_BASELINE:
        return (
            "DERIVED_HRRR_ENVIRONMENT",
            "CANDIDATE",
            "Preferred weather representation for V1.",
        )

    if col in PRIOR_HISTORY_CANDIDATES:
        return (
            "PRIOR_ATTEMPT_CONTEXT",
            "CANDIDATE",
            "Pre-attempt same-car historical context.",
        )

    if col in STRUCTURAL_CANDIDATES:
        return (
            "STRUCTURAL",
            "REVIEW",
            "Potentially useful but may encode car/driver/year identity.",
        )

    return (
        "UNCLASSIFIED",
        "REVIEW",
        "Requires manual review before modeling.",
    )


def safe_abs_corr(
    a,
    b,
):
    pair = pd.DataFrame(
        {
            "a": pd.to_numeric(
                a,
                errors="coerce",
            ),
            "b": pd.to_numeric(
                b,
                errors="coerce",
            ),
        }
    ).dropna()

    if len(pair) < 3:
        return np.nan

    if (
        pair[
            "a"
        ].nunique()
        < 2
        or pair[
            "b"
        ].nunique()
        < 2
    ):
        return np.nan

    return abs(
        pair[
            "a"
        ].corr(
            pair[
                "b"
            ]
        )
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
        "PHASE 5A-2 — ATTEMPT-PERFORMANCE "
        "MODELING READINESS / LEAKAGE AUDIT"
    )
    print("=" * 100)

    print()
    print(
        "Input rows:",
        len(df)
    )

    print(
        "Input columns:",
        len(df.columns)
    )

    if TARGET not in df.columns:
        raise RuntimeError(
            f"Missing target column: {TARGET}"
        )

    if len(df) != 136:
        raise RuntimeError(
            f"Expected 136 rows, got {len(df)}"
        )

    if df[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in performance context."
        )

    # ========================================================
    # Year / target coverage
    # ========================================================

    df = df.copy()

    df[
        "_year"
    ] = infer_year_from_session(
        df[
            "session_id"
        ]
    )

    target_numeric = pd.to_numeric(
        df[
            TARGET
        ],
        errors="coerce",
    )

    print()
    print("TARGET COVERAGE")
    print("-" * 70)

    print(
        f"{TARGET}: "
        f"{target_numeric.notna().sum()}/{len(df)}"
    )

    print()
    print("TARGET COVERAGE BY YEAR")
    print("-" * 100)

    target_year = (
        df.assign(
            _target_nonnull=target_numeric.notna()
        )
        .groupby(
            "_year",
            dropna=False,
        )
        .agg(
            rows=(
                "attempt_id",
                "size",
            ),
            target_rows=(
                "_target_nonnull",
                "sum",
            ),
        )
        .reset_index()
    )

    target_year[
        "target_coverage_pct"
    ] = (
        target_year[
            "target_rows"
        ]
        / target_year[
            "rows"
        ]
        * 100.0
    )

    print(
        target_year.to_string(
            index=False
        )
    )

    # ========================================================
    # Column-level audit
    # ========================================================

    column_rows = []

    for col in df.columns:

        if col == "_year":
            continue

        category, decision, reason = (
            classify_column(
                col,
                df,
            )
        )

        nonnull = int(
            df[
                col
            ].notna().sum()
        )

        missing = (
            len(df)
            - nonnull
        )

        unique_nonnull = int(
            df[
                col
            ]
            .dropna()
            .nunique()
        )

        numeric_fraction = (
            numeric_convertible_fraction(
                df[
                    col
                ]
            )
        )

        numeric = pd.to_numeric(
            df[
                col
            ],
            errors="coerce",
        )

        numeric_nonnull = int(
            numeric.notna().sum()
        )

        constant_numeric = (
            numeric_nonnull > 0
            and numeric.dropna().nunique()
            <= 1
        )

        target_corr = np.nan

        if (
            col != TARGET
            and numeric_nonnull >= 3
        ):
            target_corr = safe_abs_corr(
                numeric,
                target_numeric,
            )

        column_rows.append(
            {
                "column_name":
                    col,

                "category":
                    category,

                "v1_decision":
                    decision,

                "reason":
                    reason,

                "nonnull_rows":
                    nonnull,

                "missing_rows":
                    missing,

                "missing_pct":
                    (
                        missing
                        / len(df)
                        * 100.0
                    ),

                "unique_nonnull_values":
                    unique_nonnull,

                "numeric_convertible_fraction":
                    numeric_fraction,

                "numeric_nonnull_rows":
                    numeric_nonnull,

                "constant_numeric":
                    constant_numeric,

                "abs_correlation_with_target":
                    target_corr,
            }
        )

    column_audit = pd.DataFrame(
        column_rows
    )

    # ========================================================
    # Candidate features
    # ========================================================

    baseline_candidates = []

    for col in (
        DERIVED_HRRR_BASELINE
        + PRIOR_HISTORY_CANDIDATES
    ):
        if col in df.columns:
            baseline_candidates.append(
                col
            )

    # We deliberately do not include car_number in the first
    # baseline. With only 123 target rows, car identity would
    # be too easy to overfit.
    if (
        "car_attempt_index"
        in df.columns
    ):
        baseline_candidates.append(
            "car_attempt_index"
        )

    baseline_candidates = list(
        dict.fromkeys(
            baseline_candidates
        )
    )

    # ========================================================
    # Missingness policy
    # ========================================================

    feature_rows = []

    for col in baseline_candidates:

        numeric = pd.to_numeric(
            df[
                col
            ],
            errors="coerce",
        )

        missing = int(
            numeric.isna().sum()
        )

        if col in PRIOR_HISTORY_CANDIDATES:

            # Missing prior-history values are structurally
            # expected for first supported attempt. Keep them,
            # but model pipeline must impute + use prior count.
            missing_policy = (
                "STRUCTURAL_MISSING_ALLOWED"
            )

        else:
            missing_policy = (
                "SHOULD_BE_COMPLETE"
            )

        feature_rows.append(
            {
                "feature_name":
                    col,

                "feature_group":
                    (
                        "HRRR_DERIVED"
                        if col
                        in DERIVED_HRRR_BASELINE
                        else (
                            "PRIOR_ATTEMPT_CONTEXT"
                            if col
                            in PRIOR_HISTORY_CANDIDATES
                            else "STRUCTURAL"
                        )
                    ),

                "nonnull_rows":
                    int(
                        numeric.notna().sum()
                    ),

                "missing_rows":
                    missing,

                "missing_pct":
                    (
                        missing
                        / len(df)
                        * 100.0
                    ),

                "missingness_policy":
                    missing_policy,

                "baseline_v1":
                    True,
            }
        )

    feature_set = pd.DataFrame(
        feature_rows
    )

    # ========================================================
    # Correlation / redundancy audit
    # ========================================================

    numeric_candidate_df = pd.DataFrame(
        {
            col: pd.to_numeric(
                df[
                    col
                ],
                errors="coerce",
            )
            for col in baseline_candidates
        }
    )

    corr_rows = []

    for i, a in enumerate(
        baseline_candidates
    ):

        for b in baseline_candidates[
            i + 1:
        ]:

            corr = safe_abs_corr(
                numeric_candidate_df[
                    a
                ],
                numeric_candidate_df[
                    b
                ],
            )

            if pd.isna(corr):
                continue

            corr_rows.append(
                {
                    "feature_a":
                        a,

                    "feature_b":
                        b,

                    "abs_pearson_correlation":
                        corr,

                    "high_redundancy_flag":
                        bool(
                            corr >= 0.95
                        ),

                    "review_flag":
                        bool(
                            corr >= 0.85
                        ),
                }
            )

    correlation_audit = pd.DataFrame(
        corr_rows
    )

    if not correlation_audit.empty:
        correlation_audit = (
            correlation_audit
            .sort_values(
                "abs_pearson_correlation",
                ascending=False,
            )
            .reset_index(
                drop=True
            )
        )

    # ========================================================
    # Explicit raw/derived equivalence audit
    # ========================================================

    equivalence_pairs = [
        (
            "forecast_TMP_2m",
            "forecast_temp_c",
        ),
        (
            "forecast_DPT_2m",
            "forecast_dewpoint_c",
        ),
        (
            "forecast_GUST_surface",
            "forecast_gust_ms",
        ),
        (
            "forecast_PRES_surface",
            "forecast_pressure_hpa",
        ),
        (
            "forecast_TCDC_atmosphere",
            "forecast_cloud_cover_pct",
        ),
        (
            "forecast_DSWRF_surface",
            "forecast_shortwave_radiation_wm2",
        ),
    ]

    print()
    print("RAW / DERIVED HRRR REDUNDANCY")
    print("-" * 100)

    redundancy_pass = True

    for raw_col, derived_col in (
        equivalence_pairs
    ):

        if (
            raw_col not in df.columns
            or derived_col not in df.columns
        ):
            print(
                f"SKIP  {raw_col} <-> {derived_col}"
            )
            continue

        corr = safe_abs_corr(
            df[
                raw_col
            ],
            df[
                derived_col
            ],
        )

        print(
            f"{raw_col:35} "
            f"<-> {derived_col:40} "
            f"| abs corr = {corr}"
        )

        if (
            pd.notna(
                corr
            )
            and corr < 0.999
        ):
            redundancy_pass = False

    # ========================================================
    # U/V versus derived wind audit
    # ========================================================

    wind_columns_present = all(
        c in df.columns
        for c in [
            "forecast_UGRD_10m",
            "forecast_VGRD_10m",
            "forecast_wind_speed_10m_ms",
            "forecast_wind_direction_deg",
        ]
    )

    if wind_columns_present:

        u = pd.to_numeric(
            df[
                "forecast_UGRD_10m"
            ],
            errors="coerce",
        )

        v = pd.to_numeric(
            df[
                "forecast_VGRD_10m"
            ],
            errors="coerce",
        )

        speed = pd.to_numeric(
            df[
                "forecast_wind_speed_10m_ms"
            ],
            errors="coerce",
        )

        reconstructed_speed = np.sqrt(
            u ** 2
            + v ** 2
        )

        wind_speed_error = (
            reconstructed_speed
            - speed
        ).abs()

        wind_speed_mae = float(
            wind_speed_error.dropna().mean()
        )

        wind_speed_max_error = float(
            wind_speed_error.dropna().max()
        )

    else:
        wind_speed_mae = np.nan
        wind_speed_max_error = np.nan

    # ========================================================
    # Sample-size / year balance
    # ========================================================

    model_rows = df[
        target_numeric.notna()
    ].copy()

    model_rows[
        "_target"
    ] = target_numeric[
        target_numeric.notna()
    ]

    year_counts = (
        model_rows[
            "_year"
        ]
        .value_counts()
        .sort_index()
    )

    print()
    print("MODEL-ELIGIBLE TARGET ROWS BY YEAR")
    print("-" * 70)

    print(
        year_counts.to_string()
    )

    # ========================================================
    # Prior-history missingness
    # ========================================================

    print()
    print("BASELINE CANDIDATE FEATURE MISSINGNESS")
    print("-" * 100)

    print(
        feature_set.to_string(
            index=False
        )
    )

    # ========================================================
    # Highest correlations
    # ========================================================

    print()
    print("HIGHEST BASELINE FEATURE CORRELATIONS")
    print("-" * 100)

    if correlation_audit.empty:
        print(
            "No numeric feature pairs available."
        )
    else:
        print(
            correlation_audit
            .head(30)
            .to_string(
                index=False
            )
        )

    # ========================================================
    # Leakage audit report
    # ========================================================

    print()
    print("COLUMN CLASSIFICATION COUNTS")
    print("-" * 70)

    print(
        column_audit[
            [
                "category",
                "v1_decision",
            ]
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("POST-OUTCOME / HARD-EXCLUDED FIELDS")
    print("-" * 100)

    excluded = column_audit[
        column_audit[
            "category"
        ].isin(
            [
                "TARGET",
                "POST_OUTCOME_LEAKAGE",
            ]
        )
    ]

    print(
        excluded[
            [
                "column_name",
                "category",
                "reason",
            ]
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # QA / readiness rules
    # ========================================================

    weather_complete = True

    for col in DERIVED_HRRR_BASELINE:

        if col not in df.columns:
            weather_complete = False
            continue

        if (
            pd.to_numeric(
                df[
                    col
                ],
                errors="coerce",
            )
            .notna()
            .sum()
            != len(df)
        ):
            weather_complete = False

    target_rows = int(
        target_numeric.notna().sum()
    )

    years_with_target = int(
        model_rows[
            "_year"
        ].nunique()
    )

    excluded_in_baseline = (
        set(
            baseline_candidates
        )
        & (
            CURRENT_OUTCOME_FORBIDDEN
            | NON_MODEL_METADATA
            | FORECAST_MECHANICS
            | RAW_HRRR_VARIABLES
        )
    )

    high_corr_pairs = (
        int(
            (
                correlation_audit[
                    "high_redundancy_flag"
                ]
                == True
            ).sum()
        )
        if not correlation_audit.empty
        else 0
    )

    checks = {
        "input_rows_equal_136":
            len(df) == 136,

        "target_rows_equal_expected_123":
            target_rows == 123,

        "model_target_spans_4_years":
            years_with_target == 4,

        "derived_hrrr_complete_136":
            weather_complete,

        "no_hard_excluded_field_in_baseline":
            len(
                excluded_in_baseline
            )
            == 0,

        "raw_derived_redundancy_confirmed":
            redundancy_pass,

        "baseline_feature_set_nonempty":
            len(
                baseline_candidates
            )
            > 0,
    }

    qa_rows = []

    for name, passed in (
        checks.items()
    ):

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
                    "input_rows",
                "value":
                    len(df),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "target_nonnull_rows",
                "value":
                    target_rows,
                "status":
                    "INFO",
            },

            {
                "metric":
                    "baseline_candidate_features",
                "value":
                    len(
                        baseline_candidates
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "high_redundancy_pairs_ge_0_95",
                "value":
                    high_corr_pairs,
                "status":
                    "INFO",
            },

            {
                "metric":
                    "wind_speed_uv_reconstruction_mae",
                "value":
                    wind_speed_mae,
                "status":
                    "INFO",
            },

            {
                "metric":
                    "wind_speed_uv_reconstruction_max_abs_error",
                "value":
                    wind_speed_max_error,
                "status":
                    "INFO",
            },
        ]
    )

    summary = pd.DataFrame(
        qa_rows
    )

    all_pass = all(
        checks.values()
    )

    # ========================================================
    # Write outputs
    # ========================================================

    COLUMN_AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    column_audit.to_csv(
        COLUMN_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    correlation_audit.to_csv(
        CORRELATION_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    feature_set.to_csv(
        FEATURE_SET_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # Markdown report without tabulate dependency
    # ========================================================

    report = []

    report.append(
        "# Attempt-Performance Modeling Readiness Audit"
    )

    report.append("")

    report.append(
        f"Target: `{TARGET}`"
    )

    report.append("")

    report.append(
        f"Input rows: {len(df)}"
    )

    report.append(
        f"Rows with target: {target_rows}"
    )

    report.append("")

    report.append(
        "## Hard leakage exclusions"
    )

    report.append("")

    for col in sorted(
        CURRENT_OUTCOME_FORBIDDEN
    ):
        if col in df.columns:
            report.append(
                f"- `{col}`"
            )

    report.append("")

    report.append(
        "## Baseline V1 candidate features"
    )

    report.append("")

    for col in baseline_candidates:
        report.append(
            f"- `{col}`"
        )

    report.append("")

    report.append(
        "## Modeling policy"
    )

    report.append("")

    report.append(
        "- Raw HRRR fields are retained for QA but excluded "
        "from V1 when a deterministic derived equivalent exists."
    )

    report.append(
        "- Current-attempt result/status/performance derivatives "
        "are excluded from predictors."
    )

    report.append(
        "- Prior supported same-car performance is allowed because "
        "it precedes the current supported attempt timestamp."
    )

    report.append(
        "- Missing prior-history values are structural for first "
        "supported attempts and must be handled explicitly."
    )

    report.append(
        "- `car_number` is not included in the first baseline "
        "to reduce identity memorization / overfitting."
    )

    report.append(
        "- 2022 is absent from this performance-context layer "
        "because no trustworthy attempt-time bridge exists."
    )

    report.append(
        "- 2024 contributes only the seven supported timing rows; "
        "year-level validation must therefore be interpreted cautiously."
    )

    report.append("")

    report.append(
        "## Validation recommendation"
    )

    report.append("")

    report.append(
        "Use year-grouped validation rather than random row splitting. "
        "The primary evaluation should test generalization across years, "
        "with special caution around the very small 2024 supported subset."
    )

    report.append("")

    report.append(
        "## Readiness"
    )

    report.append("")

    if all_pass:

        report.append(
            "**ATTEMPT_PERFORMANCE_MODELING_READY_FOR_BASELINE_DESIGN**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED_BEFORE_BASELINE_MODELING**"
        )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # Print
    # ========================================================

    print()
    print("BASELINE V1 CANDIDATE FEATURES")
    print("-" * 100)

    for col in baseline_candidates:
        print(
            col
        )

    print()
    print("QA / READINESS")
    print("-" * 100)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)

    if all_pass:
        print(
            "FINAL STATUS: "
            "ATTEMPT_PERFORMANCE_MODELING_READY_FOR_BASELINE_DESIGN"
        )
    else:
        print(
            "FINAL STATUS: "
            "REVIEW_REQUIRED_BEFORE_BASELINE_MODELING"
        )

    print("=" * 100)

    print()
    print("IMPORTANT MODELING BOUNDARIES")

    print(
        "- Do NOT use current result_status, "
        "four_lap_total_seconds, or current speed derivatives as inputs."
    )

    print(
        "- Do NOT include both raw HRRR variables "
        "and deterministic derived equivalents."
    )

    print(
        "- Do NOT use random row train/test split as primary validation."
    )

    print(
        "- Do NOT force 2022 into this timing-dependent feature layer."
    )

    print(
        "- Do NOT interpret the seven 2024 rows as a full-year sample."
    )

    print()
    print("OUTPUTS")

    print(
        COLUMN_AUDIT_FILE
    )

    print(
        CORRELATION_AUDIT_FILE
    )

    print(
        FEATURE_SET_FILE
    )

    print(
        SUMMARY_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
