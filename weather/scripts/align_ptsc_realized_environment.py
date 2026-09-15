from pathlib import Path
import math
import pandas as pd


PTSC_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

CONSTRAINTS_FILE = Path(
    "data/canonical/v1/chronology_constraints.csv"
)

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "ptsc_attempt_realized_environment_alignment.csv"
)

QA_FILE = Path(
    "weather/output/"
    "ptsc_attempt_realized_environment_alignment_qa.csv"
)


MAX_INTERPOLATION_GAP_MINUTES = 30.0


NUMERIC_ENV_COLUMNS = [
    "ambient_c",
    "track_c",
    "humidity",
    "wind",
    "pressure",
    "sensor_1_f",
    "sensor_2_f",
    "sensor_3_f",
    "sensor_4_f",
    "sensor_avg_f",
]


def parse_utc_series(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def minutes_between(a, b):
    return abs(
        (b - a).total_seconds()
    ) / 60.0


def interpolate_numeric(
    before_row,
    after_row,
    target_time,
    column,
):
    v0 = before_row[column]
    v1 = after_row[column]

    if pd.isna(v0) or pd.isna(v1):
        return math.nan

    t0 = before_row["_utc"]
    t1 = after_row["_utc"]

    total = (
        t1 - t0
    ).total_seconds()

    if total <= 0:
        return math.nan

    fraction = (
        target_time - t0
    ).total_seconds() / total

    return float(v0) + fraction * (
        float(v1) - float(v0)
    )


def interpolate_ptsc_at_time(
    ptsc_year,
    target_time,
):
    """
    Conservative linear interpolation.

    Returns:
      status
      bracket timestamps
      gap minutes
      interpolated environment
    """

    result = {
        "interp_status": None,
        "ptsc_before_utc": None,
        "ptsc_after_utc": None,
        "ptsc_gap_minutes": math.nan,
    }

    for col in NUMERIC_ENV_COLUMNS:
        result[col] = math.nan

    if pd.isna(target_time):
        result["interp_status"] = (
            "NO_TARGET_TIME"
        )
        return result

    g = ptsc_year.sort_values(
        "_utc"
    ).reset_index(drop=True)

    before = g[
        g["_utc"] <= target_time
    ]

    after = g[
        g["_utc"] >= target_time
    ]

    if len(before) == 0 or len(after) == 0:
        result["interp_status"] = (
            "OUTSIDE_PTSC_COVERAGE"
        )
        return result

    b = before.iloc[-1]
    a = after.iloc[0]

    result["ptsc_before_utc"] = (
        b["_utc"].isoformat()
    )

    result["ptsc_after_utc"] = (
        a["_utc"].isoformat()
    )

    gap = minutes_between(
        b["_utc"],
        a["_utc"],
    )

    result["ptsc_gap_minutes"] = gap

    # Exact PTSC observation
    if b["_utc"] == a["_utc"]:
        result["interp_status"] = (
            "EXACT_PTSC_OBSERVATION"
        )

        for col in NUMERIC_ENV_COLUMNS:
            result[col] = b[col]

        return result

    # Do not interpolate over large gaps
    if gap > MAX_INTERPOLATION_GAP_MINUTES:
        result["interp_status"] = (
            "PTSC_GAP_TOO_LARGE"
        )
        return result

    result["interp_status"] = (
        "LINEAR_INTERPOLATION"
    )

    for col in NUMERIC_ENV_COLUMNS:
        result[col] = interpolate_numeric(
            b,
            a,
            target_time,
            col,
        )

    return result


def midpoint_time(lower, upper):
    if pd.isna(lower) or pd.isna(upper):
        return pd.NaT

    return lower + (
        upper - lower
    ) / 2


def classify_alignment(row):
    """
    Returns:
      alignment_class
      target_time_lower
      target_time_upper
      target_time_midpoint
      reason
    """

    quality = row["event_time_quality"]
    anchor_type = row["anchor_event_type"]

    start_lower = row[
        "_timed_run_start_lower"
    ]

    start_upper = row[
        "_timed_run_start_upper"
    ]

    end_lower = row[
        "_timed_run_end_lower"
    ]

    end_upper = row[
        "_timed_run_end_upper"
    ]

    anchor_lower = row[
        "_anchor_time_lower"
    ]

    anchor_upper = row[
        "_anchor_time_upper"
    ]

    anchor_time = row[
        "_anchor_time"
    ]

    # ---------------------------------
    # Tier A:
    # true timed-run interval available
    # ---------------------------------

    if (
        pd.notna(start_lower)
        and pd.notna(start_upper)
        and pd.notna(end_lower)
        and pd.notna(end_upper)
    ):
        run_mid_lower = midpoint_time(
            start_lower,
            end_lower,
        )

        run_mid_upper = midpoint_time(
            start_upper,
            end_upper,
        )

        target_mid = midpoint_time(
            run_mid_lower,
            run_mid_upper,
        )

        return {
            "alignment_class":
                "RUN_INTERVAL_ALIGNMENT",
            "target_time_lower_utc":
                run_mid_lower,
            "target_time_upper_utc":
                run_mid_upper,
            "target_time_midpoint_utc":
                target_mid,
            "alignment_reason":
                "VALID_TIMED_RUN_INTERVAL",
        }

    # ---------------------------------
    # Tier B:
    # occurrence window only
    # ---------------------------------

    if (
        quality == "BOUNDED_INTERVAL"
        and anchor_type
        == "ATTEMPT_OCCURRENCE"
        and pd.notna(anchor_lower)
        and pd.notna(anchor_upper)
    ):
        return {
            "alignment_class":
                "OCCURRENCE_WINDOW_ALIGNMENT",
            "target_time_lower_utc":
                anchor_lower,
            "target_time_upper_utc":
                anchor_upper,
            "target_time_midpoint_utc":
                midpoint_time(
                    anchor_lower,
                    anchor_upper,
                ),
            "alignment_reason":
                "ATTEMPT_OCCURRENCE_WINDOW_ONLY",
        }

    # ---------------------------------
    # Explicit exclusions
    # ---------------------------------

    if quality == "ORDERING_ONLY":
        return {
            "alignment_class":
                "NOT_ALIGNABLE",
            "target_time_lower_utc":
                pd.NaT,
            "target_time_upper_utc":
                pd.NaT,
            "target_time_midpoint_utc":
                pd.NaT,
            "alignment_reason":
                "ORDERING_ONLY_NO_EVENT_TIME",
        }

    if anchor_type == "TRACK_ENTRY":
        return {
            "alignment_class":
                "NOT_ALIGNABLE",
            "target_time_lower_utc":
                pd.NaT,
            "target_time_upper_utc":
                pd.NaT,
            "target_time_midpoint_utc":
                pd.NaT,
            "alignment_reason":
                "TRACK_ENTRY_NOT_TIMED_RUN_START",
        }

    if anchor_type == "CRASH":
        return {
            "alignment_class":
                "NOT_ALIGNABLE",
            "target_time_lower_utc":
                pd.NaT,
            "target_time_upper_utc":
                pd.NaT,
            "target_time_midpoint_utc":
                pd.NaT,
            "alignment_reason":
                "CRASH_TIME_NOT_TIMED_RUN_START",
        }

    if anchor_type == "RESULT_POSTED":
        return {
            "alignment_class":
                "NOT_ALIGNABLE",
            "target_time_lower_utc":
                pd.NaT,
            "target_time_upper_utc":
                pd.NaT,
            "target_time_midpoint_utc":
                pd.NaT,
            "alignment_reason":
                "RESULT_POSTED_NOT_TIMED_RUN_ENDPOINT",
        }

    if anchor_type == "INITIAL_ORDER":
        return {
            "alignment_class":
                "NOT_ALIGNABLE",
            "target_time_lower_utc":
                pd.NaT,
            "target_time_upper_utc":
                pd.NaT,
            "target_time_midpoint_utc":
                pd.NaT,
            "alignment_reason":
                "INITIAL_ORDER_CAPTURE_NOT_TIMED_RUN_START",
        }

    if (
        quality == "APPROXIMATE_OBSERVED"
        and anchor_type
        == "ATTEMPT_OCCURRENCE"
    ):
        return {
            "alignment_class":
                "OCCURRENCE_POINT_APPROXIMATION",
            "target_time_lower_utc":
                anchor_time,
            "target_time_upper_utc":
                anchor_time,
            "target_time_midpoint_utc":
                anchor_time,
            "alignment_reason":
                "ATTEMPT_OCCURRENCE_MINUTE_ONLY",
        }

    return {
        "alignment_class":
            "NOT_ALIGNABLE",
        "target_time_lower_utc":
            pd.NaT,
        "target_time_upper_utc":
            pd.NaT,
        "target_time_midpoint_utc":
            pd.NaT,
        "alignment_reason":
            "NO_ALLOWED_TIME_SEMANTIC",
    }


def main():

    for file in [
        PTSC_FILE,
        CONSTRAINTS_FILE,
        ATTEMPTS_FILE,
    ]:
        if not file.exists():
            raise FileNotFoundError(
                f"Missing file: {file}"
            )

    ptsc = pd.read_csv(
        PTSC_FILE
    )

    constraints = pd.read_csv(
        CONSTRAINTS_FILE
    )

    attempts = pd.read_csv(
        ATTEMPTS_FILE
    )

    # ---------------------------------
    # PTSC prep
    # ---------------------------------

    ptsc["_utc"] = parse_utc_series(
        ptsc["utc_datetime"]
    )

    if ptsc["_utc"].isna().any():
        raise RuntimeError(
            "PTSC contains unparseable UTC timestamps."
        )

    # ---------------------------------
    # Constraint prep
    # ---------------------------------

    constraints[
        "_anchor_time"
    ] = parse_utc_series(
        constraints[
            "anchor_time_utc"
        ]
    )

    constraints[
        "_anchor_time_lower"
    ] = parse_utc_series(
        constraints[
            "anchor_time_lower_utc"
        ]
    )

    constraints[
        "_anchor_time_upper"
    ] = parse_utc_series(
        constraints[
            "anchor_time_upper_utc"
        ]
    )

    constraints[
        "_timed_run_start_lower"
    ] = parse_utc_series(
        constraints[
            "timed_run_start_lower_utc"
        ]
    )

    constraints[
        "_timed_run_start_upper"
    ] = parse_utc_series(
        constraints[
            "timed_run_start_upper_utc"
        ]
    )

    constraints[
        "_timed_run_end_lower"
    ] = parse_utc_series(
        constraints[
            "timed_run_end_lower_utc"
        ]
    )

    constraints[
        "_timed_run_end_upper"
    ] = parse_utc_series(
        constraints[
            "timed_run_end_upper_utc"
        ]
    )

    # ---------------------------------
    # Only non-UNKNOWN chronology rows
    # ---------------------------------

    selected = constraints[
        constraints[
            "event_time_quality"
        ] != "UNKNOWN"
    ].copy()

    # Join attempt metadata
    attempt_cols = [
        "attempt_id",
        "session_id",
        "entry_key",
        "attempt_key",
        "four_lap_average_speed_mph",
        "four_lap_total_seconds",
    ]

    attempt_cols = [
        c for c in attempt_cols
        if c in attempts.columns
    ]

    selected = selected.merge(
        attempts[attempt_cols],
        on="attempt_id",
        how="left",
        suffixes=(
            "",
            "_attempt",
        ),
    )

    rows = []

    for _, row in selected.iterrows():

        classification = (
            classify_alignment(row)
        )

        target_mid = classification[
            "target_time_midpoint_utc"
        ]

        # infer year from target,
        # or from known 2024 constraints
        year = 2024

        ptsc_year = ptsc[
            ptsc["year"] == year
        ].copy()

        env = interpolate_ptsc_at_time(
            ptsc_year,
            target_mid,
        )

        out = {
            "attempt_id":
                row["attempt_id"],
            "session_id":
                row.get(
                    "session_id",
                    None,
                ),
            "car_number":
                row.get(
                    "car_number",
                    None,
                ),
            "driver_name":
                row.get(
                    "driver_name",
                    None,
                ),
            "car_attempt_index":
                row.get(
                    "car_attempt_index",
                    None,
                ),
            "result_status":
                row.get(
                    "result_status",
                    None,
                ),
            "event_time_quality":
                row.get(
                    "event_time_quality",
                    None,
                ),
            "value_classification":
                row.get(
                    "value_classification",
                    None,
                ),
            "anchor_event_type":
                row.get(
                    "anchor_event_type",
                    None,
                ),
            "alignment_class":
                classification[
                    "alignment_class"
                ],
            "alignment_reason":
                classification[
                    "alignment_reason"
                ],
            "target_time_lower_utc":
                classification[
                    "target_time_lower_utc"
                ],
            "target_time_upper_utc":
                classification[
                    "target_time_upper_utc"
                ],
            "target_time_midpoint_utc":
                classification[
                    "target_time_midpoint_utc"
                ],
            "ptsc_interp_status":
                env[
                    "interp_status"
                ],
            "ptsc_before_utc":
                env[
                    "ptsc_before_utc"
                ],
            "ptsc_after_utc":
                env[
                    "ptsc_after_utc"
                ],
            "ptsc_gap_minutes":
                env[
                    "ptsc_gap_minutes"
                ],
        }

        for col in NUMERIC_ENV_COLUMNS:
            out[
                f"ptsc_{col}"
            ] = env[col]

        rows.append(out)

    result = pd.DataFrame(rows)

    # ---------------------------------
    # QA
    # ---------------------------------

    qa_rows = []

    for cls, g in result.groupby(
        "alignment_class",
        dropna=False,
    ):
        qa_rows.append(
            {
                "check":
                    "ALIGNMENT_CLASS_COUNT",
                "category":
                    cls,
                "value":
                    len(g),
            }
        )

    for status, g in result.groupby(
        "ptsc_interp_status",
        dropna=False,
    ):
        qa_rows.append(
            {
                "check":
                    "PTSC_INTERP_STATUS_COUNT",
                "category":
                    status,
                "value":
                    len(g),
            }
        )

    qa = pd.DataFrame(
        qa_rows
    )

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

    # ---------------------------------
    # Print summary
    # ---------------------------------

    print()
    print("=" * 80)
    print(
        "PTSC REALIZED ENVIRONMENT "
        "ALIGNMENT"
    )
    print("=" * 80)

    print()
    print(
        "Input non-UNKNOWN "
        f"constraints: {len(selected)}"
    )

    print()
    print("ALIGNMENT CLASS COUNTS")
    print("-" * 40)

    print(
        result[
            "alignment_class"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print("PTSC INTERPOLATION STATUS")
    print("-" * 40)

    print(
        result[
            "ptsc_interp_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "ALIGNABLE ROWS"
    )
    print("-" * 40)

    alignable = result[
        result[
            "alignment_class"
        ].isin(
            [
                "RUN_INTERVAL_ALIGNMENT",
                "OCCURRENCE_WINDOW_ALIGNMENT",
                "OCCURRENCE_POINT_APPROXIMATION",
            ]
        )
    ]

    show_cols = [
        "car_number",
        "driver_name",
        "car_attempt_index",
        "alignment_class",
        "alignment_reason",
        "target_time_lower_utc",
        "target_time_upper_utc",
        "target_time_midpoint_utc",
        "ptsc_interp_status",
        "ptsc_gap_minutes",
        "ptsc_track_c",
        "ptsc_ambient_c",
        "ptsc_humidity",
    ]

    print(
        alignable[
            show_cols
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )


if __name__ == "__main__":
    main()