from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd


# ============================================================
# INPUT
# ============================================================

INPUT_FILE = Path(
    "weather/output/performance_context_features.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

MODEL_MATRIX_FILE = Path(
    "weather/output/attempt_performance_model_matrix_v1.csv"
)

FEATURE_MANIFEST_FILE = Path(
    "weather/output/attempt_performance_feature_manifest_v1.csv"
)

VALIDATION_FOLDS_FILE = Path(
    "weather/output/attempt_performance_validation_folds_v1.csv"
)

QA_FILE = Path(
    "weather/output/attempt_performance_v1_design_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/attempt_performance_v1_design.md"
)


# ============================================================
# TARGET
# ============================================================

TARGET = "four_lap_average_speed_mph"


# ============================================================
# FROZEN V1 FEATURES
# ============================================================

BASE_FEATURES = [
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_pressure_hpa",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
    "prior_supported_attempt_count",
    "seconds_since_prior_supported_attempt",
    "best_prior_supported_average_speed_mph",
]

DERIVED_FEATURES = [
    "forecast_wind_direction_sin",
    "forecast_wind_direction_cos",
    "has_prior_supported_attempt",
]

FINAL_FEATURES = [
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_wind_direction_sin",
    "forecast_wind_direction_cos",
    "forecast_pressure_hpa",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
    "prior_supported_attempt_count",
    "seconds_since_prior_supported_attempt",
    "best_prior_supported_average_speed_mph",
    "has_prior_supported_attempt",
]


# ============================================================
# EXPLICITLY EXCLUDED FROM V1
# ============================================================

EXCLUDED_REDUNDANT = [
    "forecast_dewpoint_c",
    "forecast_gust_ms",
    "car_attempt_index",
    "prior_supported_attempt_average_speed_mph",
    "prior_supported_attempt_total_seconds",
    "best_prior_supported_total_seconds",
]

EXCLUDED_LEAKAGE = [
    "attempt_class",
    "result_status",
    "result_counted_at_session_end",
    "four_lap_total_seconds",
    "speed_change_vs_prior_supported_attempt_mph",
    "speed_change_vs_best_prior_supported_mph",
]


# ============================================================
# VALIDATION POLICY
# ============================================================

PRIMARY_VALIDATION_YEARS = [
    2020,
    2021,
    2023,
]

SENSITIVITY_HOLDOUT_YEARS = [
    2024,
]

VALIDATION_PROTOCOL_ID = (
    "YEAR_GROUPED_LOYO_V1"
)

FEATURE_SET_ID = (
    "ATTEMPT_PERFORMANCE_FEATURE_SET_V1"
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


def infer_year(series):
    return pd.to_numeric(
        series
        .astype(str)
        .str.extract(
            r"(20\d{2})",
            expand=False,
        ),
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


def numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce",
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
        "PHASE 5A-3 — FREEZE ATTEMPT-PERFORMANCE "
        "V1 FEATURE SET + VALIDATION PROTOCOL"
    )
    print("=" * 100)

    print()
    print(
        "Input rows:",
        len(df)
    )

    if len(df) != 136:
        raise RuntimeError(
            f"Expected 136 rows, got {len(df)}"
        )

    required = [
        "attempt_id",
        "session_id",
        "car_number",
        "driver_name",
        TARGET,
        "forecast_wind_direction_deg",
    ] + BASE_FEATURES

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    if df[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id."
        )

    work = df.copy()

    work[
        "year"
    ] = infer_year(
        work[
            "session_id"
        ]
    )

    if work[
        "year"
    ].isna().any():
        raise RuntimeError(
            "Unable to infer year from session_id."
        )

    # ========================================================
    # Derived features
    # ========================================================

    wind_deg = numeric(
        work[
            "forecast_wind_direction_deg"
        ]
    )

    if wind_deg.isna().any():
        raise RuntimeError(
            "Missing wind direction in V1 source data."
        )

    wind_rad = np.deg2rad(
        wind_deg
    )

    work[
        "forecast_wind_direction_sin"
    ] = np.sin(
        wind_rad
    )

    work[
        "forecast_wind_direction_cos"
    ] = np.cos(
        wind_rad
    )

    prior_count = numeric(
        work[
            "prior_supported_attempt_count"
        ]
    )

    if prior_count.isna().any():
        raise RuntimeError(
            "Missing prior_supported_attempt_count."
        )

    work[
        "has_prior_supported_attempt"
    ] = (
        prior_count
        > 0
    ).astype(int)

    # ========================================================
    # Structural missingness
    # ========================================================

    seconds_prior = numeric(
        work[
            "seconds_since_prior_supported_attempt"
        ]
    )

    best_prior_speed = numeric(
        work[
            "best_prior_supported_average_speed_mph"
        ]
    )

    first_mask = (
        work[
            "has_prior_supported_attempt"
        ]
        == 0
    )

    repeat_mask = ~first_mask

    # First supported attempts MUST have structural missingness.
    first_seconds_null = (
        seconds_prior[
            first_mask
        ].isna().all()
    )

    first_best_null = (
        best_prior_speed[
            first_mask
        ].isna().all()
    )

    # Repeated supported attempts SHOULD have these values.
    repeat_seconds_present = (
        seconds_prior[
            repeat_mask
        ].notna().all()
    )

    repeat_best_present = (
        best_prior_speed[
            repeat_mask
        ].notna().all()
    )

    # ========================================================
    # Imputation policy for actual model matrix
    #
    # We do NOT use population means for structural missingness.
    #
    # First attempt:
    # seconds_since_prior = 0
    # best_prior_speed = 0
    #
    # has_prior_supported_attempt tells the model these zeros
    # mean "no prior supported attempt", not actual numeric zero.
    # ========================================================

    work[
        "seconds_since_prior_supported_attempt"
    ] = (
        seconds_prior.fillna(
            0.0
        )
    )

    work[
        "best_prior_supported_average_speed_mph"
    ] = (
        best_prior_speed.fillna(
            0.0
        )
    )

    # ========================================================
    # Numeric normalization of final features
    # ========================================================

    for col in FINAL_FEATURES:

        work[
            col
        ] = numeric(
            work[
                col
            ]
        )

    # ========================================================
    # Target eligibility
    # ========================================================

    work[
        TARGET
    ] = numeric(
        work[
            TARGET
        ]
    )

    model = work[
        work[
            TARGET
        ].notna()
    ].copy()

    if len(model) != 123:
        raise RuntimeError(
            f"Expected 123 target rows, got {len(model)}"
        )

    # ========================================================
    # Final feature completeness
    # ========================================================

    feature_missing = (
        model[
            FINAL_FEATURES
        ]
        .isna()
        .sum()
    )

    if (
        feature_missing
        > 0
    ).any():

        print()
        print(
            "MISSING FINAL FEATURES:"
        )

        print(
            feature_missing[
                feature_missing
                > 0
            ].to_string()
        )

        raise RuntimeError(
            "Final V1 model feature matrix contains missing values."
        )

    # ========================================================
    # Model matrix
    # ========================================================

    identity_cols = [
        "attempt_id",
        "session_id",
        "year",
        "car_number",
        "driver_name",
    ]

    model_matrix = model[
        identity_cols
        + FINAL_FEATURES
        + [
            TARGET
        ]
    ].copy()

    model_matrix[
        "feature_set_id"
    ] = FEATURE_SET_ID

    model_matrix[
        "validation_protocol_id"
    ] = VALIDATION_PROTOCOL_ID

    # ========================================================
    # Feature manifest
    # ========================================================

    manifest_rows = []

    for feature in FINAL_FEATURES:

        if feature in [
            "forecast_wind_direction_sin",
            "forecast_wind_direction_cos",
        ]:
            group = (
                "WEATHER_WIND_DIRECTION"
            )

            source = (
                "forecast_wind_direction_deg"
            )

            derivation = (
                "sin/cos circular encoding"
            )

            missing_policy = (
                "NONE"
            )

        elif feature == (
            "has_prior_supported_attempt"
        ):
            group = (
                "PRIOR_ATTEMPT_CONTEXT"
            )

            source = (
                "prior_supported_attempt_count"
            )

            derivation = (
                "1 if prior count > 0 else 0"
            )

            missing_policy = (
                "NONE"
            )

        elif feature in [
            "seconds_since_prior_supported_attempt",
            "best_prior_supported_average_speed_mph",
        ]:
            group = (
                "PRIOR_ATTEMPT_CONTEXT"
            )

            source = feature

            derivation = (
                "direct with structural-zero imputation "
                "when no prior supported attempt"
            )

            missing_policy = (
                "STRUCTURAL_ZERO_WITH_HAS_PRIOR_INDICATOR"
            )

        elif feature == (
            "prior_supported_attempt_count"
        ):
            group = (
                "PRIOR_ATTEMPT_CONTEXT"
            )

            source = feature

            derivation = (
                "direct"
            )

            missing_policy = (
                "NONE"
            )

        else:
            group = (
                "HRRR_DERIVED_WEATHER"
            )

            source = feature

            derivation = (
                "same-cycle leakage-safe HRRR interpolation"
            )

            missing_policy = (
                "NONE"
            )

        manifest_rows.append(
            {
                "feature_set_id":
                    FEATURE_SET_ID,

                "feature_name":
                    feature,

                "feature_group":
                    group,

                "source_field":
                    source,

                "derivation":
                    derivation,

                "missingness_policy":
                    missing_policy,

                "included_v1":
                    True,
            }
        )

    feature_manifest = pd.DataFrame(
        manifest_rows
    )

    # ========================================================
    # Validation folds
    # ========================================================

    fold_rows = []

    # Primary leave-one-year-out folds
    for test_year in (
        PRIMARY_VALIDATION_YEARS
    ):

        train_years = [
            y
            for y in PRIMARY_VALIDATION_YEARS
            if y != test_year
        ]

        train_rows = model[
            model[
                "year"
            ].isin(
                train_years
            )
        ]

        test_rows = model[
            model[
                "year"
            ]
            == test_year
        ]

        fold_rows.append(
            {
                "validation_protocol_id":
                    VALIDATION_PROTOCOL_ID,

                "fold_id":
                    f"PRIMARY_LOYO_{test_year}",

                "fold_role":
                    "PRIMARY",

                "train_years":
                    ",".join(
                        str(y)
                        for y in train_years
                    ),

                "test_year":
                    test_year,

                "train_rows":
                    len(train_rows),

                "test_rows":
                    len(test_rows),

                "interpretation":
                    (
                        "Primary cross-year generalization fold."
                    ),
            }
        )

    # 2024 sensitivity only
    sensitivity_train = model[
        model[
            "year"
        ].isin(
            PRIMARY_VALIDATION_YEARS
        )
    ]

    sensitivity_test = model[
        model[
            "year"
        ]
        == 2024
    ]

    fold_rows.append(
        {
            "validation_protocol_id":
                VALIDATION_PROTOCOL_ID,

            "fold_id":
                "SENSITIVITY_2024_TINY_HOLDOUT",

            "fold_role":
                "SENSITIVITY_ONLY",

            "train_years":
                ",".join(
                    str(y)
                    for y
                    in PRIMARY_VALIDATION_YEARS
                ),

            "test_year":
                2024,

            "train_rows":
                len(
                    sensitivity_train
                ),

            "test_rows":
                len(
                    sensitivity_test
                ),

            "interpretation":
                (
                    "Tiny supported 2024 subset; "
                    "do not use as primary performance conclusion."
                ),
        }
    )

    validation_folds = pd.DataFrame(
        fold_rows
    )

    # ========================================================
    # Hashes
    # ========================================================

    feature_policy_payload = {
        "feature_set_id":
            FEATURE_SET_ID,

        "features":
            FINAL_FEATURES,

        "excluded_redundant":
            EXCLUDED_REDUNDANT,

        "excluded_leakage":
            EXCLUDED_LEAKAGE,

        "structural_missingness":
            {
                "seconds_since_prior_supported_attempt":
                    (
                        "0 when no prior; "
                        "paired with has_prior_supported_attempt"
                    ),

                "best_prior_supported_average_speed_mph":
                    (
                        "0 when no prior; "
                        "paired with has_prior_supported_attempt"
                    ),
            },
    }

    feature_set_hash = stable_hash(
        feature_policy_payload
    )

    validation_policy_payload = {
        "protocol_id":
            VALIDATION_PROTOCOL_ID,

        "primary_validation_years":
            PRIMARY_VALIDATION_YEARS,

        "sensitivity_holdout_years":
            SENSITIVITY_HOLDOUT_YEARS,

        "random_split_primary":
            False,

        "primary_method":
            "leave-one-year-out",
    }

    validation_protocol_hash = (
        stable_hash(
            validation_policy_payload
        )
    )

    model_matrix[
        "feature_set_hash"
    ] = feature_set_hash

    model_matrix[
        "validation_protocol_hash"
    ] = validation_protocol_hash

    feature_manifest[
        "feature_set_hash"
    ] = feature_set_hash

    validation_folds[
        "validation_protocol_hash"
    ] = validation_protocol_hash

    # ========================================================
    # QA
    # ========================================================

    year_counts = (
        model_matrix[
            "year"
        ]
        .value_counts()
        .sort_index()
    )

    expected_year_counts = {
        2020: 39,
        2021: 49,
        2023: 28,
        2024: 7,
    }

    year_counts_match = True

    for year, expected in (
        expected_year_counts.items()
    ):

        actual = int(
            year_counts.get(
                year,
                0,
            )
        )

        if actual != expected:
            year_counts_match = False

    no_excluded_columns = not any(
        col in model_matrix.columns
        for col in (
            EXCLUDED_REDUNDANT
            + EXCLUDED_LEAKAGE
        )
    )

    wind_encoding_valid = (
        (
            model_matrix[
                "forecast_wind_direction_sin"
            ].between(
                -1.0,
                1.0,
            )
        ).all()
        and
        (
            model_matrix[
                "forecast_wind_direction_cos"
            ].between(
                -1.0,
                1.0,
            )
        ).all()
    )

    checks = {
        "model_rows_equal_123":
            len(
                model_matrix
            ) == 123,

        "attempt_id_unique":
            not model_matrix[
                "attempt_id"
            ].duplicated().any(),

        "final_feature_count_equal_12":
            len(
                FINAL_FEATURES
            ) == 12,

        "all_final_features_complete":
            model_matrix[
                FINAL_FEATURES
            ].notna().all().all(),

        "year_counts_match_expected":
            year_counts_match,

        "no_excluded_redundant_or_leakage_columns":
            no_excluded_columns,

        "wind_direction_encoding_valid":
            wind_encoding_valid,

        "first_attempt_structural_seconds_null_in_source":
            first_seconds_null,

        "first_attempt_structural_best_speed_null_in_source":
            first_best_null,

        "repeat_attempt_seconds_present_in_source":
            repeat_seconds_present,

        "repeat_attempt_best_speed_present_in_source":
            repeat_best_present,

        "primary_fold_count_equal_3":
            (
                validation_folds[
                    "fold_role"
                ]
                == "PRIMARY"
            ).sum()
            == 3,

        "sensitivity_fold_count_equal_1":
            (
                validation_folds[
                    "fold_role"
                ]
                == "SENSITIVITY_ONLY"
            ).sum()
            == 1,
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
                    "model_rows",
                "value":
                    len(
                        model_matrix
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "feature_count",
                "value":
                    len(
                        FINAL_FEATURES
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "feature_set_hash",
                "value":
                    feature_set_hash,
                "status":
                    "INFO",
            },

            {
                "metric":
                    "validation_protocol_hash",
                "value":
                    validation_protocol_hash,
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
    # WRITE
    # ========================================================

    OUTPUT_DIR = (
        MODEL_MATRIX_FILE.parent
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_matrix.to_csv(
        MODEL_MATRIX_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    feature_manifest.to_csv(
        FEATURE_MANIFEST_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_folds.to_csv(
        VALIDATION_FOLDS_FILE,
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
        "# Attempt-Performance V1 Design Freeze"
    )

    report.append("")

    report.append(
        f"Feature set ID: `{FEATURE_SET_ID}`"
    )

    report.append(
        f"Feature set hash: `{feature_set_hash}`"
    )

    report.append("")

    report.append(
        f"Validation protocol ID: `{VALIDATION_PROTOCOL_ID}`"
    )

    report.append(
        f"Validation protocol hash: `{validation_protocol_hash}`"
    )

    report.append("")

    report.append(
        "## Target"
    )

    report.append("")

    report.append(
        f"`{TARGET}`"
    )

    report.append("")

    report.append(
        "## Frozen V1 features"
    )

    report.append("")

    for feature in FINAL_FEATURES:
        report.append(
            f"- `{feature}`"
        )

    report.append("")

    report.append(
        "## Structural missingness policy"
    )

    report.append("")

    report.append(
        "- First supported attempts have no prior-attempt history."
    )

    report.append(
        "- `seconds_since_prior_supported_attempt` is set to 0 "
        "only when `has_prior_supported_attempt = 0`."
    )

    report.append(
        "- `best_prior_supported_average_speed_mph` is set to 0 "
        "only when `has_prior_supported_attempt = 0`."
    )

    report.append(
        "- The explicit indicator prevents those zeros from being "
        "interpreted as ordinary physical values."
    )

    report.append("")

    report.append(
        "## Validation"
    )

    report.append("")

    report.append(
        "- Primary evaluation: leave-one-year-out over "
        "2020, 2021, and 2023."
    )

    report.append(
        "- 2024 is a sensitivity-only tiny holdout because only "
        "seven supported target rows are available."
    )

    report.append(
        "- Random row split is not the primary validation method."
    )

    report.append("")

    report.append(
        "## Excluded from V1"
    )

    report.append("")

    for feature in (
        EXCLUDED_REDUNDANT
        + EXCLUDED_LEAKAGE
    ):
        report.append(
            f"- `{feature}`"
        )

    report.append("")

    report.append(
        "## Readiness"
    )

    report.append("")

    if all_pass:
        report.append(
            "**ATTEMPT_PERFORMANCE_V1_DESIGN_FROZEN**"
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
    # PRINT
    # ========================================================

    print()
    print("FROZEN V1 FEATURES")
    print("-" * 100)

    for feature in FINAL_FEATURES:
        print(
            feature
        )

    print()
    print("MODEL ROWS BY YEAR")
    print("-" * 70)

    print(
        year_counts.to_string()
    )

    print()
    print("VALIDATION FOLDS")
    print("-" * 120)

    print(
        validation_folds.to_string(
            index=False
        )
    )

    print()
    print("FEATURE MANIFEST")
    print("-" * 120)

    print(
        feature_manifest.to_string(
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

    print()
    print("=" * 100)

    if all_pass:
        print(
            "FINAL STATUS: "
            "ATTEMPT_PERFORMANCE_V1_DESIGN_FROZEN"
        )
    else:
        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print("OUTPUTS")

    print(
        MODEL_MATRIX_FILE
    )

    print(
        FEATURE_MANIFEST_FILE
    )

    print(
        VALIDATION_FOLDS_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
