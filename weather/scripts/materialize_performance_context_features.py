from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

PERF_2020_2023_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERF_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

HRRR_ALIGNMENT_FILE = Path(
    "weather/output/performance_grade_hrrr_forecast_alignment.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_FILE = Path(
    "weather/output/performance_context_features.csv"
)

QA_FILE = Path(
    "weather/output/performance_context_features_qa.csv"
)


EXPECTED_ROWS = 136

DERIVATION_RULE_VERSION = (
    "PERFORMANCE_CONTEXT_V1"
)


def read_required(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def iso_utc(value):
    if pd.isna(value):
        return None

    return value.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
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


def build_timing():

    old = read_required(
        PERF_2020_2023_FILE
    )

    new = read_required(
        PERF_2024_FILE
    )

    old = old.copy()
    new = new.copy()

    old[
        "performance_timing_source"
    ] = (
        "PERFORMANCE_GRADE_2020_2021_2023"
    )

    new[
        "performance_timing_source"
    ] = (
        "PERFORMANCE_GRADE_2024_SUPPORTED"
    )

    timing = pd.concat(
        [old, new],
        ignore_index=True,
        sort=False,
    )

    if len(timing) != EXPECTED_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_ROWS} timing rows, "
            f"got {len(timing)}"
        )

    if timing[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in timing."
        )

    timing[
        "_performance_time"
    ] = parse_utc(
        timing[
            "mapped_capture_time_utc"
        ]
    )

    if timing[
        "_performance_time"
    ].isna().any():
        raise RuntimeError(
            "Unparseable performance timestamp."
        )

    return timing


def main():

    attempts = read_required(
        ATTEMPTS_FILE
    )

    timing = build_timing()

    forecast = read_required(
        HRRR_ALIGNMENT_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5A-1 — PERFORMANCE CONTEXT "
        "FEATURE MATERIALIZATION"
    )
    print("=" * 100)

    print()
    print(
        "Timing rows:",
        len(timing)
    )

    print(
        "Forecast rows:",
        len(forecast)
    )

    if len(forecast) != EXPECTED_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_ROWS} HRRR alignment rows, "
            f"got {len(forecast)}"
        )

    if forecast[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in forecast alignment."
        )

    # ========================================================
    # Attempt attributes
    # ========================================================

    attempt_columns = [
        c
        for c in [
            "attempt_id",
            "session_id",
            "entry_key",
            "attempt_key",
            "car_number",
            "driver_name",
            "car_attempt_index",
            "car_attempt_order_quality",
            "attempt_class",
            "result_status",
            "result_counted_at_session_end",
            "four_lap_total_seconds",
            "four_lap_average_speed_mph",
            "fuel_strategy_class",
        ]
        if c in attempts.columns
    ]

    base = timing.merge(
        attempts[
            attempt_columns
        ],
        on="attempt_id",
        how="left",
        suffixes=(
            "_timing",
            "_attempt",
        ),
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # Resolve duplicated identity columns
    # --------------------------------------------------------

    def choose_column(
        df,
        candidates,
    ):
        for col in candidates:
            if col in df.columns:
                return df[col]

        return pd.Series(
            [pd.NA] * len(df),
            index=df.index,
        )

    base[
        "_session_id"
    ] = choose_column(
        base,
        [
            "session_id_timing",
            "session_id",
            "session_id_attempt",
        ],
    )

    base[
        "_entry_key"
    ] = choose_column(
        base,
        [
            "entry_key_timing",
            "entry_key",
            "entry_key_attempt",
        ],
    )

    base[
        "_attempt_key"
    ] = choose_column(
        base,
        [
            "attempt_key_timing",
            "attempt_key",
            "attempt_key_attempt",
        ],
    )

    base[
        "_car_number"
    ] = choose_column(
        base,
        [
            "car_number_timing",
            "car_number",
            "car_number_attempt",
        ],
    )

    base[
        "_driver_name"
    ] = choose_column(
        base,
        [
            "driver_name_timing",
            "driver_name",
            "driver_name_attempt",
        ],
    )

    base[
        "_car_attempt_index"
    ] = choose_column(
        base,
        [
            "car_attempt_index_timing",
            "car_attempt_index",
            "car_attempt_index_attempt",
        ],
    )

    if base[
        "_session_id"
    ].isna().any():
        raise RuntimeError(
            "Missing session identity after attempt join."
        )

    # ========================================================
    # Forecast join
    # ========================================================

    forecast_identity_exclude = {
        "session_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "performance_time_utc",
        "performance_timing_source",
        "timing_class",
        "timing_basis",
        "performance_alignment_usable",
        "decision_state_usable",
        "chronology_usable",
    }

    forecast_keep = [
        "attempt_id"
    ] + [
        c
        for c in forecast.columns
        if (
            c != "attempt_id"
            and c not in forecast_identity_exclude
        )
    ]

    merged = base.merge(
        forecast[
            forecast_keep
        ],
        on="attempt_id",
        how="left",
        validate="one_to_one",
    )

    forecast_match_indicator = (
        merged[
            "selected_issue_time_utc"
        ].notna()
        if "selected_issue_time_utc" in merged.columns
        else pd.Series(
            [False] * len(merged),
            index=merged.index,
        )
    )

    if not forecast_match_indicator.all():
        raise RuntimeError(
            "At least one timing row lacks "
            "HRRR forecast alignment."
        )

    # ========================================================
    # Same-car supported history
    # ========================================================

    merged[
        "_performance_time"
    ] = parse_utc(
        merged[
            "mapped_capture_time_utc"
        ]
    )

    merged = merged.sort_values(
        [
            "_session_id",
            "_car_number",
            "_performance_time",
            "attempt_id",
        ]
    ).reset_index(
        drop=True
    )

    group_cols = [
        "_session_id",
        "_car_number",
    ]

    merged[
        "prior_supported_attempt_count"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
        )
        .cumcount()
    )

    merged[
        "_prior_supported_time"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
        )[
            "_performance_time"
        ]
        .shift(1)
    )

    merged[
        "seconds_since_prior_supported_attempt"
    ] = (
        merged[
            "_performance_time"
        ]
        - merged[
            "_prior_supported_time"
        ]
    ).dt.total_seconds()

    # --------------------------------------------------------
    # Previous supported attempt performance
    # --------------------------------------------------------

    speed_numeric = pd.to_numeric(
        choose_column(
            merged,
            [
                "four_lap_average_speed_mph",
            ],
        ),
        errors="coerce",
    )

    total_numeric = pd.to_numeric(
        choose_column(
            merged,
            [
                "four_lap_total_seconds",
            ],
        ),
        errors="coerce",
    )

    merged[
        "_current_speed"
    ] = speed_numeric

    merged[
        "_current_total"
    ] = total_numeric

    merged[
        "prior_supported_attempt_average_speed_mph"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
        )[
            "_current_speed"
        ]
        .shift(1)
    )

    merged[
        "prior_supported_attempt_total_seconds"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
        )[
            "_current_total"
        ]
        .shift(1)
    )

    # --------------------------------------------------------
    # Best prior supported complete performance
    #
    # shift before expanding = current attempt cannot leak
    # into its own prior-state features.
    # --------------------------------------------------------

    def prior_expanding_max(series):
        return (
            series
            .shift(1)
            .expanding()
            .max()
        )

    def prior_expanding_min(series):
        return (
            series
            .shift(1)
            .expanding()
            .min()
        )

    merged[
        "best_prior_supported_average_speed_mph"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
            group_keys=False,
        )[
            "_current_speed"
        ]
        .apply(
            prior_expanding_max
        )
    )

    merged[
        "best_prior_supported_total_seconds"
    ] = (
        merged
        .groupby(
            group_cols,
            dropna=False,
            group_keys=False,
        )[
            "_current_total"
        ]
        .apply(
            prior_expanding_min
        )
    )

    merged[
        "speed_change_vs_prior_supported_attempt_mph"
    ] = (
        merged[
            "_current_speed"
        ]
        - merged[
            "prior_supported_attempt_average_speed_mph"
        ]
    )

    merged[
        "speed_change_vs_best_prior_supported_mph"
    ] = (
        merged[
            "_current_speed"
        ]
        - merged[
            "best_prior_supported_average_speed_mph"
        ]
    )

    # ========================================================
    # Materialize output
    # ========================================================

    output = pd.DataFrame(
        {
            "attempt_id":
                merged[
                    "attempt_id"
                ],

            "session_id":
                merged[
                    "_session_id"
                ],

            "entry_key":
                merged[
                    "_entry_key"
                ],

            "attempt_key":
                merged[
                    "_attempt_key"
                ],

            "car_number":
                merged[
                    "_car_number"
                ],

            "driver_name":
                merged[
                    "_driver_name"
                ],

            "car_attempt_index":
                merged[
                    "_car_attempt_index"
                ],

            "performance_time_utc":
                merged[
                    "_performance_time"
                ].dt.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "performance_time_semantic":
                (
                    "APPROXIMATE_RECORDER_CAPTURE_"
                    "PERFORMANCE_ALIGNMENT"
                ),

            "performance_timing_source":
                merged[
                    "performance_timing_source"
                ],

            "timing_class":
                merged[
                    "timing_class"
                ],

            "timing_basis":
                merged[
                    "timing_basis"
                ],

            "attempt_class":
                choose_column(
                    merged,
                    [
                        "attempt_class",
                    ],
                ),

            "result_status":
                choose_column(
                    merged,
                    [
                        "result_status",
                    ],
                ),

            "result_counted_at_session_end":
                choose_column(
                    merged,
                    [
                        "result_counted_at_session_end",
                    ],
                ),

            "four_lap_total_seconds":
                merged[
                    "_current_total"
                ],

            "four_lap_average_speed_mph":
                merged[
                    "_current_speed"
                ],

            "prior_supported_attempt_count":
                merged[
                    "prior_supported_attempt_count"
                ],

            "most_recent_supported_attempt_time_utc":
                merged[
                    "_prior_supported_time"
                ].dt.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "seconds_since_prior_supported_attempt":
                merged[
                    "seconds_since_prior_supported_attempt"
                ],

            "prior_supported_attempt_average_speed_mph":
                merged[
                    "prior_supported_attempt_average_speed_mph"
                ],

            "prior_supported_attempt_total_seconds":
                merged[
                    "prior_supported_attempt_total_seconds"
                ],

            "best_prior_supported_average_speed_mph":
                merged[
                    "best_prior_supported_average_speed_mph"
                ],

            "best_prior_supported_total_seconds":
                merged[
                    "best_prior_supported_total_seconds"
                ],

            "speed_change_vs_prior_supported_attempt_mph":
                merged[
                    "speed_change_vs_prior_supported_attempt_mph"
                ],

            "speed_change_vs_best_prior_supported_mph":
                merged[
                    "speed_change_vs_best_prior_supported_mph"
                ],

            "performance_alignment_usable":
                True,

            "decision_state_usable":
                False,

            "leaderboard_state_complete":
                False,

            "queue_state_available":
                False,

            "derivation_rule_version":
                DERIVATION_RULE_VERSION,
        }
    )

    # --------------------------------------------------------
    # Append HRRR forecast columns
    # --------------------------------------------------------

    hrrr_columns = [
        c
        for c in merged.columns
        if (
            c.startswith(
                "forecast_"
            )
            or c in {
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
                "availability_policy_id",
                "availability_policy_hash",
                "leakage_safe",
            }
        )
    ]

    for col in hrrr_columns:

        if col in output.columns:
            continue

        output[
            col
        ] = merged[
            col
        ]

    # --------------------------------------------------------
    # Row-level lineage hash
    # --------------------------------------------------------

    lineage_hashes = []

    for _, row in output.iterrows():

        payload = {
            "attempt_id":
                row[
                    "attempt_id"
                ],

            "performance_time_utc":
                row[
                    "performance_time_utc"
                ],

            "performance_timing_source":
                row[
                    "performance_timing_source"
                ],

            "availability_policy_hash":
                row.get(
                    "availability_policy_hash",
                    None,
                ),

            "before_forecast_snapshot_id":
                row.get(
                    "before_forecast_snapshot_id",
                    None,
                ),

            "after_forecast_snapshot_id":
                row.get(
                    "after_forecast_snapshot_id",
                    None,
                ),

            "derivation_rule_version":
                DERIVATION_RULE_VERSION,
        }

        lineage_hashes.append(
            stable_hash(
                payload
            )
        )

    output[
        "input_lineage_hash"
    ] = lineage_hashes

    # ========================================================
    # QA
    # ========================================================

    output = output.sort_values(
        [
            "session_id",
            "performance_time_utc",
            "car_number",
            "attempt_id",
        ]
    ).reset_index(
        drop=True
    )

    checks = {}

    checks[
        "output_rows_equal_136"
    ] = (
        len(output)
        == EXPECTED_ROWS
    )

    checks[
        "attempt_id_unique"
    ] = (
        not output[
            "attempt_id"
        ].duplicated().any()
    )

    checks[
        "all_performance_times_present"
    ] = (
        output[
            "performance_time_utc"
        ].notna().all()
    )

    checks[
        "all_forecast_alignment_present"
    ] = (
        output[
            "selected_issue_time_utc"
        ].notna().all()
    )

    checks[
        "all_leakage_safe"
    ] = (
        output[
            "leakage_safe"
        ].astype(bool).all()
    )

    checks[
        "decision_state_usable_false"
    ] = (
        (
            output[
                "decision_state_usable"
            ]
            == False
        ).all()
    )

    checks[
        "leaderboard_state_complete_false"
    ] = (
        (
            output[
                "leaderboard_state_complete"
            ]
            == False
        ).all()
    )

    checks[
        "queue_state_available_false"
    ] = (
        (
            output[
                "queue_state_available"
            ]
            == False
        ).all()
    )

    # First row of every supported car/session must have
    # prior count = 0 and no prior time.
    first_rows = (
        output
        .sort_values(
            [
                "session_id",
                "car_number",
                "performance_time_utc",
            ]
        )
        .groupby(
            [
                "session_id",
                "car_number",
            ],
            dropna=False,
        )
        .head(1)
    )

    checks[
        "first_supported_attempt_prior_count_zero"
    ] = (
        (
            first_rows[
                "prior_supported_attempt_count"
            ]
            == 0
        ).all()
    )

    checks[
        "first_supported_attempt_prior_time_null"
    ] = (
        first_rows[
            "most_recent_supported_attempt_time_utc"
        ].isna().all()
    )

    # Prior-time deltas must be positive.
    deltas = pd.to_numeric(
        output[
            "seconds_since_prior_supported_attempt"
        ],
        errors="coerce",
    ).dropna()

    checks[
        "prior_supported_time_deltas_positive"
    ] = (
        (
            deltas
            > 0
        ).all()
    )

    qa_rows = []

    for name, passed in checks.items():

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
                    "output_rows",
                "value":
                    len(output),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "rows_with_complete_four_lap_speed",
                "value":
                    int(
                        output[
                            "four_lap_average_speed_mph"
                        ]
                        .notna()
                        .sum()
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "rows_with_prior_supported_attempt",
                "value":
                    int(
                        (
                            output[
                                "prior_supported_attempt_count"
                            ]
                            > 0
                        ).sum()
                    ),
                "status":
                    "INFO",
            },

            {
                "metric":
                    "car_session_groups",
                "value":
                    int(
                        output[
                            [
                                "session_id",
                                "car_number",
                            ]
                        ]
                        .drop_duplicates()
                        .shape[0]
                    ),
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

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("ROWS BY SESSION")
    print("-" * 70)

    print(
        output[
            "session_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SUPPORTED SAME-CAR HISTORY")
    print("-" * 70)

    print(
        "Rows with prior supported attempt:",
        int(
            (
                output[
                    "prior_supported_attempt_count"
                ]
                > 0
            ).sum()
        ),
    )

    print(
        "Rows with complete four-lap speed:",
        int(
            output[
                "four_lap_average_speed_mph"
            ]
            .notna()
            .sum()
        ),
    )

    print()
    print("PRIOR ATTEMPT COUNT DISTRIBUTION")
    print("-" * 70)

    print(
        output[
            "prior_supported_attempt_count"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SAMPLE FEATURES")
    print("-" * 120)

    sample_columns = [
        "session_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "performance_time_utc",
        "four_lap_average_speed_mph",
        "prior_supported_attempt_count",
        "most_recent_supported_attempt_time_utc",
        "seconds_since_prior_supported_attempt",
        "prior_supported_attempt_average_speed_mph",
        "best_prior_supported_average_speed_mph",
        "forecast_temp_c",
        "forecast_wind_speed_10m_ms",
        "forecast_shortwave_radiation_wm2",
    ]

    sample_columns = [
        c
        for c in sample_columns
        if c in output.columns
    ]

    print(
        output[
            sample_columns
        ]
        .head(30)
        .to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 100)

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
            "PERFORMANCE_CONTEXT_FEATURES_READY"
        )
    else:
        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "decision_state_usable = False"
    )

    print(
        "No provisional leaderboard, cutoff, "
        "queue, or retain/withdraw decision "
        "semantics were materialized."
    )

    print()
    print("OUTPUTS")

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )


if __name__ == "__main__":
    main()
