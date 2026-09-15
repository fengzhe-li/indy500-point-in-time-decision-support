from pathlib import Path
import math
import pandas as pd
import numpy as np


# ============================================================
# INPUTS
# ============================================================

SNAPSHOTS_FILE = Path(
    "data/canonical/v1/forecast_snapshots.csv"
)

WEATHER_VALUES_FILE = Path(
    "data/canonical/v1/weather_forecasts.csv"
)

POLICY_FILE = Path(
    "weather/output/hrrr_forecast_availability_policy.csv"
)

PERF_2020_2023_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERF_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_FILE = Path(
    "weather/output/"
    "performance_grade_hrrr_forecast_alignment.csv"
)

QA_FILE = Path(
    "weather/output/"
    "performance_grade_hrrr_forecast_alignment_qa.csv"
)


# ============================================================
# FROZEN POLICY
# ============================================================

PRIMARY_LAG_MINUTES = 90

EXPECTED_ROWS = 136

EXPECTED_SNAPSHOTS = 259

CIRCULAR_VARIABLES = {
    "wind_direction_deg",
}


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


def normalize_variable_code(value):
    return str(value).strip()


def linear_interpolate(
    value_before,
    value_after,
    weight,
):
    if (
        pd.isna(value_before)
        or pd.isna(value_after)
    ):
        return np.nan

    return (
        float(value_before)
        + weight
        * (
            float(value_after)
            - float(value_before)
        )
    )


def circular_interpolate_degrees(
    value_before,
    value_after,
    weight,
):
    if (
        pd.isna(value_before)
        or pd.isna(value_after)
    ):
        return np.nan

    a = float(value_before) % 360.0
    b = float(value_after) % 360.0

    delta = (
        (b - a + 180.0)
        % 360.0
    ) - 180.0

    result = (
        a
        + weight * delta
    ) % 360.0

    return result


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
        [
            old,
            new,
        ],
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
            "Duplicate attempt_id in performance timing."
        )

    timing[
        "_target_time"
    ] = parse_utc(
        timing[
            "mapped_capture_time_utc"
        ]
    )

    if timing[
        "_target_time"
    ].isna().any():
        raise RuntimeError(
            "Unparseable mapped_capture_time_utc."
        )

    return timing


def build_snapshot_table():
    snapshots = read_required(
        SNAPSHOTS_FILE
    )

    policy = read_required(
        POLICY_FILE
    )

    if len(snapshots) != EXPECTED_SNAPSHOTS:
        raise RuntimeError(
            f"Expected {EXPECTED_SNAPSHOTS} snapshots, "
            f"got {len(snapshots)}"
        )

    if len(policy) != EXPECTED_SNAPSHOTS:
        raise RuntimeError(
            f"Expected {EXPECTED_SNAPSHOTS} policy rows, "
            f"got {len(policy)}"
        )

    required_policy = [
        "forecast_snapshot_id",
        "availability_policy_id",
        "availability_policy_hash",
        "availability_lag_minutes",
        "policy_availability_time_utc",
    ]

    missing = [
        c
        for c in required_policy
        if c not in policy.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing policy columns: "
            + ", ".join(missing)
        )

    primary_policy = policy[
        pd.to_numeric(
            policy[
                "availability_lag_minutes"
            ],
            errors="coerce",
        )
        == PRIMARY_LAG_MINUTES
    ].copy()

    if len(primary_policy) != EXPECTED_SNAPSHOTS:
        raise RuntimeError(
            "Primary 90-minute policy does not "
            "contain exactly 259 rows."
        )

    snapshot = snapshots.merge(
        primary_policy[
            required_policy
        ],
        on="forecast_snapshot_id",
        how="left",
        validate="one_to_one",
    )

    snapshot[
        "_issue_time"
    ] = parse_utc(
        snapshot[
            "issue_time_utc"
        ]
    )

    snapshot[
        "_valid_time"
    ] = parse_utc(
        snapshot[
            "valid_start_utc"
        ]
    )

    snapshot[
        "_available_time"
    ] = parse_utc(
        snapshot[
            "policy_availability_time_utc"
        ]
    )

    for col in [
        "_issue_time",
        "_valid_time",
        "_available_time",
    ]:
        if snapshot[
            col
        ].isna().any():
            raise RuntimeError(
                f"Unparseable timestamp in {col}."
            )

    return snapshot


def build_weather_lookup(
    snapshots,
):
    values = read_required(
        WEATHER_VALUES_FILE
    )

    required = [
        "forecast_snapshot_id",
        "variable_code",
        "value_numeric",
        "unit",
    ]

    missing = [
        c
        for c in required
        if c not in values.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing weather value columns: "
            + ", ".join(missing)
        )

    values = values.copy()

    values[
        "variable_code"
    ] = values[
        "variable_code"
    ].apply(
        normalize_variable_code
    )

    values[
        "value_numeric"
    ] = pd.to_numeric(
        values[
            "value_numeric"
        ],
        errors="coerce",
    )

    # No duplicate variable within one forecast snapshot.
    duplicate_key = values.duplicated(
        subset=[
            "forecast_snapshot_id",
            "variable_code",
        ],
        keep=False,
    )

    if duplicate_key.any():
        bad = values[
            duplicate_key
        ]

        raise RuntimeError(
            "Duplicate variable_code within "
            "forecast_snapshot_id.\n"
            + bad.head(
                20
            ).to_string(
                index=False
            )
        )

    known_snapshot_ids = set(
        snapshots[
            "forecast_snapshot_id"
        ].astype(str)
    )

    unknown_ids = (
        set(
            values[
                "forecast_snapshot_id"
            ].astype(str)
        )
        - known_snapshot_ids
    )

    if unknown_ids:
        raise RuntimeError(
            "weather_forecasts contains snapshot IDs "
            "not present in forecast_snapshots."
        )

    lookup = {}

    unit_lookup = {}

    for _, row in values.iterrows():
        sid = str(
            row[
                "forecast_snapshot_id"
            ]
        )

        var = row[
            "variable_code"
        ]

        lookup[
            (
                sid,
                var,
            )
        ] = row[
            "value_numeric"
        ]

        unit_lookup.setdefault(
            var,
            set(),
        ).add(
            str(
                row[
                    "unit"
                ]
            )
        )

    variable_codes = sorted(
        values[
            "variable_code"
        ].unique()
    )

    return (
        lookup,
        unit_lookup,
        variable_codes,
    )


def select_bracket(
    snapshots,
    session_id,
    target_time,
):
    session = snapshots[
        snapshots[
            "session_id"
        ].astype(str)
        == str(session_id)
    ].copy()

    eligible = session[
        session[
            "_available_time"
        ]
        <= target_time
    ].copy()

    if eligible.empty:
        raise RuntimeError(
            f"No eligible forecast for "
            f"{session_id} at {target_time}"
        )

    latest_issue = eligible[
        "_issue_time"
    ].max()

    cycle = eligible[
        eligible[
            "_issue_time"
        ]
        == latest_issue
    ].copy()

    before = cycle[
        cycle[
            "_valid_time"
        ]
        <= target_time
    ].copy()

    after = cycle[
        cycle[
            "_valid_time"
        ]
        >= target_time
    ].copy()

    if (
        before.empty
        or after.empty
    ):
        raise RuntimeError(
            "No same-cycle bracketing forecast "
            f"for {session_id} at {target_time}. "
            f"Latest eligible issue={latest_issue}"
        )

    before_row = (
        before
        .sort_values(
            "_valid_time"
        )
        .iloc[-1]
    )

    after_row = (
        after
        .sort_values(
            "_valid_time"
        )
        .iloc[0]
    )

    if (
        before_row[
            "_issue_time"
        ]
        != after_row[
            "_issue_time"
        ]
    ):
        raise RuntimeError(
            "Bracket crosses issue cycles."
        )

    if (
        before_row[
            "_available_time"
        ]
        > target_time
        or after_row[
            "_available_time"
        ]
        > target_time
    ):
        raise RuntimeError(
            "Leakage invariant failed: bracket "
            "contains unavailable forecast."
        )

    t0 = before_row[
        "_valid_time"
    ]

    t1 = after_row[
        "_valid_time"
    ]

    if t1 < t0:
        raise RuntimeError(
            "Invalid valid-time bracket."
        )

    if t0 == t1:
        weight = 0.0
    else:
        weight = (
            (
                target_time - t0
            ).total_seconds()
            /
            (
                t1 - t0
            ).total_seconds()
        )

    if (
        weight < -1e-9
        or weight > 1.0 + 1e-9
    ):
        raise RuntimeError(
            f"Interpolation weight outside [0,1]: "
            f"{weight}"
        )

    weight = min(
        1.0,
        max(
            0.0,
            float(
                weight
            ),
        ),
    )

    return (
        before_row,
        after_row,
        weight,
    )


def main():

    timing = build_timing()

    snapshots = build_snapshot_table()

    (
        weather_lookup,
        unit_lookup,
        variable_codes,
    ) = build_weather_lookup(
        snapshots
    )

    print()
    print("=" * 100)
    print(
        "PHASE 4C-3 — PERFORMANCE-GRADE "
        "HRRR FORECAST ALIGNMENT"
    )
    print("=" * 100)

    print()
    print(
        "Performance timing rows:",
        len(timing)
    )

    print(
        "Forecast snapshots:",
        len(snapshots)
    )

    print(
        "Weather variables:",
        len(variable_codes)
    )

    print()
    print("VARIABLE CODES")
    print("-" * 70)

    for var in variable_codes:
        print(
            f"{var}: "
            f"units={sorted(unit_lookup[var])}"
        )

    rows = []

    bracket_pair_counts = {}

    for _, timing_row in (
        timing.iterrows()
    ):

        target = timing_row[
            "_target_time"
        ]

        (
            before,
            after,
            weight,
        ) = select_bracket(
            snapshots,
            timing_row[
                "session_id"
            ],
            target,
        )

        before_sid = str(
            before[
                "forecast_snapshot_id"
            ]
        )

        after_sid = str(
            after[
                "forecast_snapshot_id"
            ]
        )

        lead_before = float(
            before[
                "forecast_lead_hours"
            ]
        )

        lead_after = float(
            after[
                "forecast_lead_hours"
            ]
        )

        pair_key = (
            lead_before,
            lead_after,
        )

        bracket_pair_counts[
            pair_key
        ] = (
            bracket_pair_counts.get(
                pair_key,
                0,
            )
            + 1
        )

        out = {
            "attempt_id":
                timing_row[
                    "attempt_id"
                ],

            "session_id":
                timing_row[
                    "session_id"
                ],

            "car_number":
                timing_row.get(
                    "car_number",
                    np.nan,
                ),

            "driver_name":
                timing_row.get(
                    "driver_name",
                    np.nan,
                ),

            "car_attempt_index":
                timing_row.get(
                    "car_attempt_index",
                    np.nan,
                ),

            "performance_time_utc":
                iso_utc(
                    target
                ),

            "performance_timing_source":
                timing_row[
                    "performance_timing_source"
                ],

            "timing_class":
                timing_row.get(
                    "timing_class",
                    None,
                ),

            "timing_basis":
                timing_row.get(
                    "timing_basis",
                    None,
                ),

            "forecast_selection_class":
                (
                    "LATEST_AVAILABLE_ISSUE_"
                    "SAME_CYCLE_VALID_TIME_INTERPOLATION"
                ),

            "availability_lag_minutes":
                PRIMARY_LAG_MINUTES,

            "availability_policy_id":
                before[
                    "availability_policy_id"
                ],

            "availability_policy_hash":
                before[
                    "availability_policy_hash"
                ],

            "selected_issue_time_utc":
                iso_utc(
                    before[
                        "_issue_time"
                    ]
                ),

            "selected_issue_age_minutes":
                (
                    target
                    - before[
                        "_issue_time"
                    ]
                ).total_seconds()
                / 60.0,

            "before_forecast_snapshot_id":
                before_sid,

            "after_forecast_snapshot_id":
                after_sid,

            "before_valid_time_utc":
                iso_utc(
                    before[
                        "_valid_time"
                    ]
                ),

            "after_valid_time_utc":
                iso_utc(
                    after[
                        "_valid_time"
                    ]
                ),

            "before_forecast_lead_hours":
                lead_before,

            "after_forecast_lead_hours":
                lead_after,

            "before_valid_offset_minutes":
                (
                    before[
                        "_valid_time"
                    ]
                    - target
                ).total_seconds()
                / 60.0,

            "after_valid_offset_minutes":
                (
                    after[
                        "_valid_time"
                    ]
                    - target
                ).total_seconds()
                / 60.0,

            "interpolation_weight_after":
                weight,

            "forecast_available_before_target":
                (
                    before[
                        "_available_time"
                    ]
                    <= target
                ),

            "forecast_available_after_target":
                (
                    after[
                        "_available_time"
                    ]
                    <= target
                ),

            "leakage_safe":
                True,

            "performance_alignment_usable":
                True,

            "decision_state_usable":
                False,

            "chronology_usable":
                False,

            "semantic_note":
                (
                    "HRRR forecast interpolated at an "
                    "approximate performance timestamp. "
                    "Not a retain/withdraw decision-state "
                    "timestamp. Both bracketing forecasts "
                    "come from the latest policy-available "
                    "issue cycle."
                ),
        }

        for var in variable_codes:

            vb = weather_lookup.get(
                (
                    before_sid,
                    var,
                ),
                np.nan,
            )

            va = weather_lookup.get(
                (
                    after_sid,
                    var,
                ),
                np.nan,
            )

            if var in CIRCULAR_VARIABLES:
                aligned = (
                    circular_interpolate_degrees(
                        vb,
                        va,
                        weight,
                    )
                )

                method = (
                    "CIRCULAR_SHORTEST_ARC"
                )

            else:
                aligned = linear_interpolate(
                    vb,
                    va,
                    weight,
                )

                method = (
                    "LINEAR"
                )

            out[
                f"forecast_{var}"
            ] = aligned

            out[
                f"forecast_{var}_before"
            ] = vb

            out[
                f"forecast_{var}_after"
            ] = va

            out[
                f"forecast_{var}_interpolation_method"
            ] = method

        rows.append(
            out
        )

    result = pd.DataFrame(
        rows
    )

    # ========================================================
    # QA
    # ========================================================

    if len(result) != EXPECTED_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_ROWS} rows, "
            f"got {len(result)}"
        )

    if result[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in result."
        )

    same_issue_invariant = (
        result[
            "selected_issue_time_utc"
        ].notna()
    ).all()

    leakage_invariant = (
        result[
            "forecast_available_before_target"
        ].astype(bool)
        &
        result[
            "forecast_available_after_target"
        ].astype(bool)
    ).all()

    weights = pd.to_numeric(
        result[
            "interpolation_weight_after"
        ],
        errors="coerce",
    )

    weight_invariant = (
        weights.notna().all()
        and (
            (
                weights >= 0.0
            )
            &
            (
                weights <= 1.0
            )
        ).all()
    )

    bracket_invariant = (
        (
            pd.to_numeric(
                result[
                    "before_valid_offset_minutes"
                ],
                errors="coerce",
            )
            <= 1e-9
        )
        &
        (
            pd.to_numeric(
                result[
                    "after_valid_offset_minutes"
                ],
                errors="coerce",
            )
            >= -1e-9
        )
    ).all()

    variable_aligned_counts = {}

    for var in variable_codes:
        col = (
            f"forecast_{var}"
        )

        variable_aligned_counts[
            var
        ] = int(
            result[
                col
            ].notna().sum()
        )

    qa_rows = [
        {
            "metric":
                "input_performance_rows",
            "value":
                len(timing),
            "status":
                (
                    "PASS"
                    if len(timing)
                    == EXPECTED_ROWS
                    else "FAIL"
                ),
        },

        {
            "metric":
                "output_alignment_rows",
            "value":
                len(result),
            "status":
                (
                    "PASS"
                    if len(result)
                    == EXPECTED_ROWS
                    else "FAIL"
                ),
        },

        {
            "metric":
                "same_issue_cycle_rows",
            "value":
                int(
                    same_issue_invariant
                    * len(result)
                ),
            "status":
                (
                    "PASS"
                    if same_issue_invariant
                    else "FAIL"
                ),
        },

        {
            "metric":
                "leakage_safe_rows",
            "value":
                int(
                    (
                        result[
                            "forecast_available_before_target"
                        ].astype(bool)
                        &
                        result[
                            "forecast_available_after_target"
                        ].astype(bool)
                    ).sum()
                ),
            "status":
                (
                    "PASS"
                    if leakage_invariant
                    else "FAIL"
                ),
        },

        {
            "metric":
                "valid_bracket_rows",
            "value":
                int(
                    (
                        (
                            pd.to_numeric(
                                result[
                                    "before_valid_offset_minutes"
                                ],
                                errors="coerce",
                            )
                            <= 1e-9
                        )
                        &
                        (
                            pd.to_numeric(
                                result[
                                    "after_valid_offset_minutes"
                                ],
                                errors="coerce",
                            )
                            >= -1e-9
                        )
                    ).sum()
                ),
            "status":
                (
                    "PASS"
                    if bracket_invariant
                    else "FAIL"
                ),
        },

        {
            "metric":
                "interpolation_weight_valid_rows",
            "value":
                int(
                    (
                        weights.notna()
                        &
                        (
                            weights >= 0.0
                        )
                        &
                        (
                            weights <= 1.0
                        )
                    ).sum()
                ),
            "status":
                (
                    "PASS"
                    if weight_invariant
                    else "FAIL"
                ),
        },
    ]

    for var in variable_codes:
        qa_rows.append(
            {
                "metric":
                    f"aligned_{var}_rows",
                "value":
                    variable_aligned_counts[
                        var
                    ],
                "status":
                    (
                        "PASS"
                        if variable_aligned_counts[
                            var
                        ]
                        == EXPECTED_ROWS
                        else "REVIEW"
                    ),
            }
        )

    qa = pd.DataFrame(
        qa_rows
    )

    all_core_pass = (
        same_issue_invariant
        and leakage_invariant
        and weight_invariant
        and bracket_invariant
        and len(result)
        == EXPECTED_ROWS
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("BRACKET LEAD PAIRS")
    print("-" * 70)

    for pair in sorted(
        bracket_pair_counts
    ):
        print(
            f"f{int(pair[0]):02d} -> "
            f"f{int(pair[1]):02d}: "
            f"{bracket_pair_counts[pair]}"
        )

    print()
    print("ROWS BY SESSION")
    print("-" * 70)

    print(
        result[
            "session_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SELECTED ISSUE AGE SUMMARY (MIN)")
    print("-" * 70)

    print(
        pd.to_numeric(
            result[
                "selected_issue_age_minutes"
            ],
            errors="coerce",
        )
        .describe()
        .to_string()
    )

    print()
    print("INTERPOLATION WEIGHT SUMMARY")
    print("-" * 70)

    print(
        weights
        .describe()
        .to_string()
    )

    print()
    print("VARIABLE ALIGNMENT COVERAGE")
    print("-" * 100)

    for var in variable_codes:
        print(
            f"{var}: "
            f"{variable_aligned_counts[var]}/"
            f"{EXPECTED_ROWS}"
        )

    print()
    print("SAMPLE ALIGNED ROWS")
    print("-" * 120)

    sample_columns = [
        "session_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "performance_time_utc",
        "selected_issue_time_utc",
        "before_forecast_lead_hours",
        "after_forecast_lead_hours",
        "interpolation_weight_after",
    ]

    for preferred in [
        "forecast_temp_c",
        "forecast_dewpoint_c",
        "forecast_relative_humidity_pct",
        "forecast_wind_speed_10m_ms",
        "forecast_wind_direction_deg",
        "forecast_pressure_hpa",
        "forecast_cloud_cover_pct",
        "forecast_shortwave_radiation_wm2",
    ]:
        if preferred in result.columns:
            sample_columns.append(
                preferred
            )

    print(
        result[
            sample_columns
        ]
        .head(20)
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

    # ========================================================
    # OUTPUT
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 100)

    if all_core_pass:
        print(
            "FINAL STATUS: "
            "PERFORMANCE_GRADE_FORECAST_ALIGNMENT_READY"
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
        "This layer MUST NOT be treated as the final "
        "retain/withdraw decision-state forecast layer."
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
