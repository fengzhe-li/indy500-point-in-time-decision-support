from pathlib import Path
import hashlib
import json

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

OUTPUT_FILE = Path(
    "weather/output/attempt_performance_repeat_delta_context_v1.csv"
)

QA_FILE = Path(
    "weather/output/attempt_performance_repeat_delta_context_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/attempt_performance_repeat_delta_context_v1.md"
)


# ============================================================
# FROZEN EXPECTATIONS
# ============================================================

EXPECTED_TOTAL_ROWS = 40

EXPECTED_YEAR_COUNTS = {
    2020: 11,
    2021: 16,
    2023: 12,
    2024: 1,
}

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

SENSITIVITY_YEAR = 2024

DERIVATION_RULE_VERSION = (
    "REPEAT_ATTEMPT_DELTA_CONTEXT_V1"
)


# ============================================================
# WEATHER FEATURES
# ============================================================

WEATHER_FEATURES = [
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_pressure_hpa",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
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


def parse_utc(series):

    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
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


def iso_utc(value):

    if pd.isna(value):
        return None

    return value.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
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
        "PHASE 5B-2A — REPEAT-ATTEMPT "
        "DELTA TARGET CONTEXT MATERIALIZATION"
    )
    print("=" * 100)

    print()
    print(
        "Input rows:",
        len(df)
    )

    # ========================================================
    # Required fields
    # ========================================================

    required = [
        "attempt_id",
        "session_id",
        "car_number",
        "driver_name",
        "performance_time_utc",
        "four_lap_average_speed_mph",
        "best_prior_supported_average_speed_mph",
        "prior_supported_attempt_count",
        "forecast_wind_direction_deg",
    ] + WEATHER_FEATURES

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing required fields: "
            + ", ".join(
                missing
            )
        )

    if df[
        "attempt_id"
    ].duplicated().any():

        raise RuntimeError(
            "Duplicate attempt_id in performance context."
        )

    work = df.copy()

    work[
        "_time"
    ] = parse_utc(
        work[
            "performance_time_utc"
        ]
    )

    if work[
        "_time"
    ].isna().any():

        raise RuntimeError(
            "Unparseable performance_time_utc."
        )

    work[
        "_year"
    ] = infer_year(
        work[
            "session_id"
        ]
    )

    if work[
        "_year"
    ].isna().any():

        raise RuntimeError(
            "Unable to infer year."
        )

    work[
        "_year"
    ] = work[
        "_year"
    ].astype(int)

    work[
        "_speed"
    ] = numeric(
        work[
            "four_lap_average_speed_mph"
        ]
    )

    work[
        "_reported_best_prior_speed"
    ] = numeric(
        work[
            "best_prior_supported_average_speed_mph"
        ]
    )

    work[
        "_prior_count"
    ] = numeric(
        work[
            "prior_supported_attempt_count"
        ]
    )

    for feature in WEATHER_FEATURES:

        work[
            feature
        ] = numeric(
            work[
                feature
            ]
        )

    work[
        "forecast_wind_direction_deg"
    ] = numeric(
        work[
            "forecast_wind_direction_deg"
        ]
    )

    if work[
        WEATHER_FEATURES
        + [
            "forecast_wind_direction_deg"
        ]
    ].isna().any().any():

        raise RuntimeError(
            "Weather field missing in performance context."
        )

    # ========================================================
    # Stable chronology within supported car/session subset
    # ========================================================

    work = (
        work
        .sort_values(
            [
                "session_id",
                "car_number",
                "_time",
                "attempt_id",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    output_rows = []

    # ========================================================
    # Find actual best-prior attempt for every complete
    # repeat target row.
    # ========================================================

    for (
        session_id,
        car_number,
    ), group in work.groupby(
        [
            "session_id",
            "car_number",
        ],
        dropna=False,
        sort=False,
    ):

        group = (
            group
            .sort_values(
                [
                    "_time",
                    "attempt_id",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        for current_position in range(
            len(group)
        ):

            current = group.iloc[
                current_position
            ]

            current_speed = current[
                "_speed"
            ]

            if pd.isna(
                current_speed
            ):
                continue

            if current_position == 0:
                continue

            prior = (
                group
                .iloc[
                    :current_position
                ]
                .copy()
            )

            prior_complete = prior[
                prior[
                    "_speed"
                ].notna()
            ].copy()

            if prior_complete.empty:
                continue

            # ------------------------------------------------
            # Best prior supported complete speed.
            #
            # Tie-break:
            # latest prior performance time.
            # ------------------------------------------------

            best_speed = float(
                prior_complete[
                    "_speed"
                ].max()
            )

            best_candidates = prior_complete[
                np.isclose(
                    prior_complete[
                        "_speed"
                    ].astype(float),
                    best_speed,
                    atol=1e-9,
                    rtol=0.0,
                )
            ].copy()

            baseline = (
                best_candidates
                .sort_values(
                    [
                        "_time",
                        "attempt_id",
                    ]
                )
                .iloc[-1]
            )

            reported_best = current[
                "_reported_best_prior_speed"
            ]

            if pd.isna(
                reported_best
            ):

                raise RuntimeError(
                    "Complete repeat target row has no "
                    "reported best-prior speed: "
                    f"{current['attempt_id']}"
                )

            if not np.isclose(
                float(
                    reported_best
                ),
                best_speed,
                atol=1e-9,
                rtol=0.0,
            ):

                raise RuntimeError(
                    "Reconstructed best-prior speed does not "
                    "match frozen performance-context value.\n"
                    f"attempt_id={current['attempt_id']}\n"
                    f"reported={reported_best}\n"
                    f"reconstructed={best_speed}"
                )

            # ------------------------------------------------
            # Immediately previous supported attempt
            # diagnostic.
            # ------------------------------------------------

            immediate_prior = prior.iloc[
                -1
            ]

            baseline_is_immediate = (
                str(
                    immediate_prior[
                        "attempt_id"
                    ]
                )
                ==
                str(
                    baseline[
                        "attempt_id"
                    ]
                )
            )

            # ------------------------------------------------
            # Time delta
            # ------------------------------------------------

            seconds_since_baseline = (
                current[
                    "_time"
                ]
                - baseline[
                    "_time"
                ]
            ).total_seconds()

            if seconds_since_baseline <= 0:

                raise RuntimeError(
                    "Non-positive baseline time delta."
                )

            # ------------------------------------------------
            # Wind circular representation
            # ------------------------------------------------

            current_dir_rad = np.deg2rad(
                float(
                    current[
                        "forecast_wind_direction_deg"
                    ]
                )
            )

            baseline_dir_rad = np.deg2rad(
                float(
                    baseline[
                        "forecast_wind_direction_deg"
                    ]
                )
            )

            current_dir_sin = float(
                np.sin(
                    current_dir_rad
                )
            )

            current_dir_cos = float(
                np.cos(
                    current_dir_rad
                )
            )

            baseline_dir_sin = float(
                np.sin(
                    baseline_dir_rad
                )
            )

            baseline_dir_cos = float(
                np.cos(
                    baseline_dir_rad
                )
            )

            row = {
                "current_attempt_id":
                    current[
                        "attempt_id"
                    ],

                "baseline_attempt_id":
                    baseline[
                        "attempt_id"
                    ],

                "session_id":
                    session_id,

                "year":
                    int(
                        current[
                            "_year"
                        ]
                    ),

                "car_number":
                    car_number,

                "driver_name":
                    current[
                        "driver_name"
                    ],

                "current_performance_time_utc":
                    iso_utc(
                        current[
                            "_time"
                        ]
                    ),

                "baseline_performance_time_utc":
                    iso_utc(
                        baseline[
                            "_time"
                        ]
                    ),

                "seconds_since_baseline_attempt":
                    float(
                        seconds_since_baseline
                    ),

                "prior_supported_attempt_count":
                    int(
                        current[
                            "_prior_count"
                        ]
                    ),

                "prior_complete_attempt_count":
                    int(
                        len(
                            prior_complete
                        )
                    ),

                "baseline_is_immediately_previous_supported_attempt":
                    bool(
                        baseline_is_immediate
                    ),

                "baseline_speed_mph":
                    float(
                        baseline[
                            "_speed"
                        ]
                    ),

                "current_speed_mph":
                    float(
                        current_speed
                    ),

                "target_speed_delta_vs_best_prior_mph":
                    float(
                        current_speed
                        - baseline[
                            "_speed"
                        ]
                    ),

                "current_forecast_wind_direction_sin":
                    current_dir_sin,

                "current_forecast_wind_direction_cos":
                    current_dir_cos,

                "baseline_forecast_wind_direction_sin":
                    baseline_dir_sin,

                "baseline_forecast_wind_direction_cos":
                    baseline_dir_cos,

                "delta_forecast_wind_direction_sin":
                    (
                        current_dir_sin
                        - baseline_dir_sin
                    ),

                "delta_forecast_wind_direction_cos":
                    (
                        current_dir_cos
                        - baseline_dir_cos
                    ),

                "derivation_rule_version":
                    DERIVATION_RULE_VERSION,
            }

            # ------------------------------------------------
            # Current / baseline / delta weather
            # ------------------------------------------------

            for feature in WEATHER_FEATURES:

                short = feature.replace(
                    "forecast_",
                    ""
                )

                current_value = float(
                    current[
                        feature
                    ]
                )

                baseline_value = float(
                    baseline[
                        feature
                    ]
                )

                row[
                    f"current_{short}"
                ] = current_value

                row[
                    f"baseline_{short}"
                ] = baseline_value

                row[
                    f"delta_{short}"
                ] = (
                    current_value
                    - baseline_value
                )

            # ------------------------------------------------
            # Lineage
            # ------------------------------------------------

            lineage_payload = {
                "current_attempt_id":
                    row[
                        "current_attempt_id"
                    ],

                "baseline_attempt_id":
                    row[
                        "baseline_attempt_id"
                    ],

                "baseline_speed_mph":
                    row[
                        "baseline_speed_mph"
                    ],

                "current_speed_mph":
                    row[
                        "current_speed_mph"
                    ],

                "derivation_rule_version":
                    DERIVATION_RULE_VERSION,
            }

            row[
                "input_lineage_hash"
            ] = stable_hash(
                lineage_payload
            )

            output_rows.append(
                row
            )

    output = pd.DataFrame(
        output_rows
    )

    if output.empty:

        raise RuntimeError(
            "No repeat-attempt delta rows materialized."
        )

    output = (
        output
        .sort_values(
            [
                "year",
                "current_performance_time_utc",
                "car_number",
                "current_attempt_id",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # QA
    # ========================================================

    year_counts = (
        output[
            "year"
        ]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    target = numeric(
        output[
            "target_speed_delta_vs_best_prior_mph"
        ]
    )

    checks = {
        "output_rows_equal_40":
            len(
                output
            )
            == EXPECTED_TOTAL_ROWS,

        "current_attempt_id_unique":
            not output[
                "current_attempt_id"
            ].duplicated().any(),

        "year_counts_match_expected":
            year_counts
            == EXPECTED_YEAR_COUNTS,

        "all_baseline_attempt_ids_present":
            output[
                "baseline_attempt_id"
            ].notna().all(),

        "all_baseline_speeds_present":
            output[
                "baseline_speed_mph"
            ].notna().all(),

        "all_current_speeds_present":
            output[
                "current_speed_mph"
            ].notna().all(),

        "all_delta_targets_present":
            target.notna().all(),

        "all_baseline_time_deltas_positive":
            (
                numeric(
                    output[
                        "seconds_since_baseline_attempt"
                    ]
                )
                > 0
            ).all(),

        "all_lineage_hashes_present":
            output[
                "input_lineage_hash"
            ].notna().all(),

        "primary_rows_equal_39":
            int(
                output[
                    "year"
                ]
                .isin(
                    PRIMARY_YEARS
                )
                .sum()
            )
            == 39,

        "sensitivity_2024_rows_equal_1":
            int(
                (
                    output[
                        "year"
                    ]
                    == SENSITIVITY_YEAR
                )
                .sum()
            )
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
                    "output_rows",

                "value":
                    len(
                        output
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "primary_rows",

                "value":
                    int(
                        output[
                            "year"
                        ]
                        .isin(
                            PRIMARY_YEARS
                        )
                        .sum()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "target_delta_mean_mph",

                "value":
                    float(
                        target.mean()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "target_delta_median_mph",

                "value":
                    float(
                        target.median()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "target_delta_mae_vs_zero_baseline_mph",

                "value":
                    float(
                        target.abs().mean()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "target_delta_rmse_vs_zero_baseline_mph",

                "value":
                    float(
                        np.sqrt(
                            np.mean(
                                target ** 2
                            )
                        )
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "immediately_previous_baseline_rows",

                "value":
                    int(
                        output[
                            "baseline_is_immediately_previous_supported_attempt"
                        ]
                        .astype(bool)
                        .sum()
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
    # PRINT
    # ========================================================

    print()
    print("ROWS BY YEAR")
    print("-" * 70)

    print(
        output[
            "year"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("DELTA TARGET SUMMARY")
    print("-" * 100)

    print(
        target.describe().to_string()
    )

    print()
    print(
        "Zero-delta naive MAE:",
        float(
            target.abs().mean()
        ),
        "mph",
    )

    print(
        "Zero-delta naive RMSE:",
        float(
            np.sqrt(
                np.mean(
                    target ** 2
                )
            )
        ),
        "mph",
    )

    print()
    print("DELTA TARGET BY YEAR")
    print("-" * 120)

    year_summary = (
        output
        .groupby(
            "year"
        )
        .agg(
            rows=(
                "current_attempt_id",
                "size",
            ),
            mean_delta_mph=(
                "target_speed_delta_vs_best_prior_mph",
                "mean",
            ),
            median_delta_mph=(
                "target_speed_delta_vs_best_prior_mph",
                "median",
            ),
            mae_vs_zero_mph=(
                "target_speed_delta_vs_best_prior_mph",
                lambda x: float(
                    np.mean(
                        np.abs(
                            x
                        )
                    )
                ),
            ),
            min_delta_mph=(
                "target_speed_delta_vs_best_prior_mph",
                "min",
            ),
            max_delta_mph=(
                "target_speed_delta_vs_best_prior_mph",
                "max",
            ),
        )
        .reset_index()
    )

    print(
        year_summary.to_string(
            index=False
        )
    )

    print()
    print("SAMPLE REPEAT-ATTEMPT DELTA ROWS")
    print("-" * 160)

    sample_cols = [
        "year",
        "car_number",
        "driver_name",
        "baseline_speed_mph",
        "current_speed_mph",
        "target_speed_delta_vs_best_prior_mph",
        "seconds_since_baseline_attempt",
        "delta_temp_c",
        "delta_relative_humidity_pct",
        "delta_wind_speed_10m_ms",
        "delta_shortwave_radiation_wm2",
        "baseline_is_immediately_previous_supported_attempt",
    ]

    print(
        output[
            sample_cols
        ]
        .head(30)
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
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Repeat-Attempt Delta Context V1"
    )

    report.append("")

    report.append(
        "Target:"
    )

    report.append("")

    report.append(
        "`current_speed_mph - best_prior_supported_speed_mph`"
    )

    report.append("")

    report.append(
        f"Rows: `{len(output)}`"
    )

    report.append(
        f"Primary rows (2020/2021/2023): "
        f"`{int(output['year'].isin(PRIMARY_YEARS).sum())}`"
    )

    report.append(
        f"2024 sensitivity rows: "
        f"`{int((output['year'] == 2024).sum())}`"
    )

    report.append("")

    report.append(
        "## Interpretation"
    )

    report.append("")

    report.append(
        "The baseline attempt is the highest-speed earlier "
        "supported complete attempt for the same car/session."
    )

    report.append(
        "If multiple prior attempts have exactly the same best speed, "
        "the latest such prior attempt is selected deterministically."
    )

    report.append(
        "The target therefore measures gain/loss relative to the "
        "best prior supported performance baseline."
    )

    report.append("")

    report.append(
        "## Weather"
    )

    report.append("")

    report.append(
        "Current, baseline-attempt, and current-minus-baseline "
        "forecast weather values are preserved."
    )

    report.append(
        "Wind direction is represented with sin/cos terms rather "
        "than direct degree subtraction."
    )

    report.append("")

    report.append(
        "## Boundary"
    )

    report.append("")

    report.append(
        "- This is a repeat-attempt performance layer."
    )

    report.append(
        "- It is not a retain/withdraw decision-state layer."
    )

    report.append(
        "- It does not infer queue state or decision time."
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
            "**REPEAT_ATTEMPT_DELTA_CONTEXT_READY**"
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
            "REPEAT_ATTEMPT_DELTA_CONTEXT_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO PREDICTIVE MODEL WAS TRAINED."
    )

    print(
        "NO DECISION-STATE OR QUEUE SEMANTICS WERE ADDED."
    )

    print()
    print("OUTPUTS")

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
