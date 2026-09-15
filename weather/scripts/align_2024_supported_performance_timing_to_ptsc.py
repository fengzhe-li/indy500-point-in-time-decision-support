from pathlib import Path
import math
import pandas as pd


TIMING_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported.csv"
)

PTSC_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment_2024_supported.csv"
)

QA_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment_2024_supported_qa.csv"
)

MAX_INTERPOLATION_GAP_MINUTES = 30.0


PREFERRED_ENV_COLUMNS = [
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


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def interpolate_value(
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

    total_seconds = (
        t1 - t0
    ).total_seconds()

    if total_seconds <= 0:
        return math.nan

    fraction = (
        target_time - t0
    ).total_seconds() / total_seconds

    return (
        float(v0)
        + fraction
        * (
            float(v1)
            - float(v0)
        )
    )


def align_one_time(
    ptsc,
    target_time,
    env_columns,
):
    result = {
        "ptsc_alignment_status": None,
        "ptsc_before_utc": None,
        "ptsc_after_utc": None,
        "ptsc_gap_minutes": math.nan,
    }

    for col in env_columns:
        result[f"ptsc_{col}"] = math.nan

    if pd.isna(target_time):
        result[
            "ptsc_alignment_status"
        ] = "NO_TARGET_TIME"

        return result

    g = ptsc.sort_values(
        "_utc"
    ).reset_index(drop=True)

    before = g[
        g["_utc"] <= target_time
    ]

    after = g[
        g["_utc"] >= target_time
    ]

    if before.empty or after.empty:
        result[
            "ptsc_alignment_status"
        ] = "OUTSIDE_PTSC_COVERAGE"

        return result

    b = before.iloc[-1]
    a = after.iloc[0]

    result[
        "ptsc_before_utc"
    ] = b["_utc"].isoformat()

    result[
        "ptsc_after_utc"
    ] = a["_utc"].isoformat()

    gap_minutes = (
        a["_utc"] - b["_utc"]
    ).total_seconds() / 60.0

    result[
        "ptsc_gap_minutes"
    ] = gap_minutes

    if b["_utc"] == a["_utc"]:

        result[
            "ptsc_alignment_status"
        ] = "EXACT_PTSC_OBSERVATION"

        for col in env_columns:
            result[
                f"ptsc_{col}"
            ] = b[col]

        return result

    if (
        gap_minutes
        > MAX_INTERPOLATION_GAP_MINUTES
    ):

        result[
            "ptsc_alignment_status"
        ] = "PTSC_GAP_TOO_LARGE"

        return result

    result[
        "ptsc_alignment_status"
    ] = "LINEAR_INTERPOLATION"

    for col in env_columns:
        result[
            f"ptsc_{col}"
        ] = interpolate_value(
            b,
            a,
            target_time,
            col,
        )

    return result


def main():

    if not TIMING_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {TIMING_FILE}"
        )

    if not PTSC_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {PTSC_FILE}"
        )

    timing = pd.read_csv(
        TIMING_FILE
    )

    ptsc = pd.read_csv(
        PTSC_FILE
    )

    if len(timing) != 7:
        raise RuntimeError(
            f"Expected 7 timing rows, got {len(timing)}"
        )

    timing["_target_utc"] = parse_utc(
        timing[
            "mapped_capture_time_utc"
        ]
    )

    if timing[
        "_target_utc"
    ].isna().any():
        raise RuntimeError(
            "Unparseable mapped_capture_time_utc found."
        )

    ptsc = ptsc[
        ptsc["year"] == 2024
    ].copy()

    ptsc["_utc"] = parse_utc(
        ptsc["utc_datetime"]
    )

    if ptsc.empty:
        raise RuntimeError(
            "No 2024 PTSC rows found."
        )

    if ptsc[
        "_utc"
    ].isna().any():
        raise RuntimeError(
            "Unparseable PTSC UTC timestamp found."
        )

    env_columns = [
        col
        for col in PREFERRED_ENV_COLUMNS
        if col in ptsc.columns
    ]

    if "track_c" not in env_columns:
        raise RuntimeError(
            "PTSC track_c column not found."
        )

    rows = []

    for _, row in timing.iterrows():

        aligned = align_one_time(
            ptsc,
            row["_target_utc"],
            env_columns,
        )

        out = {
            "attempt_id":
                row["attempt_id"],
            "session_id":
                row["session_id"],
            "year":
                2024,
            "car_number":
                row["car_number"],
            "driver_name":
                row["driver_name"],
            "car_attempt_index":
                row.get(
                    "car_attempt_index"
                ),
            "mapped_capture_event_id":
                row[
                    "mapped_capture_event_id"
                ],
            "mapped_capture_time_utc":
                row[
                    "mapped_capture_time_utc"
                ],
            "timing_class":
                row[
                    "timing_class"
                ],
            "timing_basis":
                row[
                    "timing_basis"
                ],
            "mapping_support":
                row[
                    "mapping_support"
                ],
            "environment_time_semantic":
                (
                    "RECORDER_CAPTURE_AS_"
                    "PERFORMANCE_GRADE_APPROXIMATION"
                ),
            "performance_alignment_usable":
                True,
            "chronology_usable":
                False,
            "queue_replay_usable":
                False,
            "max_interpolation_gap_minutes":
                MAX_INTERPOLATION_GAP_MINUTES,
        }

        out.update(
            aligned
        )

        rows.append(
            out
        )

    result = pd.DataFrame(
        rows
    )

    if len(result) != 7:
        raise RuntimeError(
            "Unexpected output row count."
        )

    if result[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in output."
        )

    usable_mask = result[
        "ptsc_alignment_status"
    ].isin(
        [
            "EXACT_PTSC_OBSERVATION",
            "LINEAR_INTERPOLATION",
        ]
    )

    qa = pd.DataFrame(
        [
            {
                "metric":
                    "input_timing_rows",
                "value":
                    len(result),
            },
            {
                "metric":
                    "environment_aligned_rows",
                "value":
                    int(
                        usable_mask.sum()
                    ),
            },
            {
                "metric":
                    "track_c_nonnull_rows",
                "value":
                    int(
                        result[
                            "ptsc_track_c"
                        ].notna().sum()
                    ),
            },
            {
                "metric":
                    "outside_ptsc_coverage_rows",
                "value":
                    int(
                        (
                            result[
                                "ptsc_alignment_status"
                            ]
                            == "OUTSIDE_PTSC_COVERAGE"
                        ).sum()
                    ),
            },
            {
                "metric":
                    "gap_too_large_rows",
                "value":
                    int(
                        (
                            result[
                                "ptsc_alignment_status"
                            ]
                            == "PTSC_GAP_TOO_LARGE"
                        ).sum()
                    ),
            },
        ]
    )

    result = result.sort_values(
        "mapped_capture_time_utc"
    ).reset_index(
        drop=True
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

    print()
    print("=" * 90)
    print(
        "2024 SUPPORTED PERFORMANCE-GRADE "
        "TIMING TO PTSC ALIGNMENT"
    )
    print("=" * 90)

    print()
    print(
        "Input timing rows:",
        len(result)
    )

    print()
    print("ALIGNMENT STATUS COUNTS")
    print("-" * 40)

    print(
        result[
            "ptsc_alignment_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print("ALIGNED ROWS")
    print("-" * 40)

    display_cols = [
        "car_number",
        "driver_name",
        "car_attempt_index",
        "mapped_capture_time_utc",
        "timing_class",
        "ptsc_alignment_status",
        "ptsc_gap_minutes",
        "ptsc_track_c",
    ]

    if "ptsc_ambient_c" in result.columns:
        display_cols.append(
            "ptsc_ambient_c"
        )

    if "ptsc_humidity" in result.columns:
        display_cols.append(
            "ptsc_humidity"
        )

    print(
        result[
            display_cols
        ].to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 40)

    print(
        qa.to_string(
            index=False
        )
    )

    print()
    print("SEMANTIC POLICY")
    print("-" * 40)

    print(
        "Recorder capture remains an approximate "
        "performance-alignment timestamp."
    )

    print(
        "It is NOT treated as exact timed-run start."
    )

    print(
        "Existing chronology-derived 2024 "
        "environment rows are NOT overwritten."
    )

    print(
        "PTSC interpolation rejected when "
        f"gap > "
        f"{MAX_INTERPOLATION_GAP_MINUTES:.0f} minutes."
    )

    print()
    print("=" * 90)
    print("OUTPUT")
    print("=" * 90)

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )


if __name__ == "__main__":
    main()
